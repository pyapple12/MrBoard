# 主题样式模块：QSS 模板 + 双调色板（浅/深），配额阈值/颜色外置 ui.json

from config.settings import THEMES
from config.static.static_config import get_static_config

# ===== QSS 模板（{占位符} 由调色板替换；QSS 自身的 {} 保持不变） =====
_QSS_TEMPLATE = """
QMainWindow, QWidget {
    background-color: {bg};
    color: {fg};
}
QFrame#card {
    background-color: {card_bg};
    border: 1px solid {card_border};
    border-radius: 8px;
}
QLabel#card_value {
    font-size: 20px;
    font-weight: bold;
    color: {card_value_color};
}
QLabel#card_title {
    font-size: 12px;
    color: {card_title_color};
}
QLabel#section_title {
    font-size: 14px;
    font-weight: bold;
    color: {section_title_color};
}
QLabel#status_ok { color: {status_ok}; }
QLabel#status_warn { color: {status_warn}; }
QProgressBar {
    border: 1px solid {progress_border};
    border-radius: 6px;
    background-color: {progress_bg};
    text-align: center;
    height: 18px;
    color: {fg};
}
QProgressBar::chunk { border-radius: 6px; background-color: {chunk_ok}; }
QTableWidget {
    background-color: {table_bg};
    border: 1px solid {card_border};
    border-radius: 6px;
    gridline-color: {table_grid};
    color: {fg};
}
QHeaderView::section {
    background-color: {header_bg};
    border: none;
    padding: 6px;
    font-weight: bold;
    color: {fg};
}
QPushButton {
    background-color: {button_bg};
    color: {button_fg};
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
}
QPushButton:hover { background-color: {button_hover}; }
QComboBox {
    background-color: {combo_bg};
    border: 1px solid {combo_border};
    border-radius: 4px;
    padding: 4px 8px;
    color: {fg};
}
QComboBox::drop-down { border: none; }
QStatusBar { background-color: {statusbar_bg}; color: {statusbar_fg}; }
QMenu { background-color: {menu_bg}; color: {fg}; }
QMenu::item:selected { background-color: {menu_selected}; }
"""

# 浅色调色板
_LIGHT_PALETTE = {
    "bg": "#f5f6f8",
    "fg": "#333333",
    "card_bg": "#ffffff",
    "card_border": "#e0e0e0",
    "card_value_color": "#1976d2",
    "card_title_color": "#888888",
    "section_title_color": "#444444",
    "status_ok": "#2e7d32",
    "status_warn": "#e65100",
    "progress_border": "#cccccc",
    "progress_bg": "#eeeeee",
    "table_bg": "#ffffff",
    "table_grid": "#eeeeee",
    "header_bg": "#f0f1f3",
    "button_bg": "#1976d2",
    "button_fg": "#ffffff",
    "button_hover": "#1565c0",
    "combo_bg": "#ffffff",
    "combo_border": "#cccccc",
    "statusbar_bg": "#e8eaed",
    "statusbar_fg": "#666666",
    "menu_bg": "#ffffff",
    "menu_selected": "#e3f2fd",
}

# 深色调色板
_DARK_PALETTE = {
    "bg": "#1e1e1e",
    "fg": "#d4d4d4",
    "card_bg": "#2a2a2a",
    "card_border": "#3a3a3a",
    "card_value_color": "#64b5f6",
    "card_title_color": "#9e9e9e",
    "section_title_color": "#c0c0c0",
    "status_ok": "#81c784",
    "status_warn": "#ffb74d",
    "progress_border": "#444444",
    "progress_bg": "#333333",
    "table_bg": "#262626",
    "table_grid": "#333333",
    "header_bg": "#333333",
    "button_bg": "#1976d2",
    "button_fg": "#ffffff",
    "button_hover": "#1565c0",
    "combo_bg": "#2a2a2a",
    "combo_border": "#444444",
    "statusbar_bg": "#2a2a2a",
    "statusbar_fg": "#9e9e9e",
    "menu_bg": "#2a2a2a",
    "menu_selected": "#37474f",
}

# 配额颜色与阈值（S8.3：外置 ui.json，静态配置解包）
_SC = get_static_config()
QUOTA_WARN_PERCENT = int(_SC.ui["quota_warn_percent"])
QUOTA_DANGER_PERCENT = int(_SC.ui["quota_danger_percent"])
QUOTA_COLOR_OK = str(_SC.ui["colors"]["quota_ok"])
QUOTA_COLOR_WARN = str(_SC.ui["colors"]["quota_warn"])
QUOTA_COLOR_DANGER = str(_SC.ui["colors"]["quota_danger"])


def _build_theme(palette: dict[str, str]) -> str:
    # 按调色板构建 QSS（str.replace 注入占位符，避开 QSS 自身花括号）
    result = _QSS_TEMPLATE
    for key, value in palette.items():
        result = result.replace("{" + key + "}", value)
    return result


LIGHT_THEME = _build_theme(_LIGHT_PALETTE)
DARK_THEME = _build_theme(_DARK_PALETTE)


def get_theme(name: str) -> str:
    # 按主题名返回 QSS 样式字符串（THEMES[1] = dark，单一来源见 config.settings，未知返回浅色）
    if name == THEMES[1]:
        return DARK_THEME
    return LIGHT_THEME


def quota_chunk_color(percent: int) -> str:
    # 按配额使用百分比返回进度条颜色：<50 绿、50-80 黄、>80 红
    if percent >= QUOTA_DANGER_PERCENT:
        return QUOTA_COLOR_DANGER
    if percent >= QUOTA_WARN_PERCENT:
        return QUOTA_COLOR_WARN
    return QUOTA_COLOR_OK


# ===== ui/themes.py 模块说明 =====
# 模块级常量：
#   _QSS_TEMPLATE：QSS 模板（{占位符} 由调色板注入；QSS 自身花括号不受影响）
#   _LIGHT_PALETTE / _DARK_PALETTE：浅/深色调色板（20+ 色值键）
#   QUOTA_WARN_PERCENT / QUOTA_DANGER_PERCENT：配额阈值（50/80，多处共用）
#   QUOTA_COLOR_OK / WARN / DANGER：配额三档颜色
#   LIGHT_THEME / DARK_THEME：由模板 + 调色板构建的最终 QSS
# 函数：
#   _build_theme(palette)：str.replace 注入占位符（审计 D10：消除两套 QSS 60 行
#     重复，改一处样式只需改模板或调色板）
#   get_theme(name)：按主题名返回 QSS（默认浅色）
#   quota_chunk_color(percent)：按使用百分比返回 chunk 颜色（阈值用常量，审计 D13）
# 设计理由：样式集中管理；QProgressBar::chunk 动态颜色通过 setStyleSheet 单行覆盖
# 异常处理：无（纯常量与纯函数）
# 关联配置：主题名由 main_window 维护（S5 持久化）
