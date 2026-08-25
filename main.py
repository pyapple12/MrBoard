# myboard 程序入口模块

import sys

# D0.13（大会战 A3）：--version 检查需在 PyQt import 之前（CLI 路径不加载 GUI 依赖）
if "--version" in sys.argv or "-V" in sys.argv:
    from utils.logger import VERSION

    print(VERSION)
    raise SystemExit(0)

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from config.static.static_config import get_static_config
from modules.go_quota import GoQuotaInfo
from ui.main_window import MainWindow
from ui.system_tray import SystemTray
from ui.theme_loader import QUOTA_DANGER_PERCENT
from utils.logger import APP_NAME, get_logger

logger = get_logger(__name__)

# 静态配置解包（S8：参数外置 base.json；版本号单点导出 utils.logger，6A.3 R4）
_SC = get_static_config()

# 6A.3 O4：配额预警去重标志（持续超限只在首次触发时通知，状态回落复位）
_notified_danger = False


def main() -> None:
    # 程序入口：--version/-V 已在 import 前处理（D0.13），默认启动 GUI（主窗口 + 系统托盘）
    run_gui()


def run_gui() -> None:
    # 启动 GUI：创建应用/主窗口/托盘，连接托盘信号，进入事件循环
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    tray = SystemTray(window)
    tray.refresh_requested.connect(window.refresh)
    tray.quit_requested.connect(lambda: _quit_app(app, window, tray))
    window.quota_updated.connect(lambda info: _on_quota_updated(tray, info))
    # B0.9：托盘不可用（远程桌面/精简系统）时不 show，窗口关闭走真退出路径
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray.show()
    window.show()
    sys.exit(app.exec())


def _danger_notify(tray: SystemTray, info: GoQuotaInfo, suffix: str) -> None:
    # 超阈预警气泡单点（O1.1 收敛成功/缓存兜底两路复制）：阈值判定+去重标志+
    # 模板格式化+坏模板静态拼接兜底（P24/O0.3 含 AttributeError）+标题提取；
    # suffix 为消息尾部标注（成功路径空串、缓存路径配置缓存后缀，O2.2）
    global _notified_danger
    if info.overall_used_percent < QUOTA_DANGER_PERCENT or _notified_danger:
        return
    _notified_danger = True
    try:
        message = str(_SC.ui["notify_message_template"]).format(
            used=info.overall_used_percent,
            remaining=info.remaining_percent,
        )
    except (KeyError, ValueError, IndexError, AttributeError):
        # P24 定案（选项 X'）：坏模板兜底单层化——静态拼接为最终防线（不依赖
        # 配置，任何损坏都兜得住，信息不丢）
        message = (
            f"配额已使用 {info.overall_used_percent}%，剩余 {info.remaining_percent}%"
        )
    # notify_quota 在 try/except 链之外（模板正常与回退路径都执行）；
    # D0.7：notify_title 访问并入防护（契约校验已兜底，双保险）
    try:
        title = str(_SC.ui["notify_title"])
    except KeyError:
        title = APP_NAME
    tray.notify_quota(title, f"{message}{suffix}")


def _on_quota_updated(tray: SystemTray, infos: list[GoQuotaInfo]) -> None:
    # 配额加载完成（PL001.8 多账户列表）：取最紧的有效账户驱动托盘图标/预警；
    # 全部无效才置灰图标；overall ≥ QUOTA_DANGER_PERCENT 时气泡预警（6A.3 O4 去重
    # 语义不变；O1.1 弹泡逻辑单点化至 _danger_notify，成功/缓存兜底两路共用）
    global _notified_danger
    valid = [item for item in infos if item.error is None or item.is_cached]
    if not valid:
        # 全部账户失败：图标置灰 + 复位去重标志（下次成功重新可弹）
        _notified_danger = False
        tray.update_quota_status(None)
        return
    info = max(valid, key=lambda item: item.overall_used_percent)
    if info.error is None:
        tray.update_quota_status(info.overall_used_percent)
        _danger_notify(tray, info, "")
        if info.overall_used_percent < QUOTA_DANGER_PERCENT:
            # 回落到阈值以下：复位去重标志（再次超限才重新弹）
            _notified_danger = False
    else:
        # D0.3：错误/缓存兜底（is_cached）不是失败——托盘按真实数据更新、
        # 不复位去重标志（否则 60s 窗口内手动刷新即复位，超限重复弹气泡）；
        # N3.1/O2.2：超阈仍弹气泡，尾部标注读配置缓存后缀（data_page_messages
        # 组已入契约，导入期拦截删键）
        tray.update_quota_status(info.overall_used_percent)
        _danger_notify(tray, info, str(_SC.ui["data_page_messages"]["cache_suffix"]))


def _quit_app(app: QApplication, window: MainWindow, tray: SystemTray) -> None:
    # 托盘退出：保存窗口状态后退出应用（对齐 AccelWorld 修复 B2 经验；
    # D0.10：保存失败仅 warning，不阻塞退出流程）
    try:
        window.save_state()
    except Exception as exc:
        logger.warning("保存窗口状态失败：%s", exc)
    tray.hide()
    app.quit()


if __name__ == "__main__":
    main()

# ===== main.py 模块说明 =====
# 模块级常量：
#   _SC：静态配置解包单例（base.json/ui.json，模块顶层一次性读取）
#   _notified_danger：配额预警去重标志（持续超限只在首次触发时通知，回落复位）
#   APP_NAME：应用名（来自 utils.logger 单一来源，D1/C14）
#   QUOTA_DANGER_PERCENT：配额预警阈值（ui/theme_loader 导出，ui.json
#     quota_danger_percent 驱动，J3.1 补列）
# 模块级导入：QApplication / QSystemTrayIcon（PyQt6.QtWidgets，J4.1 补列——
#   run_gui 创建应用实例、_quit_app 与 closeEvent 判断托盘可用性）
# 版本说明：VERSION 由 utils.logger 单点导出（R4），main.py 仅 --version 分支
#   局部 import（D0.13），不再作为模块属性导出（F3.1/G3.2 同步）
# 函数：
#   main()：E3.4 同步 D0.13——仅分发 run_gui()；--version/-V 已在模块顶层
#     （PyQt import 前）处理（D0.13，SystemExit 提前返回，CLI 不加载 GUI 依赖）
#   run_gui()：
#     逻辑步骤：QApplication → MainWindow → SystemTray（信号连接：刷新→window.refresh，
#       退出→_quit_app，配额→_on_quota_updated 托盘图标/预警）→ 显示 → app.exec()
#     设计理由：顶层 import（循环依赖已根治，审计 M2）；托盘/窗口装配集中在入口
#   _danger_notify(tray, info, suffix)：
#     逻辑步骤：阈值判定+去重标志检查 → notify_message_template 格式化（坏模板
#       静态拼接兜底，含 AttributeError）→ notify_title 提取（缺键兜底 APP_NAME）
#       → tray.notify_quota(title, message+suffix)
#     设计理由：O1.1 收敛成功/缓存兜底两路复制的气泡逻辑单点化；suffix 由调用方
#       注入来源标注（成功空串/缓存读 data_page_messages.cache_suffix，O2.2）
#   _on_quota_updated(tray, infos)：
#     逻辑步骤：多账户列表取"最紧有效账户"（error 为空或 is_cached 中 overall
#       最高者，A0.16/K3.5 口径同步）驱动托盘图标/状态色；全部无效才置灰；
#       超阈弹泡统一委托 _danger_notify（N3.1 起缓存兜底路径同样弹泡并标注
#       缓存来源；成功路径回落至阈值以下复位去重标志，O4 去重语义不变）
#     设计理由：审计 B2 修复——托盘预警功能接线；PL001.8 起多账户语义
#   _quit_app(app, window, tray)：
#     逻辑步骤：window.save_state() → tray.hide() → app.quit()
#     设计理由：任何退出路径都先保存状态（对齐 AccelWorld B2 修复经验）
# 异常处理：GUI 异常由 Qt 事件循环处理；本模块无网络/文件操作
# 关联配置：config/static/base.json（version）；ui.json（notify_title/notify_message_template，
#   P24 定案后 fallback 键已移除）；ui/theme_loader（quota_danger_percent）
