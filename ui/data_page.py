# 数据与动态页签（PL002）：纯展示层——官方动态卡 + 五表格（时序/Token 成本/缓存比/
# 会话成本/国家分布），只消费数据层快照结果，零网络零解析

from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config.static.static_config import get_static_config

# 静态配置解包（S8：参数外置 ui.json）
_SC = get_static_config()
DATA_PAGE_TAB_TITLE = str(_SC.ui["data_page_tab_title"])
DATA_RELEASES_TITLE = str(_SC.ui["data_releases_title"])
DATA_DAILY_TITLE = str(_SC.ui["data_daily_title"])
DATA_BLOCKS_TITLE = str(_SC.ui["data_blocks_title"])
DATA_EMPTY_TEXT = str(_SC.ui["data_empty_text"])
DATA_RELEASES_EMPTY = str(_SC.ui["data_releases_empty"])
_DATA_TABLE_HEADERS: dict[str, list[str]] = {
    str(key): [str(item) for item in value]
    for key, value in _SC.ui["data_table_headers"].items()
}

# 列字段键集（P23 契约惯例：代码内显式声明 + 导入期自校验，不随表头外置）
DAILY_COLUMN_IDS = ("date", "total_t", "models")
TOKEN_COST_COLUMN_IDS = ("model", "total", "input", "output", "cached")
CACHE_RATIO_COLUMN_IDS = ("model", "ratio", "cached", "uncached", "total")
SESSION_COST_COLUMN_IDS = ("model", "cost", "tokens")
COUNTRY_COLUMN_IDS = ("country", "continent", "tokens", "share")

# 导入期契约校验：表头标题数量与列字段键数一致（防 ui.json 错位，C0.6 同机制）
_BLOCK_TABLES = (
    ("tokenCost", TOKEN_COST_COLUMN_IDS),
    ("cacheRatio", CACHE_RATIO_COLUMN_IDS),
    ("sessionCost", SESSION_COST_COLUMN_IDS),
    ("country", COUNTRY_COLUMN_IDS),
)
for _key, _column_ids in (("daily", DAILY_COLUMN_IDS),) + _BLOCK_TABLES:
    _header_count = len(_DATA_TABLE_HEADERS.get(_key, []))
    if _header_count != len(_column_ids):
        raise RuntimeError(
            f"data_table_headers[{_key}] 列数 {_header_count} 与列字段键数 "
            f"{len(_column_ids)} 不一致（契约校验）"
        )


class DataPage(QWidget):
    # 数据与动态页签：官方动态卡 + 五表格（懒加载标志 has_loaded 供装配层触发拉取）

    def __init__(self, parent: QWidget | None = None) -> None:
        # 初始化：滚动区骨架 + 官方动态卡 + 五表格（列头固定，空数据占位）
        super().__init__(parent)
        # 懒加载标志：首次数据灌入后置 True（装配层据此只拉取一次）
        self.has_loaded = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        container = QWidget()
        container.setObjectName("dataPage")
        self._box = QVBoxLayout(container)
        self._box.setContentsMargins(12, 12, 12, 12)
        self._box.setSpacing(12)
        scroll.setWidget(container)

        # 官方动态卡：版本号粗体 + 发布日期 + 正文只读
        releases_frame = QFrame()
        releases_frame.setObjectName("card")
        releases_box = QVBoxLayout(releases_frame)
        releases_title = QLabel(DATA_RELEASES_TITLE)
        releases_title.setObjectName("section_title")
        releases_box.addWidget(releases_title)
        self._releases_label = QLabel(DATA_RELEASES_EMPTY)
        self._releases_label.setWordWrap(True)
        self._releases_label.setObjectName("card_title")
        releases_box.addWidget(self._releases_label)
        self._releases_body = QTextEdit()
        self._releases_body.setReadOnly(True)
        self._releases_body.setMaximumHeight(140)
        self._releases_body.setObjectName("dataPageReleasesBody")
        releases_box.addWidget(self._releases_body)
        self._box.addWidget(releases_frame)

        # 热门模型时序表
        daily_title = QLabel(DATA_DAILY_TITLE)
        daily_title.setObjectName("section_title")
        self._box.addWidget(daily_title)
        self._daily_table = QTableWidget(0, len(DAILY_COLUMN_IDS))
        self._daily_table.setHorizontalHeaderLabels(_DATA_TABLE_HEADERS["daily"])
        # O3.6：表格静态属性收敛 init 单点一次（原填充/占位分支每次重复设置，
        # 且初始占位漏设 NoEditTriggers 致占位格可编辑）
        self._daily_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._daily_table.setAlternatingRowColors(True)
        self._box.addWidget(self._daily_table)

        # 四数据块表
        blocks_title = QLabel(DATA_BLOCKS_TITLE)
        blocks_title.setObjectName("section_title")
        self._box.addWidget(blocks_title)
        self._block_tables: dict[str, QTableWidget] = {}
        for key, column_ids in _BLOCK_TABLES:
            table = QTableWidget(0, len(column_ids))
            table.setHorizontalHeaderLabels(_DATA_TABLE_HEADERS[key])
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
            self._block_tables[key] = table
            self._box.addWidget(table)

        self._populate_placeholder()

    def set_releases(self, items: list[dict[str, Any]]) -> None:
        # 渲染官方动态：版本号/日期列表 + 最新一条正文（空列表显示占位）
        if not items:
            self._releases_label.setText(DATA_RELEASES_EMPTY)
            self._releases_body.clear()
            return
        first = items[0]
        tag = first.get("tag_name", "")
        date = str(first.get("published_at", ""))[:10]
        self._releases_label.setText(f"{tag}　{date}")
        body = str(first.get("body", "") or "")
        self._releases_body.setPlainText(body if body else DATA_RELEASES_EMPTY)

    def set_daily_usage(self, rows: list[dict[str, Any]]) -> None:
        # 渲染热门模型时序表（日期/总量 T/模型占比拼接）
        self._populate_table(
            self._daily_table,
            rows,
            DAILY_COLUMN_IDS,
            self._format_cell,
        )

    def set_model_data(self, blocks: dict[str, list[dict[str, Any]]]) -> None:
        # 渲染四数据块表（tokenCost/cacheRatio/sessionCost/country）
        for key, column_ids in _BLOCK_TABLES:
            table = self._block_tables[key]
            rows = blocks.get(key, [])
            self._populate_table(table, rows, column_ids, self._format_cell)

    def _populate_table(
        self,
        table: QTableWidget,
        rows: list[dict[str, Any]],
        column_ids: tuple[str, ...],
        formatter: Callable[[str, Any], str],
    ) -> None:
        # 通用表格填充：行数同步 + 逐格格式化（缺字段兜底空串）
        if not rows:
            # N3.5/O0.1：空结果单行占位（避免空白表格）；列结构与中文表头
            # 已由 __init__ 固定，此处不得覆写（否则表头永久变英文键名）
            table.setRowCount(1)
            table.setItem(0, 0, QTableWidgetItem(DATA_EMPTY_TEXT))
            return
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, column_id in enumerate(column_ids):
                value = row.get(column_id) if isinstance(row, dict) else None
                item = QTableWidgetItem(formatter(column_id, value))
                table.setItem(row_index, col_index, item)

    def _populate_placeholder(self) -> None:
        # 空数据占位：各表格首行填"尚未获取数据"（单行）
        for table in (self._daily_table, *self._block_tables.values()):
            table.setRowCount(1)
            item = QTableWidgetItem(DATA_EMPTY_TEXT)
            table.setItem(0, 0, item)

    @staticmethod
    def _format_cell(column_id: str, value: Any) -> str:
        # 单元格格式化：T 单位/百分比/模型占比拼接/数值规整；None 兜底空串
        if value is None:
            return ""
        if column_id == "total_t":
            if not isinstance(value, (int, float)):
                return str(value)
            return f"{value:.1f}T"
        if column_id in ("ratio", "share"):
            if not isinstance(value, (int, float)):
                return str(value)
            return f"{value:.1f}%"
        if column_id == "models":
            if not isinstance(value, dict):
                return str(value)
            top = sorted(value.items(), key=lambda pair: pair[1], reverse=True)[:4]
            return " · ".join(f"{name} {pct:.1f}%" for name, pct in top)
        if isinstance(value, float):
            text = f"{value:.4f}".rstrip("0").rstrip(".")
            return text if text else "0"
        return str(value)


# ===== ui/data_page.py 模块说明 =====
# 模块级常量：
#   DATA_PAGE_TAB_TITLE/DATA_RELEASES_TITLE/DATA_DAILY_TITLE/DATA_BLOCKS_TITLE/
#   DATA_EMPTY_TEXT/DATA_RELEASES_EMPTY：页签/区块标题与占位文案（ui.json 驱动）
#   _DATA_TABLE_HEADERS：五表列头标题（ui.json 驱动）
#   DAILY_COLUMN_IDS/TOKEN_COST_COLUMN_IDS/CACHE_RATIO_COLUMN_IDS/
#   SESSION_COST_COLUMN_IDS/COUNTRY_COLUMN_IDS：列字段键集（P23 契约：代码内声明，
#     表头标题数量与之导入期校验，防 ui.json 错位）
# 类型：DataPage——数据与动态页签（纯展示，零网络零解析）
# 方法：
#   __init__：滚动区骨架 + 官方动态卡（版本/日期/正文只读）+ 五表格（列头固定）+
#     空数据占位；has_loaded 懒加载标志供装配层触发
#   set_releases/set_daily_usage/set_model_data：三纯渲染入口（数据层快照结构直接
#     灌入，零解析）
#   _populate_table：通用填充（行数同步 + 逐格 formatter）
#   _populate_placeholder：空数据占位文案
#   _format_cell：单元格格式化（T/百分比/模型占比/数值规整；None 兜底空串）
# 设计理由：与数据层三层分离——主题取舍点集中在 objectName（dataPage 系列）供
#   QSS（P25 拟物化重构只动主题层）
# 异常处理：渲染路径无网络/解析，缺字段兜底空串；导入期契约校验抛 RuntimeError
# 关联配置：config/static/ui.json（data_page_tab_title/data_*_title/data_empty_text/
#   data_table_headers）
