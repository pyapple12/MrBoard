# 主窗口模块：用量总览卡片 + Go 配额进度条 + 分组表格 + 后台加载与定时刷新

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import (
    QByteArray,
    QObject,
    QPoint,
    QRunnable,
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
    QVBoxLayout,
    QWidget,
)

from config.settings import load_config, save_config
from config.static.static_config import get_static_config
from modules import browser_creds
from modules.exporter import export_all
from modules.go_quota import (
    ERROR_STAGE_AUTH,
    ERROR_STAGE_NO_CREDS,
    QUOTA_WINDOW_KEYS,
    DashboardCredentials,
    GoQuotaError,
    GoQuotaInfo,
    fetch_dashboard_usage,
    fetch_go_quota,
    save_dashboard_credentials,
)
from modules.opencode_usage import (
    OpenCodeDB,
    TokenStats,
    UsageRow,
    UsageSummary,
    find_db_path,
)
from ui.themes import DARK_THEME_NAME, LIGHT_THEME_NAME, get_theme, quota_chunk_color
from utils.logger import build_app_title, get_logger

logger = get_logger(__name__)

# 静态配置解包（S8：参数外置 base.json，运行时零 IO）
_SC = get_static_config()
AUTO_LOAD_DELAY_MS = int(_SC.base["auto_load_delay_ms"])
# L8/L10：表格行数上限与 CDP 超时（base.json 驱动）
TABLE_LIMIT_GROUP = int(_SC.base["table_limit_group"])
TABLE_LIMIT_DAY = int(_SC.base["table_limit_day"])
CDP_FETCH_TIMEOUT = int(_SC.base["cdp_fetch_timeout"])
CDP_WAIT_TIMEOUT = int(_SC.base["cdp_wait_timeout"])
# S7：CDP 引导参数模块级解包（一次性解包约定）
CDP_POLL_INTERVAL = int(_SC.base["cdp_poll_interval"])
CDP_LOGIN_WAIT_SECONDS = int(_SC.base["cdp_login_wait_seconds"])
# L9：剩余量饼图参数（ui.json 驱动）
PIE_SIZE = int(_SC.ui["pie_size"])
PIE_FONT_SIZE = float(_SC.ui["pie_font_size"])
PIE_COLOR_BG = str(_SC.ui["colors"]["quota_pie_bg"])
PIE_COLOR_TEXT = str(_SC.ui["colors"]["quota_pie_text"])
# C11：饼图绘制角度常量（Qt 角度单位 1/16 度；90°=12 点方向起点）
PIE_START_ANGLE = 90 * 16
FULL_CIRCLE_16 = 360 * 16
# C22：布局参数外置（边距/间距/配额名称列宽）；C11：卡片区间距/重置时间格式
LAYOUT_MARGINS = tuple(int(v) for v in _SC.ui["layout_margins"])
LAYOUT_SPACING = int(_SC.ui["layout_spacing"])
QUOTA_NAME_WIDTH = int(_SC.ui["quota_name_width"])
CARDS_SPACING = int(_SC.ui["cards_spacing"])
RESET_TIME_FORMAT = str(_SC.ui["reset_time_format"])

# 分组维度与表格列配置（表头文案外置 ui.json，S8.3；维度枚举保留代码内）
# P15：总览已移出维度下拉（独立显示 + 点击弹明细），保留 total 数据供弹窗用
# D5：维度标签/配额窗口标签/引导卡片文案外置 ui.json
DIMENSIONS = ("month", "day", "model", "provider", "agent", "session")
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
TABLE_HEADERS = tuple(_SC.ui["table_headers"])
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
        ("refresh", "export", "theme", "settings"),
        BUTTON_LABELS,
    ),
    ("menu_labels", ("show_window", "refresh", "quit"), dict(_SC.ui["menu_labels"])),
)
for _cfg_name, _required, _actual in _UI_STRUCT_KEYS:
    _missing = [k for k in _required if k not in _actual]
    if _missing:
        raise RuntimeError(f"ui.json {_cfg_name} 缺少必需键：{_missing}")
# D0.7：notify_title 为标量键，单独契约校验（main.py 消费，C0.8 键集遗漏补全）
if "notify_title" not in _SC.ui:
    raise RuntimeError("ui.json 缺少必需键：notify_title")
# C0.7：table_headers 严格相等（防短防长——加列后多出列渲染为空且列开关无法控制）
if len(TABLE_HEADERS) != len(COLUMN_IDS):
    raise RuntimeError(
        f"ui.json table_headers 长度与 COLUMN_IDS 不一致"
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
    "notify_message_fallback": str(_SC.ui.get("notify_message_fallback", "")),
}
for _tname, _tmpl in _TEMPLATE_MAP.items():
    try:
        _tmpl.format_map(_TEMPLATE_PLACEHOLDERS)
    except (KeyError, ValueError, IndexError) as _exc:
        raise RuntimeError(f"ui.json 模板键 {_tname} 占位符异常：{_exc}") from None


@dataclass
class UsageData:
    # 后台任务返回的完整用量数据（内存驻留，维度切换不再查库）

    summary: UsageSummary
    rows: dict[str, list[UsageRow]]


class _LoadSignals(QObject):
    # 用量/配额加载信号载体（usage_ready 携带刷新序号，B0.5 去重用）

    usage_ready = pyqtSignal(int, object)
    quota_ready = pyqtSignal(int, object)
    error = pyqtSignal(int, str)  # C0.5：携带刷新序号


class _ExportSignals(QObject):
    # 导出任务信号载体：完成/失败回传主线程

    done = pyqtSignal(str)
    failed = pyqtSignal(str)


class _UsageTask(QRunnable):
    # 用量统计后台任务：独立打开只读连接（规避 sqlite 跨线程限制），完成后发信号

    def __init__(self, db_path: Path, signals: _LoadSignals, seq: int = 0) -> None:
        # 初始化任务：记录数据库路径、信号对象与刷新序号（B0.5 去重）
        super().__init__()
        self.db_path = db_path
        self.signals = signals
        self.seq = seq

    def run(self) -> None:
        # 后台执行：totals + 全部分组查询，失败发 error 信号
        try:
            db = OpenCodeDB(self.db_path)
            try:
                summary = db.totals()
                # C1：rows 不含 total 伪维度（从未消费；总量明细弹窗直接读 summary）
                # R1：按 DIMENSIONS 推导构建（day 特例 TABLE_LIMIT_DAY），新增维度只改 DIMENSIONS
                rows = {
                    dim: getattr(db, f"by_{dim}")(
                        limit=TABLE_LIMIT_DAY if dim == "day" else TABLE_LIMIT_GROUP
                    )
                    for dim in DIMENSIONS
                }
            finally:
                db.close()
            self.signals.usage_ready.emit(
                self.seq, UsageData(summary=summary, rows=rows)
            )
        except Exception as exc:
            self.signals.error.emit(
                self.seq,
                STATUS_MESSAGES["usage_failed_template"].format(error=exc),
            )


class _QuotaTask(QRunnable):
    # Go 配额后台任务：网络请求不阻塞 UI，完成后发信号

    def __init__(
        self,
        signals: _LoadSignals,
        quota_fetcher: Callable[..., GoQuotaInfo],
        seq: int = 0,
    ) -> None:
        # 初始化任务：记录信号对象、配额获取函数与刷新序号（C0.5 去重）
        super().__init__()
        self.signals = signals
        self.quota_fetcher = quota_fetcher
        self.seq = seq

    def run(self) -> None:
        # 后台执行：拉取 Go 配额（内部含节流与缓存兜底）
        try:
            self.signals.quota_ready.emit(self.seq, self.quota_fetcher())
        except Exception as exc:
            self.signals.quota_ready.emit(
                self.seq,
                GoQuotaInfo(
                    error=STATUS_MESSAGES["quota_failed_template"].format(error=exc)
                ),
            )


class _ExportTask(QRunnable):
    # 导出后台任务：独立连接查询 + exporter 落盘，完成后发信号

    def __init__(self, db_path: Path, out_dir: Path, signals: _ExportSignals) -> None:
        # 初始化任务：记录数据库路径/输出目录/信号对象
        super().__init__()
        self.db_path = db_path
        self.out_dir = out_dir
        self.signals = signals

    def run(self) -> None:
        # 后台执行：全量导出到 out_dir，成功发 done / 失败发 failed
        try:
            db = OpenCodeDB(self.db_path)
            try:
                export_all(db, self.out_dir)
            finally:
                db.close()
            self.signals.done.emit(
                STATUS_MESSAGES["export_done_template"].format(dir=self.out_dir)
            )
        except Exception as exc:
            self.signals.failed.emit(
                STATUS_MESSAGES["export_failed_template"].format(error=exc)
            )


class _RemainingPieChart(QWidget):
    # 剩余量饼图：已用/剩余双色圆弧 + 中心"剩余 Y%"标注（P16，替换"最紧窗口"文字位）

    def __init__(self, parent: QWidget | None = None) -> None:
        # 初始化：已用比例为 0，尺寸/色值/字号由 ui.json 驱动（L9）
        super().__init__(parent)
        self._used_percent = 0.0
        self.setFixedSize(PIE_SIZE, PIE_SIZE)
        self.setToolTip(TOOLTIPS["pie_remaining"])

    def set_used_percent(self, percent: float) -> None:
        # 更新已用比例并重绘（0-100 截断，越界防御）
        self._used_percent = max(0.0, min(100.0, percent))
        self.update()

    def used_percent(self) -> float:
        # 返回当前已用比例（外部读取/测试用）
        return self._used_percent

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        # 自绘：浅色底（剩余）→ 分级色圆弧（已用）→ 中心"剩余 Y%"文字
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(3, 3, -3, -3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PIE_COLOR_BG))
        painter.drawEllipse(rect)
        used = self._used_percent / 100.0
        # C10：int(round()) 提局部变量（圆弧颜色/剩余文字共用同一口径）
        used_percent_int = int(round(self._used_percent))
        if used > 0:
            painter.setBrush(QColor(quota_chunk_color(used_percent_int)))
            painter.drawPie(rect, PIE_START_ANGLE, -int(used * FULL_CIRCLE_16))
        painter.setPen(QColor(PIE_COLOR_TEXT))
        font = painter.font()
        font.setPointSizeF(PIE_FONT_SIZE)
        painter.setFont(font)
        remaining = max(0, 100 - used_percent_int)
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            PIE_REMAINING_TEMPLATE.format(percent=remaining),
        )


class _CdpGuideSignals(QObject):
    # CDP 凭据引导任务信号载体：成功/失败回传主线程

    success = pyqtSignal(str)
    failed = pyqtSignal(str)


def _wait_for_login_cookie(deadline: float) -> tuple[str | None, str | None]:
    # 端到端轮询：CDP 拿 cookie + 登录后当前页面 URL 提取 workspaceID，实测 dashboard
    # 可解析才算登录完成（防占位 cookie 误判：打开登录页时页面会种匿名 auth cookie）
    # 返回 (cookie, 验证通过的 workspace_id)——多账户场景保存时须用验证通过的
    while time.time() < deadline:
        candidate, workspace_id = browser_creds.fetch_login_state_via_cdp(
            timeout=CDP_FETCH_TIMEOUT
        )
        if candidate and workspace_id:
            try:
                usage = fetch_dashboard_usage(
                    DashboardCredentials(workspace_id, candidate, "cdp验证")
                )
                if usage:
                    logger.info("cookie 验证通过（dashboard 可解析）")
                    return candidate, workspace_id
            except GoQuotaError:
                # 占位 cookie/页面未跳转：dashboard 返回登录页或解析失败，继续轮询
                pass
        time.sleep(CDP_POLL_INTERVAL)
    return None, None


class _CdpGuideTask(QRunnable):
    # CDP 一键获取凭据后台任务：启动临时调试 Chrome → 等登录 → 存凭据 → 清理

    def __init__(
        self, signals: _CdpGuideSignals, login_wait_seconds: int | None = None
    ) -> None:
        # 初始化任务：记录信号对象与登录等待时长（None 时统一取静态配置）
        super().__init__()
        self.signals = signals
        self.login_wait_seconds = (
            CDP_LOGIN_WAIT_SECONDS if login_wait_seconds is None else login_wait_seconds
        )

    def run(self) -> None:
        # 后台执行：环境预检 → 启动调试 Chrome → 轮询登录（CDP 拿 cookie + 页面 URL
        # 提取 workspaceID）→ 写凭据 → 清理
        proc = None
        try:
            if browser_creds.is_chrome_running():
                logger.info("检测到用户 Chrome 正在运行（独立临时 profile 不冲突）")
            # B0.1：双浏览器判定（Edge-only v20 用户不再误判为 v10）
            if not browser_creds.has_v20_cookies():
                self.signals.failed.emit(GUIDE_MESSAGES["v10_detect"])
                return
            proc = browser_creds.launch_chrome_debug()
            if proc is None:
                self.signals.failed.emit(GUIDE_MESSAGES["launch_failed"])
                return
            if not browser_creds.wait_cdp_ready(timeout=CDP_WAIT_TIMEOUT):
                self.signals.failed.emit(GUIDE_MESSAGES["cdp_not_ready"])
                return
            auth_cookie, workspace_id = _wait_for_login_cookie(
                time.time() + self.login_wait_seconds
            )
            if not auth_cookie or not workspace_id:
                self.signals.failed.emit(
                    GUIDE_MESSAGES["login_timeout_template"].format(
                        minutes=self.login_wait_seconds // 60
                    )
                )
                return
            save_dashboard_credentials(workspace_id, auth_cookie)
            self.signals.success.emit(
                GUIDE_MESSAGES["creds_saved_template"].format(
                    workspace_id=workspace_id[:16]
                )
            )
        except Exception as exc:
            self.signals.failed.emit(
                GUIDE_MESSAGES["auto_fetch_failed"].format(error=exc)
            )
        finally:
            if proc is not None:
                browser_creds.shutdown_chrome_debug(proc)


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

    quota_updated = pyqtSignal(object)  # 配额加载完成信号（托盘图标/预警接线用）

    def __init__(
        self,
        db_path: Path | None = None,
        quota_fetcher: Callable[..., GoQuotaInfo] = fetch_go_quota,
    ) -> None:
        # 初始化窗口：探测数据库、装配 UI、启动延迟加载与定时器
        super().__init__()
        self.db_path = db_path if db_path is not None else find_db_path()
        self.quota_fetcher = quota_fetcher
        self._usage_data: UsageData | None = None
        self._pending_auto_load = False
        # B0.5：刷新序号（_UsageTask 乱序完成时丢弃过期结果）
        self._refresh_seq = 0
        # globalInstance 可能返回 None（PyQt6 stub Optional），兜底新建实例
        self._pool = QThreadPool.globalInstance() or QThreadPool()
        self._signals = _LoadSignals()
        self._signals.usage_ready.connect(self._on_usage_ready)
        self._signals.quota_ready.connect(self._on_quota_ready)
        self._signals.error.connect(self._on_load_error)
        self._export_signals = _ExportSignals()
        # M11 结构性整改：_status_bar 作为窗口基础设施提前创建（setStatusBar），
        # 导出信号直连 showMessage——所有信号连接统一在前部，消除对 _build_ui
        # 的初始化顺序依赖（不再需要转发方法或后置连接）
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._export_signals.done.connect(self._status_bar.showMessage)
        self._export_signals.failed.connect(self._status_bar.showMessage)
        self._guide_signals = _CdpGuideSignals()
        self._guide_signals.success.connect(self._on_guide_success)
        self._guide_signals.failed.connect(self._on_guide_failed)
        # A0.6/A0.7：CDP 引导进行中标志（抑制引导卡重现 + 禁用手动填写防并发写）
        self._guide_active = False

        self.setWindowTitle(build_app_title())
        self.resize(int(_SC.base["window_width"]), int(_SC.base["window_height"]))
        # 恢复配置：主题/窗口几何（S5 配置持久化）
        self._config = load_config()
        self._is_dark = self._config.theme == DARK_THEME_NAME
        # 列开关状态（P13：持久化于用户配置 hidden_columns）
        self._hidden_columns: set[str] = set(self._config.hidden_columns)
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
        # 装配界面：卡片区 + 配额区 + 引导卡 + 明细区（状态栏已在 __init__ 提前创建，M11）
        central = QWidget()
        self.setCentralWidget(central)
        self._layout = QVBoxLayout(central)
        self._layout.setContentsMargins(*LAYOUT_MARGINS)
        self._layout.setSpacing(LAYOUT_SPACING)
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
        # 构建 Go 配额区（标题/状态 + 3 进度条 + 重置时间 + 剩余量饼图；P12 已移除凭据元信息行）
        quota_frame = QFrame()
        quota_frame.setObjectName("card")
        quota_box = QVBoxLayout(quota_frame)
        title_row = QHBoxLayout()
        quota_title = QLabel(QUOTA_SECTION_TITLE)
        quota_title.setObjectName("section_title")
        self._quota_status = QLabel("")
        self._quota_status.setObjectName("status_ok")
        title_row.addWidget(quota_title)
        title_row.addStretch(1)
        title_row.addWidget(self._quota_status)
        # P16：剩余量饼图（正常显示；缓存/错误时隐藏让位给警告文字）
        self._quota_pie = _RemainingPieChart()
        title_row.addWidget(self._quota_pie)
        quota_box.addLayout(title_row)
        self._quota_bars: dict[str, QProgressBar] = {}
        self._quota_reset: dict[str, QLabel] = {}
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
            quota_box.addLayout(row)
            self._quota_bars[key] = bar
            self._quota_reset[key] = reset_label
        self._layout.addWidget(quota_frame)

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
        self._theme_button = QPushButton(BUTTON_LABELS["theme"])
        self._theme_button.clicked.connect(self.toggle_theme)
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
        section_row.addWidget(self._theme_button)
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
        # （B0.5：递增序号，_on_usage_ready 据此丢弃乱序完成的过期结果）
        self._pending_auto_load = False
        self._refresh_seq += 1
        self._status_bar.showMessage(STATUS_MESSAGES["refreshing"])
        if self.db_path is not None:
            self._pool.start(_UsageTask(self.db_path, self._signals, self._refresh_seq))
        else:
            self._status_bar.showMessage(STATUS_MESSAGES["no_db_found"])
        self._pool.start(
            _QuotaTask(self._signals, self.quota_fetcher, self._refresh_seq)
        )

    def toggle_theme(self) -> None:
        # 切换亮/暗主题并应用
        self._is_dark = not self._is_dark
        self._apply_theme()

    def _apply_theme(self) -> None:
        # 应用当前主题 QSS 到应用级样式（isinstance 收窄 QCoreApplication → QApplication）
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setStyleSheet(
                get_theme(DARK_THEME_NAME if self._is_dark else LIGHT_THEME_NAME)
            )

    def _on_usage_ready(self, seq: int, data: UsageData) -> None:
        # 用量加载完成：渲染卡片、总览按钮与表格（成功后视图才替换，失败保留旧 view；
        # B0.5：序号不匹配（旧任务乱序晚完成）直接丢弃，防覆盖新数据）
        if seq != self._refresh_seq:
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

    def _on_quota_ready(self, seq: int, info: GoQuotaInfo) -> None:
        # 配额加载完成：渲染进度条与状态；凭据类错误时显示引导卡片；发射更新信号
        # （C0.5：旧任务乱序晚完成直接丢弃，与 usage 同机制）
        if seq != self._refresh_seq:
            return
        self._render_quota(info)
        self.quota_updated.emit(info)
        # 引导卡片显示条件：CDP 可解决的凭据类错误（无 dashboard 凭据/cookie 失效），
        # 且无缓存（历史成功过则不打扰）；其他阶段 CDP 解决不了，不显示
        # （E8：remaining==0/five_hour is None 在错误非缓存路径恒真，精简；
        #   A0.6：引导进行中不重现引导卡，防界面状态混乱）
        show_guide = (
            info.error is not None
            and not info.is_cached
            and not self._guide_active
            and info.error_stage in (ERROR_STAGE_NO_CREDS, ERROR_STAGE_AUTH)
        )
        self._guide_frame.setVisible(show_guide)

    def _on_load_error(self, seq: int, message: str) -> None:
        # 加载失败：仅状态栏提示（保留旧 view，z.plan 第四章保留旧数据策略；
        # C0.5：旧任务失败消息不覆盖新任务状态）
        if seq != self._refresh_seq:
            return
        self._status_bar.showMessage(message)

    def _start_cdp_guide(self) -> None:
        # 一键自动获取：后台执行 CDP 引导流程（独立临时 Chrome，不影响用户浏览器）
        self._guide_frame.hide()
        self._auto_guide_button.setEnabled(False)
        # A0.6/A0.7：引导期间禁用手动填写（防与 worker 并发写凭据）+ 抑制引导卡重现
        self._manual_guide_button.setEnabled(False)
        self._guide_active = True
        # B0.8：引导期暂停定时刷新（最长 3 分钟，避免无意义唤醒与节流纠缠）
        self._refresh_timer.stop()
        self._status_bar.showMessage(STATUS_MESSAGES["guide_starting"])
        self._pool.start(_CdpGuideTask(self._guide_signals))

    def _manual_guide(self) -> None:
        # 手动填写入口：弹对话框输入 workspaceId + authCookie，程序加密写入
        # （P4：不再直接编辑明文文件，所有写入路径统一 DPAPI 加密）
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
            save_dashboard_credentials(workspace_id.strip(), auth_cookie.strip())
            self._status_bar.showMessage(STATUS_MESSAGES["creds_saved"])
            self.refresh()
        except Exception as exc:
            self._status_bar.showMessage(
                STATUS_MESSAGES["creds_save_failed"].format(error=exc)
            )

    def _on_guide_success(self, message: str) -> None:
        # 引导成功：提示并立即刷新配额（凭据已落盘，凭据链可读到）
        self._auto_guide_button.setEnabled(True)
        self._manual_guide_button.setEnabled(True)
        self._guide_active = False
        self._refresh_timer.start(
            self._config.refresh_interval_ms
        )  # B0.8：恢复定时刷新
        self._status_bar.showMessage(message)
        self.refresh()

    def _on_guide_failed(self, message: str) -> None:
        # 引导失败：状态栏提示，保留引导卡片供重试/手动填写
        self._auto_guide_button.setEnabled(True)
        self._manual_guide_button.setEnabled(True)
        self._guide_active = False
        self._refresh_timer.start(
            self._config.refresh_interval_ms
        )  # B0.8：恢复定时刷新
        self._guide_frame.show()
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
        self._pool.start(_ExportTask(self.db_path, Path(out_dir), self._export_signals))

    def _render_cards(self, summary: UsageSummary) -> None:
        # 渲染用量总览卡片值（P17 新顺序）
        self._cards["tokens"].setText(_format_tokens(summary.tokens.total))
        self._cards["input"].setText(_format_tokens(summary.tokens.input))
        self._cards["output"].setText(_format_tokens(summary.tokens.output))
        self._cards["cache_rate"].setText(_format_cache_rate_of(summary.tokens))
        self._cards["cost"].setText(_format_cost(summary.recorded_cost))

    def _set_status_style(self, object_name: str) -> None:
        # 设置配额状态标签样式名并强制 QSS 重算（setObjectName 后不重算颜色不生效）
        self._quota_status.setObjectName(object_name)
        style = self._quota_status.style()
        if style is not None:
            style.unpolish(self._quota_status)
            style.polish(self._quota_status)

    def _render_quota(self, info: GoQuotaInfo) -> None:
        # 渲染 Go 配额进度条与状态信息（颜色分级）
        windows = {field: getattr(info, field) for field in QUOTA_WINDOW_KEYS}
        for key, window in windows.items():
            bar = self._quota_bars[key]
            reset_label = self._quota_reset[key]
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
                f"QProgressBar::chunk {{ background-color: {quota_chunk_color(percent)}; }}"
            )
            reset_label.setText(
                STATUS_MESSAGES["reset_template"].format(
                    time=window.reset_date.astimezone().strftime(RESET_TIME_FORMAT)
                )
                if window.reset_date
                else "-"
            )
        if info.is_cached:
            self._set_status_style("status_warn")
            self._quota_pie.hide()
            self._quota_status.setText(
                f"{STATUS_MESSAGES['cached_prefix']}{info.error or ''}"
            )
        elif info.error:
            self._set_status_style("status_warn")
            self._quota_pie.hide()
            self._quota_status.setText(f"{STATUS_MESSAGES['warn_prefix']}{info.error}")
        else:
            # P16：正常时剩余量饼图（最紧窗口文字已删除；overall 内部保留供托盘预警）
            self._set_status_style("status_ok")
            self._quota_pie.show()
            self._quota_pie.set_used_percent(info.overall_used_percent)
            self._quota_status.clear()

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
        config.theme = DARK_THEME_NAME if self._is_dark else LIGHT_THEME_NAME
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
#   TABLE_LIMIT_GROUP / TABLE_LIMIT_DAY：表格行数上限（base.json）
#   CDP_FETCH_TIMEOUT / CDP_WAIT_TIMEOUT / CDP_POLL_INTERVAL / CDP_LOGIN_WAIT_SECONDS：
#     CDP 引导参数（base.json）
#   PIE_SIZE / PIE_FONT_SIZE / PIE_COLOR_BG / PIE_COLOR_TEXT：剩余量饼图参数（ui.json）
#   PIE_START_ANGLE / FULL_CIRCLE_16：饼图绘制角度常量（Qt 角度单位，代码内，C11）
#   LAYOUT_MARGINS / LAYOUT_SPACING / QUOTA_NAME_WIDTH / CARDS_SPACING：
#     布局参数（ui.json）；RESET_TIME_FORMAT：重置时间显示格式（ui.json）
#   DIMENSIONS / DIMENSION_LABELS / QUOTA_WINDOW_LABELS / GUIDE_* / TABLE_HEADERS /
#     COLUMN_IDS：维度与文案配置（标签外置 ui.json，列模型代码内）
#   TOTAL_TOKEN_PREFIX / CARD_TITLES / QUOTA_SECTION_TITLE / DETAIL_SECTION_TITLE /
#     BUTTON_LABELS / TOOLTIPS / STATUS_MESSAGES / DIALOG_TITLES / DIALOG_PROMPTS：
#     界面文案外置 ui.json（5A.3 C3/C4：卡片/区域/按钮/状态栏/对话框文案单一来源）
#   COST_ZERO_EPSILON / TOTAL_TOKENS_UNIT / TOTAL_TOKENS_UNIT_THRESHOLD /
#     STATUS_TIME_FORMAT / TOKEN_ABBR_UNITS：容差/单位/时间格式外置（6A.3 H5/H6 + A2.1）
# 契约校验块：_UI_STRUCT_KEYS 逐组校验 ui.json 键集（card_titles/quota_window_labels/
#   dimension_labels/detail_line_templates/status_messages 显式 18 键/guide_messages/
#   tooltips/button_labels/menu_labels 等，B0.6/C0.8/D0.2）+ notify_title 标量键（D0.7）+
#   table_headers 长度严格相等（C0.7）——删键/改键导入期抛错，防运行时 KeyError/IndexError
# 类型：
#   UsageData：后台任务返回的完整用量数据（summary + 各维度行，内存驻留）
#   _LoadSignals：跨线程信号载体（usage_ready/quota_ready/error）
#   _ExportSignals：导出任务信号载体（done/failed）
#   _CdpGuideSignals：CDP 凭据引导任务信号载体（success/failed）
#   _UsageTask：用量统计后台任务（独立打开只读连接，规避 sqlite 跨线程限制）
#   _QuotaTask：配额拉取后台任务（网络不阻塞 UI，支持注入 fetcher）
#   _ExportTask：导出后台任务（独立连接 + exporter.export_all 落盘）
#   _CdpGuideTask：CDP 一键获取凭据任务（启动临时调试 Chrome → 轮询登录[CDP 拿
#     cookie + 页面 URL 提取 workspaceID，E4 改案] → 写凭据文件 → 关闭清理；
#     不影响用户浏览器；login_wait_seconds 默认 None 从 base.json 读）
#   _RemainingPieChart：剩余量饼图控件（QPainter 双色圆弧 + 中心"剩余 Y%"，P16）
# 函数：
#   _format_tokens()：K/M/B/G 缩写格式化
#   _format_cost()：费用格式化（近零容差内显示 -，≥1 两位小数，<1 四位小数）
#   _cache_rate_percent()：缓存率计算（(缓存读+缓存写)/总 token，卡片与表格共用，P17）
#   _format_cache_rate()：缓存率格式化（一位小数百分比）
#   _format_cache_rate_of()：缓存率计算+格式化复合（卡片/明细弹窗/表格 3 处共用，6A.4 O3）
#   _format_total_tokens()：总览总 token 格式化（千分位 + 亿单位，P15）
#   _wait_for_login_cookie()：端到端轮询登录（实测 dashboard 可解析才算完成，
#     返回验证通过的 workspace_id，多账户场景防保存错误）
#   MainWindow：
#     __init__：注入 db_path/quota_fetcher（可测试）；恢复配置（主题/窗口几何/
#       刷新间隔/隐藏列，config.settings.load_config）；装配 UI；启动延迟加载
#       （QTimer.singleShot(AUTO_LOAD_DELAY_MS) + _pending_auto_load 标志，手动刷新
#       取消防双加载，参考 OpenCode-Token 的 after(10)+after_cancel 模式）；QTimer 定时刷新
#     quota_updated 信号：配额加载完成发射（main.py 接线托盘图标/预警）
#     _build_ui：卡片区（P17：总 tokens/输入/输出/缓存率/总费用）+ Go 配额区（3 进度条 +
#       状态 + 剩余量饼图[P16]）+ 明细区（总览按钮[P15]/维度下拉/刷新/导出/设置[P13]/
#       主题按钮 + QTableWidget）；状态栏在 __init__ 信号连接区提前创建（M11）
#     refresh：手动/定时入口——取消自动加载标志，QThreadPool 并行启动两个任务
#     toggle_theme/_apply_theme：亮暗主题切换（QApplication.setStyleSheet）
#     _on_usage_ready/_on_quota_ready/_on_load_error：结果渲染；失败仅状态栏提示，
#       保留旧 view（成功后视图才替换）；配额缓存/错误仅状态栏警告不弹窗；
#       凭据缺失（错误且无缓存无来源）时显示引导卡片
#     _show_total_detail：点击总览按钮弹出总量明细（QMessageBox，P15）
#     _show_columns_menu/_on_column_toggle：列显示开关（QMenu 勾选，
#       setColumnHidden + hidden_columns 持久化，P13；E0.3：持久化失败仅
#       warning 降级，与 D0.10 同式）
#     _export_data：QFileDialog 选目录 → 后台 _ExportTask（状态栏提示导出中）
#     _render_cards/_render_quota/_render_table：卡片（P17 新顺序 + 缓存率）/进度条（颜色
#       分级，使用 themes.quota_chunk_color）与剩余量饼图（P16，正常显示/异常隐藏）/
#       表格渲染（内存数据，维度切换不查库；P13 新列顺序）
#     _set_status_style：配额状态标签样式名强制 QSS 重算（unpolish/polish）
#     _start_cdp_guide：后台启动 CDP 一键获取（按钮禁用防重复，状态栏提示）
#     _manual_guide：QInputDialog 输入 workspaceId + authCookie → save_dashboard_credentials
#       加密写入（P4：不再直接编辑明文文件）→ 自动刷新
#     _on_guide_success/_on_guide_failed：引导结果回传（成功自动刷新配额，
#       失败保留引导卡片供重试/手动填写）
#     save_state：窗口几何（QByteArray hex）/主题/刷新间隔/隐藏列 → config 持久化
#     closeEvent：保存状态并隐藏到托盘（常驻模式，真退出走托盘菜单）
# 设计理由：数据加载全后台（QThreadPool）+ 信号回传（线程安全）；worker 自建
#   只读连接避免 sqlite check_same_thread 问题；维度切换零查询；
#   配置"退出即存、启动即恢复"（对齐 AccelWorld B2 修复经验）；
#   CDP 引导独立临时 profile，不打扰用户正在使用的浏览器（S6.1 实测结论）
# 异常处理：任务内异常转 error/done/failed 信号；配额错误包装为 GoQuotaInfo
#   携带提示；引导失败仅状态栏提示不弹窗
# 关联配置：VERSION（main.py）；config.settings（geometry/theme/refresh_interval_ms/
#   hidden_columns）；go_quota（fetch_go_quota/save_dashboard_credentials 均可注入替换，
#   测试用）
