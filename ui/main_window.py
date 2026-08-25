# 主窗口模块：用量总览卡片 + Go 配额进度条 + 分组表格 + 后台加载与定时刷新

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import (
    QByteArray,
    QPoint,
    QThreadPool,
    QTimer,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QCloseEvent, QColor, QPaintEvent, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.settings import load_config, save_config
from config.static.static_config import get_static_config

# A017/PL006：仅保留 DTO 类型注解用途的 modules import（函数调用与运行时常量
# 一律走 services 门面；M1.3：ERROR_STAGE_*/QUOTA_WINDOW_KEYS 改由 services 再导出）
from modules.go_quota import GoQuotaInfo
from services.service import (
    ERROR_STAGE_AUTH,
    ERROR_STAGE_NO_CREDS,
    QUOTA_WINDOW_KEYS,
)
from modules.opencode_usage import TokenStats, UsageRow, UsageSummary
from modules.opencode_data import ModelDataSnapshot
from services import get_service
from services.service import DIMENSIONS, ServiceError, UsageData
from ui.data_page import DATA_PAGE_TAB_TITLE, DataPage
from ui.task_runner import TaskRunner
from ui.theme_loader import (
    DEFAULT_THEME_NAME,
    THEME_DISPLAY_NAMES,
    THEME_NAMES,
    get_palette,
    get_theme,
    quota_chunk_color,
)
from utils.logger import build_app_title, get_logger

logger = get_logger(__name__)

# 静态配置解包（S8：参数外置 base.json，运行时零 IO）
_SC = get_static_config()
AUTO_LOAD_DELAY_MS = int(_SC.base["auto_load_delay_ms"])
# L9：剩余量饼图参数（ui.json 驱动；PL003.1.d 起 bg/text 色随主题 palette，
# 模块级仅保留默认主题色作初始值）
PIE_SIZE = int(_SC.ui["pie_size"])
PIE_FONT_SIZE = float(_SC.ui["pie_font_size"])
_DEFAULT_PALETTE = get_palette(DEFAULT_THEME_NAME)
# 默认主题饼图色（palette 必含 pie_bg/pie_text——themes 动态色契约校验兜底）
PIE_COLOR_BG_DEFAULT = str(_DEFAULT_PALETTE["pie_bg"])
PIE_COLOR_TEXT_DEFAULT = str(_DEFAULT_PALETTE["pie_text"])
# PL004.3：配额账户选择器文案（ui.json 驱动）
QUOTA_ACCOUNT_LABEL = str(_SC.ui["quota_account_label"])
QUOTA_ACCOUNT_UNKNOWN = str(_SC.ui["quota_account_unknown"])
# PL005.1：添加账户常驻入口按钮文案（ui.json 驱动）
QUOTA_ADD_ACCOUNT_BUTTON = str(_SC.ui["quota_add_account_button"])
# PL002.11：页签名（ui.json 驱动）
USAGE_TAB_TITLE = str(_SC.ui["usage_tab_title"])
DATA_PAGE_ERROR_TEMPLATE = str(_SC.ui["data_page_error_template"])
# PL003.2/PL007：主题显示名映射（theme.json display_name，键集契约由
# theme_loader 导入期 C0.6 校验保证与注册表一致）
THEME_LABELS = THEME_DISPLAY_NAMES
# C11：饼图绘制角度常量（Qt 角度单位 1/16 度；90°=12 点方向起点）
PIE_START_ANGLE = 90 * 16
FULL_CIRCLE_16 = 360 * 16
# C22：布局参数外置（边距/间距/配额名称列宽）；C11：卡片区间距/重置时间格式
LAYOUT_MARGINS = tuple(int(v) for v in _SC.ui["layout_margins"])
LAYOUT_SPACING = int(_SC.ui["layout_spacing"])
QUOTA_NAME_WIDTH = int(_SC.ui["quota_name_width"])
CARDS_SPACING = int(_SC.ui["cards_spacing"])
RESET_TIME_FORMAT = str(_SC.ui["reset_time_format"])

# 分组维度与表格列配置（表头文案外置 ui.json，S8.3）
# P15：总览已移出维度下拉（独立显示 + 点击弹明细），保留 total 数据供弹窗用
# D5：维度标签/配额窗口标签/引导卡片文案外置 ui.json
# M1.2：DIMENSIONS 由 services.service 单点导出（编排与 UI 同源，消除双份字面量漂移）
DIMENSION_LABELS = dict(_SC.ui["dimension_labels"])
QUOTA_WINDOW_LABELS = dict(_SC.ui["quota_window_labels"])
GUIDE_CARD_TEXT = str(_SC.ui["guide_card_text"])
GUIDE_AUTO_BUTTON = str(_SC.ui["guide_auto_button"])
GUIDE_MANUAL_BUTTON = str(_SC.ui["guide_manual_button"])
# R5：窗口标题中段统一来自 ui.json（主窗口标题与托盘 tooltip 共用）
# A1.1：标题拼接单点 utils.logger.build_app_title（本文件不再本地解包 APP_SUBTITLE）
# 5A.3 C3/C4/C5：文案外置（卡片标题/区域标题/按钮/tooltip/状态栏/对话框/前缀）
TOTAL_TOKEN_PREFIX = str(_SC.ui["total_token_prefix"])
CARD_TITLES = dict(_SC.ui["card_titles"])
QUOTA_SECTION_TITLE = str(_SC.ui["quota_section_title"])
DETAIL_SECTION_TITLE = str(_SC.ui["detail_section_title"])
BUTTON_LABELS = dict(_SC.ui["button_labels"])
TOOLTIPS = dict(_SC.ui["tooltips"])
STATUS_MESSAGES = dict(_SC.ui["status_messages"])
DIALOG_TITLES = dict(_SC.ui["dialog_titles"])
DIALOG_PROMPTS = dict(_SC.ui["dialog_prompts"])
PIE_REMAINING_TEMPLATE = str(_SC.ui["pie_remaining_template"])
GUIDE_MESSAGES = dict(_SC.ui["guide_messages"])
DETAIL_LINE_TEMPLATES = dict(_SC.ui["detail_line_templates"])
# 6A.3 H5/H6：容差/单位/时间格式外置（ui.json 单一来源）
COST_ZERO_EPSILON = float(_SC.ui["cost_zero_epsilon"])
TOTAL_TOKENS_UNIT = str(_SC.ui["total_tokens_unit"])
TOTAL_TOKENS_UNIT_THRESHOLD = float(_SC.ui["total_tokens_unit_threshold"])
STATUS_TIME_FORMAT = str(_SC.ui["status_time_format"])
# A2.1：K/M/B/G 缩写单位外置（阈值→后缀映射；B2.1：显式按阈值降序排序，
# 消除对 JSON 键序的隐含依赖——调乱键序不再导致缩略错值）
TOKEN_ABBR_UNITS = tuple(
    sorted(
        (
            (float(threshold), suffix)
            for threshold, suffix in dict(_SC.ui["token_abbr_units"]).items()
        ),
        reverse=True,
    )
)
# PL003.4：列元数据外置——table_columns [{id, title, width?, visible?}]，
# 数组顺序即展示顺序；TABLE_HEADERS 从 title 派生单源化（删除平行数组防错位）
_TABLE_COLUMNS: list[dict[str, Any]] = [
    {str(key): value for key, value in item.items()} for item in _SC.ui["table_columns"]
]
TABLE_HEADERS = tuple(str(item["title"]) for item in _TABLE_COLUMNS)
# 列模型：id 与 TABLE_HEADERS 索引对齐（P13 列顺序 + P18 缓存率；列开关用 id）
COLUMN_IDS = (
    "label",
    "total",
    "calls",
    "input",
    "output",
    "reasoning",
    "cache",
    "cache_rate",
    "cost",
)
# PL003.4.c：columns id 集合与 COLUMN_IDS 严格相等（P23 契约定案：键名仍在代码，
# 外置仅展示元数据；防加列/删列/改 id 静默错位）
_TABLE_COLUMN_IDS = tuple(str(item["id"]) for item in _TABLE_COLUMNS)
if tuple(_TABLE_COLUMN_IDS) != COLUMN_IDS:
    raise RuntimeError(
        f"ui.json table_columns id 序列与 COLUMN_IDS 不一致："
        f"{_TABLE_COLUMN_IDS} vs {COLUMN_IDS}"
    )

# B0.6：ui.json 结构性键契约校验（配置删键/改键 → 导入期抛错，防运行时 KeyError/IndexError；
# C0.8：键集扩至全部消费键（含 system_tray/main.py 消费的文案组））
_UI_STRUCT_KEYS = (
    ("card_titles", ("tokens", "input", "output", "cache_rate", "cost"), CARD_TITLES),
    ("quota_window_labels", tuple(QUOTA_WINDOW_KEYS), QUOTA_WINDOW_LABELS),
    ("dimension_labels", DIMENSIONS, DIMENSION_LABELS),
    (
        "detail_line_templates",
        (
            "sessions",
            "messages",
            "days",
            "input",
            "output",
            "reasoning",
            "cache_read",
            "cache_write",
            "cache_rate",
            "cost",
        ),
        DETAIL_LINE_TEMPLATES,
    ),
    (
        "status_messages",
        (
            "loading",
            "refreshing",
            "no_db_found",
            "updated_template",
            "usage_not_loaded",
            "creds_saved",
            "creds_save_failed",
            "no_db_export",
            "exporting",
            "guide_starting",
            "not_fetched",
            "reset_template",
            "cached_prefix",
            "warn_prefix",
            "usage_failed_template",
            "quota_failed_template",
            "export_done_template",
            "export_failed_template",
        ),
        STATUS_MESSAGES,
    ),
    (
        "dialog_titles",
        ("total_detail", "manual_creds", "export_dir"),
        DIALOG_TITLES,
    ),
    (
        "dialog_prompts",
        ("workspace_id", "auth_cookie"),
        DIALOG_PROMPTS,
    ),
    (
        "guide_messages",
        (
            "v10_detect",
            "launch_failed",
            "cdp_not_ready",
            "login_timeout_template",
            "creds_saved_template",
            "auto_fetch_failed",
        ),
        GUIDE_MESSAGES,
    ),
    ("tooltips", ("total_detail", "columns", "pie_remaining"), TOOLTIPS),
    (
        "button_labels",
        ("refresh", "export", "settings"),
        BUTTON_LABELS,
    ),
    ("menu_labels", ("show_window", "refresh", "quit"), dict(_SC.ui["menu_labels"])),
    # F0.1：go_quota_error_messages 组入契约（go_quota 消费方裸读 _SC.ui，
    # 删键将运行时 KeyError——B0.6/C0.8 历史遗漏 + E2.1 新增键未同步）
    (
        "go_quota_error_messages",
        ("no_credentials", "in_flight"),
        dict(_SC.ui["go_quota_error_messages"]),
    ),
)
for _cfg_name, _required, _actual in _UI_STRUCT_KEYS:
    _missing = [k for k in _required if k not in _actual]
    if _missing:
        raise RuntimeError(f"ui.json {_cfg_name} 缺少必需键：{_missing}")
# D0.7：notify_title 为标量键，单独契约校验（main.py 消费，C0.8 键集遗漏补全）
if "notify_title" not in _SC.ui:
    raise RuntimeError("ui.json 缺少必需键：notify_title")
# H0.8：notify 模板键入契约——删键从运行时兜底改导入期报错（与 C0.8
# "键集扩至全部消费键"宣称对齐；P24 定案选项 X'：fallback 键随三层链
# 单层化移除，仅保留主模板键）
for _notify_key in ("notify_message_template",):
    if _notify_key not in _SC.ui:
        raise RuntimeError(f"ui.json 缺少必需键：{_notify_key}")
# C0.7：TABLE_HEADERS 与 COLUMN_IDS 严格相等（防短防长——加列后多出列渲染为空且列开关无法控制；
# PL003.4 起 TABLE_HEADERS 从 table_columns title 派生，此校验与 id 序列校验双保险）
if len(TABLE_HEADERS) != len(COLUMN_IDS):
    raise RuntimeError(
        f"table_columns title 数量与 COLUMN_IDS 不一致"
        f"（需要 {len(COLUMN_IDS)}，实际 {len(TABLE_HEADERS)}）"
    )
# C0.8：模板类键占位符校验（花括号配对 + 无未知命名占位符，format_map 统一探测；
# D0.5：并入 pie_remaining_template/detail_line_templates，补 value/percent 占位符）
_TEMPLATE_PLACEHOLDERS = {
    "time": "",
    "error": "",
    "dir": "",
    "used": 0,
    "remaining": 0,
    "percent": 0,
    "minutes": 0,
    "workspace_id": "",
    "value": "",
}
_TEMPLATE_MAP = {
    **{f"status.{k}": v for k, v in STATUS_MESSAGES.items() if "{" in v},
    **{f"guide.{k}": v for k, v in GUIDE_MESSAGES.items() if "{" in v},
    "pie_remaining_template": PIE_REMAINING_TEMPLATE,
    **{f"detail.{k}": v for k, v in DETAIL_LINE_TEMPLATES.items()},
    "notify_message_template": str(_SC.ui.get("notify_message_template", "")),
}
for _tname, _tmpl in _TEMPLATE_MAP.items():
    try:
        _tmpl.format_map(_TEMPLATE_PLACEHOLDERS)
    except (KeyError, ValueError, IndexError) as _exc:
        raise RuntimeError(f"ui.json 模板键 {_tname} 占位符异常：{_exc}") from None


# F0.2：usage 任务在途/待补发标志（连点去重——跨线程读写由 GIL 保证原子，
# 与 go_quota._fetch_in_flight 同式；A017/PL006 起复位逻辑经 usage 任务包装函数
# 的 finally 单点保持，H0.6 时序结论不变）
_usage_task_in_flight = False
_usage_pending = False


class _RemainingPieChart(QWidget):
    # 剩余量饼图：分级色圆弧（随用量三档变色，A017/L0.1）+ 中心"剩余 Y%"标注
    # （P16，替换"最紧窗口"文字位）

    def __init__(self, parent: QWidget | None = None) -> None:
        # 初始化：已用比例为 0，尺寸/色值/字号由 ui.json 驱动（L9）；
        # PL003.1.d：背景/文字色为实例属性（随主题 set_colors 更新）
        super().__init__(parent)
        self._used_percent = 0.0
        self._bg_color = QColor(PIE_COLOR_BG_DEFAULT)
        self._text_color = QColor(PIE_COLOR_TEXT_DEFAULT)
        self._theme_name = DEFAULT_THEME_NAME
        self._arc_color = QColor(quota_chunk_color(0, DEFAULT_THEME_NAME))
        self.setFixedSize(PIE_SIZE, PIE_SIZE)
        self.setToolTip(TOOLTIPS["pie_remaining"])

    def set_colors(self, bg: QColor, text: QColor, theme_name: str) -> None:
        # 更新饼图背景/文字色并重绘（PL003.1.d：切主题时随调色板同步）；
        # A017/L0.1：弧色不再外部传入——控件按主题名 + 当前用量三档自算
        # （与进度条 quota_chunk_color 同源同档，高用量同步警示）
        self._bg_color = bg
        self._text_color = text
        self._theme_name = theme_name
        self._sync_arc_color()
        self.update()

    def set_used_percent(self, percent: float) -> None:
        # 更新已用比例并重绘（0-100 截断，越界防御）；A017/L0.1：弧色随用量联动
        self._used_percent = max(0.0, min(100.0, percent))
        self._sync_arc_color()
        self.update()

    def _sync_arc_color(self) -> None:
        # 弧色单点计算：<60% 绿 / 60-80% 黄 / ≥80% 红（quota_chunk_color 三档，
        # 与进度条 chunk 同源同主题——高用量时饼图与进度条同步警示）
        used_int = int(round(self._used_percent))
        self._arc_color = QColor(quota_chunk_color(used_int, self._theme_name))

    def used_percent(self) -> float:
        # 返回当前已用比例（外部读取/测试用）
        return self._used_percent

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        # 自绘：浅色底（剩余）→ 分级色圆弧（已用，A017/L0.1）→ 中心"剩余 Y%"文字
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(3, 3, -3, -3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bg_color)
        painter.drawEllipse(rect)
        used = self._used_percent / 100.0
        # C10：int(round()) 提局部变量（圆弧颜色/剩余文字共用同一口径）
        used_percent_int = int(round(self._used_percent))
        if used > 0:
            painter.setBrush(self._arc_color)
            painter.drawPie(rect, PIE_START_ANGLE, -int(used * FULL_CIRCLE_16))
        painter.setPen(self._text_color)
        font = painter.font()
        font.setPointSizeF(PIE_FONT_SIZE)
        painter.setFont(font)
        remaining = max(0, 100 - used_percent_int)
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            PIE_REMAINING_TEMPLATE.format(percent=remaining),
        )


def _format_tokens(count: int) -> str:
    # token 数格式化：K/M/B/G 缩写（阈值与后缀来自 ui.json token_abbr_units，A2.1）
    for threshold, suffix in TOKEN_ABBR_UNITS:
        if count >= threshold:
            return f"{count / threshold:.1f}{suffix}"
    return str(count)


def _format_cost(cost: float) -> str:
    # 费用格式化：≥1 保留 2 位，<1 保留 4 位；近零显示 -（浮点容差 ui.json 驱动，5A.1 E5）
    if cost < COST_ZERO_EPSILON:
        return "-"
    if cost >= 1:
        return f"${cost:.2f}"
    return f"${cost:.4f}"


def _cache_rate_percent(tokens: TokenStats) -> float:
    # 缓存率计算：(缓存读+缓存写)/总 token 的百分比（P17 卡片与 P18 表格共用）
    total = tokens.compute_total()
    if total <= 0:
        return 0.0
    return (tokens.cache_read + tokens.cache_write) / total * 100


def _format_cache_rate(percent: float) -> str:
    # 缓存率格式化：一位小数百分比（如 56.2%）
    return f"{percent:.1f}%"


def _format_cache_rate_of(tokens: TokenStats) -> str:
    # 缓存率计算+格式化复合（6A.3 O3：卡片/明细弹窗/表格 3 处组合收敛）
    return _format_cache_rate(_cache_rate_percent(tokens))


def _format_total_tokens(count: int) -> str:
    # 总览总 token 显示：个位数精确 + 千分位 + 亿单位（P15，如 12,345,678（0.12 亿））
    if count >= TOTAL_TOKENS_UNIT_THRESHOLD:
        return f"{count:,}（{count / TOTAL_TOKENS_UNIT_THRESHOLD:.2f} {TOTAL_TOKENS_UNIT}）"
    return f"{count:,}"


class MainWindow(QMainWindow):
    # myboard 主窗口：装配卡片/配额/表格 + 后台加载 + 定时刷新 + 主题切换

    quota_updated = pyqtSignal(
        object
    )  # 配额加载完成信号（托盘图标/预警接线用；PL001.8 起载荷为 list[GoQuotaInfo]）

    def __init__(
        self,
        db_path: Path | None = None,
        quota_fetcher: Callable[..., list[GoQuotaInfo]] | None = None,
    ) -> None:
        # 初始化窗口：探测数据库、装配 UI、启动延迟加载与定时器；
        # A017/PL006：后端调用一律走 services 门面（quota_fetcher 可注入供测试）
        super().__init__()
        self._service = get_service()
        self.db_path = (
            db_path if db_path is not None else self._service.resolve_db_path()
        )
        self.quota_fetcher = quota_fetcher or self._service.get_quotas
        self._usage_data: UsageData | None = None
        self._pending_auto_load = False
        # B0.5：刷新序号（任务乱序完成时丢弃过期结果）
        self._refresh_seq = 0
        # globalInstance 可能返回 None（PyQt6 stub Optional），兜底新建实例
        self._pool = QThreadPool.globalInstance() or QThreadPool()
        # A017/PL006：每职责一个 TaskRunner 实例，信号直连对应 handler 零分发
        # （M11 结构保留：状态栏先建，导出/失败消息直连 showMessage）
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._usage_runner = TaskRunner(self._pool, self)
        self._usage_runner.finished.connect(self._on_usage_ready)
        self._usage_runner.failed.connect(self._on_load_error)
        self._quota_runner = TaskRunner(self._pool, self)
        self._quota_runner.finished.connect(self._on_quota_ready)
        self._quota_runner.failed.connect(self._on_quota_failed)
        self._data_runner = TaskRunner(self._pool, self)
        self._data_runner.finished.connect(self._on_data_ready)
        self._data_runner.failed.connect(self._on_data_error)
        self._export_runner = TaskRunner(self._pool, self)
        self._export_runner.finished.connect(self._on_export_done)
        self._export_runner.failed.connect(
            lambda _seq, msg: self._status_bar.showMessage(
                STATUS_MESSAGES["export_failed_template"].format(error=msg)
            )
        )
        self._guide_runner = TaskRunner(self._pool, self)
        self._guide_runner.finished.connect(self._on_guide_done)
        self._guide_runner.failed.connect(self._on_guide_failed)
        self._data_page_seq = 0
        # A0.6/A0.7：CDP 引导进行中标志（抑制引导卡重现 + 禁用手动填写防并发写）
        self._guide_active = False

        self.setWindowTitle(build_app_title())
        self.resize(int(_SC.base["window_width"]), int(_SC.base["window_height"]))
        # 恢复配置：主题/窗口几何（S5 配置持久化）
        self._config = load_config()
        # PL003.1.f：主题名字符串（settings 白名单已保证合法；N 主题支持）
        self._theme_name = self._config.theme or DEFAULT_THEME_NAME
        # 列开关状态（P13：持久化于用户配置 hidden_columns）
        self._hidden_columns: set[str] = set(self._config.hidden_columns)
        # 最近一次配额 infos 缓存（PL004.3：切换选择时免网络重渲染）
        self._last_infos: list[GoQuotaInfo] = []
        # 待自动选中的新添加账户（PL005.2：一次性标志，匹配成功后清除）
        self._pending_quota_account = ""
        if self._config.window_geometry:
            self.restoreGeometry(
                QByteArray.fromHex(self._config.window_geometry.encode())
            )
        self._build_ui()
        self._apply_theme()
        self._status_bar.showMessage(STATUS_MESSAGES["loading"])

        # 启动延迟加载（手动刷新会取消该调度，防双加载）
        self._pending_auto_load = True
        QTimer.singleShot(AUTO_LOAD_DELAY_MS, self._trigger_auto_load)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(self._config.refresh_interval_ms)

    def _build_ui(self) -> None:
        # 装配界面：QTabWidget 两页（PL002.11：用量监控 = 现有卡片区+配额区+引导卡+
        # 明细区整体迁入只换父容器；数据与动态 = DataPage 懒加载）
        central = QWidget()
        self.setCentralWidget(central)
        tabs = QTabWidget()
        self._tabs = tabs
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.addWidget(tabs)
        usage_tab = QWidget()
        self._layout = QVBoxLayout(usage_tab)
        self._layout.setContentsMargins(*LAYOUT_MARGINS)
        self._layout.setSpacing(LAYOUT_SPACING)
        tabs.addTab(usage_tab, USAGE_TAB_TITLE)
        # PL002.10：数据与动态页（首次切换触发懒加载，has_loaded 幂等）
        self._data_page = DataPage()
        tabs.addTab(self._data_page, DATA_PAGE_TAB_TITLE)
        tabs.currentChanged.connect(self._on_tab_changed)
        self._build_cards()
        self._build_quota_section()
        self._build_guide_card()
        self._build_detail_section()
        # _status_bar 已在 __init__ 信号连接区提前创建（M11 结构性整改）

    def _build_cards(self) -> None:
        # 构建用量总览卡片区（P17：总 tokens/输入/输出/缓存率/总费用，删除会话数）
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(CARDS_SPACING)
        self._cards: dict[str, QLabel] = {}
        for key, title in CARD_TITLES.items():
            frame = QFrame()
            frame.setObjectName("card")
            card_box = QVBoxLayout(frame)
            value_label = QLabel("-")
            value_label.setObjectName("card_value")
            value_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            title_label = QLabel(title)
            title_label.setObjectName("card_title")
            title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            card_box.addWidget(value_label)
            card_box.addWidget(title_label)
            cards_layout.addWidget(frame)
            self._cards[key] = value_label
        self._layout.addLayout(cards_layout)

    def _build_quota_section(self) -> None:
        # 构建 Go 配额区（PL004.3 单卡）：账户选择器行 + 单张配额卡；
        # 选择器选项由 _render_quota 按每次刷新的 infos 重建；
        # PL005.1：行尾常驻"添加账户"按钮（已有凭据时引入新账户的唯一入口）
        selector_row = QHBoxLayout()
        selector_label = QLabel(QUOTA_ACCOUNT_LABEL)
        selector_label.setObjectName("section_title")
        self._quota_account_combo = QComboBox()
        self._quota_account_combo.currentIndexChanged.connect(
            self._on_quota_account_changed
        )
        # PL005.1：点击弹菜单两条添加路径（复用既有引导流程文案与逻辑）；
        # A017/L1.1：动作引用保留，引导期间禁用防静默无反馈
        self._add_account_button = QPushButton(QUOTA_ADD_ACCOUNT_BUTTON)
        self._add_account_menu = QMenu(self._add_account_button)
        auto_action = QAction(GUIDE_AUTO_BUTTON, self._add_account_menu)
        manual_action = QAction(GUIDE_MANUAL_BUTTON, self._add_account_menu)
        auto_action.triggered.connect(self._start_cdp_guide)
        manual_action.triggered.connect(self._manual_guide)
        self._add_account_menu.addAction(auto_action)
        self._add_account_menu.addAction(manual_action)
        self._add_account_actions = (auto_action, manual_action)
        self._add_account_button.setMenu(self._add_account_menu)
        selector_row.addWidget(selector_label)
        selector_row.addWidget(self._quota_account_combo, 1)
        selector_row.addWidget(self._add_account_button)
        self._layout.addLayout(selector_row)
        container = QWidget()
        self._quota_cards_layout = QHBoxLayout(container)
        self._quota_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._build_quota_card(QUOTA_SECTION_TITLE)
        self._layout.addWidget(container)

    def _build_quota_card(self, title_text: str) -> None:
        # 构建单张配额卡（标题/状态 + 3 窗口进度条 + 重置时间 + 饼图）；
        # 组件经 self._quota_card dict 与 _quota_bars/_quota_pie 实例属性暴露
        frame = QFrame()
        frame.setObjectName("card")
        box = QVBoxLayout(frame)
        title_row = QHBoxLayout()
        title_label = QLabel(title_text)
        title_label.setObjectName("section_title")
        status_label = QLabel("")
        status_label.setObjectName("status_ok")
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        title_row.addWidget(status_label)
        # P16：剩余量饼图（正常显示；缓存/错误时隐藏让位给警告文字）
        pie = _RemainingPieChart()
        title_row.addWidget(pie)
        box.addLayout(title_row)
        bars: dict[str, QProgressBar] = {}
        resets: dict[str, QLabel] = {}
        # R2：窗口键统一来自 go_quota.QUOTA_WINDOW_KEYS（6A.3，字段名 = GoQuotaInfo 字段）
        for key in QUOTA_WINDOW_KEYS:
            row = QHBoxLayout()
            name_label = QLabel(QUOTA_WINDOW_LABELS[key])
            name_label.setFixedWidth(QUOTA_NAME_WIDTH)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            reset_label = QLabel("")
            reset_label.setObjectName("card_title")
            row.addWidget(name_label)
            row.addWidget(bar, 1)
            row.addWidget(reset_label)
            box.addLayout(row)
            bars[key] = bar
            resets[key] = reset_label
        card = {
            "frame": frame,
            "title": title_label,
            "bars": bars,
            "resets": resets,
            "status": status_label,
            "pie": pie,
        }
        self._quota_cards_layout.addWidget(frame)
        # 单卡引用（PL004.3/A0.16-K3.1）：仅保留有消费的实例属性
        # （_quota_bars/_quota_pie 用于 _apply_theme 重着色；frame/status/reset
        # 经 dict 访问，无独立消费者不再暴露）
        self._quota_card = card
        self._quota_pie = pie
        self._quota_bars = bars

    def _build_guide_card(self) -> None:
        # 构建凭据配置引导卡片（凭据缺失时显示，S6.2；文案外置 ui.json，D5）
        guide_frame = QFrame()
        guide_frame.setObjectName("card")
        guide_box = QVBoxLayout(guide_frame)
        guide_text = QLabel(GUIDE_CARD_TEXT)
        guide_text.setWordWrap(True)
        guide_text.setObjectName("card_title")
        guide_box.addWidget(guide_text)
        guide_buttons = QHBoxLayout()
        self._auto_guide_button = QPushButton(GUIDE_AUTO_BUTTON)
        self._auto_guide_button.clicked.connect(self._start_cdp_guide)
        self._manual_guide_button = QPushButton(GUIDE_MANUAL_BUTTON)
        self._manual_guide_button.clicked.connect(self._manual_guide)
        guide_buttons.addWidget(self._auto_guide_button)
        guide_buttons.addWidget(self._manual_guide_button)
        guide_buttons.addStretch(1)
        guide_box.addLayout(guide_buttons)
        guide_frame.hide()
        self._layout.addWidget(guide_frame)
        self._guide_frame = guide_frame

    def _build_detail_section(self) -> None:
        # 构建明细区（总览按钮/维度下拉/刷新/导出/主题/设置按钮 + 分组表格）
        section_row = QHBoxLayout()
        detail_title = QLabel(DETAIL_SECTION_TITLE)
        detail_title.setObjectName("section_title")
        self._dimension_combo = QComboBox()
        for dim in DIMENSIONS:
            self._dimension_combo.addItem(DIMENSION_LABELS[dim], dim)
        self._dimension_combo.currentIndexChanged.connect(self._render_table)
        self._refresh_button = QPushButton(BUTTON_LABELS["refresh"])
        self._refresh_button.clicked.connect(self.refresh)
        self._export_button = QPushButton(BUTTON_LABELS["export"])
        self._export_button.clicked.connect(self._export_data)
        # PL003.2：主题下拉（THEME_DISPLAY_NAMES 显示名，userData = 主题名；切换即应用即存）
        self._theme_combo = QComboBox()
        for name in THEME_NAMES:
            self._theme_combo.addItem(THEME_LABELS.get(name, name), name)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self._apply_theme()
        # 启动恢复持久化主题（blockSignals 防 currentIndexChanged 回环触发二次应用）
        restore_index = self._theme_combo.findData(self._theme_name)
        self._theme_combo.blockSignals(True)
        self._theme_combo.setCurrentIndex(restore_index if restore_index >= 0 else 0)
        self._theme_combo.blockSignals(False)
        # P15：总览独立显示在明细旁（点击弹出总量明细）
        self._total_button = QPushButton(f"{TOTAL_TOKEN_PREFIX}-")
        self._total_button.setFlat(True)
        self._total_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._total_button.setToolTip(TOOLTIPS["total_detail"])
        self._total_button.clicked.connect(self._show_total_detail)
        # P13：列显示开关设置按钮（按下显示/未按下隐藏）
        self._columns_button = QPushButton(BUTTON_LABELS["settings"])
        self._columns_button.setToolTip(TOOLTIPS["columns"])
        self._columns_button.clicked.connect(self._show_columns_menu)
        section_row.addWidget(detail_title)
        section_row.addWidget(self._total_button)
        section_row.addStretch(1)
        section_row.addWidget(self._dimension_combo)
        section_row.addWidget(self._refresh_button)
        section_row.addWidget(self._export_button)
        section_row.addWidget(self._columns_button)
        section_row.addWidget(self._theme_combo)
        self._layout.addLayout(section_row)

        self._table = QTableWidget(0, len(TABLE_HEADERS))
        self._table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        # 恢复持久化的隐藏列（P13）
        for col, col_id in enumerate(COLUMN_IDS):
            if col_id in self._hidden_columns:
                self._table.setColumnHidden(col, True)
        self._layout.addWidget(self._table, 1)

    def _trigger_auto_load(self) -> None:
        # 执行启动延迟加载（标志位确认未被手动刷新取消）
        if self._pending_auto_load:
            self.refresh()

    def refresh(self) -> None:
        # 手动/定时刷新入口：取消待执行自动加载，后台并行拉用量与配额
        # （B0.5：递增序号，_on_usage_ready 据此丢弃乱序完成的过期结果；
        # F0.2：usage 任务在途时仅标记待补发，不叠加 DB 查询）
        global _usage_task_in_flight, _usage_pending
        self._pending_auto_load = False
        self._refresh_seq += 1
        self._status_bar.showMessage(STATUS_MESSAGES["refreshing"])
        if self.db_path is not None:
            if _usage_task_in_flight:
                _usage_pending = True
                self._quota_runner.run(self.quota_fetcher, seq=self._refresh_seq)
                return
            _usage_task_in_flight = True
            self._usage_runner.run(self._usage_job, seq=self._refresh_seq)
        else:
            self._status_bar.showMessage(STATUS_MESSAGES["no_db_found"])
        self._quota_runner.run(self.quota_fetcher, seq=self._refresh_seq)

    def _usage_job(self) -> UsageData:
        # usage 任务体（A017/PL006：Service 调用 + in-flight 复位单点——H0.6 时序
        # 结论保持：emit 后 finally 复位，_consume_pending 只读 pending 无竞态）
        global _usage_task_in_flight
        try:
            return self._service.get_usage(self.db_path)
        except ServiceError as exc:
            raise RuntimeError(str(exc)) from exc
        finally:
            _usage_task_in_flight = False

    def _on_theme_changed(self, index: int) -> None:
        # 主题下拉切换（PL003.2）：更新主题名 → 应用 → 立即持久化
        # （常驻托盘应用可能长期不关，切完即存防丢）
        name = str(self._theme_combo.itemData(index) or DEFAULT_THEME_NAME)
        if name == self._theme_name:
            return
        self._theme_name = name
        self._apply_theme()
        try:
            config = load_config()
            config.theme = name
            save_config(config)
        except Exception as exc:
            logger.warning("保存主题配置失败：%s", exc)

    def _apply_theme(self) -> None:
        # 应用当前主题 QSS 到应用级样式（PL003.2：切换即应用 + 动态色重着色 +
        # 饼图实例色同步；isinstance 收窄 QCoreApplication → QApplication）
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setStyleSheet(get_theme(self._theme_name))
        # PL003.2.d 连带：进度条 chunk 动态色统一重着色（防残留旧主题色）
        for key in QUOTA_WINDOW_KEYS:
            bar = self._quota_bars[key]
            if bar.value() > 0:
                bar.setStyleSheet(
                    f"QProgressBar::chunk {{ background-color: "
                    f"{quota_chunk_color(bar.value(), self._theme_name)}; }}"
                )
        # 饼图背景/文字色随主题（实例色，PL003.1.d）；弧色由控件按主题+用量自算
        # （A017/L0.1：set_colors 第三参改为 theme 名，弧色分级联动）
        palette = self._theme_palette()
        self._quota_pie.set_colors(
            QColor(palette["pie_bg"]),
            QColor(palette["pie_text"]),
            self._theme_name,
        )

    def _theme_palette(self) -> dict[str, str]:
        # 当前主题调色板（quota 动态色/饼图色取色源；未知主题回退默认——
        # PL007 起由 theme_loader.get_palette 提供，资源源自各主题 theme.json）
        return get_palette(self._theme_name)

    def _on_usage_ready(self, seq: int, data: UsageData) -> None:
        # 用量加载完成：渲染卡片、总览按钮与表格（成功后视图才替换，失败保留旧 view；
        # B0.5：序号不匹配（旧任务乱序晚完成）直接丢弃，防覆盖新数据）
        global _usage_pending
        if seq != self._refresh_seq:
            # G0.1：过期结果丢弃前消费 pending——连点场景任务完成时 seq 必已
            # 递增，此处是补发的必经路径（否则 pending 残留 + 数据挂起）
            self._consume_pending()
            return
        self._usage_data = data
        self._render_cards(data.summary)
        self._total_button.setText(
            f"{TOTAL_TOKEN_PREFIX}{_format_total_tokens(data.summary.tokens.total)}"
        )
        self._render_table()
        self._status_bar.showMessage(
            STATUS_MESSAGES["updated_template"].format(
                time=datetime.now().strftime(STATUS_TIME_FORMAT)
            )
        )
        # F0.2：连点期间的待补发请求——以最新序号再启动一次（I3.1 措辞修正：
        # 在途标志复位由 H0.6 finally 保证（emit 后），跨线程队列连接下
        # 槽执行必然晚于 worker finally，此处判定无竞态）
        self._consume_pending()

    def _consume_pending(self) -> None:
        # G0.1：消费待补发请求——以最新序号再启动一次（I3.1 措辞修正：复位由
        # H0.6 finally 保证，主线程判定安全依赖队列连接时序；补发任务完成时
        # seq 匹配、pending 已清，不会循环；渲染路径与过期丢弃路径共用，
        # 防双路径漂移）
        global _usage_pending
        if _usage_pending:
            _usage_pending = False
            _usage_task_in_flight = True
            self._usage_runner.run(self._usage_job, seq=self._refresh_seq)

    def _show_total_detail(self) -> None:
        # 点击总览弹出总量明细：会话/消息/天数/tokens 分解/缓存率/费用（P15）
        if self._usage_data is None:
            self._status_bar.showMessage(STATUS_MESSAGES["usage_not_loaded"])
            return
        summary = self._usage_data.summary
        tokens = summary.tokens
        dlt = DETAIL_LINE_TEMPLATES
        lines = [
            dlt["sessions"].format(value=summary.sessions),
            dlt["messages"].format(value=summary.messages),
            dlt["days"].format(value=summary.days),
            dlt["input"].format(value=f"{tokens.input:,}"),
            dlt["output"].format(value=f"{tokens.output:,}"),
            dlt["reasoning"].format(value=f"{tokens.reasoning:,}"),
            dlt["cache_read"].format(value=f"{tokens.cache_read:,}"),
            dlt["cache_write"].format(value=f"{tokens.cache_write:,}"),
            f"{TOTAL_TOKEN_PREFIX}{_format_total_tokens(tokens.total)}",
            dlt["cache_rate"].format(value=_format_cache_rate_of(tokens)),
            dlt["cost"].format(value=_format_cost(summary.recorded_cost)),
        ]
        QMessageBox.information(self, DIALOG_TITLES["total_detail"], "\n".join(lines))

    def _on_quota_ready(self, seq: int, infos: list[GoQuotaInfo]) -> None:
        # 配额加载完成（PL001.8 多账户列表）：渲染进度条与状态；凭据类错误时显示
        # 引导卡片；发射更新信号（C0.5：旧任务乱序晚完成直接丢弃，与 usage 同机制）
        if seq != self._refresh_seq:
            return
        self._render_quota(infos)
        self.quota_updated.emit(infos)
        # 引导卡片显示条件单点维护于 _should_show_guide（PL005.2：failed 回调同源
        # 复用，防双路径漂移）
        self._guide_frame.setVisible(self._should_show_guide(infos))

    def _should_show_guide(self, infos: list[GoQuotaInfo]) -> bool:
        # 引导卡片显示条件：全部账户均为 CDP 可解决的凭据类错误（无 dashboard 凭据/
        # cookie 失效），且无缓存（历史成功过则不打扰）；其他阶段 CDP 解决不了，不显示
        # （E8：remaining==0/five_hour is None 在错误非缓存路径恒真，精简；
        #   A0.6：引导进行中不重现引导卡，防界面状态混乱；
        #   PL005.2：配额区添加账户失败回调复用本方法——已有有效凭据时不弹引导卡）
        if not infos or self._guide_active:
            return False
        return all(
            info.error is not None
            and not info.is_cached
            and info.error_stage in (ERROR_STAGE_NO_CREDS, ERROR_STAGE_AUTH)
            for info in infos
        )

    def _on_quota_failed(self, seq: int, message: str) -> None:
        # 配额任务异常兜底（A017/PL006.3：构造占位错误项走既有渲染路径——
        # 保持"配额失败不弹窗只降级"策略）
        self._on_quota_ready(
            seq,
            [
                GoQuotaInfo(
                    error=STATUS_MESSAGES["quota_failed_template"].format(error=message)
                )
            ],
        )

    def _on_load_error(self, seq: int, message: str) -> None:
        # 加载失败：仅状态栏提示（保留旧 view，z.plan 第四章保留旧数据策略；
        # C0.5：旧任务失败消息不覆盖新任务状态）；
        # A017/L3.3：seq 匹配的本次失败同样消费待补发标志（防残留至下次成功后
        # 冗余补发一次全维度查询）
        if seq != self._refresh_seq:
            # M0.4：过期失败回调同样消费待补发标志（对齐 _on_usage_ready 失配分支，
            # 防 pending 悬挂至下周期冗余补发全维度查询）
            self._consume_pending()
            return
        self._consume_pending()
        self._status_bar.showMessage(message)

    def _on_tab_changed(self, index: int) -> None:
        # 数据与动态页首次切换触发懒加载（PL002.10：has_loaded 幂等防重复拉取）
        if index == 1 and not self._data_page.has_loaded:
            self._data_page_seq += 1
            self._data_runner.run(self._service.get_data_page, seq=self._data_page_seq)

    def _on_data_ready(self, seq: int, snapshot: ModelDataSnapshot) -> None:
        # 数据页快照就绪：灌入三渲染入口 + has_loaded 置位（懒加载幂等）；
        # 部分失败仅状态栏提示（非核心子系统降级）
        if seq != self._data_page_seq:
            return
        page = self._data_page
        page.set_releases(snapshot.releases)
        page.set_daily_usage(snapshot.daily_usage)
        page.set_model_data(snapshot.model_blocks)
        page.has_loaded = True
        if snapshot.errors:
            self._status_bar.showMessage("；".join(snapshot.errors[:2]))

    def _on_data_error(self, seq: int, message: str) -> None:
        # 数据页拉取异常：仅状态栏提示（不弹窗，错误策略：降级不中断）
        if seq != self._data_page_seq:
            return
        self._status_bar.showMessage(DATA_PAGE_ERROR_TEMPLATE.format(message=message))

    def _set_guide_actions_enabled(self, enabled: bool) -> None:
        # 配额区"添加账户"菜单动作随引导态启停（A017/L1.1：引导期间禁用防静默
        # 无反馈——用户点击有感知，引导结束恢复）
        for action in self._add_account_actions:
            action.setEnabled(enabled)

    def _start_cdp_guide(self) -> None:
        # 一键自动获取：后台执行 CDP 引导流程（独立临时 Chrome，不影响用户浏览器）；
        # A0.16/K0.2：引导进行中早退——配额区添加账户菜单与引导卡共用本入口，
        # 防双 CDP 任务并发（双临时 Chrome/端口冲突/凭据并发写）；
        # A017/L1.1：早退补状态栏提示（不再静默无反馈）
        if self._guide_active:
            self._status_bar.showMessage(
                str(_SC.ui["go_quota_error_messages"]["in_flight"])
            )
            return
        self._guide_frame.hide()
        self._auto_guide_button.setEnabled(False)
        # A0.6/A0.7：引导期间禁用手动填写（防与 worker 并发写凭据）+ 抑制引导卡重现
        self._manual_guide_button.setEnabled(False)
        self._guide_active = True
        self._set_guide_actions_enabled(False)
        # B0.8：引导期暂停定时刷新（最长 3 分钟，避免无意义唤醒与节流纠缠）
        self._refresh_timer.stop()
        self._status_bar.showMessage(STATUS_MESSAGES["guide_starting"])
        self._guide_runner.run(
            lambda: self._service.add_account_via_cdp(), seq=self._refresh_seq
        )

    def _manual_guide(self) -> None:
        # 手动填写入口：弹对话框输入 workspaceId + authCookie，程序加密写入
        # （P4：不再直接编辑明文文件，所有写入路径统一 DPAPI 加密）；
        # A0.16/K0.2：引导进行中早退——防与 CDP worker 并发写凭据
        if self._guide_active:
            return
        workspace_id, ok1 = QInputDialog.getText(
            self, DIALOG_TITLES["manual_creds"], DIALOG_PROMPTS["workspace_id"]
        )
        if not ok1 or not workspace_id.strip():
            return
        auth_cookie, ok2 = QInputDialog.getText(
            self, DIALOG_TITLES["manual_creds"], DIALOG_PROMPTS["auth_cookie"]
        )
        if not ok2 or not auth_cookie.strip():
            return
        try:
            self._service.save_account(workspace_id.strip(), auth_cookie.strip())
            # PL005.2：记录 pending，刷新回来后选择器自动选中新添加的账户
            self._pending_quota_account = workspace_id.strip()
            self._status_bar.showMessage(STATUS_MESSAGES["creds_saved"])
            self.refresh()
        except Exception as exc:
            self._status_bar.showMessage(
                STATUS_MESSAGES["creds_save_failed"].format(error=exc)
            )

    def _on_guide_done(self, seq: int, result: object) -> None:
        # 引导成功（A017/PL006.3：TaskRunner finished 载荷为 (auth_cookie, workspace_id)
        # 元组——凭据已在 Service 内落盘）：提示并立即刷新配额；
        # PL005.2：记录 pending workspace_id，刷新回来后选择器自动选中新账户
        # N0.1：载荷契约守卫——finished 信号载荷须为二元组，上游契约变更返回非二元组
        # 时直接解包会抛 ValueError 致 GUI 崩溃，降级为状态栏提示而非崩溃
        if not (isinstance(result, tuple) and len(result) == 2):
            self._status_bar.showMessage(STATUS_MESSAGES["guide_data_format_error"])
            return
        auth_cookie, workspace_id = result
        message = GUIDE_MESSAGES["creds_saved_template"].format(
            workspace_id=workspace_id[:16]
        )
        self._auto_guide_button.setEnabled(True)
        self._manual_guide_button.setEnabled(True)
        self._guide_active = False
        self._set_guide_actions_enabled(True)
        if workspace_id:
            self._pending_quota_account = workspace_id
        self._refresh_timer.start(
            self._config.refresh_interval_ms
        )  # B0.8：恢复定时刷新
        self._status_bar.showMessage(message)
        self.refresh()

    def _on_guide_failed(self, seq: int, message: str) -> None:
        # 引导失败：状态栏提示；引导卡按条件显示（PL005.2：已有有效凭据时从配额区
        # 添加账户失败不弹引导卡——与 _on_quota_ready 同源判断，防界面语义混乱）；
        # M0.3：seq 为 TaskRunner.failed(int,str) 信号首参（对齐其他 handler，本处忽略）
        self._auto_guide_button.setEnabled(True)
        self._manual_guide_button.setEnabled(True)
        self._guide_active = False
        self._set_guide_actions_enabled(True)
        self._refresh_timer.start(
            self._config.refresh_interval_ms
        )  # B0.8：恢复定时刷新
        self._guide_frame.setVisible(self._should_show_guide(self._last_infos))
        self._status_bar.showMessage(message)

    def _export_data(self) -> None:
        # 选择导出目录并后台导出全部数据（CSV + JSON）
        if self.db_path is None:
            self._status_bar.showMessage(STATUS_MESSAGES["no_db_export"])
            return
        out_dir = QFileDialog.getExistingDirectory(self, DIALOG_TITLES["export_dir"])
        if not out_dir:
            return
        self._status_bar.showMessage(STATUS_MESSAGES["exporting"])
        self._export_runner.run(
            lambda: self._service.export_data(self.db_path, Path(out_dir)),
            seq=self._refresh_seq,
        )

    def _on_export_done(self, seq: int, out_dir: Path) -> None:
        # 导出完成：状态栏提示（A017/PL006.3 导出任务完成语义）
        self._status_bar.showMessage(
            STATUS_MESSAGES["export_done_template"].format(dir=out_dir)
        )

    def _render_cards(self, summary: UsageSummary) -> None:
        # 渲染用量总览卡片值（P17 新顺序）
        self._cards["tokens"].setText(_format_tokens(summary.tokens.total))
        self._cards["input"].setText(_format_tokens(summary.tokens.input))
        self._cards["output"].setText(_format_tokens(summary.tokens.output))
        self._cards["cache_rate"].setText(_format_cache_rate_of(summary.tokens))
        self._cards["cost"].setText(_format_cost(summary.recorded_cost))

    def _render_quota(self, infos: list[GoQuotaInfo]) -> None:
        # 渲染 Go 配额（PL004.3 单卡）：选择器按 infos 重建后，渲染当前选中账户项；
        # 选中失配（凭据已删/尚未刷出）回落持久化值，仍失配保持首项
        # （不保证有效性，A017/L3.1 注释按 K0.3 现状修正）；
        # PL005.2：新添加账户的 pending 标志优先匹配选中（一次性，失配静默清除）；
        # A0.16/K1.5：渲染目标按选择器当前索引取（combo 顺序 == infos 顺序）——
        # 同 workspace 双 cookie 时按索引区分，不再按 workspace_id 恒匹配首项
        if not infos:
            return
        self._last_infos = infos
        self._rebuild_quota_account_combo(infos)
        if self._pending_quota_account:
            pos = self._quota_account_combo.findData(self._pending_quota_account)
            self._pending_quota_account = ""
            if pos >= 0:
                self._quota_account_combo.setCurrentIndex(pos)
        idx = self._quota_account_combo.currentIndex()
        target = infos[idx] if 0 <= idx < len(infos) else None
        if target is None:
            target = next(
                (item for item in infos if item.error is None),
                infos[0],
            )
        self._render_quota_card(self._quota_card, target)

    def _rebuild_quota_account_combo(self, infos: list[GoQuotaInfo]) -> None:
        # 按本次刷新的 infos 重建选择器选项（userData = workspace_id；解密失败的
        # 凭据不会出现在 infos 中，自然不进下拉）；选中策略（A0.16/K0.3）：
        # 当前会话选中仍在 infos 则保持不动（防启动快照打回会话内选择）；
        # 失配才回落持久化值；仍失配保持 index 0——blockSignals 防回环触发保存
        self._quota_account_combo.blockSignals(True)
        try:
            # 先取当前选中再 clear（clear 后 currentData 归空无法回读）
            current = str(self._quota_account_combo.currentData() or "")
            self._quota_account_combo.clear()
            for info in infos:
                label = info.workspace_id[:8] or (
                    info.credential_source or QUOTA_ACCOUNT_UNKNOWN
                )
                self._quota_account_combo.addItem(label, info.workspace_id)
            if current and any(i.workspace_id == current for i in infos):
                # 会话内选中仍有效：恢复到原位置（A0.16/K0.3 防快照打回）
                pos = self._quota_account_combo.findData(current)
                if pos >= 0:
                    self._quota_account_combo.setCurrentIndex(pos)
                return
            target = load_config().quota_account
            pos = self._quota_account_combo.findData(target)
            if pos >= 0:
                self._quota_account_combo.setCurrentIndex(pos)
        finally:
            self._quota_account_combo.blockSignals(False)

    def _on_quota_account_changed(self, index: int) -> None:
        # 配额账户切换（PL004.3）：立即持久化 → 用最近一次 infos 重渲染单卡
        # （数据已在缓存列表，不发网络请求）
        config = load_config()
        config.quota_account = str(self._quota_account_combo.itemData(index) or "")
        try:
            save_config(config)
        except Exception as exc:
            logger.warning("保存配额账户选择失败：%s", exc)
        cached = self._last_infos
        if cached:
            # A0.16/K1.5：按切换后的索引取渲染目标（与 _render_quota 同语义，
            # 同 workspace 双 cookie 时按索引区分不回落首项）
            target = (
                cached[index]
                if 0 <= index < len(cached)
                else next((item for item in cached if item.error is None), cached[0])
            )
            self._render_quota_card(self._quota_card, target)

    def _render_quota_card(self, card: dict[str, Any], info: GoQuotaInfo) -> None:
        # 渲染单张配额卡：三窗口进度条 + 重置时间 + 状态文字/饼图（颜色分级）
        windows = {field: getattr(info, field) for field in QUOTA_WINDOW_KEYS}
        for key, window in windows.items():
            bar = card["bars"][key]
            reset_label = card["resets"][key]
            if window is None:
                # A0.5：重置格式与 chunk 样式（防窗口值→None 过渡残留旧百分比）
                bar.setValue(0)
                bar.setFormat("")
                bar.setStyleSheet("")
                reset_label.setText(STATUS_MESSAGES["not_fetched"])
                continue
            # D0.6：外部数据钳制 0-100（dashboard 异常负值/超百不再外显 -5%/120%）
            percent = max(0, min(100, int(round(window.usage_percent))))
            bar.setValue(percent)
            bar.setFormat(f"{percent}%")
            bar.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: "
                f"{quota_chunk_color(percent, self._theme_name)}; }}"
            )
            reset_label.setText(
                STATUS_MESSAGES["reset_template"].format(
                    time=window.reset_date.astimezone().strftime(RESET_TIME_FORMAT)
                )
                if window.reset_date
                else "-"
            )
        status_label = card["status"]
        pie = card["pie"]
        if info.is_cached:
            status_label.setObjectName("status_warn")
            pie.hide()
            status_label.setText(
                f"{STATUS_MESSAGES['cached_prefix']}{info.error or ''}"
            )
        elif info.error:
            status_label.setObjectName("status_warn")
            pie.hide()
            status_label.setText(f"{STATUS_MESSAGES['warn_prefix']}{info.error}")
        else:
            # P16：正常时剩余量饼图（最紧窗口文字已删除；overall 内部保留供托盘预警）
            status_label.setObjectName("status_ok")
            pie.show()
            pie.set_used_percent(info.overall_used_percent)
            status_label.clear()
        # 强制 QSS 重算（setObjectName 后不重算颜色不生效）
        style = status_label.style()
        if style is not None:
            style.unpolish(status_label)
            style.polish(status_label)

    def _show_columns_menu(self) -> None:
        # 弹出列显示开关菜单（P13：勾选 = 显示，取消 = 隐藏）
        menu = QMenu(self)
        for col, col_id in enumerate(COLUMN_IDS):
            # C 方案：QAction 构造式（绕开 PyQt6 stub 对 addAction 的 Optional 返回标注）
            action = QAction(TABLE_HEADERS[col], menu)
            menu.addAction(action)
            action.setCheckable(True)
            action.setChecked(col_id not in self._hidden_columns)
            action.toggled.connect(
                lambda checked, c=col, cid=col_id: self._on_column_toggle(
                    c, cid, checked
                )
            )
        menu.popup(
            self._columns_button.mapToGlobal(QPoint(0, self._columns_button.height()))
        )

    def _on_column_toggle(self, col: int, col_id: str, checked: bool) -> None:
        # 列开关回调：按下显示/未按下隐藏，并持久化到用户配置（P13）
        self._table.setColumnHidden(col, not checked)
        if checked:
            self._hidden_columns.discard(col_id)
        else:
            self._hidden_columns.add(col_id)
        config = load_config()
        config.hidden_columns = self._sorted_hidden_columns()
        try:
            # E0.3：列开关持久化失败仅 warning（与 D0.10 同式降级——磁盘满/权限
            # 错误不逃逸 Qt 槽，状态已改、持久化失败可接受）
            save_config(config)
        except Exception as exc:
            logger.warning("保存列配置失败：%s", exc)

    def _render_table(self) -> None:
        # 按当前维度渲染分组表格（P13 新列顺序：标签/总token/调用数/输入/输出/推理/缓存合并/缓存率/费用）
        dimension = self._dimension_combo.currentData()
        rows = self._usage_data.rows.get(dimension, []) if self._usage_data else []
        self._table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            cache_sum = row.tokens.cache_read + row.tokens.cache_write
            values = {
                "label": str(row.label),
                "total": _format_tokens(row.tokens.total),
                "calls": str(row.calls),
                "input": _format_tokens(row.tokens.input),
                "output": _format_tokens(row.tokens.output),
                "reasoning": _format_tokens(row.tokens.reasoning),
                "cache": _format_tokens(cache_sum),
                "cache_rate": _format_cache_rate_of(row.tokens),
                "cost": _format_cost(row.cost),
            }
            for col, col_id in enumerate(COLUMN_IDS):
                self._table.setItem(index, col, QTableWidgetItem(values[col_id]))

    def save_state(self) -> None:
        # 保存窗口状态：几何/主题/刷新间隔/隐藏列到配置文件（托盘退出与关闭时调用）
        config = load_config()
        config.window_geometry = bytes(self.saveGeometry().toHex().data()).decode()
        config.theme = self._theme_name
        config.refresh_interval_ms = self._refresh_timer.interval()
        config.hidden_columns = self._sorted_hidden_columns()
        save_config(config)

    def _sorted_hidden_columns(self) -> tuple[str, ...]:
        # 隐藏列规范化排序（保存/关闭两处共用单点，B1.2；D0.15：过滤不在
        # COLUMN_IDS 的脏 id——版本升级删列/手改配置的残留不永续回写）
        return tuple(sorted(c for c in self._hidden_columns if c in COLUMN_IDS))

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        # 关闭按钮：保存状态；托盘可用时隐藏到托盘（常驻模式，不真正退出），
        # 不可用时真退出（隐藏将无法恢复，B0.9；D0.10：保存失败仅提示不阻塞退出）
        try:
            self.save_state()
        except Exception as exc:
            logger.warning("保存窗口状态失败：%s", exc)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            if a0 is not None:
                a0.ignore()
        elif a0 is not None:
            a0.accept()


# ===== ui/main_window.py 模块说明 =====
# 模块级常量：
#   AUTO_LOAD_DELAY_MS：启动延迟加载毫秒数（base.json 驱动）
#   PIE_SIZE / PIE_FONT_SIZE / PIE_COLOR_BG_DEFAULT / PIE_COLOR_TEXT_DEFAULT：
#     剩余量饼图参数与默认主题色（ui.json + 默认 palette 派生，A0.16/K3.6 改名同步）
#   PIE_START_ANGLE / FULL_CIRCLE_16：饼图绘制角度常量（Qt 角度单位，代码内，C11）
#   LAYOUT_MARGINS / LAYOUT_SPACING / QUOTA_NAME_WIDTH / CARDS_SPACING：
#     布局参数（ui.json）；RESET_TIME_FORMAT：重置时间显示格式（ui.json）
#   DIMENSIONS / DIMENSION_LABELS / QUOTA_WINDOW_LABELS / GUIDE_* / TABLE_HEADERS /
#     COLUMN_IDS：维度与文案配置（标签外置 ui.json，列模型代码内）
#   TOTAL_TOKEN_PREFIX / CARD_TITLES / QUOTA_SECTION_TITLE / DETAIL_SECTION_TITLE /
#     BUTTON_LABELS / TOOLTIPS / STATUS_MESSAGES / DIALOG_TITLES / DIALOG_PROMPTS：
#     界面文案外置 ui.json（5A.3 C3/C4：卡片/区域/按钮/状态栏/对话框文案单一来源）
#   USAGE_TAB_TITLE / DATA_PAGE_ERROR_TEMPLATE / THEME_LABELS / QUOTA_ACCOUNT_LABEL /
#     QUOTA_ACCOUNT_UNKNOWN / QUOTA_ADD_ACCOUNT_BUTTON：页签/数据页错误模板/主题显示名/
#     配额账户选择器与添加账户文案（PL002.11/PL003.2/PL004.3/PL005.1）
#   COST_ZERO_EPSILON / TOTAL_TOKENS_UNIT / TOTAL_TOKENS_UNIT_THRESHOLD /
#     STATUS_TIME_FORMAT / TOKEN_ABBR_UNITS：容差/单位/时间格式外置（6A.3 H5/H6 + A2.1）
#   _usage_task_in_flight / _usage_pending：usage 任务在途/待补发标志（F0.2 补列，
#     连点去重——跨线程读写 GIL 原子，与 go_quota._fetch_in_flight 同式；
#     A017/PL006 起复位经 _usage_job finally 单点）
# 契约校验块：_UI_STRUCT_KEYS 逐组校验 ui.json 键集（card_titles/quota_window_labels/
#   dimension_labels/detail_line_templates/status_messages 显式 18 键/guide_messages/
#   tooltips/button_labels/menu_labels/go_quota_error_messages（F0.1 补列）等，
#   B0.6/C0.8/D0.2）+ notify_title 标量键（D0.7）+
#   notify_message_template（H0.8，I3.5 补列；P24 定案后仅主模板键）+
#   table_headers 长度严格相等（C0.7）——删键/改键导入期抛错，防运行时 KeyError/IndexError
# 类型：
#   UsageData：后台任务返回的完整用量数据（summary + 各维度行，内存驻留；
#     A017/PL006.1 定义迁至 services.service，此处 import 供注解）
#   _RemainingPieChart：剩余量饼图控件（QPainter 分级色圆弧[随用量三档变色] +
#     中心"剩余 Y%"，P16/A017-L0.1）
#   补充函数条目（A018/M3.4：审计发现函数清单漏列，补全覆盖）：
#     _usage_job()：用量聚合任务体（AppService.get_usage 包装，供 TaskRunner 提交；
#       F0.2 在途/待补发标志复位经其 finally 单点，H0.6 时序结论）
#     _consume_pending()：消费待补发请求——以最新序号再启动一次 _usage_job（G0.1；
#       渲染路径与过期丢弃路径共用，防双路径漂移）
#     _set_guide_actions_enabled(enabled)：引导按钮启用/禁用（PL005.2 引导完成/失败时复位）
# 函数：
#   _format_tokens()：K/M/B/G 缩写格式化
#   _format_cost()：费用格式化（近零容差内显示 -，≥1 两位小数，<1 四位小数）
#   _cache_rate_percent()：缓存率计算（(缓存读+缓存写)/总 token，卡片与表格共用，P17）
#   _format_cache_rate()：缓存率格式化（一位小数百分比）
#   _format_cache_rate_of()：缓存率计算+格式化复合（卡片/明细弹窗/表格 3 处共用，6A.4 O3）
#   _format_total_tokens()：总览总 token 格式化（千分位 + 亿单位，P15）
#   MainWindow：
#     __init__：注入 db_path/quota_fetcher（可测试）；恢复配置（主题/窗口几何/
#       刷新间隔/隐藏列，config.settings.load_config）；装配 UI；启动延迟加载
#       （QTimer.singleShot(AUTO_LOAD_DELAY_MS) + _pending_auto_load 标志，手动刷新
#       取消防双加载，参考 OpenCode-Token 的 after(10)+after_cancel 模式）；QTimer 定时刷新
#     quota_updated 信号：配额加载完成发射（main.py 接线托盘图标/预警）
#     _build_ui：QTabWidget 两页装配（PL002.11）——用量监控页（卡片区[P17] +
#       Go 配额区[选择器行 PL004.3 + 添加账户按钮 PL005.1 + 单卡三进度条 +
#       状态 + 饼图 P16] + 明细区[总览按钮 P15/维度下拉/刷新/导出/设置 P13/
#       主题下拉 PL003.2 + QTableWidget]）+ 数据与动态页；状态栏在 __init__
#       信号连接区提前创建（M11）
#     _trigger_auto_load：启动延迟加载执行（_pending_auto_load 标志确认）
#     refresh：手动/定时入口——取消自动加载标志，QThreadPool 并行启动两个任务
#       （F0.2/G3.4：usage 任务在途时仅置 pending 补发标志并只启动配额任务）
#     _apply_theme：主题应用（QApplication.setStyleSheet + chunk/饼图动态色重着色）；
#       _theme_combo/_on_theme_changed：主题下拉切换即存（PL003.2）
#     _on_usage_ready/_on_quota_ready/_on_load_error/_on_quota_failed/_on_export_done：
#       结果渲染；失败仅状态栏提示，
#       保留旧 view（成功后视图才替换）；配额缓存/错误仅状态栏警告不弹窗；
#       引导卡显示条件单点维护于 _should_show_guide（全部账户凭据类错误且无缓存
#       且非引导进行中，A0.16/K3.6 口径同步）
#     _show_total_detail：点击总览按钮弹出总量明细（QMessageBox，P15）
#     _on_tab_changed/_on_data_ready/_on_data_error：数据页懒加载（首次切换触发，
#       PL002.10）与结果回传
#     _theme_palette：当前主题 palette 取用（饼图/动态色消费）
#     _show_columns_menu/_on_column_toggle：列显示开关（QMenu 勾选，
#       setColumnHidden + hidden_columns 持久化，P13；E0.3：持久化失败仅
#       warning 降级，与 D0.10 同式）
#     _export_data：QFileDialog 选目录 → 后台导出（TaskRunner，状态栏提示导出中）
#     _render_cards/_render_quota/_render_quota_card/_render_table：卡片（P17 新顺序 +
#       缓存率）/配额单卡渲染（PL004.3：选择器按 infos 重建 + 按索引取渲染目标
#       [A0.16/K1.5] + pending 自动选中新账户 PL005.2）/表格渲染
#       （内存数据，维度切换不查库；P13 新列顺序）
#     _build_quota_section/_build_quota_card：Go 配额区装配（选择器行 + 添加账户
#       按钮[PL005.1 QMenu 两路径] + 单张配额卡）
#     _rebuild_quota_account_combo/_on_quota_account_changed：账户选择器重建
#       （会话选中保持防快照打回 A0.16/K0.3）与切换即存即渲染
#     _start_cdp_guide/_manual_guide/_on_guide_done/_on_guide_failed：凭据引导
#       双路径（A0.16/K0.2 引导互斥早退防并发；成功 pending 记录+自动刷新；
#       失败按 _should_show_guide 条件显示引导卡）
#     _should_show_guide：引导卡显示条件单点维护（_on_quota_ready 与 failed 回调共用）
#     save_state：窗口几何（QByteArray hex）/主题/刷新间隔/隐藏列 → config 持久化
#     closeEvent：保存状态并隐藏到托盘（常驻模式，真退出走托盘菜单）
# 设计理由：数据加载全后台（services 门面 + ui.task_runner 统一线程池封装）+
#   信号回传（线程安全）；worker 自建只读连接避免 sqlite check_same_thread 问题；
#   维度切换零查询；配置"退出即存、启动即恢复"（对齐 AccelWorld B2 修复经验）；
#   CDP 引导独立临时 profile，不打扰用户正在使用的浏览器（S6.1 实测结论）；
#   A017/PL006 起后端编排全部收敛 services.AppService（UI 与 modules 解耦，
#   前端可整体替换）
# 异常处理：任务内异常转 finished/failed 信号；配额错误包装为 GoQuotaInfo
#   携带提示；引导失败仅状态栏提示不弹窗
# 关联配置：VERSION（utils.logger 单点导出，G3.4 同步）；config.settings（geometry/theme/refresh_interval_ms/
#   hidden_columns）；services（get_service 后端门面单点，quota_fetcher 可注入替换，测试用）
