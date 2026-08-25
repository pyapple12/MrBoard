# OpenCode 用量统计模块：只读读取本地 opencode.db 并聚合 tokens/费用

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from config.static.static_config import get_static_config
from modules import pricing
from utils.convert import round_cost, to_int
from utils.logger import get_logger
from utils.sqlite_utils import open_readonly

logger = get_logger(__name__)

# 静态配置单点解包（A3.4：与全项目 _SC 模式一致，运行时零 IO）
_SC = get_static_config()

UNKNOWN_LABEL = str(_SC.ui["unknown_label"])  # 6A.3 H2：分组缺失标签外置
# C19：默认库路径由 base.json 驱动（~ 展开），消除代码内硬编码
DEFAULT_DB_PATH = Path(str(_SC.base["db_default_path"])).expanduser()
ASSISTANT_ROLE = "assistant"
_EPOCH_MS = 1000
_DAY_MS = _EPOCH_MS * 86400  # 天毫秒数（3A.1 R12 派生，消除魔法数字）
SUBPROCESS_TIMEOUT = float(_SC.base["subprocess_timeout"])  # 子进程探测超时（R7）
# C5：分组查询默认行数收敛（消除 8 处 limit=100 魔法数字，与 GUI 配置一致）
TABLE_LIMIT_GROUP = int(_SC.base["table_limit_group"])
TABLE_LIMIT_DAY = int(_SC.base["table_limit_day"])

# 聚合 SQL 列模板（_base_sql 与 _query_grouped 共用，加字段只改一处）
_TOKEN_SUM_SELECT = (
    " COALESCE(SUM(json_extract(data, '$.tokens.input')), 0) AS input,"
    " COALESCE(SUM(json_extract(data, '$.tokens.output')), 0) AS output,"
    " COALESCE(SUM(json_extract(data, '$.tokens.reasoning')), 0) AS reasoning,"
    " COALESCE(SUM(json_extract(data, '$.tokens.cache.read')), 0) AS cache_read,"
    " COALESCE(SUM(json_extract(data, '$.tokens.cache.write')), 0) AS cache_write,"
    " COALESCE(SUM(json_extract(data, '$.tokens.total')), 0) AS total,"
    " COALESCE(SUM(json_extract(data, '$.cost')), 0) AS recorded_cost"
)


@dataclass
class TokenStats:
    # 单次聚合的 token 统计（input/output/reasoning/cache_read/cache_write/total 六字段，
    # S9 注释补全）

    input: int = 0
    output: int = 0
    reasoning: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total: int = 0

    def compute_total(self) -> int:
        # 计算总 token：优先已有 total，否则用五字段之和兜底（兼容旧版无 total 格式）
        if self.total > 0:
            return self.total
        return (
            self.input
            + self.output
            + self.reasoning
            + self.cache_read
            + self.cache_write
        )


def flatten_tokens(tokens: TokenStats, prefix: str = "") -> dict[str, Any]:
    # token 六字段平铺为 dict（prefix 加在字段名前；CLI 嵌套结构传 ""，导出传 "tokens_"）
    return {
        f"{prefix}input": tokens.input,
        f"{prefix}output": tokens.output,
        f"{prefix}reasoning": tokens.reasoning,
        f"{prefix}cache_read": tokens.cache_read,
        f"{prefix}cache_write": tokens.cache_write,
        f"{prefix}total": tokens.total,
    }


@dataclass
class UsageRow:
    # 一条分组聚合结果：label 为分组键，calls 为消息数，tokens/cost 为聚合值

    label: str
    calls: int = 0
    tokens: TokenStats = field(default_factory=TokenStats)
    cost: float = 0.0


# F0.3：TokenStats/UsageRow 字段契约——显式键集与 dataclass 字段比对（非自证，
# 键集独立于字段定义；_render_table 等跨模块消费方直读属性，改名 AttributeError
# 会逃逸 Qt 槽，导入期拦截优于运行时崩溃）
_TOKEN_STATS_FIELDS = (
    "input",
    "output",
    "reasoning",
    "cache_read",
    "cache_write",
    "total",
)
_USAGE_ROW_FIELDS = ("label", "calls", "tokens", "cost")
for _name, _fields, _expected in (
    ("TokenStats", TokenStats.__dataclass_fields__, _TOKEN_STATS_FIELDS),
    ("UsageRow", UsageRow.__dataclass_fields__, _USAGE_ROW_FIELDS),
):
    _actual = tuple(_fields)
    if _actual != _expected:
        raise RuntimeError(
            f"{_name} 字段与消费契约不一致：期望 {_expected}，实际 {_actual}"
        )


@dataclass
class UsageSummary:
    # 全局用量总览：会话/消息/天数 + token/费用聚合结果

    sessions: int = 0
    messages: int = 0
    days: int = 0
    tokens: TokenStats = field(default_factory=TokenStats)
    recorded_cost: float = 0.0
    estimated_cost_totals: dict[str, float] = field(default_factory=dict)
    estimated_cost_total: float | None = None
    cost_source: str = "recorded"  # recorded / estimated / mixed
    since: int | None = None
    until: int | None = None


# G0.2：UsageSummary 字段契约（与 F0.3 同机制——main_window/exporter/CLI
# 跨模块直读属性，改名 AttributeError 会逃逸 Qt 槽；契约块必须在类定义后）
_USAGE_SUMMARY_FIELDS = (
    "sessions",
    "messages",
    "days",
    "tokens",
    "recorded_cost",
    "estimated_cost_totals",
    "estimated_cost_total",
    "cost_source",
    "since",
    "until",
)
if tuple(UsageSummary.__dataclass_fields__) != _USAGE_SUMMARY_FIELDS:
    raise RuntimeError(
        f"UsageSummary 字段与消费契约不一致：期望 {_USAGE_SUMMARY_FIELDS}，"
        f"实际 {tuple(UsageSummary.__dataclass_fields__)}"
    )


def find_db_path() -> Path | None:
    # 三级探测 opencode.db：OPENCODE_DB 环境变量 → opencode db path 子进程 → XDG 默认路径
    env_path = os.environ.get("OPENCODE_DB")
    if env_path:
        path = Path(env_path)
        if path.is_file():
            return path
        logger.warning("OPENCODE_DB 指定的路径不存在：%s", env_path)
    cli_path = _query_db_path_from_cli()
    if cli_path is not None and cli_path.is_file():
        return cli_path
    if cli_path is not None:
        # 6A.1 E6：子进程返回了路径但文件不存在——补 warning 与 env 分支一致
        logger.warning("opencode db path 返回的路径不存在：%s", cli_path)
    if DEFAULT_DB_PATH.is_file():
        return DEFAULT_DB_PATH
    return None


def _query_db_path_from_cli() -> Path | None:
    # 调用 `opencode db path` 子进程查询数据库路径；二进制不可用/失败时返回 None
    binary = shutil.which("opencode")
    if binary is None:
        return None
    try:
        result = subprocess.run(
            [binary, "db", "path"],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            # H0.7：无控制台环境不闪黑窗（非 Windows 无此属性，getattr 兜底为 0）
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("调用 opencode db path 失败：%s", exc)
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip())


class OpenCodeDB:
    # opencode.db 只读访问封装：持有一个连接，提供多维度聚合查询

    def __init__(self, db_path: Path) -> None:
        # 只读连接防误写（z.plan 第四章：只读防误写策略；URI 转义统一在 utils，6A.3 R1）
        self.conn = open_readonly(db_path)
        self.db_path = db_path
        # PRAGMA 检测结果缓存（by_session 周期调用避免重复查表结构，M14）
        self._session_columns: bool | None = None

    @classmethod
    def auto(cls) -> "OpenCodeDB":
        # 自动探测数据库路径并打开；探测失败抛 FileNotFoundError（带提示）
        path = find_db_path()
        if path is None:
            raise FileNotFoundError(
                f"未找到 opencode.db（可用 OPENCODE_DB 环境变量指定路径，默认位置：{DEFAULT_DB_PATH}）"
            )
        return cls(path)

    def close(self) -> None:
        # 关闭数据库连接（进程退出或窗口关闭时调用）
        self.conn.close()

    def totals(
        self,
        since: int | None = None,
        until: int | None = None,
        estimate: bool = False,
        price_map: dict[str, Any] | None = None,
    ) -> UsageSummary:
        # 全量聚合：会话数/消息数/活动跨度天数 + token/费用；estimate=True 时对库 cost 缺失的消息做定价估算
        summary = UsageSummary(since=since, until=until)
        time_clause, time_params = self._time_clause(since, until)
        row = self._fetch_one(
            f"SELECT COUNT(DISTINCT session_id) AS sessions,"
            f" MIN(json_extract(data, '$.time.created')) AS min_ts,"
            f" MAX(json_extract(data, '$.time.created')) AS max_ts"
            f" FROM message WHERE json_extract(data, '$.role') = ?{time_clause}",
            [ASSISTANT_ROLE] + time_params,
        )
        summary.sessions = to_int(row["sessions"])
        min_ts = row["min_ts"]
        max_ts = row["max_ts"]
        if min_ts is not None and max_ts is not None:
            min_v = to_int(min_ts)
            max_v = to_int(max_ts)
            if min_v <= 0 or max_v <= 0:
                # E0.4：time.created=0 记录（未知创建时间）会让跨度虚高至数十年
                # （0→now ≈ 20000+ 天）——视为无有效时间数据，天数归零并告警
                logger.warning(
                    "检测到 time.created=0 记录（未知创建时间），活动跨度归零"
                )
                summary.days = 0
            else:
                # 活动跨度天数 = 跨度毫秒转天向下取整 + 1（对齐 opencode stats 的 Days 口径）
                summary.days = int((max_v - min_v) / _DAY_MS) + 1
        agg = self._fetch_one(
            self._base_sql(time_clause),
            [ASSISTANT_ROLE] + time_params,
        )
        # 消息数按全量统计（含 user，对齐 opencode stats 的 Messages 口径）
        msg_row = self._fetch_one(
            f"SELECT COUNT(*) AS messages FROM message WHERE 1=1{time_clause}",
            time_params,
        )
        summary.messages = to_int(msg_row["messages"])
        summary.tokens = self._row_to_tokens(agg)
        summary.recorded_cost = round_cost(agg["recorded_cost"])
        if estimate:
            estimates = self._estimate_missing_costs(price_map, since, until)
            summary.estimated_cost_totals, summary.estimated_cost_total = (
                pricing.aggregate_estimated_costs(estimates)
            )
        # S4：以 estimated_cost_totals 非空判定估算存在（多币种时 total=None 但 totals 非空，
        # 此时应标 mixed/estimated 而非 recorded）
        if summary.recorded_cost > 0:
            summary.cost_source = (
                "recorded"
                if not estimate or not summary.estimated_cost_totals
                else "mixed"
            )
        else:
            summary.cost_source = (
                "estimated"
                if estimate and summary.estimated_cost_totals
                else "recorded"
            )
        return summary

    def by_day(
        self,
        since: int | None = None,
        until: int | None = None,
        limit: int = TABLE_LIMIT_DAY,
    ) -> list[UsageRow]:
        # 按日期分组聚合（日期降序，最近日期在前，本地时区；P7 由近到远）
        return self._query_grouped(
            self._day_expr(),
            since,
            until,
            order="label DESC",
            limit=limit,
        )

    def by_month(
        self,
        since: int | None = None,
        until: int | None = None,
        limit: int = TABLE_LIMIT_GROUP,
    ) -> list[UsageRow]:
        # 按月份分组聚合（%Y-%m 降序，最新月在前；P8 月度统计）
        return self._query_grouped(
            self._month_expr(),
            since,
            until,
            order="label DESC",
            limit=limit,
        )

    def by_session(
        self,
        since: int | None = None,
        until: int | None = None,
        limit: int = TABLE_LIMIT_GROUP,
    ) -> list[UsageRow]:
        # 按会话分组聚合：会话标题｜项目目录（P19，LEFT JOIN session 表；
        # session 表缺 id/title/directory 列时降级仅显示 session_id，兼容旧库/测试库）
        if self._has_session_columns():
            label_expr = "COALESCE(NULLIF(s.title, ''), m.session_id)"
            dir_expr = "COALESCE(s.directory, '')"
            join_clause = " LEFT JOIN session s ON s.id = m.session_id"
        else:
            label_expr = "m.session_id"
            dir_expr = "''"
            join_clause = ""
        time_clause, params = self._time_clause(since, until)
        sql = (
            f"SELECT {label_expr} AS label, {dir_expr} AS directory,"
            " COUNT(*) AS calls,"
            + _TOKEN_SUM_SELECT
            + f" FROM message m{join_clause}"
            + " WHERE json_extract(m.data, '$.role') = ?"
            + time_clause
            + " GROUP BY m.session_id ORDER BY total DESC LIMIT ?"
        )
        rows = self.conn.execute(sql, [ASSISTANT_ROLE] + params + [limit]).fetchall()
        result: list[UsageRow] = []
        for row in rows:
            # C15：复用 _row_to_usage_row 后再拼接目录（避免手写重复构造）
            item = self._row_to_usage_row(row)
            directory = str(row["directory"])
            item.label = f"{item.label}｜{directory}" if directory else item.label
            result.append(item)
        return result

    def _has_session_columns(self) -> bool:
        # 检测 session 表是否含 id/title/directory 列（旧库可能缺表或缺列，
        # by_session 降级用；6A.1 D1：缺 id 列时 JOIN 会崩，一并校验；
        # 结果缓存于实例属性，只读连接生命周期内表结构不变）
        if self._session_columns is None:
            try:
                cols = [
                    row["name"]
                    for row in self.conn.execute("PRAGMA table_info(session)")
                ]
                self._session_columns = (
                    "id" in cols and "title" in cols and "directory" in cols
                )
            except sqlite3.Error:
                self._session_columns = False
        return self._session_columns

    def by_model(
        self,
        since: int | None = None,
        until: int | None = None,
        limit: int = TABLE_LIMIT_GROUP,
    ) -> list[UsageRow]:
        # 按模型分组聚合（按总 token 降序）
        return self._by_field(
            f"COALESCE(NULLIF(json_extract(data, '$.modelID'), ''), '{UNKNOWN_LABEL}')",
            since,
            until,
            limit,
        )

    def by_provider(
        self,
        since: int | None = None,
        until: int | None = None,
        limit: int = TABLE_LIMIT_GROUP,
    ) -> list[UsageRow]:
        # 按 provider 分组聚合（按总 token 降序）
        return self._by_field(
            f"COALESCE(NULLIF(json_extract(data, '$.providerID'), ''), '{UNKNOWN_LABEL}')",
            since,
            until,
            limit,
        )

    def by_agent(
        self,
        since: int | None = None,
        until: int | None = None,
        limit: int = TABLE_LIMIT_GROUP,
    ) -> list[UsageRow]:
        # 按 agent 分组聚合（含子 agent；缺失显示未知，按总 token 降序）
        return self._by_field(
            f"COALESCE(NULLIF(json_extract(data, '$.agent'), ''), '{UNKNOWN_LABEL}')",
            since,
            until,
            limit,
        )

    def _by_field(
        self,
        json_expr: str,
        since: int | None = None,
        until: int | None = None,
        limit: int = TABLE_LIMIT_GROUP,
    ) -> list[UsageRow]:
        # 按 JSON 字段分组聚合（按总 token 降序；by_model/by_provider/by_agent 共用，R15）
        return self._query_grouped(
            json_expr,
            since,
            until,
            order="total DESC",
            limit=limit,
        )

    def _base_sql(self, time_clause: str = "") -> str:
        # 构造基础聚合 SQL：只统计 assistant 消息；时间片段由调用方传入
        # （6A.3 O1：totals 已生成 time_clause，消除内部重复生成，改字段只改一处）
        return (
            "SELECT COUNT(*) AS calls,"
            + _TOKEN_SUM_SELECT
            + " FROM message WHERE json_extract(data, '$.role') = ?"
            + time_clause
        )

    def _time_clause(
        self,
        since: int | None = None,
        until: int | None = None,
    ) -> tuple[str, list[int]]:
        # 构造时间过滤 SQL 片段与参数（毫秒 epoch，半开区间 [since, until)）；
        # 参数按 SQL 中 ? 出现顺序追加
        parts: list[str] = []
        params: list[int] = []
        if since is not None:
            parts.append(" AND json_extract(data, '$.time.created') >= ?")
            params.append(since)
        if until is not None:
            parts.append(" AND json_extract(data, '$.time.created') < ?")
            params.append(until)
        return ("".join(parts), params)

    def _day_expr(self) -> str:
        # 按天分组表达式：毫秒时间戳转本地时区日期字符串（L12：复用 _EPOCH_MS）
        return (
            f"date(json_extract(data, '$.time.created') / {_EPOCH_MS},"
            " 'unixepoch', 'localtime')"
        )

    def _month_expr(self) -> str:
        # 按月分组表达式：毫秒时间戳转本地时区 %Y-%m 字符串（字符串排序 = 时间排序）
        return (
            f"strftime('%Y-%m', datetime(json_extract(data, '$.time.created')"
            f" / {_EPOCH_MS}, 'unixepoch', 'localtime'))"
        )

    def _query_grouped(
        self,
        group_expr: str,
        since: int | None = None,
        until: int | None = None,
        order: str = "total DESC",
        limit: int = TABLE_LIMIT_GROUP,
    ) -> list[UsageRow]:
        # 通用分组查询：按 group_expr 分组聚合，返回 UsageRow 列表（order 用 SELECT 别名）
        time_clause, params = self._time_clause(since, until)
        sql = (
            f"SELECT {group_expr} AS label, COUNT(*) AS calls,"
            + _TOKEN_SUM_SELECT
            + f" FROM message WHERE json_extract(data, '$.role') = ?{time_clause}"
            f" GROUP BY label ORDER BY {order} LIMIT ?"
        )
        rows = self.conn.execute(sql, [ASSISTANT_ROLE] + params + [limit]).fetchall()
        return [self._row_to_usage_row(r) for r in rows]

    def _row_to_tokens(self, row: sqlite3.Row) -> TokenStats:
        # 将查询行转换为 TokenStats（total 优先，五字段之和兜底）
        tokens = TokenStats(
            input=to_int(row["input"]),
            output=to_int(row["output"]),
            reasoning=to_int(row["reasoning"]),
            cache_read=to_int(row["cache_read"]),
            cache_write=to_int(row["cache_write"]),
            total=to_int(row["total"]),
        )
        tokens.total = tokens.compute_total()
        return tokens

    def _row_to_usage_row(self, row: sqlite3.Row) -> UsageRow:
        # 将分组查询行转换为 UsageRow
        return UsageRow(
            label=str(row["label"]),
            calls=to_int(row["calls"]),
            tokens=self._row_to_tokens(row),
            cost=round_cost(row["recorded_cost"]),
        )

    def _fetch_one(self, sql: str, params: list[Any]) -> sqlite3.Row:
        # 执行查询并返回单行结果
        return self.conn.execute(sql, params).fetchone()

    def _estimate_missing_costs(
        self,
        price_map: dict[str, Any] | None,
        since: int | None = None,
        until: int | None = None,
    ) -> list[pricing.CostEstimate]:
        # 对库 cost 为 0/缺失且 token 非零的消息做定价估算（时间范围与 totals 一致）
        if price_map is None:
            price_map = pricing.load_price_map()
        time_clause, time_params = self._time_clause(since, until)
        rows = self.conn.execute(
            "SELECT json_extract(data, '$.providerID') AS provider,"
            " json_extract(data, '$.modelID') AS model,"
            " json_extract(data, '$.tokens.input') AS input,"
            " json_extract(data, '$.tokens.output') AS output,"
            " json_extract(data, '$.tokens.cache.read') AS cache_read,"
            " json_extract(data, '$.tokens.cache.write') AS cache_write"
            " FROM message WHERE json_extract(data, '$.role') = ?"
            " AND (COALESCE(json_extract(data, '$.cost'), 0) = 0)"
            f" AND COALESCE(json_extract(data, '$.tokens.total'), 0) > 0{time_clause}"
            # D0.11（大会战 A1）：估算加 LIMIT 防大库拖死（CLI --estimate 路径）
            # E0.2：LIMIT 前补 ORDER BY created DESC——估算优先最新消息，否则
            # 按 rowid 取最早插入样本，旧模型价格停售导致 unpriced 占比偏高
            f" ORDER BY json_extract(data, '$.time.created') DESC LIMIT {TABLE_LIMIT_GROUP}",
            [ASSISTANT_ROLE] + time_params,
        ).fetchall()
        estimates: list[pricing.CostEstimate] = []
        for row in rows:
            tokens = {
                "input": to_int(row["input"]),
                "output": to_int(row["output"]),
                "cache_read": to_int(row["cache_read"]),
                "cache_write": to_int(row["cache_write"]),
            }
            if not any(tokens.values()):
                continue
            estimates.append(
                pricing.estimate_cost(
                    price_map,
                    str(row["provider"] or ""),
                    str(row["model"] or ""),
                    tokens,
                )
            )
        return estimates


def parse_time_arg(spec: str) -> datetime:
    # 解析时间参数：支持 '7d'/'2w'/'3h'/'5m' 相对时长或 ISO 日期；非法输入抛 ValueError
    # （E6 统一 strip；6A.1 E5：正则支持 m，注释/help 同步）
    spec = spec.strip()
    match = re.fullmatch(r"(\d+)([dhwm])", spec)
    if match:
        amount = min(
            int(match.group(1)), 100000
        )  # J0.1：相对时长上界钳制（防 timedelta OverflowError，H0.5 同模式）
        unit = match.group(2)
        now = datetime.now()
        if unit == "d":
            return now - timedelta(days=amount)
        if unit == "w":
            return now - timedelta(weeks=amount)
        if unit == "h":
            return now - timedelta(hours=amount)
        if unit == "m":
            return now - timedelta(minutes=amount)
    try:
        return datetime.fromisoformat(spec)
    except ValueError:
        raise ValueError(
            f"无法解析时间参数：{spec}（支持 7d/2w/3h/5m 或 ISO 日期）"
        ) from None


def _to_epoch_ms(dt: datetime) -> int:
    # datetime 转毫秒时间戳（聚合时间过滤用）
    return int(dt.timestamp() * _EPOCH_MS)


def main() -> None:
    # CLI 自测入口：打印用量统计（对照 opencode stats 用）
    parser = argparse.ArgumentParser(
        description="myboard 用量统计 CLI（对照 opencode stats 用）"
    )
    parser.add_argument("--db", default=None, help="opencode.db 路径（默认自动探测）")
    parser.add_argument(
        "--since", default=None, help="起始时间：7d/2w/3h/5m 或 ISO 日期（默认全部）"
    )
    parser.add_argument(
        "--by",
        default="total",
        choices=["total", "day", "month", "model", "provider", "agent", "session"],
        help="分组维度（默认 total 总览）",
    )
    parser.add_argument("--limit", type=int, default=20, help="分组结果行数上限")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument(
        "--estimate", action="store_true", help="对库 cost 缺失的消息做定价估算"
    )
    args = parser.parse_args()
    # H0.5：CLI --limit 钳制（负值会致 SQLite 报错、超大值全表驻留——开发自测路径）
    args.limit = max(1, min(args.limit, 10000))

    since_ms = None
    since_label = "全部"
    if args.since:
        try:
            since_dt = parse_time_arg(args.since)
            since_ms = _to_epoch_ms(since_dt)
            since_label = args.since
        except (
            ValueError,
            OverflowError,
        ) as exc:  # J0.1：双捕（钳制漏网的极端路径兜底）
            print(f"错误：{exc}", file=sys.stderr)
            sys.exit(1)

    try:
        if args.db:
            db = OpenCodeDB(Path(args.db))
        else:
            db = OpenCodeDB.auto()
    except FileNotFoundError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as exc:
        # S5：坏库/路径为目录时统一中文提示（防英文 traceback）
        print(f"错误：无法打开数据库（{exc}）", file=sys.stderr)
        sys.exit(1)

    try:
        if args.by == "total":
            summary = db.totals(since=since_ms, estimate=args.estimate)
            data = {
                "period": since_label,
                "sessions": summary.sessions,
                "messages": summary.messages,
                "days": summary.days,
                "tokens": flatten_tokens(summary.tokens),
                "recorded_cost": summary.recorded_cost,
                "estimated_cost_total": summary.estimated_cost_total,
                "estimated_cost_totals": summary.estimated_cost_totals,
                "cost_source": summary.cost_source,
            }
        else:
            methods = {
                "day": db.by_day,
                "month": db.by_month,
                "model": db.by_model,
                "provider": db.by_provider,
                "agent": db.by_agent,
                "session": db.by_session,
            }
            rows = methods[args.by](
                since=since_ms,
                limit=max(1, args.limit),  # B0.10：limit 下界
            )
            data = {
                "period": since_label,
                "rows": [
                    {
                        "label": r.label,
                        "calls": r.calls,
                        "tokens": flatten_tokens(r.tokens),
                        "cost": r.cost,
                    }
                    for r in rows
                ],
            }
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            for key, value in data.items():
                if key == "rows":
                    for row in value:
                        print(
                            f"  {row['label']}: {row['calls']} 次, "
                            f"tokens={row['tokens']['total']}, cost={row['cost']}"
                        )
                else:
                    print(f"{key}: {value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

# ===== modules/opencode_usage.py 模块说明 =====
# 模块级常量：
#   UNKNOWN_LABEL：分组缺失值显示（ui.json unknown_label 驱动，6A.3 H2）
#   DEFAULT_DB_PATH：XDG 默认数据库路径（%USERPROFILE%\.local\share\opencode\opencode.db）
#   ASSISTANT_ROLE：只统计 assistant 消息（user 消息无 token 数据）
#   _EPOCH_MS：毫秒换算基数（时间戳/分组表达式共用）
#   _DAY_MS：天毫秒数（_EPOCH_MS * 86400 派生）
#   SUBPROCESS_TIMEOUT：子进程探测超时（base.json subprocess_timeout）
#   TABLE_LIMIT_GROUP / TABLE_LIMIT_DAY：分组/按日查询行数上限（base.json 驱动，
#     各分组查询的默认 limit）
#   _TOKEN_SUM_SELECT：聚合列 SQL 模板（_base_sql 与 _query_grouped 共用，加字段只改一处）
#   _TOKEN_STATS_FIELDS / _USAGE_ROW_FIELDS：TokenStats/UsageRow 字段契约键集
#     （F0.3 补列——与 dataclass 字段导入期比对，防跨模块消费方 AttributeError）
# 类型：
#   TokenStats：token 五字段 + compute_total()（total 优先，五字段和兜底，兼容新旧格式）
#   UsageRow：分组行（label/calls/tokens/cost）
#   UsageSummary：总览（sessions/messages/days/tokens/cost 多口径 + cost_source 标注）
# 函数：
#   find_db_path()：三级探测——OPENCODE_DB 环境变量 → opencode db path 子进程
#     （shutil.which + base.json subprocess_timeout 驱动超时，失败返回 None）→
#     XDG 默认路径；参考 opencode-usage 的探测链，GUI 每次启动只需调用一次
#   _query_db_path_from_cli()：子进程查询 opencode db path（失败/超时返回 None）
#   OpenCodeDB：只读连接（mode=ro 防误写）+ row_factory；聚合入口——totals 总览 /
#     by_day（日期降序）/ by_month（%Y-%m 降序）/ by_model / by_provider / by_agent /
#     by_session（会话标题｜项目目录，LEFT JOIN session 表，缺列降级 session_id）；
#     内部经 _base_sql/_query_grouped/_time_clause/_day_expr/_month_expr 组合 SQL；
#     _has_session_columns（PRAGMA 结果实例缓存）；费用决策：库 cost 优先，
#     estimate=True 时对 cost=0 且 token 非零的消息逐条走 pricing.estimate_cost
#     （多币种分桶，E0.2：取最新样本 ORDER BY created DESC 再 LIMIT）；
#     totals 活动跨度：E0.4 time.created=0 记录归零并告警（防虚高数十年）；
#     _row_to_tokens/_row_to_usage_row/_fetch_one/_estimate_missing_costs
#     为行转换与查询辅助
#   parse_time_arg()：时间参数解析（7d/2w/3h/5m 相对或 ISO 日期）
#   _to_epoch_ms()：datetime 转毫秒时间戳（时间过滤用）
#   main()：CLI 自测（--db/--since/--by/--limit/--json/--estimate），供对照
#     `opencode stats` 验证数字一致性
# 设计理由：SQL 用 json_extract + COALESCE 聚合，不依赖 tokens.total 存在
#   （真实库新旧格式混合）；时间过滤参数化（毫秒半开区间）防注入；
#   费用两层口径：recorded（库值，权威）与 estimated（估算，仅缺失回退）
# 异常处理：连接只读不会写坏库；探测失败抛 FileNotFoundError 带提示；
#   子进程不可用/超时静默降级；CLI 解析错误打印用法退出码 1
# 关联配置：OPENCODE_DB 环境变量可覆盖数据库路径；config/static/base.json
#   （db_default_path/table_limit_group/table_limit_day/subprocess_timeout）；
#   ui.json（unknown_label 未知模型/Provider 标签）
