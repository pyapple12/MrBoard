# OpenCode 数据页与官方动态模块（PL002）：数据页 $R 块解析 / 热门模型时序 /
# GitHub Releases 拉取——纯数据层，零 Qt 依赖

import json
import re
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from config.static.static_config import get_static_config
from utils.cache_util import mark_cached
from utils.logger import get_logger
from utils.network import CHROME_UA, http_get

logger = get_logger(__name__)

# 静态配置解包（S8：参数外置 base.json，运行时零 IO）
_SC = get_static_config()

# M1.4：in-flight 去重标志与状态锁（移植 go_quota D0.4/L1.7 同式）——连点/定时叠加
# 并发刷新只放行一个，防打爆非官方接口（GitHub 匿名限额）；网络 IO 不持锁
_data_in_flight = False
_DATA_FETCH_LOCK = threading.Lock()

DATA_URL = str(_SC.base["data_url"])
GH_RELEASES_API_URL = str(_SC.base["gh_releases_api_url"])
GH_RELEASES_RSS_URL = str(_SC.base["gh_releases_rss_url"])
# 节流间隔（base.json 驱动，PL002.2；对齐 go_quota.MIN_FETCH_INTERVAL 模式；
# A0.16/K2.3：原"缓存 TTL"从未实现语义，无效配置键已一并删除）
FETCH_INTERVAL = int(_SC.base["data_fetch_interval_sec"])

# 数据页四数据块锚点键（PL002.4：$R 块字段名与展示列头对应）
MODEL_BLOCK_KEYS = ("tokenCost", "cacheRatio", "sessionCost", "country")

# 模块级缓存：上次成功快照与时间戳（网络失败兜底，z.plan 第四章缓存兜底策略）
_last_snapshot: "ModelDataSnapshot | None" = None
_last_success_at: float = 0.0

# $R 单对象正则：$R[N]={...}（无嵌套大括号；数据页 $R 块均为简单对象）
_R_OBJECT_PATTERN = re.compile(r"\$R\[(\d+)\]=(\{[^{}]*\})")


@dataclass
class ModelDataSnapshot:
    # 数据页快照聚合（PL002.7）：四数据块 + 热门模型时序 + Releases +
    # 缓存/错误状态标注（三源独立失败互不拖垮）
    model_blocks: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    daily_usage: list[dict[str, Any]] = field(default_factory=list)
    releases: list[dict[str, Any]] = field(default_factory=list)
    is_cached: bool = False
    fetched_at: datetime | None = None
    errors: list[str] = field(default_factory=list)


def _throttled_snapshot(force: bool) -> ModelDataSnapshot | None:
    # 节流检查（PL002.2）：非强制且距上次成功不足 FETCH_INTERVAL 秒时返回标注缓存
    # （避免打爆非官方接口；对齐 go_quota._throttled_cache 同式）
    if (
        not force
        and _last_snapshot is not None
        and time.time() - _last_success_at < FETCH_INTERVAL
    ):
        return mark_cached(
            _last_snapshot,
            str(_SC.ui["go_quota_error_messages"]["throttled_template"]).format(
                seconds=FETCH_INTERVAL
            ),
            list_field="errors",
        )
    return None


def _extract_r_objects(body: str) -> dict[int, str]:
    # 提取全部 $R[N]={...} 单对象文本（实测 2135 个规模；嵌套大括号对象跳过——
    # 数据页 $R 块均为简单对象，嵌套形态不存在）
    return {
        int(match.group(1)): match.group(2)
        for match in _R_OBJECT_PATTERN.finditer(body)
    }


def _split_top_level(text: str) -> list[str]:
    # 顶层逗号切分（引号 + 括号深度感知：字符串内逗号/对象内逗号不误切）
    parts: list[str] = []
    current: list[str] = []
    in_quote = False
    depth = 0
    for ch in text:
        if ch == '"':
            in_quote = not in_quote
            current.append(ch)
        elif in_quote:
            current.append(ch)
        elif ch in "{([":
            depth += 1
            current.append(ch)
        elif ch in "})]":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return [part for part in parts if part]


def _parse_loose_value(text: str) -> Any:
    # JS 字面量值宽容解析：引号字符串 / 布尔 / null / 数值；未知形态保留原文
    value = text.strip()
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    if value in ("null", "undefined"):
        return None
    try:
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_loose_object(text: str) -> dict[str, Any]:
    # JS 对象字面量宽容解析：键无引号/单双引号字符串/数值/布尔/null；
    # 畸形输入返回空 dict（宽容解析策略，z.plan 第四章）
    stripped = text.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return {}
    result: dict[str, Any] = {}
    for part in _split_top_level(stripped[1:-1]):
        if ":" not in part:
            continue
        key, _, value = part.partition(":")
        key = key.strip().strip('"').strip("'")
        if key:
            result[key] = _parse_loose_value(value)
    return result


def _capture_array_text(body: str, start: int) -> str | None:
    # 从 body[start]（应为 '['）配平捕获数组文本（内嵌 $R[N] 引用含方括号，
    # 简单正则会被提前截断；引号感知防字符串内括号误判）
    if start >= len(body) or body[start] != "[":
        return None
    depth = 0
    in_quote = False
    for index in range(start, len(body)):
        ch = body[index]
        if ch == '"':
            in_quote = not in_quote
        elif not in_quote:
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return body[start : index + 1]
    return None


def _expand_array_ref(array_text: str, objects: dict[int, str]) -> list[dict[str, Any]]:
    # 数组引用链展开：`[$R[1868]={...},$R[1869]={...}]` 元素剥引用前缀后解析；
    # 纯 `$R[N]` 引用（对象定义在别处）查表兜底
    stripped = array_text.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return []
    rows: list[dict[str, Any]] = []
    for element in _split_top_level(stripped[1:-1]):
        match = re.match(r"\$R\[(\d+)\]\s*=(.*)$", element, re.DOTALL)
        if match:
            inline = match.group(2).strip()
            if inline.startswith("{"):
                rows.append(_parse_loose_object(inline))
            else:
                obj_text = objects.get(int(match.group(1)))
                if obj_text is not None:
                    rows.append(_parse_loose_object(obj_text))
        elif re.match(r"\$R\[\d+\]$", element):
            obj_text = objects.get(int(re.search(r"\d+", element).group()))
            if obj_text is not None:
                rows.append(_parse_loose_object(obj_text))
        elif element.startswith("{"):
            rows.append(_parse_loose_object(element))
    return rows


def fetch_model_data(body: str) -> dict[str, list[dict[str, Any]]]:
    # 提取四数据块（tokenCost/cacheRatio/sessionCost/country）：锚点定位根 $R ID
    # → 配平捕获数组文本 → 元素引用链展开；锚点缺失的块缺省
    # （调用方按 MODEL_BLOCK_KEYS 补 errors 警告）
    objects = _extract_r_objects(body)
    blocks: dict[str, list[dict[str, Any]]] = {}
    for key in MODEL_BLOCK_KEYS:
        anchor = re.search(rf"{key}:" + re.escape("$R[") + r"(\d+)\]=", body)
        if anchor is None:
            continue
        array_start = body.find("[", anchor.end())
        array_text = _capture_array_text(body, array_start)
        if array_text is None:
            continue
        blocks[key] = _expand_array_ref(array_text, objects)
    return blocks


def refresh_data_page(force: bool = False) -> ModelDataSnapshot:
    # 数据页聚合入口（PL002.7）：节流 → 三源独立拉取（互不拖垮）→ 快照；
    # 整体失败保留上次快照标 is_cached（缓存兜底策略）；
    # M1.4：in-flight 去重——并发刷新在途时直返缓存（防双击刷新打爆接口）
    global _last_snapshot, _last_success_at, _data_in_flight
    cached = _throttled_snapshot(force)
    if cached is not None:
        return cached
    with _DATA_FETCH_LOCK:
        if _data_in_flight:
            if _last_snapshot is not None:
                return mark_cached(
                    _last_snapshot,
                    _SC.ui["data_page_messages"]["in_flight"],
                    list_field="errors",
                )
            # O0.7：无缓存在途快照带进行中标注（裸空快照使 UI 无法区分"进行中"
            # 与"失败"，与 go_quota 占位项口径对齐）
            _placeholder = ModelDataSnapshot(fetched_at=datetime.now(timezone.utc))
            _placeholder.errors.append(_SC.ui["data_page_messages"]["in_flight"])
            return _placeholder
        _data_in_flight = True
    captured: list = []
    try:
        now = datetime.now(timezone.utc)
        snapshot = ModelDataSnapshot(fetched_at=now)
        try:
            body = http_get(DATA_URL, headers=_GH_API_HEADERS).decode(
                "utf-8", errors="replace"
            )
            snapshot.model_blocks = fetch_model_data(body)
            snapshot.daily_usage = parse_daily_usage(body)
            # 缺块容忍：四块键全集缺失时补 decoding 警告（不抛中断）
            for key in MODEL_BLOCK_KEYS:
                if key not in snapshot.model_blocks:
                    snapshot.errors.append(
                        _SC.ui["data_page_messages"]["block_missing"].format(key=key)
                    )
        except Exception as exc:
            # O2.1：错误文案外置（模板含 {error} 占位符，与 fetch_failed 兜底键同组）
            snapshot.errors.append(
                _SC.ui["data_page_messages"]["fetch_failed_template"].format(error=exc)
            )
        try:
            snapshot.releases = fetch_github_releases()
        except Exception as exc:
            snapshot.errors.append(
                _SC.ui["data_page_messages"]["release_failed_template"].format(
                    error=exc
                )
            )
        # A0.16/K1.1：三源全空且已有历史缓存时保留旧快照标注返回（失败不覆盖成功
        # 数据，对齐 go_quota 只缓存成功项的模式）；首刷无缓存时照常返回空快照+错误。
        # A017/L1.4 已知取舍声明：守卫粒度为三源整体——单源失败（如 Releases 网络抖动
        # 返回 []）而其他源成功时，空源仍会覆盖旧值；per-source 合并待后续评估
        has_data = bool(
            snapshot.model_blocks or snapshot.daily_usage or snapshot.releases
        )
        if not has_data and _last_snapshot is not None:
            dpm = _SC.ui["data_page_messages"]
            message = (
                "；".join(snapshot.errors) if snapshot.errors else dpm["fetch_failed"]
            )
            return mark_cached(
                _last_snapshot,
                f"{message}{dpm['cache_suffix']}",
                list_field="errors",
            )
        captured = [snapshot]
        return snapshot
    finally:
        # M1.4 + N3.2：缓存发布与在途标志复位同持锁，保证原子可见
        with _DATA_FETCH_LOCK:
            if captured:
                _last_snapshot = captured[0]
                _last_success_at = time.time()
            _data_in_flight = False


# 热门模型时序：data-slot 标记与 aria-label 形态（SolidJS 渲染属性）；
# WTH001.b：token 数收紧为 \d+(?:\.\d+)?——旧宽松写法会放行 "1.2.3" 形态致 float 抛错丢整图
_DAILY_BAR_PATTERN = re.compile(
    r'data-slot="top-models-bar"[^>]*aria-label="([A-Z]{3} \d+) (\d+(?:\.\d+)?)T'
)
_DAILY_STACK_PATTERN = re.compile(
    r'data-slot="top-models-stack" style="grid-template-rows:([^"]+)"'
)
_DAILY_MODEL_PATTERN = re.compile(r'data-model="([^"]+)"')
# 月份缩写映射（时序排序用，JAN=1…DEC=12）
_MONTH_INDEX = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def parse_daily_usage(body: str) -> list[dict[str, Any]]:
    # 解析热门模型每日时序（PL002.5）：top-models-bar 的 aria-label 提取日期与总量
    # （T 单位浮点），stack 的 grid-template-rows 百分比序列 × data-model 名单按序
    # zip 为模型占比 dict；SolidJS 渲染属性比 $R 块略脆——解析失败返回空列表降级
    rows: list[dict[str, Any]] = []
    for bar_match in _DAILY_BAR_PATTERN.finditer(body):
        date_text = bar_match.group(1)
        total_t = float(bar_match.group(2))
        # WTH001.c：扫描窗口 6000 为字符数上限（自 bar 起点向后截取，防 markup 变更
        # 致 stack 结束标记丢失时无限扫描；超窗静默丢行为已知取舍）
        segment = body[bar_match.end() : bar_match.end() + 6000]
        stack_match = _DAILY_STACK_PATTERN.search(segment)
        if stack_match is None:
            continue
        percents = [float(value.rstrip("%")) for value in stack_match.group(1).split()]
        # data-model 的 <i> 元素在 stack 容器内部（stack 起点后至 </div>）
        stack_end = segment.find("</div>", stack_match.end())
        if stack_end < 0:
            stack_end = len(segment)
        model_names = _DAILY_MODEL_PATTERN.findall(
            segment[stack_match.end() : stack_end]
        )
        models = {}
        # WTH001.l：双列表数量不齐时告警（zip 按短侧截断为既定语义，不再静默丢行）
        if len(model_names) != len(percents):
            logger.warning(
                "热门模型时序 name/percent 数量不齐（%d/%d），按短侧截断对齐",
                len(model_names),
                len(percents),
            )
        for name, percent in zip(model_names, percents):
            models[name] = models.get(name, 0.0) + percent
        rows.append(
            {
                "date": date_text,
                "total_t": total_t,
                "models": models,
            }
        )
    rows.sort(
        key=lambda row: (
            _MONTH_INDEX.get(row["date"].split()[0].upper(), 0),
            int(row["date"].split()[1]),
        )
    )
    return rows


# GitHub Releases：JSON 快照键与 RSS 命名空间
_GH_API_HEADERS = {"User-Agent": CHROME_UA}
_RSS_NS = {"atom": "http://www.w3.org/2005/Atom"}
_RELEASE_LIMIT = 3  # 最新 N 条（展示范围收敛，z.plan PL002）


def _fetch_releases_json() -> list[dict[str, Any]]:
    # GitHub Releases API 拉取（匿名限速 60 次/小时够用；浏览器 UA 头必须）；
    # 解析 tag_name/published_at/body，取最新 3 条
    raw = http_get(GH_RELEASES_API_URL, headers=_GH_API_HEADERS)
    data = json.loads(raw.decode("utf-8", errors="replace"))
    # M0.5：GitHub 匿名限速期返回 dict（如 {"message":"API rate limit..."}）而非
    # list——data[:N] 会抛 TypeError 回退 RSS 前浪费一次注定失败的请求；
    # 前置校验回退，错误原因可读（A017/L1.6 同口径）
    if not isinstance(data, list):
        logger.warning("Releases API 返回非列表（可能限速），回退 RSS 动态")
        return []
    items: list[dict[str, Any]] = []
    for release in data[:_RELEASE_LIMIT]:
        if not isinstance(release, dict):
            continue
        items.append(
            {
                # A017/L1.6：(x or "") 兜底显式 null——与 RSS 路径同口径，
                # 防 "None" 字面量外显
                "tag_name": str(release.get("tag_name") or ""),
                "published_at": str(release.get("published_at") or ""),
                "body": str(release.get("body") or ""),
            }
        )
    return items


def _fetch_releases_rss() -> list[dict[str, Any]]:
    # RSS 回退路径（JSON API 不可用时）：releases.atom entry 解析 title/updated/content
    raw = http_get(GH_RELEASES_RSS_URL, headers=_GH_API_HEADERS)
    root = ET.fromstring(raw.decode("utf-8", errors="replace"))
    items: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", _RSS_NS)[:_RELEASE_LIMIT]:
        title_el = entry.find("atom:title", _RSS_NS)
        updated_el = entry.find("atom:updated", _RSS_NS)
        content_el = entry.find("atom:content", _RSS_NS)
        items.append(
            {
                "tag_name": (title_el.text or "").strip()
                if title_el is not None
                else "",
                "published_at": (updated_el.text or "")
                if updated_el is not None
                else "",
                "body": (content_el.text or "").strip()
                if content_el is not None
                else "",
            }
        )
    return items


def fetch_github_releases() -> list[dict[str, Any]]:
    # GitHub Releases 拉取（PL002.6；O3.1 删除从未读取的 force 死参数——节流
    # 实际由快照层 refresh_data_page 统一控制）：JSON 优先、异常回退 RSS、
    # 双路径全失败返回空列表（宽容降级）
    try:
        return _fetch_releases_json()
    except Exception as exc:
        logger.debug("GitHub JSON 拉取失败（尝试 RSS 回退）：%s", exc)
    try:
        return _fetch_releases_rss()
    except Exception as exc:
        logger.warning("GitHub RSS 回退也失败：%s", exc)
        return []


def main() -> None:
    # CLI 自测入口：拉取数据页快照并打印各源状态（不打印凭据）
    snapshot = refresh_data_page()
    print(f"数据页快照（获取时间：{snapshot.fetched_at}）")
    print(f"  数据块：{list(snapshot.model_blocks.keys())}")
    print(f"  时序条数：{len(snapshot.daily_usage)}")
    print(f"  Releases 条数：{len(snapshot.releases)}")
    if snapshot.is_cached:
        print(f"  [缓存数据] {snapshot.errors}")
    elif snapshot.errors:
        print(f"  [部分失败] {snapshot.errors}")


if __name__ == "__main__":
    main()

# ===== modules/opencode_data.py 模块说明 =====
# 模块级常量：
#   DATA_URL / GH_RELEASES_API_URL / GH_RELEASES_RSS_URL：数据源 URL（base.json 驱动）
#   FETCH_INTERVAL：数据页刷新节流间隔（base.json 驱动，PL002.2）
#   CHROME_UA：浏览器 UA（自 utils.network 单点导入；无浏览器 UA 会被 opencode.ai
#     403 拦截，实测 Python-urllib 默认 UA 被拒）
#   _GH_API_HEADERS / _RSS_NS / _RELEASE_LIMIT：GitHub 请求头/RSS 命名空间/条数上限
#   _R_OBJECT_PATTERN 等 $R/时序正则族：页面结构锚点（markup 变更时集中调整）
# 模块级变量：_last_snapshot / _last_success_at——成功快照缓存与时间戳（缓存兜底；
#   A0.16/K1.1 起仅含实质数据的快照才写入，失败保留旧数据）
# 类型：
#   ModelDataSnapshot：快照聚合（model_blocks/daily_usage/releases/is_cached/
#     fetched_at/errors）
# 函数：
#   _extract_r_objects(body)：提取全部 $R[N]={...} 单对象文本（嵌套大括号跳过）
#   _split_top_level(text)：顶层逗号切分（嵌套感知）
#   _parse_loose_value/_parse_loose_object：宽松 JSON 解析（键无引号容忍）
#   _capture_array_text/_expand_array_ref：数组捕获与 $R 引用展开（配平括号）
#   fetch_model_data(body)：四数据块锚点解析（PL002.4）
#   parse_daily_usage(body)：热门模型时序解析（data-slot 正则，PL002.5）
#   _fetch_releases_json()：Releases API 路径（PL002.6）
#   _fetch_releases_rss()：Releases RSS 回退路径（JSON 不可用时）
#   fetch_github_releases()：JSON→RSS 回退链聚合（O3.1 删 force 死参数）
#   _throttled_snapshot(force)：节流检查——窗口内返回标注缓存（对齐 go_quota 同式）
#   mark_cached(snapshot, message, list_field="errors")：缓存兜底标注（来自 utils.cache_util，浅拷贝防污染）
#   refresh_data_page(force)：聚合入口——节流 → 三源独立拉取（互不拖垮）→
#     A0.16/K1.1 失败且有旧缓存时保留旧快照标注返回（不覆盖成功数据）
#   main()：CLI 自测入口
# 异常处理：三源独立 try 隔离（任一失败仅 errors 追加，不影响其他源）；
#   A0.16/K3.2 删除从未抛出的 DataPageError 空壳类（宽容降级走 errors 列表）
# 关联配置：config/static/base.json（data_url/gh_releases_api_url/
#   gh_releases_rss_url/data_fetch_interval_sec）
