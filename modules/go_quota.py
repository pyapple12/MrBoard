# OpenCode Go 配额监控模块：凭据探测 / key 校验 / dashboard HTML 抓取 / 节流缓存

import html
import json
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
from modules import browser_creds
from utils.file_utils import write_json
from utils.logger import get_logger
from utils.retry import retry_call

logger = get_logger(__name__)

MODELS_URL = "https://opencode.ai/zen/go/v1/models"
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
AUTH_KEY_FIELDS = ("key", "access", "token", "apiKey", "value")
WORKSPACE_ID_FIELDS = ("workspaceId", "workspaceID", "workspace_id")
AUTH_COOKIE_FIELDS = ("authCookie", "auth_cookie", "cookie")
CREDENTIALS_FILE = Path.home() / ".config" / "myboard" / "opencode-go.json"

# 模块级缓存：上次成功结果与时间戳（网络失败兜底用，z.plan 第四章缓存兜底策略）
_last_quota: "GoQuotaInfo | None" = None
_last_success_at: float = 0.0


def save_dashboard_credentials(workspace_id: str, auth_cookie: str) -> None:
    # 保存 dashboard 凭据到配置文件（CDP 一键获取与手动填写共用，key 与探测兼容）
    write_json(
        CREDENTIALS_FILE, {"workspaceId": workspace_id, "authCookie": auth_cookie}
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
    model_count: int | None = None
    auth_source: str = ""
    credential_source: str = ""
    fetched_at: datetime | None = None
    is_cached: bool = False
    error: str | None = None
    # 错误阶段（UI 按阶段决定处理方式，如 CDP 引导仅对凭据类错误有效）：
    #   no_key / no_dashboard_creds / auth / network / provider / decoding
    error_stage: str | None = None


class GoQuotaError(Exception):
    # Go 配额业务错误：code 分类（auth/network/decoding/provider），message 为中文提示

    def __init__(self, code: str, message: str) -> None:
        # 初始化错误分类与提示，供 UI 按分类展示
        super().__init__(message)
        self.code = code
        self.message = message


def find_auth_file() -> Path | None:
    # 多路径探测 auth.json：XDG_DATA_HOME → ~/.local/share/opencode → ~/.config/opencode
    candidates: list[Path] = []
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        candidates.append(Path(xdg_data) / "opencode" / "auth.json")
    home = Path.home()
    candidates.append(home / ".local" / "share" / "opencode" / "auth.json")
    candidates.append(home / ".config" / "opencode" / "auth.json")
    for path in candidates:
        if path.is_file():
            return path
    return None


def read_auth_json(path: Path) -> dict[str, Any] | None:
    # 读取 auth.json（先剥离 jsonc 注释再解析）；解析失败返回 None（宽容降级）
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("读取 auth.json 失败：%s", exc)
        return None
    try:
        data = json.loads(strip_json_comments(text))
    except json.JSONDecodeError as exc:
        logger.warning("解析 auth.json 失败：%s", exc)
        return None
    return data if isinstance(data, dict) else None


def strip_json_comments(text: str) -> str:
    # 状态机剥离 JSONC 注释（// 与 /* */），字符串字面量内的注释保留
    result: list[str] = []
    index = 0
    length = len(text)
    in_string = False
    escape = False
    while index < length:
        char = text[index]
        next_char = text[index + 1] if index + 1 < length else ""
        if in_string:
            result.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            while index < length and text[index] != "\n":
                index += 1
            continue
        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < length and not (
                text[index] == "*" and text[index + 1] == "/"
            ):
                index += 1
            index += 2
            continue
        result.append(char)
        index += 1
    return "".join(result)


def get_opencode_go_key(auth_data: dict[str, Any] | None) -> str | None:
    # 从 auth.json 提取 opencode-go API key：dict 多键兼容或裸字符串；无则返回 None
    if not auth_data:
        return None
    entry = auth_data.get("opencode-go")
    if isinstance(entry, dict):
        for field in AUTH_KEY_FIELDS:
            value = entry.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
    elif isinstance(entry, str) and entry.strip():
        return entry.strip()
    return None


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
        raw = _read_credentials_json(path)
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
    # 配置文件候选路径：$OPENCODE_GO_CONFIG_FILE → XDG_CONFIG_HOME 系列 → ~/.config 系列
    paths: list[Path] = []
    env_file = os.environ.get("OPENCODE_GO_CONFIG_FILE")
    if env_file:
        paths.append(Path(env_file).expanduser())
    home = Path.home()
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        xdg_base = Path(xdg_config)
        for sub in ("myboard", "opencode-bar", "opencode-quota"):
            paths.append(xdg_base / sub / "opencode-go.json")
    for sub in ("myboard", "opencode-bar", "opencode-quota"):
        paths.append(home / ".config" / sub / "opencode-go.json")
    return paths


def _read_credentials_json(path: Path) -> dict[str, Any] | None:
    # 读取凭据 JSON 文件（宽容解析）；文件不存在/损坏返回 None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("读取凭据配置失败 %s：%s", path, exc)
        return None
    return raw if isinstance(raw, dict) else None


def _first_value(data: dict[str, Any], fields: tuple[str, ...]) -> str:
    # 按字段优先级取第一个非空字符串值（key 兼容集合）
    for field in fields:
        value = data.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def fetch_model_count(api_key: str) -> int | None:
    # 校验 API key 并返回可用模型数；请求失败返回 None（不阻断主流程）
    try:
        body = retry_call(
            _http_get,
            MODELS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            retries=RETRY_COUNT,
            exceptions=(urllib.error.URLError, TimeoutError),
            delay=RETRY_DELAY,
        )
    except GoQuotaError:
        raise
    except Exception as exc:
        logger.warning("拉取模型数失败：%s", exc)
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None
    for key in ("data", "models"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, list):
            return len(value)
    if isinstance(data, list):
        return len(data)
    return None


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
    usage, missing = parse_dashboard_html(
        body.decode("utf-8", errors="replace"), datetime.now(timezone.utc)
    )
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
    # datetime 加秒数（兼容 naive/aware，保持原时区语义）
    if now.tzinfo is None:
        return now + timedelta(seconds=seconds)
    return now + timedelta(seconds=seconds)


def _capture_object_body(field_name: str, text: str) -> str | None:
    # 正则抓取字段对象体：兼容 {"field": {...}} 与 "field":$R[12]={...} 两种形态
    pattern = rf"""["']?{re.escape(field_name)}["']?\s*:\s*(?:\$R\[\d+\]\s*=\s*)?\{{(?P<body>[^{{}}]*)\}}"""
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
    url: str, headers: dict[str, str] | None = None, timeout: float = 15.0
) -> bytes:
    # 发送 GET 请求返回响应体；401/403 转 auth 分类，网络/其他 HTTP 异常原样抛出（交 retry_call 重试）
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                raise GoQuotaError("provider", f"HTTP {response.status}")
            return response.read()
    except urllib.error.HTTPError as exc:
        # 凭据问题不可重试 → auth 分类；其余（5xx/429）抛原异常由 retry_call 重试
        if exc.code in (401, 403):
            raise GoQuotaError(
                "auth", f"OpenCode Go 凭据无效（HTTP {exc.code}）"
            ) from exc
        raise


def _throttled_cache(now: datetime, force: bool) -> GoQuotaInfo | None:
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
    model_count: int | None,
    auth_path: Path | None,
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
        model_count=model_count,
        auth_source=str(auth_path) if auth_path else "",
        credential_source=used_source,
        fetched_at=now,
    )
    _last_quota = info
    _last_success_at = time.time()
    return info


def fetch_go_quota(force: bool = False) -> GoQuotaInfo:
    # 主流程：节流 → key → 模型数 → dashboard 凭据 → 三窗口；缓存兜底 + 分类错误
    global _last_quota, _last_success_at
    now = datetime.now(timezone.utc)
    cached = _throttled_cache(now, force)
    if cached is not None:
        return cached

    auth_path = find_auth_file()
    auth_data = read_auth_json(auth_path) if auth_path else None
    api_key = get_opencode_go_key(auth_data)
    if not api_key:
        return _fallback(
            now,
            "未找到 OpenCode Go API key（检查 auth.json 的 opencode-go 条目）",
            auth_path,
            stage="no_key",
        )

    model_count: int | None = None
    try:
        model_count = fetch_model_count(api_key)
    except GoQuotaError as exc:
        return _fallback(
            now,
            exc.message,
            auth_path,
            stage=exc.code if exc.code in ("auth", "network") else "provider",
        )

    credentials = find_dashboard_credentials()
    if not credentials:
        return _fallback(
            now,
            "未找到 dashboard 凭据（设置 OPENCODE_GO_WORKSPACE_ID/OPENCODE_GO_AUTH_COOKIE"
            " 或创建 opencode-go.json 配置文件）",
            auth_path,
            stage="no_dashboard_creds",
        )

    usage, used_source, last_stage, last_error = _fetch_usage_with_fallback(credentials)
    if usage is None:
        return _fallback(
            now,
            f"dashboard 拉取失败：{last_error or '未知错误'}",
            auth_path,
            stage=last_stage,
        )
    return _build_info(now, usage, model_count, auth_path, used_source)
    _last_quota = info
    _last_success_at = time.time()
    return info


def _mark_cached(info: GoQuotaInfo, message: str) -> GoQuotaInfo:
    # 缓存兜底标注：浅拷贝缓存对象再标记（防止污染共享对象，UI 持有旧引用不受影响）
    return replace(info, is_cached=True, error=message)


def _fallback(
    now: datetime, message: str, auth_path: Path | None, stage: str | None = None
) -> GoQuotaInfo:
    # 失败兜底：返回上次缓存（标注 is_cached）或空白信息（带 error 提示与阶段）
    global _last_quota
    if _last_quota is not None:
        marked = _mark_cached(_last_quota, message)
        if stage is not None:
            marked.error_stage = stage
        return marked
    return GoQuotaInfo(
        auth_source=str(auth_path) if auth_path else "",
        fetched_at=now,
        error=message,
        error_stage=stage,
    )


def main() -> None:
    # CLI 自测入口：打印 Go 配额三窗口与状态（不打印任何凭据）
    info = fetch_go_quota()
    print(f"OpenCode Go 配额（获取时间：{info.fetched_at}）")
    print(f"  API key 来源：{info.auth_source or '未找到'}")
    print(f"  dashboard 凭据来源：{info.credential_source or '未找到'}")
    print(f"  模型数：{info.model_count if info.model_count is not None else '未知'}")
    for label, window in (
        ("5 小时", info.five_hour),
        ("每周", info.weekly),
        ("每月", info.monthly),
    ):
        if window:
            print(
                f"  {label}：已用 {window.usage_percent:.0f}%"
                f"，重置于 {window.reset_date.strftime('%Y-%m-%d %H:%M:%S')}"
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
#   MODELS_URL：API key 校验 + 模型数接口
#   DASHBOARD_URL_TEMPLATE / DASHBOARD_ACCEPT / CHROME_UA：dashboard HTML 请求参数
#     （Cookie auth= 自动补前缀，参考 opencode-bar OpenCodeGoProvider.swift）
#   MIN_FETCH_INTERVAL：接口节流 60 秒（z.plan 第四章节流策略）
#   AUTH_KEY_FIELDS / WORKSPACE_ID_FIELDS / AUTH_COOKIE_FIELDS：凭据字段兼容集合
# 模块级变量：_last_quota / _last_success_at——成功结果缓存与时间戳（缓存兜底）
# 类型：
#   GoQuotaWindow：单窗口（usage_percent/reset_in_sec/reset_date）
#   DashboardCredentials：dashboard 凭据候选（含来源标注）
#   GoQuotaInfo：配额总览（三窗口 + 最紧窗口 + 元信息 + is_cached/error 状态）
#   GoQuotaError：分类业务错误（auth/network/decoding/provider），UI 只认 code
# 函数：
#   find_auth_file()：多路径探测 auth.json（XDG_DATA_HOME → ~/.local/share →
#     ~/.config/opencode），返回首个存在的文件
#   read_auth_json()：jsonc 注释剥离 + 宽容解析，失败返回 None
#   strip_json_comments()：状态机剥离 // 与 /* */（字符串字面量内保留）
#   get_opencode_go_key()：opencode-go 条目提取（dict 多键兼容 + 裸字符串）
#   find_dashboard_credentials()：环境变量 → 配置文件多路径收集候选，
#     去重键 workspace_id::auth_cookie；key 名兼容集合（workspaceId/workspaceID/
#     workspace_id、authCookie/auth_cookie/cookie）
#   _dashboard_config_paths()：$OPENCODE_GO_CONFIG_FILE → $XDG_CONFIG_HOME 系列
#     → ~/.config/{myboard,opencode-bar,opencode-quota}/
#   fetch_model_count()：Bearer 校验 + data[]/models[]/裸数组三形态取模型数，
#     失败返回 None 不阻断主流程
#   fetch_dashboard_usage()：HTML 抓取 + 解析（HTTP 错误按分类抛 GoQuotaError）
#   parse_dashboard_html()：纯函数（可测）：实体反转义 → 逐窗口正则解析 →
#     缺失窗口仅警告、全部缺失抛 decoding 错误
#   _capture_object_body/_capture_number/_normalize_html：opencode-bar 正则移植
#     （兼容 "field":$R[12]={...} 赋值形态与字符串/数字双形态值）
#   fetch_go_quota(force)：主流程——节流检查 → key → 模型数 → 凭据候选逐个
#     尝试（首成功返回）→ 组装 GoQuotaInfo；任一步失败走 _fallback 缓存兜底
#   _fallback()：失败返回缓存（标注 is_cached + error）或空白信息（带提示）
#   main()：CLI 自测，仅打印展示数据，绝不打印凭据
# 设计理由：错误分类统一（z.plan 第四章）；窗口缺失容忍（dashboard 非公开 API，
#   markup 可能变更）；凭据只在内存流转、日志不打印
# 异常处理：网络/解析/凭据错误全部分类化；单凭据失败继续尝试下一个候选
# 关联配置：OPENCODE_GO_WORKSPACE_ID/OPENCODE_GO_AUTH_COOKIE/OPENCODE_GO_CONFIG_FILE
#   环境变量；~/.config/myboard/opencode-go.json 配置文件（含凭据，严禁入库）
