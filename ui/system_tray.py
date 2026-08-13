# 系统托盘模块：常驻图标 + 菜单（显示窗口/刷新/退出）+ 配额状态通知

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from config.static.static_config import get_static_config
from ui.themes import QUOTA_COLOR_OK, quota_chunk_color
from utils.logger import build_app_title

# 图标/通知参数（S8.3：外置 ui.json，静态配置解包）
_SC = get_static_config()
ICON_SIZE = int(_SC.ui["icon_size"])
NOTIFY_DURATION_MS = int(_SC.ui["notify_duration_ms"])
QUOTA_GRAY = str(_SC.ui["colors"]["quota_gray"])
PIE_DOT_COLOR = str(_SC.ui["colors"]["quota_pie_dot"])  # C23：白点色值外置
# A1.1：标题拼接单点 utils.logger.build_app_title（tooltip 与主窗口标题一致）
MENU_LABELS = dict(_SC.ui["menu_labels"])  # 5A.3 C5：菜单文案外置 ui.json


class SystemTray(QSystemTrayIcon):
    # 常驻托盘：图标颜色反映配额状态，菜单触发信号由 main.py 装配

    refresh_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        # 初始化托盘：构建图标与菜单，连接激活信号（C12 补类型注解）
        super().__init__(parent)
        self.setIcon(self._build_icon(QUOTA_COLOR_OK))
        self.setToolTip(build_app_title())
        # 6A.2 D2：QSystemTrayIcon 非 QWidget 不能挂父，菜单存实例属性防 GC
        # （setContextMenu 不接管所有权，局部变量在 Python 引用消失后会被销毁）
        self._menu = QMenu()
        show_action = QAction(MENU_LABELS["show_window"], self._menu)
        show_action.triggered.connect(self.show_requested)
        refresh_action = QAction(MENU_LABELS["refresh"], self._menu)
        refresh_action.triggered.connect(self.refresh_requested)
        quit_action = QAction(MENU_LABELS["quit"], self._menu)
        quit_action.triggered.connect(self.quit_requested)
        self._menu.addAction(show_action)
        self._menu.addAction(refresh_action)
        self._menu.addSeparator()
        self._menu.addAction(quit_action)
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

    def show_requested(self) -> None:
        # 菜单"显示窗口"：主窗口显示并置前（isinstance 收窄类型供静态检查）
        window = self.parent()
        if isinstance(window, QWidget):
            window.show()
            window.raise_()
            window.activateWindow()

    def update_quota_status(self, used_percent: int | None) -> None:
        # 按最紧窗口使用百分比更新图标颜色（阈值/分级复用 themes.quota_chunk_color，
        # None → 灰色）
        if used_percent is None:
            self.setIcon(self._build_icon(QColor(QUOTA_GRAY)))
            return
        self.setIcon(self._build_icon(quota_chunk_color(used_percent)))

    def notify_quota(self, title: str, message: str) -> None:
        # 气泡通知配额状态（常驻后台时提示关键信息）
        self.showMessage(
            title, message, QSystemTrayIcon.MessageIcon.Information, NOTIFY_DURATION_MS
        )

    def _build_icon(self, color: QColor | str) -> QIcon:
        # 绘制圆形配额图标：中心填充状态色 + 白色圆点（几何按 ICON_SIZE 比例，L11）
        color = QColor(color)
        pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        margin = ICON_SIZE // 16  # 外圆边距（原 8/128）
        painter.drawEllipse(
            margin, margin, ICON_SIZE - margin * 2, ICON_SIZE - margin * 2
        )
        painter.setPen(QColor(PIE_DOT_COLOR))
        painter.setBrush(QColor(PIE_DOT_COLOR))
        dot = ICON_SIZE // 8  # 白色中心圆点直径（原 28/128）
        offset = (ICON_SIZE - dot) // 2
        painter.drawEllipse(offset, offset, dot, dot)
        painter.end()
        return QIcon(pixmap)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # 托盘图标单击/双击：显示主窗口
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_requested()


# ===== ui/system_tray.py 模块说明 =====
# 模块级常量：ICON_SIZE（图标像素尺寸）、NOTIFY_DURATION_MS（气泡通知时长）、
#   QUOTA_GRAY（托盘灰色，错误/未知态）、PIE_DOT_COLOR（中心圆点白色）、
#   MENU_LABELS（菜单文案，ui.json 外置，5A.3 C5）
# 导入函数：build_app_title（来自 utils.logger，标题单点——tooltip 与主窗口标题一致，B3.1/C3.5 归类）、
#   QUOTA_COLOR_OK / quota_chunk_color（来自 ui.themes，图标颜色与进度条分级同源，C13 归类）
# 类：SystemTray(QSystemTrayIcon)
#   信号：
#     refresh_requested / quit_requested：菜单触发，由 main.py 装配连接
#   方法：
#     __init__：构建状态色图标 + 菜单（显示窗口/刷新/退出）+ 激活信号
#     show_requested()：菜单"显示窗口"——window.show + raise_ + activateWindow
#     update_quota_status(used_percent)：按最紧窗口使用百分比更新图标颜色
#       （阈值/分级复用 themes.quota_chunk_color，None 灰色），供 main.py 在配额加载后调用
#     notify_quota(title, message)：气泡通知（常驻后台提示关键变化）
#     _build_icon(color)：QPainter 绘制圆形图标（状态色圆 + 白色中心点，几何按 ICON_SIZE 比例）
#     _on_activated(reason)：单击/双击托盘显示窗口
# 设计理由：常驻托盘形态（对齐 opencode-bar 菜单栏模式）；图标颜色一眼可见
#   配额紧张度；退出信号与刷新信号解耦，装配逻辑集中在 main.py
# 异常处理：托盘在 offscreen/无托盘环境下仅构造对象（不 show），不崩溃
# 关联配置：QUOTA 三色/阈值与分级来自 ui/themes.py（ui.json 外置）
