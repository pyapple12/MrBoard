# myboard 程序入口模块

import sys

from PyQt6.QtWidgets import QApplication

from config.constants import VERSION
from modules.go_quota import GoQuotaInfo
from ui.main_window import MainWindow
from ui.system_tray import SystemTray


def main() -> None:
    # 程序入口：--version/-V 打印版本号，默认启动 GUI（主窗口 + 系统托盘）
    if "--version" in sys.argv or "-V" in sys.argv:
        print(VERSION)
        return
    run_gui()


def run_gui() -> None:
    # 启动 GUI：创建应用/主窗口/托盘，连接托盘信号，进入事件循环
    app = QApplication(sys.argv)
    app.setApplicationName("myboard")
    window = MainWindow()
    tray = SystemTray(window)
    tray.refresh_requested.connect(window.refresh)
    tray.quit_requested.connect(lambda: _quit_app(app, window, tray))
    window.quota_updated.connect(lambda info: _on_quota_updated(tray, info))
    tray.show()
    window.show()
    sys.exit(app.exec())


def _on_quota_updated(tray: SystemTray, info: GoQuotaInfo) -> None:
    # 配额加载完成：更新托盘图标状态色；≥80% 时气泡预警（错误时图标置灰）
    if info.error is None:
        tray.update_quota_status(info.overall_used_percent)
        if info.overall_used_percent >= 80:
            tray.notify_quota(
                "OpenCode Go 配额预警",
                f"最紧窗口已使用 {info.overall_used_percent}%，剩余 {info.remaining_percent}%",
            )
    else:
        tray.update_quota_status(None)


def _quit_app(app: QApplication, window: MainWindow, tray: SystemTray) -> None:
    # 托盘退出：保存窗口状态后退出应用（对齐 AccelWorld 修复 B2 经验）
    window.save_state()
    tray.hide()
    app.quit()


if __name__ == "__main__":
    main()

# ===== main.py 模块说明 =====
# 模块级常量：
#   VERSION：来自 config.constants（单一来源），main.py 与 ui 层共同引用，
#     消除循环依赖（审计 M1/M2 修复：原 VERSION 放 main.py 导致 ui 反向引用）
# 函数：
#   main()：
#     输入：sys.argv 命令行参数
#     输出：--version/-V 时打印版本号；否则进入 GUI 事件循环
#     逻辑步骤：判断参数含 --version 或 -V 则打印 VERSION 提前返回；否则 run_gui()
#   run_gui()：
#     逻辑步骤：QApplication → MainWindow → SystemTray（信号连接：刷新→window.refresh，
#       退出→_quit_app，配额→_on_quota_updated 托盘图标/预警）→ 显示 → app.exec()
#     设计理由：顶层 import（循环依赖已根治，审计 M2）；托盘/窗口装配集中在入口
#   _on_quota_updated(tray, info)：
#     逻辑步骤：错误置灰图标；正常更新状态色；overall ≥80% 时气泡预警
#     设计理由：审计 B2 修复——托盘预警功能接线
#   _quit_app(app, window, tray)：
#     逻辑步骤：window.save_state() → tray.hide() → app.quit()
#     设计理由：任何退出路径都先保存状态（对齐 AccelWorld B2 修复经验）
# 异常处理：GUI 异常由 Qt 事件循环处理；本模块无网络/文件操作
# 关联配置：config.constants.VERSION
