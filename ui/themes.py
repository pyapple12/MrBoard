# 主题样式模块：QSS 模板 + 注册制调色板（N 主题泛化，PL003），配额阈值/颜色外置 ui.json

import re

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
QWidget, QMainWindow, QLabel, QPushButton, QComboBox, QTableWidget, QProgressBar {
    font-family: {font_family};
}
"""

# 调色板（4A.2 D5：整体外置 ui.json palettes，S8.3 颜色外置补齐；
# PL003.1：注册制泛化——遍历 palettes 全键构建，N 主题天然支持）
_SC = get_static_config()
# H3.1：palettes 容器类型校验（手改容器为 str/list 时 dict() 抛裸 ValueError——
# 与 E3.9 值类型校验同式，契约风格 RuntimeError 统一诊断）
# I0.1：根容器类型前置校验（根为 str/list 时 .get 抛裸 AttributeError——
# H3.1 只护子容器，此处补全；C0.6 的 .keys() 连带受益）
if not isinstance(_SC.ui.get("palettes"), dict):
    raise RuntimeError(
        f"ui.json palettes 必须是对象，当前 {type(_SC.ui.get('palettes')).__name__}"
    )
for _palette_name in _SC.ui["palettes"]:
    if not isinstance(_SC.ui["palettes"].get(_palette_name), dict):
        raise RuntimeError(
            f"ui.json palettes.{_palette_name} 必须是对象，"
            f"当前 {type(_SC.ui['palettes'].get(_palette_name)).__name__}"
        )
_PALETTES: dict[str, dict[str, str]] = {}
for _palette_name, _palette_data in _SC.ui["palettes"].items():
    # 值保留原始类型（E3.9 值类型校验在 _build_theme 内执行，此处不转换防吞错）
    _PALETTES[str(_palette_name)] = {
        str(key): value for key, value in _palette_data.items()
    }

# 配额窗口内动态色键集（PL003.1.d：不随 QSS 占位符走——运行时 setStyleSheet 覆盖，
# 残留检测兜不住，需显式契约：每主题 palette 必含全部动态色键）
_QUOTA_DYNAMIC_KEYS = (
    "chunk_ok",
    "chunk_warn",
    "chunk_danger",
    "quota_gray",
    "pie_bg",
    "pie_text",
)

# 配额颜色与阈值（S8.3：外置 ui.json，静态配置解包）
QUOTA_WARN_PERCENT = int(_SC.ui["quota_warn_percent"])
QUOTA_DANGER_PERCENT = int(_SC.ui["quota_danger_percent"])
# 托盘专用正常色（PL003.1.e：与窗口主题无关，留 ui.json colors 节）
QUOTA_COLOR_OK = str(_SC.ui["colors"]["quota_ok"])


def _build_theme(palette: dict[str, str]) -> str:
    # 按调色板构建 QSS（str.replace 注入占位符，避开 QSS 自身花括号；
    # A3.5：构建后检测残留 {占位符}——palette 缺键会静默残留无效值
    # （6A.1 chunk_ok 事故根因），发现即抛错防再犯）
    result = _QSS_TEMPLATE
    for key, value in palette.items():
        if not isinstance(value, str):
            # E3.9：palette 值非字符串（手改配置）→ 契约风格 RuntimeError，
            # 而非 TypeError（与 A3.5/B0.6 导入期校验同机制）
            raise RuntimeError(
                f"调色板 {key} 值必须是字符串，当前 {type(value).__name__}"
            )
        result = result.replace("{" + key + "}", value)
    missing = re.findall(r"\{[a-zA-Z_]+\}", result)
    if missing:
        raise RuntimeError(f"调色板缺少占位符对应键：{sorted(set(missing))}")
    return result


# 主题名常量（6A.3 R3：从 ui.json themes 数组派生，与 settings.THEMES 同源）
THEME_NAMES = tuple(str(item) for item in _SC.ui["themes"])
# A3.5：主题名长度契约校验（数组被手改短会致索引越界，导入期即抛错）
if len(THEME_NAMES) < 2:
    raise RuntimeError(
        f"ui.json themes 数组至少需要 light/dark 两项，当前 {THEME_NAMES}"
    )
# C0.6：主题名-调色板顺序契约（E0.1 补全：键序必须与 palettes 完全一致——
# 仅"⊆+互异"不防 ["dark","light"] 改序，名称与视觉效果错位）
_palette_keys = tuple(_PALETTES.keys())
if (
    any(name not in _palette_keys for name in THEME_NAMES)
    or len(set(THEME_NAMES)) != len(THEME_NAMES)
    or tuple(THEME_NAMES) != _palette_keys
):
    raise RuntimeError(
        f"ui.json themes 数组与 palettes 键不一致：{THEME_NAMES} vs {list(_palette_keys)}"
    )
# PL003.1.d：配额动态色键必含契约——逐主题校验（残留检测兜不住运行时覆盖色）
for _name in THEME_NAMES:
    _missing = [key for key in _QUOTA_DYNAMIC_KEYS if key not in _PALETTES[_name]]
    if _missing:
        raise RuntimeError(f"主题 {_name} 缺少配额动态色键：{_missing}")
DEFAULT_THEME_NAME = THEME_NAMES[0]

# PL003.1.a：注册制构建——遍历全部调色板生成 _THEME_QSS
_THEME_QSS: dict[str, str] = {
    name: _build_theme(palette) for name, palette in _PALETTES.items()
}


def get_theme(name: str) -> str:
    # 按主题名返回 QSS 样式字符串（字典查找；未知名回退默认主题，PL003.1.c）
    return _THEME_QSS.get(name, _THEME_QSS[DEFAULT_THEME_NAME])


def quota_chunk_color(percent: int, theme_name: str | None = None) -> str:
    # 按配额使用百分比返回进度条颜色：>=QUOTA_DANGER_PERCENT 红、
    # >=QUOTA_WARN_PERCENT 黄、其余绿（阈值来自 ui.json；色值随主题 palette，
    # PL003.1.d；theme_name 缺省回退默认主题——托盘图标无主题语义）
    palette = _PALETTES.get(theme_name or "", _PALETTES[DEFAULT_THEME_NAME])
    if percent >= QUOTA_DANGER_PERCENT:
        return palette["chunk_danger"]
    if percent >= QUOTA_WARN_PERCENT:
        return palette["chunk_warn"]
    return palette["chunk_ok"]


# ===== ui/themes.py 模块说明 =====
# 模块级常量：
#   _QSS_TEMPLATE：QSS 模板（{占位符} 由调色板注入；QSS 自身花括号不受影响；
#     PL003.3 新增 {font_family} 占位符）
#   _PALETTES：注册制调色板全集（遍历 ui.json palettes 全键构建，N 主题泛化 PL003.1）
#   _QUOTA_DYNAMIC_KEYS：配额窗口内动态色键集（chunk 三档/quota_gray/pie_bg/pie_text，
#     每主题必含契约校验——运行时 setStyleSheet 覆盖不走 QSS 占位符，残留检测兜不住）
#   QUOTA_WARN_PERCENT / QUOTA_DANGER_PERCENT：配额阈值（ui.json 驱动）
#   QUOTA_COLOR_OK：托盘专用正常色（PL003.1.e：与窗口主题无关，留 ui.json colors）
#   THEME_NAMES / DEFAULT_THEME_NAME：主题名常量（ui.json themes 数组派生）
#   _THEME_QSS：注册制构建的 QSS 全集（dict[theme_name, qss]）
# 函数：
#   _build_theme(palette)：str.replace 注入占位符（残留占位符/非字符串值抛契约错）
#   get_theme(name)：字典查找 + 未知名回退默认主题（PL003.1.c 消除"第三主题错位"）
#   quota_chunk_color(percent, theme_name=None)：三档色随主题 palette（阈值常量，
#     theme_name 缺省回退默认——托盘图标无主题语义）
# 设计理由：样式集中管理；QProgressBar::chunk 动态颜色通过 setStyleSheet 单行覆盖
# 异常处理：_build_theme 残留占位符/值类型、themes 数组长度、palettes 键序
#   （themes 数组与 palettes 键序完全一致，E0.1 收紧防 light/dark 错位）、
#   动态色键缺失——导入期抛 RuntimeError（配置契约校验，A3.5/B0.6/C0.6 同机制）
# 关联配置：主题名由 main_window 维护（S5 持久化，PL003.2 下拉切换即存）
