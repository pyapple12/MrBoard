# 主窗口模块：用量总览卡片 + Go 配额进度条 + 分组表格 + 后台加载与定时刷新

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import (
    QByteArray,
    QObject,
    QRunnable,
    QThreadPool,
    QTimer,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
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
    CREDENTIALS_FILE,
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
from ui.themes import get_theme, quota_chunk_color
from utils.file_utils import write_json
from utils.logger import get_logger

logger = get_logger(__name__)

# 静态配置解包（S8：参数外置 base.json，运行时零 IO）
_SC = get_static_config()
VERSION = str(_SC.base["version"])
REFRESH_INTERVAL_MS = int(_SC.base["refresh_interval_ms"])
AUTO_LOAD_DELAY_MS = int(_SC.base["auto_load_delay_ms"])

# 分组维度与表格列配置（表头文案外置 ui.json，S8.3；维度枚举保留代码内）
DIMENSIONS = ("total", "day", "model", "provider", "agent")
DIMENSION_LABELS = {
    "total": "总览",
    "day": "按日期",
    "model": "按模型",
    "provider": "按 Provider",
    "agent": "按 Agent",
}
TABLE_HEADERS = tuple(_SC.ui["table_headers"])


@dataclass
class UsageData:
    # 后台任务返回的完整用量数据（内存驻留，维度切换不再查库）

    summary: UsageSummary
    rows: dict[str, list[UsageRow]]


class _LoadSignals(QObject):
    # 后台任务信号载体：用量/配额就绪与错误（跨线程 emit 回主线程）

    usage_ready = pyqtSignal(object)
    quota_ready = pyqtSignal(object)
    error = pyqtSignal(str)


class _ExportSignals(QObject):
    # 导出任务信号载体：完成/失败回传主线程

    done = pyqtSignal(str)
    failed = pyqtSignal(str)


class _UsageTask(QRunnable):
    # 用量统计后台任务：独立打开只读连接（规避 sqlite 跨线程限制），完成后发信号

    def __init__(self, db_path: Path, signals: _LoadSignals) -> None:
        # 初始化任务：记录数据库路径与信号对象
        super().__init__()
        self.db_path = db_path
        self.signals = signals

    def run(self) -> None:
        # 后台执行：totals + 全部分组查询，失败发 error 信号
        try:
            db = OpenCodeDB(self.db_path)
            try:
                summary = db.totals()
                rows = {
                    "total": [
                        UsageRow(
                            label="总计",
                            calls=summary.messages,
                            tokens=summary.tokens,
                            cost=summary.recorded_cost,
                        )
                    ],
                    "day": db.by_day(limit=200),
                    "model": db.by_model(limit=50),
                    "provider": db.by_provider(limit=50),
                    "agent": db.by_agent(limit=50),
                }
            finally:
                db.close()
            self.signals.usage_ready.emit(UsageData(summary=summary, rows=rows))
        except Exception as exc:
            self.signals.error.emit(f"用量统计失败：{exc}")


class _QuotaTask(QRunnable):
    # Go 配额后台任务：网络请求不阻塞 UI，完成后发信号

    def __init__(
        self, signals: _LoadSignals, quota_fetcher: Callable[..., GoQuotaInfo]
    ) -> None:
        # 初始化任务：记录信号对象与配额获取函数（支持测试注入）
        super().__init__()
        self.signals = signals
        self.quota_fetcher = quota_fetcher

    def run(self) -> None:
        # 后台执行：拉取 Go 配额（内部含节流与缓存兜底）
        try:
            self.signals.quota_ready.emit(self.quota_fetcher())
        except Exception as exc:
            self.signals.quota_ready.emit(GoQuotaInfo(error=f"配额拉取异常：{exc}"))


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
            self.signals.done.emit(f"导出完成：{self.out_dir}")
        except Exception as exc:
            self.signals.failed.emit(f"导出失败：{exc}")


class _CdpGuideSignals(QObject):
    # CDP 凭据引导任务信号载体：成功/失败回传主线程

    success = pyqtSignal(str)
    failed = pyqtSignal(str)


def _wait_for_login_cookie(
    deadline: float, workspace_ids: list[str]
) -> tuple[str | None, str | None]:
    # 端到端轮询：拿 cookie 后实测 dashboard 可解析才算登录完成
    # （防占位 cookie 误判：打开登录页时页面会种匿名 auth cookie）
    # 返回 (cookie, 验证通过的 workspace_id)——多账户场景保存时须用验证通过的
    auth_cookie = None
    valid_workspace_id = None
    while time.time() < deadline and auth_cookie is None:
        # 调试：记录剩余等待时间，排查提前退出
        logger.info("轮询登录中（剩余 %.0f 秒）", deadline - time.time())
        candidate = browser_creds.fetch_auth_cookie_via_cdp(timeout=10)
        if candidate:
            if not workspace_ids:
                # 无 workspace 可验证：直接返回，交由上层"无 workspaceID"分支提示
                auth_cookie = candidate
                break
            for workspace_id in workspace_ids:
                try:
                    usage = fetch_dashboard_usage(
                        DashboardCredentials(workspace_id, candidate, "cdp验证")
                    )
                    if usage:
                        auth_cookie = candidate
                        valid_workspace_id = workspace_id
                        logger.info("cookie 验证通过（dashboard 可解析）")
                        break
                except GoQuotaError:
                    # 占位 cookie/未登录：dashboard 返回登录页或解析失败，继续轮询
                    continue
        if auth_cookie is None:
            time.sleep(int(_SC.base["cdp_poll_interval"]))
    # 调试：记录退出原因（超时还是拿到 cookie）
    logger.info(
        "轮询结束：cookie=%s，剩余 %.0f 秒",
        bool(auth_cookie),
        deadline - time.time(),
    )
    return auth_cookie, valid_workspace_id


class _CdpGuideTask(QRunnable):
    # CDP 一键获取凭据后台任务：启动临时调试 Chrome → 等登录 → 存凭据 → 清理

    def __init__(
        self, signals: _CdpGuideSignals, login_wait_seconds: int = 180
    ) -> None:
        # 初始化任务：记录信号对象与登录等待时长（默认取静态配置）
        super().__init__()
        self.signals = signals
        self.login_wait_seconds = (
            login_wait_seconds
            if login_wait_seconds is not None
            else int(_SC.base["cdp_login_wait_seconds"])
        )

    def run(self) -> None:
        # 后台执行：环境预检 → 快照 workspaceID → 启动调试 Chrome → 轮询登录 → 写凭据 → 清理
        proc = None
        try:
            user_data = browser_creds._chrome_user_data_dir()
            if browser_creds.is_chrome_running():
                logger.info("检测到用户 Chrome 正在运行（独立临时 profile 不冲突）")
            if not browser_creds.has_v20_cookies(user_data):
                self.signals.failed.emit(
                    "检测到旧版浏览器加密（v10），凭据可自动探测："
                    "请关闭浏览器后重启应用自动获取，无需 CDP 引导"
                )
                return
            workspace_ids = browser_creds._read_workspace_ids(
                user_data / "Default" / "History"
            )
            proc = browser_creds.launch_chrome_debug()
            if proc is None:
                self.signals.failed.emit(
                    "无法启动 Chrome 调试模式（未找到 chrome.exe，或调试端口已被占用）"
                )
                return
            if not browser_creds.wait_cdp_ready(timeout=30):
                self.signals.failed.emit("Chrome 调试端口未就绪，请重试或使用手动填写")
                return
            auth_cookie, valid_workspace_id = _wait_for_login_cookie(
                time.time() + self.login_wait_seconds, workspace_ids
            )
            if not auth_cookie:
                # 调试：确认超时路径
                logger.info("登录超时，关闭调试实例")
                self.signals.failed.emit(
                    f"等待登录超时（{self.login_wait_seconds // 60} 分钟）。"
                    "请确认已在新窗口登录 opencode.ai 后重试，或使用手动填写"
                )
                return
            # 调试：确认拿到 cookie 路径
            logger.info("已获取 cookie，写入凭据")
            if not workspace_ids:
                self.signals.failed.emit(
                    "已获取 cookie 但未在浏览历史中找到 workspaceID，请使用手动填写"
                )
                return
            # 保存验证通过的 workspace（多账户场景：不能固定取第一个）
            saved_workspace_id = valid_workspace_id or workspace_ids[0]
            save_dashboard_credentials(saved_workspace_id, auth_cookie)
            self.signals.success.emit(
                f"凭据已保存（workspaceId: {saved_workspace_id[:16]}…），正在刷新配额"
            )
        except Exception as exc:
            self.signals.failed.emit(f"自动获取失败：{exc}")
        finally:
            if proc is not None:
                browser_creds.shutdown_chrome_debug(proc)


def _format_tokens(count: int) -> str:
    # token 数格式化：K/M/B/G 缩写（千/百万/十亿/万亿）
    if count >= 1e9:
        return f"{count / 1e9:.1f}B"
    if count >= 1e6:
        return f"{count / 1e6:.1f}M"
    if count >= 1e3:
        return f"{count / 1e3:.1f}K"
    return str(count)


def _format_cost(cost: float) -> str:
    # 费用格式化：≥1 保留 2 位，<1 保留 4 位；为 0 显示 -
    if cost == 0:
        return "-"
    if cost >= 1:
        return f"${cost:.2f}"
    return f"${cost:.4f}"


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
        self._quota_info: GoQuotaInfo | None = None
        self._is_dark = False
        self._pending_auto_load = False
        # globalInstance 可能返回 None（PyQt6 stub Optional），兜底新建实例
        self._pool = QThreadPool.globalInstance() or QThreadPool()
        self._signals = _LoadSignals()
        self._signals.usage_ready.connect(self._on_usage_ready)
        self._signals.quota_ready.connect(self._on_quota_ready)
        self._signals.error.connect(self._on_load_error)
        self._export_signals = _ExportSignals()
        self._export_signals.done.connect(self._status_bar_show)
        self._export_signals.failed.connect(self._status_bar_show)
        self._guide_signals = _CdpGuideSignals()
        self._guide_signals.success.connect(self._on_guide_success)
        self._guide_signals.failed.connect(self._on_guide_failed)

        self.setWindowTitle(f"myboard 用量与配额 {VERSION}")
        self.resize(int(_SC.base["window_width"]), int(_SC.base["window_height"]))
        # 恢复配置：主题/窗口几何（S5 配置持久化）
        self._config = load_config()
        self._is_dark = self._config.theme == "dark"
        if self._config.window_geometry:
            self.restoreGeometry(
                QByteArray.fromHex(self._config.window_geometry.encode())
            )
        self._build_ui()
        self._apply_theme()
        self._status_bar.showMessage("正在加载…")

        # 启动延迟加载（手动刷新会取消该调度，防双加载）
        self._pending_auto_load = True
        QTimer.singleShot(AUTO_LOAD_DELAY_MS, self._trigger_auto_load)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(self._config.refresh_interval_ms)

    def _build_ui(self) -> None:
        # 装配界面：卡片区 + 配额区 + 引导卡 + 明细区 + 状态栏（各段独立方法）
        central = QWidget()
        self.setCentralWidget(central)
        self._layout = QVBoxLayout(central)
        self._layout.setContentsMargins(16, 12, 16, 8)
        self._layout.setSpacing(10)
        self._build_cards()
        self._build_quota_section()
        self._build_guide_card()
        self._build_detail_section()
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

    def _build_cards(self) -> None:
        # 构建用量总览卡片区（会话/tokens/费用/输入/缓存读）
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(8)
        self._cards: dict[str, QLabel] = {}
        for key, title in (
            ("sessions", "会话"),
            ("tokens", "总 tokens"),
            ("cost", "总费用"),
            ("input", "输入"),
            ("cache_read", "缓存读"),
        ):
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
        # 构建 Go 配额区（标题/状态 + 3 进度条 + 元信息）
        quota_frame = QFrame()
        quota_frame.setObjectName("card")
        quota_box = QVBoxLayout(quota_frame)
        title_row = QHBoxLayout()
        quota_title = QLabel("OpenCode Go 配额")
        quota_title.setObjectName("section_title")
        self._quota_status = QLabel("")
        self._quota_status.setObjectName("status_ok")
        title_row.addWidget(quota_title)
        title_row.addStretch(1)
        title_row.addWidget(self._quota_status)
        quota_box.addLayout(title_row)
        self._quota_bars: dict[str, QProgressBar] = {}
        self._quota_reset: dict[str, QLabel] = {}
        for key, label in (
            ("five_hour", "5 小时"),
            ("weekly", "每周"),
            ("monthly", "每月"),
        ):
            row = QHBoxLayout()
            name_label = QLabel(label)
            name_label.setFixedWidth(60)
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
        meta_label = QLabel("")
        meta_label.setObjectName("card_title")
        quota_box.addWidget(meta_label)
        self._quota_meta = meta_label
        self._layout.addWidget(quota_frame)

    def _build_guide_card(self) -> None:
        # 构建凭据配置引导卡片（凭据缺失时显示，S6.2）
        guide_frame = QFrame()
        guide_frame.setObjectName("card")
        guide_box = QVBoxLayout(guide_frame)
        guide_text = QLabel(
            '未配置 Go 配额凭据。点击"一键自动获取"将临时打开一个 Chrome 窗口'
            "（不影响你正在使用的浏览器），登录 opencode.ai 后自动保存凭据；"
            '或点击"手动填写"自行配置。'
        )
        guide_text.setWordWrap(True)
        guide_text.setObjectName("card_title")
        guide_box.addWidget(guide_text)
        guide_buttons = QHBoxLayout()
        self._auto_guide_button = QPushButton("一键自动获取")
        self._auto_guide_button.clicked.connect(self._start_cdp_guide)
        self._manual_guide_button = QPushButton("手动填写")
        self._manual_guide_button.clicked.connect(self._manual_guide)
        guide_buttons.addWidget(self._auto_guide_button)
        guide_buttons.addWidget(self._manual_guide_button)
        guide_buttons.addStretch(1)
        guide_box.addLayout(guide_buttons)
        guide_frame.hide()
        self._layout.addWidget(guide_frame)
        self._guide_frame = guide_frame

    def _build_detail_section(self) -> None:
        # 构建明细区（维度下拉/刷新/导出/主题按钮 + 分组表格）
        section_row = QHBoxLayout()
        detail_title = QLabel("用量明细")
        detail_title.setObjectName("section_title")
        self._dimension_combo = QComboBox()
        for dim in DIMENSIONS:
            self._dimension_combo.addItem(DIMENSION_LABELS[dim], dim)
        self._dimension_combo.currentIndexChanged.connect(self._render_table)
        self._refresh_button = QPushButton("刷新")
        self._refresh_button.clicked.connect(self.refresh)
        self._export_button = QPushButton("导出")
        self._export_button.clicked.connect(self._export_data)
        self._theme_button = QPushButton("主题")
        self._theme_button.clicked.connect(self.toggle_theme)
        section_row.addWidget(detail_title)
        section_row.addStretch(1)
        section_row.addWidget(self._dimension_combo)
        section_row.addWidget(self._refresh_button)
        section_row.addWidget(self._export_button)
        section_row.addWidget(self._theme_button)
        self._layout.addLayout(section_row)

        self._table = QTableWidget(0, len(TABLE_HEADERS))
        self._table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._layout.addWidget(self._table, 1)

    def _trigger_auto_load(self) -> None:
        # 执行启动延迟加载（标志位确认未被手动刷新取消）
        if self._pending_auto_load:
            self.refresh()

    def refresh(self) -> None:
        # 手动/定时刷新入口：取消待执行自动加载，后台并行拉用量与配额
        self._pending_auto_load = False
        self._status_bar.showMessage("刷新中…")
        if self.db_path is not None:
            self._pool.start(_UsageTask(self.db_path, self._signals))
        else:
            self._status_bar.showMessage(
                "未找到 opencode.db（可用 OPENCODE_DB 环境变量指定）"
            )
        self._pool.start(_QuotaTask(self._signals, self.quota_fetcher))

    def toggle_theme(self) -> None:
        # 切换亮/暗主题并应用
        self._is_dark = not self._is_dark
        self._apply_theme()

    def _apply_theme(self) -> None:
        # 应用当前主题 QSS 到应用级样式（isinstance 收窄 QCoreApplication → QApplication）
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setStyleSheet(get_theme("dark" if self._is_dark else "light"))

    def _on_usage_ready(self, data: UsageData) -> None:
        # 用量加载完成：渲染卡片与表格（成功后视图才替换，失败保留旧 view）
        self._usage_data = data
        self._render_cards(data.summary)
        self._render_table()
        self._status_bar.showMessage(
            f"用量已更新（{datetime.now().strftime('%H:%M:%S')}）"
        )

    def _on_quota_ready(self, info: GoQuotaInfo) -> None:
        # 配额加载完成：渲染进度条与元信息；凭据类错误时显示引导卡片；发射更新信号
        self._quota_info = info
        self._render_quota(info)
        self.quota_updated.emit(info)
        # 引导卡片显示条件：CDP 可解决的凭据类错误（无 dashboard 凭据/cookie 失效），
        # 且无缓存（历史成功过则不打扰）；no_key 等阶段 CDP 解决不了，不显示
        show_guide = (
            info.error is not None
            and not info.is_cached
            and info.error_stage in ("no_dashboard_creds", "auth")
            and info.remaining_percent == 0
            and info.five_hour is None
        )
        self._guide_frame.setVisible(show_guide)

    def _on_load_error(self, message: str) -> None:
        # 加载失败：仅状态栏提示（保留旧 view，z.plan 第四章保留旧数据策略）
        self._status_bar.showMessage(message)

    def _status_bar_show(self, message: str) -> None:
        # 状态栏消息显示（供导出信号槽复用）
        self._status_bar.showMessage(message)

    def _start_cdp_guide(self) -> None:
        # 一键自动获取：后台执行 CDP 引导流程（独立临时 Chrome，不影响用户浏览器）
        self._guide_frame.hide()
        self._auto_guide_button.setEnabled(False)
        self._status_bar.showMessage(
            "正在启动临时 Chrome，请在弹出的窗口登录 opencode.ai…"
        )
        self._pool.start(_CdpGuideTask(self._guide_signals))

    def _manual_guide(self) -> None:
        # 手动填写入口：生成配置模板并打开配置文件夹
        try:
            CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
            if not CREDENTIALS_FILE.is_file():
                write_json(CREDENTIALS_FILE, {"workspaceId": "", "authCookie": ""})
            example_path = CREDENTIALS_FILE.parent / "opencode-go.example.json"
            if not example_path.is_file():
                example_path.write_text(
                    json.dumps(
                        {
                            "_说明": "将本文件内容填入 opencode-go.json 后重命名",
                            "workspaceId": "wrk_xxx（从 opencode.ai 浏览器地址栏 /workspace/ 后复制）",
                            "authCookie": "xxx（浏览器开发者工具 → Application → Cookies → opencode.ai → auth 的值）",
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            os.startfile(str(CREDENTIALS_FILE.parent))
            self._status_bar.showMessage(
                f"已打开配置文件夹，请填写 opencode-go.json（示例见 opencode-go.example.json）"
            )
        except OSError as exc:
            self._status_bar.showMessage(f"打开配置文件夹失败：{exc}")

    def _on_guide_success(self, message: str) -> None:
        # 引导成功：提示并立即刷新配额（凭据已落盘，凭据链可读到）
        self._auto_guide_button.setEnabled(True)
        self._status_bar.showMessage(message)
        self.refresh()

    def _on_guide_failed(self, message: str) -> None:
        # 引导失败：状态栏提示，保留引导卡片供重试/手动填写
        self._auto_guide_button.setEnabled(True)
        self._guide_frame.show()
        self._status_bar.showMessage(message)

    def _export_data(self) -> None:
        # 选择导出目录并后台导出全部数据（CSV + JSON）
        if self.db_path is None:
            self._status_bar.showMessage("无数据库可导出")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not out_dir:
            return
        self._status_bar.showMessage("导出中…")
        self._pool.start(_ExportTask(self.db_path, Path(out_dir), self._export_signals))

    def _render_cards(self, summary: UsageSummary) -> None:
        # 渲染用量总览卡片值
        self._cards["sessions"].setText(str(summary.sessions))
        self._cards["tokens"].setText(_format_tokens(summary.tokens.total))
        self._cards["cost"].setText(_format_cost(summary.recorded_cost))
        self._cards["input"].setText(_format_tokens(summary.tokens.input))
        self._cards["cache_read"].setText(_format_tokens(summary.tokens.cache_read))

    def _set_status_style(self, object_name: str) -> None:
        # 设置配额状态标签样式名并强制 QSS 重算（setObjectName 后不重算颜色不生效）
        self._quota_status.setObjectName(object_name)
        style = self._quota_status.style()
        if style is not None:
            style.unpolish(self._quota_status)
            style.polish(self._quota_status)

    def _render_quota(self, info: GoQuotaInfo) -> None:
        # 渲染 Go 配额进度条与状态信息（颜色分级）
        windows = {
            "five_hour": info.five_hour,
            "weekly": info.weekly,
            "monthly": info.monthly,
        }
        for key, window in windows.items():
            bar = self._quota_bars[key]
            reset_label = self._quota_reset[key]
            if window is None:
                bar.setValue(0)
                reset_label.setText("未获取到")
                continue
            percent = int(round(window.usage_percent))
            bar.setValue(percent)
            bar.setFormat(f"{percent}%")
            bar.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {quota_chunk_color(percent)}; }}"
            )
            reset_label.setText(
                f"重置于 {window.reset_date.strftime('%H:%M') if window.reset_date else '-'}"
            )
        if info.is_cached:
            self._set_status_style("status_warn")
            self._quota_status.setText(f"⚠ 缓存数据：{info.error or ''}")
        elif info.error:
            self._set_status_style("status_warn")
            self._quota_status.setText(f"⚠ {info.error}")
        else:
            self._set_status_style("status_ok")
            self._quota_status.setText(
                f"最紧窗口 {info.overall_used_percent}% / 剩余 {info.remaining_percent}%"
            )
        self._quota_meta.setText(
            f"模型数：{info.model_count if info.model_count is not None else '未知'} ｜ "
            f"dashboard 凭据：{info.credential_source or '未配置'}"
        )

    def _render_table(self) -> None:
        # 按当前维度渲染分组表格（数据已在内存，不查库）
        dimension = self._dimension_combo.currentData()
        rows = self._usage_data.rows.get(dimension, []) if self._usage_data else []
        self._table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            values = (
                str(row.label),
                str(row.calls),
                _format_tokens(row.tokens.input),
                _format_tokens(row.tokens.output),
                _format_tokens(row.tokens.reasoning),
                _format_tokens(row.tokens.cache_read),
                _format_tokens(row.tokens.cache_write),
                _format_tokens(row.tokens.total),
                _format_cost(row.cost),
            )
            for col, value in enumerate(values):
                self._table.setItem(index, col, QTableWidgetItem(value))

    def save_state(self) -> None:
        # 保存窗口状态：几何/主题/刷新间隔到配置文件（托盘退出与关闭时调用）
        config = load_config()
        config.window_geometry = bytes(self.saveGeometry().toHex().data()).decode()
        config.theme = "dark" if self._is_dark else "light"
        config.refresh_interval_ms = self._refresh_timer.interval()
        save_config(config)

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        # 关闭按钮：保存状态并隐藏到托盘（常驻模式，不真正退出；签名对齐 PyQt6 stub）
        self.save_state()
        self.hide()
        if a0 is not None:
            a0.ignore()


# ===== ui/main_window.py 模块说明 =====
# 模块级常量：
#   REFRESH_INTERVAL_MS：定时刷新间隔 5 分钟
#   DIMENSIONS / DIMENSION_LABELS / TABLE_HEADERS：分组维度与表格列配置
# 类型：
#   UsageData：后台任务返回的完整用量数据（summary + 各维度行，内存驻留）
#   _LoadSignals：跨线程信号载体（usage_ready/quota_ready/error）
#   _ExportSignals：导出任务信号载体（done/failed）
#   _CdpGuideSignals：CDP 凭据引导任务信号载体（success/failed）
#   _UsageTask：用量统计后台任务（独立打开只读连接，规避 sqlite 跨线程限制）
#   _QuotaTask：配额拉取后台任务（网络不阻塞 UI，支持注入 fetcher）
#   _ExportTask：导出后台任务（独立连接 + exporter.export_all 落盘）
#   _CdpGuideTask：CDP 一键获取凭据任务（快照 workspaceID → 启动临时调试
#     Chrome → 轮询登录 → 写凭据文件 → 关闭清理；不影响用户浏览器）
# 函数：
#   _format_tokens()：K/M/B/G 缩写格式化
#   _format_cost()：费用格式化（0 显示 -，≥1 两位小数）
#   MainWindow：
#     __init__：注入 db_path/quota_fetcher（可测试）；恢复配置（主题/窗口几何/
#       刷新间隔，config.settings.load_config）；装配 UI；启动延迟加载
#       （QTimer.singleShot(10) + _pending_auto_load 标志，手动刷新取消防双加载，
#       参考 OpenCode-Token 的 after(10)+after_cancel 模式）；QTimer 定时刷新
#     quota_updated 信号：配额加载完成发射（main.py 接线托盘图标/预警）
#     _build_ui：卡片区（会话/tokens/费用/输入/缓存读）+ Go 配额区（3 进度条 +
#       状态与元信息）+ 明细区（维度下拉/刷新/导出/主题按钮 + QTableWidget）+ 状态栏
#     refresh：手动/定时入口——取消自动加载标志，QThreadPool 并行启动两个任务
#     toggle_theme/_apply_theme：亮暗主题切换（QApplication.setStyleSheet）
#     _on_usage_ready/_on_quota_ready/_on_load_error：结果渲染；失败仅状态栏提示，
#       保留旧 view（成功后视图才替换）；配额缓存/错误仅状态栏警告不弹窗
#     _export_data：QFileDialog 选目录 → 后台 _ExportTask（状态栏提示导出中）
#     _render_cards/_render_quota/_render_table：卡片/进度条（颜色分级，使用
#       themes.quota_chunk_color）/表格渲染（内存数据，维度切换不查库）
#     _on_quota_ready：凭据缺失（错误且无缓存无来源）时显示引导卡片
#     _start_cdp_guide：后台启动 CDP 一键获取（按钮禁用防重复，状态栏提示）
#     _manual_guide：生成 opencode-go.json 模板 + 示例文件 + 打开配置文件夹
#     _on_guide_success/_on_guide_failed：引导结果回传（成功自动刷新配额，
#       失败保留引导卡片供重试/手动填写）
#     save_state：窗口几何（QByteArray hex）/主题/刷新间隔 → config 持久化
#     closeEvent：保存状态并隐藏到托盘（常驻模式，真退出走托盘菜单）
# 设计理由：数据加载全后台（QThreadPool）+ 信号回传（线程安全）；worker 自建
#   只读连接避免 sqlite check_same_thread 问题；维度切换零查询；
#   配置"退出即存、启动即恢复"（对齐 AccelWorld B2 修复经验）；
#   CDP 引导独立临时 profile，不打扰用户正在使用的浏览器（S6.1 实测结论）
# 异常处理：任务内异常转 error/done/failed 信号；配额错误包装为 GoQuotaInfo
#   携带提示；引导失败仅状态栏提示不弹窗
# 关联配置：VERSION（main.py）；config.settings（geometry/theme/refresh_interval_ms）；
#   go_quota.CREDENTIALS_FILE（凭据文件）；OpenCodeDB/fetch_go_quota 均可注入
#   替换（测试用）
