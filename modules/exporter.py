# 用量数据导出模块：CSV（UTF-8 BOM，Excel 直接打开）+ JSON（脚本处理）

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from config.static.static_config import get_static_config
from modules.opencode_usage import (
    OpenCodeDB,
    TokenStats,
    UsageRow,
    UsageSummary,
    flatten_tokens,
)
from utils.convert import round_cost
from utils.file_utils import write_json
from utils.logger import get_logger

logger = get_logger(__name__)

# 静态配置解包（S8：参数外置 base.json）
_SC = get_static_config()
EXPORT_LIMIT = int(_SC.base["export_limit"])
# R14：token 列名由 flatten_tokens 键推导（单一来源，加字段只改 TokenStats/flatten_tokens）
_TOKEN_COLUMNS = tuple(flatten_tokens(TokenStats(), prefix="tokens_").keys())
SUMMARY_CSV_COLUMNS = ("sessions", "messages", "days") + _TOKEN_COLUMNS + ("cost",)
GROUP_CSV_COLUMNS = ("label", "calls") + _TOKEN_COLUMNS + ("cost",)


def export_all(db: OpenCodeDB, out_dir: Path) -> Path:
    # 导出全部用量数据到 out_dir：summary + 六维度 CSV（UTF-8 BOM）+ usage.json
    # （P8 月份、P19 会话）
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = db.totals()
    datasets: dict[str, list[Any]] = {
        "summary": [_summary_to_row(summary)],
        "by_month": [_group_to_row(r) for r in db.by_month(limit=EXPORT_LIMIT)],
        "by_day": [_group_to_row(r) for r in db.by_day(limit=EXPORT_LIMIT)],
        "by_model": [_group_to_row(r) for r in db.by_model(limit=EXPORT_LIMIT)],
        "by_provider": [_group_to_row(r) for r in db.by_provider(limit=EXPORT_LIMIT)],
        "by_agent": [_group_to_row(r) for r in db.by_agent(limit=EXPORT_LIMIT)],
        "by_session": [_group_to_row(r) for r in db.by_session(limit=EXPORT_LIMIT)],
    }
    summary_columns = SUMMARY_CSV_COLUMNS
    group_columns = GROUP_CSV_COLUMNS
    # C16：单次遍历完成 CSV 写入与 JSON 组装（C17：CSV 数量动态计算）
    json_payload: dict[str, Any] = {
        "exported_at": datetime.now().isoformat(timespec="seconds")
    }
    for name, rows in datasets.items():
        if name == "summary":
            json_payload[name] = rows[0]
            _write_csv(out_dir / "summary.csv", summary_columns, rows)
        else:
            _write_csv(out_dir / f"{name}.csv", group_columns, rows)
            json_payload[name] = rows
    write_json(out_dir / "usage.json", json_payload)
    logger.info("导出完成：%s（%d 个 CSV + 1 个 JSON）", out_dir, len(datasets))
    return out_dir


def _summary_to_row(summary: UsageSummary) -> dict[str, Any]:
    # 总览转 CSV/JSON 行（token 六字段平铺）
    row = flatten_tokens(summary.tokens, prefix="tokens_")
    row.update(
        {
            "sessions": summary.sessions,
            "messages": summary.messages,
            "days": summary.days,
            "cost": round_cost(summary.recorded_cost),
        }
    )
    return row


def _group_to_row(row: UsageRow) -> dict[str, Any]:
    # 分组行转 CSV/JSON 行（token 六字段平铺）
    flat = flatten_tokens(row.tokens, prefix="tokens_")
    flat.update({"label": row.label, "calls": row.calls, "cost": round_cost(row.cost)})
    return flat


def _write_csv(
    path: Path, columns: tuple[str, ...], rows: list[dict[str, Any]]
) -> None:
    # 写 CSV 文件：utf-8-sig（UTF-8 BOM）让 Excel 打开中文不乱码
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows(rows)


# ===== modules/exporter.py 模块说明 =====
# 模块级常量：
#   EXPORT_LIMIT：分组导出行数上限（10 万行，防超长表）
#   _TOKEN_COLUMNS：token 列名（由 flatten_tokens 键推导，单一来源）
#   SUMMARY_CSV_COLUMNS / GROUP_CSV_COLUMNS：CSV 固定列顺序（由 _TOKEN_COLUMNS 推导）
# 函数：
#   export_all(db, out_dir)：主入口——
#     查询 totals + 六维度分组 → 写 7 个 CSV（summary/by_month/by_day/by_model/
#     by_provider/by_agent/by_session，P8 月份、P19 会话）+ usage.json → 返回输出目录
#   _summary_to_row / _group_to_row：dataclass 转平铺 dict（复用
#     opencode_usage.flatten_tokens(prefix="tokens_") + cost 等扩展字段）
#   _write_csv：utf-8-sig（UTF-8 BOM）——Excel 按 UTF-8 识别中文不乱码
#     （参考 OpenCode-Token exporter 的产品决策）
#   JSON 写入复用 utils/file_utils.write_json（原子写，审计 D3 消重）
# 设计理由：导出数据与 GUI 展示解耦（CLI/脚本/未来功能可复用）；
#   CSV 面向人（Excel/报表/归档），JSON 面向程序（jq/图表/迁移）
# 异常处理：IO 异常由调用方处理（GUI 状态栏提示 / CLI 打印）
# 关联配置：config/static/base.json（export_limit 导出行数上限，B3.1 补列）
