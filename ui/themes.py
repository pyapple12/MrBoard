# 主题样式模块：QSS 模板 + 双调色板（浅/深），配额阈值/颜色外置 ui.json

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

# 浅/深色调色板（4A.2 D5：整体外置 ui.json palettes，S8.3 颜色外置补齐）
_SC = get_static_config()
_LIGHT_PALETTE = dict(_SC.ui["palettes"]["light"])
_DARK_PALETTE = dict(_SC.ui["palettes"]["dark"])

# 配额颜色与阈值（S8.3：外置 ui.json，静态配置解包）
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


# 主题名常量（6A.3 R3：从 ui.json themes 数组派生，与 settings.THEMES 同源；
# 数组顺序即 light/dark 契约；替代 THEMES[1] 魔法索引与 "dark"/"light" 魔法字符串，
# main_window 切换与持久化共用）
THEME_NAMES = tuple(str(item) for item in _SC.ui["themes"])
LIGHT_THEME_NAME = THEME_NAMES[0]
DARK_THEME_NAME = THEME_NAMES[1]


def get_theme(name: str) -> str:
    # 按主题名返回 QSS 样式字符串（未知返回浅色）
    if name == DARK_THEME_NAME:
        return DARK_THEME
    return LIGHT_THEME


def quota_chunk_color(percent: int) -> str:
    # 按配额使用百分比返回进度条颜色：>=QUOTA_DANGER_PERCENT 红、
    # >=QUOTA_WARN_PERCENT 黄、其余绿（阈值来自 ui.json）
    if percent >= QUOTA_DANGER_PERCENT:
        return QUOTA_COLOR_DANGER
    if percent >= QUOTA_WARN_PERCENT:
        return QUOTA_COLOR_WARN
    return QUOTA_COLOR_OK


# ===== ui/themes.py 模块说明 =====
# 模块级常量：
#   _QSS_TEMPLATE：QSS 模板（{占位符} 由调色板注入；QSS 自身花括号不受影响）
#   _LIGHT_PALETTE / _DARK_PALETTE：浅/深色调色板（20+ 色值键）
#   QUOTA_WARN_PERCENT / QUOTA_DANGER_PERCENT：配额阈值（ui.json quota_warn/danger_percent 驱动）
#   QUOTA_COLOR_OK / WARN / DANGER：配额三档颜色
#   LIGHT_THEME / DARK_THEME：由模板 + 调色板构建的最终 QSS
#   LIGHT_THEME_NAME / DARK_THEME_NAME：主题名常量（main_window 切换/持久化共用）
# 函数：
#   _build_theme(palette)：str.replace 注入占位符（审计 D10：消除两套 QSS 60 行
#     重复，改一处样式只需改模板或调色板）
#   get_theme(name)：按主题名返回 QSS（默认浅色）
#   quota_chunk_color(percent)：按使用百分比返回 chunk 颜色（阈值用常量，审计 D13）
# 设计理由：样式集中管理；QProgressBar::chunk 动态颜色通过 setStyleSheet 单行覆盖
# 异常处理：无（纯常量与纯函数）
# 关联配置：主题名由 main_window 维护（S5 持久化）
