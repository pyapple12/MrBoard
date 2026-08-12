# OpenCode Go 配额监控模块：凭据探测 / dashboard HTML 抓取 / 节流缓存

import html
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config.static.static_config import get_static_config
from modules import browser_creds, credential_store
from utils.file_utils import get_project_root, write_json
from utils.logger import get_logger
from utils.retry import retry_call

logger = get_logger(__name__)

DASHBOARD_URL_TEMPLATE = "https://opencode.ai/workspace/{workspace_id}/go"
DASHBOARD_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
# 静态配置解包（S8：参数外置 base.json）
_SC = get_static_config()
MIN_FETCH_INTERVAL = int(_SC.base["min_fetch_interval"])
RETRY_COUNT = int(_SC.base["retry_count"])
RETRY_DELAY = float(_SC.base["retry_delay"])
HTTP_TIMEOUT = float(_SC.base["http_timeout"])  # L13：网络请求超时统一（base.json）
WORKSPACE_ID_FIELDS = ("workspaceId", "workspaceID", "workspace_id")
AUTH_COOKIE_FIELDS = ("authCookie", "auth_cookie", "cookie")
# dashboard 凭据文件（P2：集中项目内 data/credentials，不使用用户目录）
CREDENTIALS_FILE = get_project_root() / _SC.base["credentials_dir"] / "opencode-go.json"

# 模块级缓存：上次成功结果与时间戳（网络失败兜底用，z.plan 第四章缓存兜底策略）
_last_quota: "GoQuotaInfo | None" = None
_last_success_at: float = 0.0


def save_dashboard_credentials(workspace_id: str, auth_cookie: str) -> None:
    # 保存 dashboard 凭据到配置文件（DPAPI 加密写入，P4；win32crypt 缺失拒绝明文写入）
    write_json(
        CREDENTIALS_FILE,
        {
            credential_store.ENCRYPTED_KEY: credential_store.encrypt_credentials(
                workspace_id, auth_cookie
            )
        },
    )


@dataclass
class GoQuotaWindow:
    # 单个配额窗口：已用百分比 + 重置时间（now + resetInSec）

    usage_percent: float
    reset_in_sec: int
    reset_date: datetime


@dataclass
class DashboardCredentials:
    # dashboard 凭据候选：workspace_id + auth_cookie + 来源标注

    workspace_id: str
    auth_cookie: str
    source: str


@dataclass
class GoQuotaInfo:
    # Go 配额总览：三窗口 + 最紧窗口汇总 + 元信息（含缓存/错误状态）

    five_hour: GoQuotaWindow | None = None
    weekly: GoQuotaWindow | None = None
    monthly: GoQuotaWindow | None = None
    overall_used_percent: int = 0
    remaining_percent: int = 0
    credential_source: str = ""
    fetched_at: datetime | None = None
    is_cached: bool = False
    error: str | None = None
    # 错误阶段（UI 按阶段决定处理方式，如 CDP 引导仅对凭据类错误有效）：
    #   no_dashboard_creds / auth / network / provider / decoding
    error_stage: str | None = None


class GoQuotaError(Exception):
    # Go 配额业务错误：code 分类（auth/network/decoding/provider），message 为中文提示

    def __init__(self, code: str, message: str) -> None:
        # 初始化错误分类与提示，供 UI 按分类展示
        super().__init__(message)
        self.code = code
        self.message = message


def find_dashboard_credentials() -> list[DashboardCredentials]:
    # 收集 dashboard 凭据候选：环境变量 → 配置文件多路径；去重键 workspace_id::auth_cookie
    candidates: list[DashboardCredentials] = []
    seen: set[str] = set()

    def add(workspace_id: str, auth_cookie: str, source: str) -> None:
        # 按去重键追加一个候选（已有则跳过）
        workspace_id = workspace_id.strip()
        auth_cookie = auth_cookie.strip()
        if not workspace_id or not auth_cookie:
            return
        key = f"{workspace_id}::{auth_cookie}"
        if key in seen:
            return
        seen.add(key)
        candidates.append(DashboardCredentials(workspace_id, auth_cookie, source))

    env_workspace = os.environ.get("OPENCODE_GO_WORKSPACE_ID", "")
    env_cookie = os.environ.get("OPENCODE_GO_AUTH_COOKIE", "")
    if env_workspace and env_cookie:
        add(env_workspace, env_cookie, "Environment")
    for path in _dashboard_config_paths():
        raw = credential_store.read_credentials_file(path)
        if raw is None:
            continue
        add(
            _first_value(raw, WORKSPACE_ID_FIELDS),
            _first_value(raw, AUTH_COOKIE_FIELDS),
            str(path),
        )
    # 浏览器凭据（零配置体验，S6.1）：Chrome/Edge 登录 opencode.ai 后自动探测
    for cred in browser_creds.find_browser_credentials():
        add(cred.workspace_id, cred.auth_cookie, f"浏览器:{cred.source}")
    return candidates


def _dashboard_config_paths() -> list[Path]:
    # 配置文件候选路径：$OPENCODE_GO_CONFIG_FILE → 项目内 data/credentials/opencode-go.json
    # （P2：凭据集中项目目录，不再探测用户目录；P6：不读其他项目配置）
    paths: list[Path] = []
    env_file = os.environ.get("OPENCODE_GO_CONFIG_FILE")
    if env_file:
        paths.append(Path(env_file).expanduser())
    paths.append(CREDENTIALS_FILE)
    return paths


def _first_value(data: dict[str, Any], fields: tuple[str, ...]) -> str:
    # 按字段优先级取第一个非空字符串值（key 兼容集合）
    for field in fields:
        value = data.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def fetch_dashboard_usage(
    credentials: DashboardCredentials,
) -> dict[str, GoQuotaWindow | None]:
    # 抓取 dashboard HTML 并解析三窗口；HTTP 错误按分类抛 GoQuotaError
    url = DASHBOARD_URL_TEMPLATE.format(workspace_id=credentials.workspace_id)
    headers = {
        "Accept": DASHBOARD_ACCEPT,
        "Cookie": _cookie_header(credentials.auth_cookie),
        "User-Agent": CHROME_UA,
    }
    try:
        body = retry_call(
            _http_get,
            url,
            headers=headers,
            retries=RETRY_COUNT,
            exceptions=(urllib.error.URLError, TimeoutError),
            delay=RETRY_DELAY,
        )
    except GoQuotaError:
        # _http_get 的 401/403 分类错误经 retry_call 传播至此，须原样放行
        # （否则被 except Exception 捕获包装成 network，破坏 auth 分类）
        raise
    except urllib.error.HTTPError as exc:
        # 重试耗尽后分类：401/403 为凭据问题，其余为 provider 错误
        if exc.code in (401, 403):
            raise GoQuotaError(
                "auth", f"OpenCode Go 凭据无效（HTTP {exc.code}）"
            ) from exc
        raise GoQuotaError("provider", f"HTTP {exc.code}") from exc
    except Exception as exc:
        raise GoQuotaError("network", f"请求 dashboard 失败：{exc}") from exc
    html = body.decode("utf-8", errors="replace")
    if "OpenAuth" in html:
        # 未登录会话被重定向到 OpenAuth 登录页：凭据失效，按 auth 分类
        # （引导卡片据此显示，用户可一键重新获取）
        raise GoQuotaError(
            "auth", "OpenCode Go 登录会话已失效，请点击一键自动获取重新登录"
        )
    usage, missing = parse_dashboard_html(html, datetime.now(timezone.utc))
    if missing:
        logger.warning("dashboard 缺失窗口：%s", "、".join(missing))
    return usage


def _cookie_header(auth_cookie: str) -> str:
    # 构造 Cookie 头：无 auth= 前缀时自动补全
    if auth_cookie.startswith("auth="):
        return auth_cookie
    return f"auth={auth_cookie}"


def parse_dashboard_html(
    raw_html: str, now: datetime
) -> tuple[dict[str, GoQuotaWindow | None], list[str]]:
    # 纯函数解析 dashboard HTML：返回三窗口 dict 与缺失窗口名列表（全部缺失抛 GoQuotaError）
    text = _normalize_html(raw_html)
    usage: dict[str, GoQuotaWindow | None] = {}
    for name in ("rollingUsage", "weeklyUsage", "monthlyUsage"):
        usage[name] = _parse_window(name, text, now)
    missing = [name for name, window in usage.items() if window is None]
    if len(missing) == len(usage):
        raise GoQuotaError(
            "decoding",
            "OpenCode Go dashboard 页面结构可能已变更，未解析到任何使用窗口，请反馈此问题",
        )
    return usage, missing


def _normalize_html(raw_html: str) -> str:
    # HTML 实体反转义：html.unescape 处理 &quot;/&#34;/&#x27;/&amp; 等，" 手动替换
    text = html.unescape(raw_html)
    return text.replace("\\u0022", '"')


def _parse_window(field_name: str, text: str, now: datetime) -> GoQuotaWindow | None:
    # 解析单个窗口对象：抓 {field: {...}} 体后提取 usagePercent 与 resetInSec
    body = _capture_object_body(field_name, text)
    if body is None:
        return None
    percent = _capture_number("usagePercent", body)
    reset_seconds_raw = _capture_number("resetInSec", body)
    if percent is None or reset_seconds_raw is None:
        return None
    reset_seconds = max(0, int(round(reset_seconds_raw)))
    return GoQuotaWindow(
        usage_percent=percent,
        reset_in_sec=reset_seconds,
        reset_date=_add_seconds(now, reset_seconds),
    )


def _add_seconds(now: datetime, seconds: int) -> datetime:
    # datetime 加秒数（naive/aware 的 + 均保持原时区语义）
    return now + timedelta(seconds=seconds)


def _capture_object_body(field_name: str, text: str) -> str | None:
    # 正则抓取字段对象体：兼容 {"field": {...}} 与 "field":$R[12]={...} 两种形态
    pattern = (
        rf"""["']?{re.escape(field_name)}["']?\s*:\s*"""
        rf"""(?:\$R\[\d+\]\s*=\s*)?\{{(?P<body>[^{{}}]*)\}}"""
    )
    match = re.search(pattern, text, re.DOTALL)
    return match.group("body") if match else None


def _capture_number(field_name: str, text: str) -> float | None:
    # 正则提取数字字段：兼容 "usagePercent":23 与 usagePercent:"23" 形态
    pattern = rf"""["']?{re.escape(field_name)}["']?\s*:\s*"?(-?\d+(?:\.\d+)?)"?"""
    match = re.search(pattern, text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _http_get(
    url: str, headers: dict[str, str] | None = None, timeout: float = HTTP_TIMEOUT
) -> bytes:
    # 发送 GET 请求返回响应体；401/403 转 auth 分类，网络/其他 HTTP 异常原样抛出（交 retry_call 重试）
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            # urlopen 对非 2xx 直接抛 HTTPError（3xx 自动跟随），能返回必为 2xx
            return response.read()
    except urllib.error.HTTPError as exc:
        # 凭据问题不可重试 → auth 分类；其余（5xx/429）抛原异常由 retry_call 重试
        if exc.code in (401, 403):
            raise GoQuotaError(
                "auth", f"OpenCode Go 凭据无效（HTTP {exc.code}）"
            ) from exc
        raise


def _throttled_cache(force: bool) -> GoQuotaInfo | None:
    # 节流检查：非强制且距上次成功不足 60s 时返回标注后的缓存（避免打爆接口）
    if (
        not force
        and _last_quota is not None
        and time.time() - _last_success_at < MIN_FETCH_INTERVAL
    ):
        return _mark_cached(
            _last_quota, f"距上次刷新不足 {MIN_FETCH_INTERVAL} 秒，显示缓存数据"
        )
    return None


def _fetch_usage_with_fallback(
    credentials: list[DashboardCredentials],
) -> tuple[dict[str, GoQuotaWindow | None] | None, str, str, str]:
    # 逐个尝试凭据候选拉取 dashboard 用量；返回 (usage, used_source, last_stage, last_error)
    last_error = ""
    last_stage = "network"
    for credentials_item in credentials:
        try:
            usage = fetch_dashboard_usage(credentials_item)
            return usage, credentials_item.source, last_stage, last_error
        except GoQuotaError as exc:
            last_error = exc.message
            last_stage = (
                exc.code if exc.code in ("auth", "network", "provider") else "provider"
            )
            logger.warning(
                "dashboard 凭据 %s 失败：%s", credentials_item.source, exc.message
            )
    return None, "", last_stage, last_error


def _build_info(
    now: datetime,
    usage: dict[str, GoQuotaWindow | None],
    used_source: str,
) -> GoQuotaInfo:
    # 组装成功配额信息并更新缓存（overall = max 三窗口）
    global _last_quota, _last_success_at
    windows = [
        window
        for window in (
            usage.get("rollingUsage"),
            usage.get("weeklyUsage"),
            usage.get("monthlyUsage"),
        )
        if window is not None
    ]
    overall = max((w.usage_percent for w in windows), default=0.0)
    info = GoQuotaInfo(
        five_hour=usage.get("rollingUsage"),
        weekly=usage.get("weeklyUsage"),
        monthly=usage.get("monthlyUsage"),
        overall_used_percent=int(round(overall)),
        remaining_percent=max(0, 100 - int(round(overall))),
        credential_source=used_source,
        fetched_at=now,
    )
    _last_quota = info
    _last_success_at = time.time()
    return info


def fetch_go_quota(force: bool = False) -> GoQuotaInfo:
    # 主流程：节流 → dashboard 凭据 → 三窗口；缓存兜底 + 分类错误（P3：无 key 链路）
    global _last_quota, _last_success_at
    now = datetime.now(timezone.utc)
    cached = _throttled_cache(force)
    if cached is not None:
        return cached

    credentials = find_dashboard_credentials()
    if not credentials:
        return _fallback(
            now,
            "未找到 dashboard 凭据（设置 OPENCODE_GO_WORKSPACE_ID/OPENCODE_GO_AUTH_COOKIE"
            " 或创建 opencode-go.json 配置文件）",
            stage="no_dashboard_creds",
        )

    usage, used_source, last_stage, last_error = _fetch_usage_with_fallback(credentials)
    if usage is None:
        return _fallback(
            now,
            f"dashboard 拉取失败：{last_error or '未知错误'}",
            stage=last_stage,
        )
    return _build_info(now, usage, used_source)


def _mark_cached(info: GoQuotaInfo, message: str) -> GoQuotaInfo:
    # 缓存兜底标注：浅拷贝缓存对象再标记（防止污染共享对象，UI 持有旧引用不受影响）
    return replace(info, is_cached=True, error=message)


def _fallback(now: datetime, message: str, stage: str | None = None) -> GoQuotaInfo:
    # 失败兜底：返回上次缓存（标注 is_cached）或空白信息（带 error 提示与阶段）
    global _last_quota
    if _last_quota is not None:
        marked = _mark_cached(_last_quota, message)
        if stage is not None:
            marked.error_stage = stage
        return marked
    return GoQuotaInfo(
        fetched_at=now,
        error=message,
        error_stage=stage,
    )


def main() -> None:
    # CLI 自测入口：打印 Go 配额三窗口与状态（不打印任何凭据）
    info = fetch_go_quota()
    print(f"OpenCode Go 配额（获取时间：{info.fetched_at}）")
    print(f"  dashboard 凭据来源：{info.credential_source or '未找到'}")
    for label, window in (
        ("5 小时", info.five_hour),
        ("每周", info.weekly),
        ("每月", info.monthly),
    ):
        if window:
            print(
                f"  {label}：已用 {window.usage_percent:.0f}%"
                f"，重置于 {window.reset_date.astimezone().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            print(f"  {label}：未获取到")
    print(f"  最紧窗口：{info.overall_used_percent}%（剩余 {info.remaining_percent}%）")
    if info.is_cached:
        print(f"  [缓存数据] {info.error}")
    elif info.error:
        print(f"  [错误] {info.error}")


if __name__ == "__main__":
    main()

# ===== modules/go_quota.py 模块说明 =====
# 模块级常量：
#   DASHBOARD_URL_TEMPLATE / DASHBOARD_ACCEPT / CHROME_UA：dashboard HTML 请求参数
#     （Cookie auth= 自动补前缀，参考 opencode-bar OpenCodeGoProvider.swift）
#   MIN_FETCH_INTERVAL：接口节流 60 秒（z.plan 第四章节流策略）
#   WORKSPACE_ID_FIELDS / AUTH_COOKIE_FIELDS：凭据字段兼容集合
#   CREDENTIALS_FILE：dashboard 凭据文件（项目内 data/credentials/opencode-go.json，
#     P2 定案集中项目内；含凭据严禁入库）
# 模块级变量：_last_quota / _last_success_at——成功结果缓存与时间戳（缓存兜底）
# 类型：
#   GoQuotaWindow：单窗口（usage_percent/reset_in_sec/reset_date）
#   DashboardCredentials：dashboard 凭据候选（含来源标注）
#   GoQuotaInfo：配额总览（三窗口 + 最紧窗口 + 元信息 + is_cached/error 状态）
#   GoQuotaError：分类业务错误（auth/network/decoding/provider），UI 只认 code
# 函数：
#   save_dashboard_credentials()：DPAPI 加密写入凭据（P4：经 credential_store，
#     win32crypt 缺失拒绝明文落盘）
#   find_dashboard_credentials()：环境变量 → 配置文件多路径收集候选，
#     去重键 workspace_id::auth_cookie；key 名兼容集合（workspaceId/workspaceID/
#     workspace_id、authCookie/auth_cookie/cookie）
#   _dashboard_config_paths()：$OPENCODE_GO_CONFIG_FILE → 项目内
#     data/credentials/opencode-go.json（P2：凭据集中项目目录，不探测用户目录；
#     P6：不读其他项目配置）
#   _first_value()：按字段优先级取第一个非空字符串（key 兼容集合）
#   fetch_dashboard_usage()：HTML 抓取 + 解析（HTTP 错误按分类抛 GoQuotaError；
#     401/403 经 _http_get 转 auth 后由 except GoQuotaError 原样放行）
#   _cookie_header()：Cookie 头补 auth= 前缀
#   parse_dashboard_html()：纯函数（可测）：实体反转义 → 逐窗口正则解析 →
#     缺失窗口仅警告、全部缺失抛 decoding 错误
#   _normalize_html()：HTML 实体反转义（含 \u0022 手动替换）
#   _parse_window()：单窗口对象解析（usagePercent/resetInSec → GoQuotaWindow）
#   _add_seconds()：datetime 加秒（naive/aware 保持原时区）
#   _capture_object_body/_capture_number：opencode-bar 正则移植（兼容
#     "field":$R[12]={...} 赋值形态与字符串/数字双形态值）
#   _http_get()：GET 请求（401/403 转 auth 分类；其余异常原样抛交 retry 重试）
#   _throttled_cache(force)：节流检查——非强制且距上次成功不足 60s 返回缓存
#   _fetch_usage_with_fallback()：凭据候选逐个尝试（首成功返回 + 来源标注）
#   _build_info()：组装成功配额信息并更新缓存（overall = max 三窗口）
#   _mark_cached()：缓存兜底标注（浅拷贝防污染）
#   fetch_go_quota(force)：主流程——节流检查 → 凭据候选逐个尝试（首成功返回）→
#     组装 GoQuotaInfo；任一步失败走 _fallback 缓存兜底（P3：无 API key 链路，
#     程序不接触任何 key）
#   _fallback()：失败返回缓存（标注 is_cached + error）或空白信息（带提示）
#   main()：CLI 自测，仅打印展示数据，绝不打印凭据
# 设计理由：错误分类统一（z.plan 第四章）；窗口缺失容忍（dashboard 非公开 API，
#   markup 可能变更）；凭据只在内存流转、日志不打印；P3 删除 API key 链路——
#   程序从任何路径（本地读取或网络外发）都不接触 API key，仅使用 dashboard
#   登录会话凭据（workspaceId + authCookie）
# 异常处理：网络/解析/凭据错误全部分类化；单凭据失败继续尝试下一个候选
# 关联配置：OPENCODE_GO_WORKSPACE_ID/OPENCODE_GO_AUTH_COOKIE/OPENCODE_GO_CONFIG_FILE
#   环境变量；项目内 data/credentials/opencode-go.json 配置文件（含凭据，严禁入库）
