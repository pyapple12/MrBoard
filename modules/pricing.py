# 模型定价模块：内置表 + models.dev 远程缓存 + 本地覆盖 + 多币种分桶

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.static.static_config import get_static_config
from utils.convert import to_float, to_optional_float
from utils.file_utils import get_project_root, read_json, write_json
from utils.logger import get_logger
from utils.retry import retry_call

logger = get_logger(__name__)

# 静态配置解包（S8：参数外置 base.json）
_SC = get_static_config()
MODELS_DEV_URL = str(_SC.base["models_dev_url"])
# 价格缓存目录（P2：集中项目内 data/prices，不使用用户目录）
PRICE_CACHE_DIR = get_project_root() / Path(str(_SC.base["prices_dir"]))
PRICE_CACHE_FILE = PRICE_CACHE_DIR / "prices.json"
PRICE_LOCAL_FILE = PRICE_CACHE_DIR / "prices.local.json"
PRICE_CACHE_TTL = int(_SC.base["price_cache_ttl"])  # 远程价格缓存有效期：1 天
HTTP_TIMEOUT = float(_SC.base["http_timeout"])  # L13：网络请求超时统一（base.json）

# 内置常见模型价格表（单位：美元/百万 token，cache 价格缺省为 None 表示按无折扣计）
# 来源：models.dev 快照与 opencode-bar 测试数据，仅作无网络/无缓存时的回退
BUNDLED_PRICES: dict[str, dict[str, Any]] = {
    "anthropic:claude-sonnet-4-5": {
        "input_price": 3.0,
        "output_price": 15.0,
        "cache_read_price": 0.3,
        "cache_write_price": 3.75,
        "currency": "USD",
    },
    "anthropic:claude-opus-4-5": {
        "input_price": 5.0,
        "output_price": 25.0,
        "cache_read_price": 0.5,
        "cache_write_price": 6.25,
        "currency": "USD",
    },
    "openai:gpt-4o": {
        "input_price": 2.5,
        "output_price": 10.0,
        "cache_read_price": 1.25,
        "cache_write_price": 2.5,
        "currency": "USD",
    },
    "deepseek:deepseek-chat": {
        "input_price": 0.27,
        "output_price": 1.1,
        "cache_read_price": 0.07,
        "cache_write_price": 0.27,
        "currency": "USD",
    },
    "opencode-go:deepseek-v4-flash": {
        "input_price": 0.1,
        "output_price": 0.4,
        "cache_read_price": 0.03,
        "cache_write_price": 0.1,
        "currency": "USD",
    },
}


@dataclass
class RateInfo:
    # 单个 provider:model 的计费单价（单位：美元/百万 token，currency 指定币种）

    input_price: float
    output_price: float
    cache_read_price: float | None = None
    cache_write_price: float | None = None
    currency: str = "USD"
    source: str = "bundled"


@dataclass
class CostEstimate:
    # 单条消息的估算成本结果（含状态与来源标记）

    estimated_cost: float | None = None
    currency: str = "USD"
    price_status: str = "priced"  # priced / unpriced
    price_source: str = "bundled"  # bundled / local / remote / missing


def canonical_key(provider: str, model: str) -> str:
    # 归一化 provider/model 为小写 key（provider:model），用于价格表索引
    return f"{provider}:{model}".lower()


def load_price_map(refresh: bool = False) -> dict[str, RateInfo]:
    # 加载定价表：缓存（TTL 内）→ 远程 models.dev（无缓存或 refresh）→ 内置表，最后合并本地覆盖
    # （H6：refresh 且远程失败时回退 TTL 内旧缓存，不降级为内置表）
    price_map = _load_cached_prices(refresh)
    if not price_map:
        cached_fallback = _load_cached_prices(False) if refresh else None
        remote = _fetch_remote_prices()
        if remote:
            price_map = remote
            write_json(PRICE_CACHE_FILE, _serialize(remote))
            logger.info("远程定价表已缓存：%d 条", len(remote))
        elif cached_fallback:
            price_map = cached_fallback
            logger.info("远程定价刷新失败，回退旧缓存：%d 条", len(cached_fallback))
        else:
            price_map = _load_bundled()
            logger.info("远程定价不可用，回退内置表：%d 条", len(price_map))
    _apply_local_overrides(price_map)
    return price_map


def estimate_cost(
    price_map: dict[str, RateInfo],
    provider: str,
    model: str,
    tokens: dict[str, int],
) -> CostEstimate:
    # 按价格表估算 tokens 成本；查不到价格返回 unpriced（estimated_cost 为 None）
    rate = price_map.get(canonical_key(provider, model))
    if rate is None:
        return CostEstimate(price_status="unpriced", price_source="missing")
    input_count = tokens.get("input", 0)
    output_count = tokens.get("output", 0)
    cache_read_count = tokens.get("cache_read", 0)
    cache_write_count = tokens.get("cache_write", 0)
    cost = (
        input_count / 1e6 * rate.input_price
        + output_count / 1e6 * rate.output_price
        + (
            cache_read_count / 1e6 * rate.cache_read_price
            if rate.cache_read_price is not None
            else 0.0
        )
        + (
            cache_write_count / 1e6 * rate.cache_write_price
            if rate.cache_write_price is not None
            else 0.0
        )
    )
    return CostEstimate(
        estimated_cost=round(cost, 10),
        currency=rate.currency,
        price_status="priced",
        price_source=rate.source,
    )


def aggregate_estimated_costs(
    estimates: list[CostEstimate],
) -> tuple[dict[str, float], float | None]:
    # 多币种分桶汇总：仅 1 种币时返回其和；≥2 种币返回 None 禁止跨币种相加
    totals: dict[str, float] = {}
    for est in estimates:
        if est.estimated_cost is not None:
            totals[est.currency] = totals.get(est.currency, 0.0) + est.estimated_cost
    if not totals:
        return {}, None
    if len(totals) == 1:
        return totals, round(next(iter(totals.values())), 10)
    return totals, None


def _rate_from_raw(item: dict[str, Any], default_source: str) -> RateInfo | None:
    # 从 dict 弹性构建 RateInfo（内置/缓存/本地覆盖三处来源共用）；字段非法返回 None
    try:
        return RateInfo(
            input_price=to_float(item.get("input_price")),
            output_price=to_float(item.get("output_price")),
            cache_read_price=to_optional_float(item.get("cache_read_price")),
            cache_write_price=to_optional_float(item.get("cache_write_price")),
            currency=str(item.get("currency", "USD")),
            source=str(item.get("source", default_source)),
        )
    except (TypeError, ValueError):
        return None


def _load_bundled() -> dict[str, RateInfo]:
    # 将内置 BUNDLED_PRICES 常量转为 RateInfo 字典（source=bundled）
    result: dict[str, RateInfo] = {}
    for key, item in BUNDLED_PRICES.items():
        rate = _rate_from_raw(item, "bundled")
        if rate is not None:
            result[key] = rate
    return result


def _load_cached_prices(refresh: bool) -> dict[str, RateInfo] | None:
    # 读取本地缓存价格文件（TTL 内有效）；refresh 或文件缺失/损坏时返回 None
    if refresh or not PRICE_CACHE_FILE.is_file():
        return None
    try:
        if PRICE_CACHE_FILE.stat().st_mtime + PRICE_CACHE_TTL < time.time():
            return None
    except OSError:
        return None
    raw = read_json(PRICE_CACHE_FILE, default=None, use_cache=False)
    if not isinstance(raw, dict):
        return None
    return _deserialize(raw)


def _serialize(price_map: dict[str, RateInfo]) -> dict[str, dict[str, Any]]:
    # 将 RateInfo 字典转为可写 JSON 的 dict 结构
    return {
        key: {
            "input_price": rate.input_price,
            "output_price": rate.output_price,
            "cache_read_price": rate.cache_read_price,
            "cache_write_price": rate.cache_write_price,
            "currency": rate.currency,
            "source": rate.source,
        }
        for key, rate in price_map.items()
    }


def _deserialize(raw: dict[str, Any]) -> dict[str, RateInfo]:
    # 将缓存的 dict 结构还原为 RateInfo 字典（宽容解析，坏条目跳过）
    result: dict[str, RateInfo] = {}
    for key, item in raw.items():
        if not isinstance(item, dict):
            continue
        rate = _rate_from_raw(item, "remote")
        if rate is not None:
            result[key] = rate
    return result


def _apply_local_overrides(price_map: dict[str, RateInfo]) -> None:
    # 合并本地覆盖文件 prices.local.json：命中 key 覆盖单价并打标 source=local
    raw = read_json(PRICE_LOCAL_FILE, default=None, use_cache=False)
    if not isinstance(raw, dict):
        return
    for key, item in raw.items():
        if not isinstance(item, dict):
            continue
        rate = _rate_from_raw(item, "local")
        if rate is not None:
            price_map[key] = rate


def _fetch_remote_prices() -> dict[str, RateInfo] | None:
    # 从 models.dev 拉取全量定价并转 RateInfo 字典；网络失败返回 None（宽容降级）
    try:
        body = retry_call(
            _http_get,
            MODELS_DEV_URL,
            retries=2,
            exceptions=(urllib.error.URLError, TimeoutError),
            delay=1.0,
        )
        data = json.loads(body.decode("utf-8"))
    except Exception as exc:
        logger.warning("拉取 models.dev 定价失败：%s", exc)
        return None
    if not isinstance(data, dict) or not isinstance(data.get("models"), dict):
        return None
    result: dict[str, RateInfo] = {}
    for model_key, model_info in data["models"].items():
        if not isinstance(model_info, dict):
            continue
        pricing = model_info.get("pricing")
        if not isinstance(pricing, dict):
            continue
        provider, _, model = model_key.partition("/")
        if not provider or not model:
            continue
        result[canonical_key(provider, model)] = RateInfo(
            input_price=to_float(pricing.get("input"), 0.0),
            output_price=to_float(pricing.get("output"), 0.0),
            cache_read_price=to_optional_float(pricing.get("cache_read")),
            cache_write_price=to_optional_float(pricing.get("cache_write")),
            currency=str(pricing.get("currency", "USD")),
            source="remote",
        )
    return result or None


def _http_get(url: str) -> bytes:
    # 发送 GET 请求返回响应体（超时走 base.json http_timeout，L13），供 retry_call 重试调用
    # UA 版本跟随 base.json（H7）
    request = urllib.request.Request(
        url, headers={"User-Agent": f"myboard/{_SC.base['version']}"}
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
        return response.read()


# ===== modules/pricing.py 模块说明 =====
# 模块级常量：
#   MODELS_DEV_URL：models.dev 全量定价接口
#   PRICE_CACHE_FILE / PRICE_LOCAL_FILE：缓存与本地覆盖文件（项目内 data/prices/，
#     P2：集中项目内，不使用用户目录）
#   PRICE_CACHE_TTL：远程缓存有效期 1 天
#   BUNDLED_PRICES：内置常见模型价格（无网络回退，仅机制兜底）
# 类型：
#   RateInfo：单价 dataclass（input/output/cache_read/cache_write + currency + source）
#   CostEstimate：估算结果（estimated_cost/currency/price_status/price_source）
# 函数：
#   canonical_key()：provider:model 归一化索引 key
#   load_price_map(refresh=False)：三级加载链——本地缓存（TTL 内）→ 远程 models.dev
#     （无缓存或 refresh）→ 内置表；最后合并本地覆盖文件；任一层失败宽容降级
#   estimate_cost()：单条成本估算 = input/M*in + output/M*out + cache_read/M*read
#     + cache_write/M*write；查不到价格返回 unpriced（estimated_cost=None）
#   aggregate_estimated_costs()：多币种分桶；仅 1 币种返回其和，≥2 币种返回 None
#     （禁止跨币种相加，参考 OpenCode-Token 的 estimated_cost_totals 设计）
#   _load_bundled / _load_cached_prices / _serialize / _deserialize / _apply_local_overrides：
#     定价表各层来源的装载与合并（坏条目逐条跳过，宽容解析）
#   _fetch_remote_prices / _http_get：models.dev 拉取与解析（urllib 实现，
#     复用 utils/retry.py 指数退避重试，失败返回 None 不崩溃）
#   弹性数字转换复用 utils/convert.py 的 to_float / to_optional_float
#     （String/Int 兼容，z.plan 第四章宽容解析）
# 设计理由：库 cost 优先（opencode_usage 聚合），估算仅作缺失回退；价格数据带
#   source 标记可审计；TTL 缓存避免每次启动打网络
# 异常处理：网络失败/JSON 损坏/坏条目全部降级，绝不因价格问题阻断统计
# 关联配置：config/static/base.json（prices_dir/models_dev_url/price_cache_ttl）；
#   PRICE_LOCAL_FILE 可由用户手写覆盖（data/prices/prices.local.json）
