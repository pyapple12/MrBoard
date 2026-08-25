# 主题资源加载器（PL007）：ui/themes/ 为零 .py 的纯声明式资源文件夹，
# 本模块是唯一代码入口——扫描注册表逐主题加载 theme.json + base.qss 构建 QSS 全集；
# 契约校验链全套保留（A3.5/C0.6/E3.9/动态色必含，文件源适配）；新增主题 =
# 新建文件夹 + theme.json，不改任何一行 .py

import json
import re
from pathlib import Path

from config.static.static_config import get_static_config
from utils.logger import get_logger

logger = get_logger(__name__)

# ===== 主题资源根目录（本模块同级的 themes/ 文件夹） =====
_THEMES_DIR = Path(__file__).parent / "themes"

# ===== 共享 QSS 结构模板（{占位符} 由调色板替换；QSS 自身的 {} 保持不变） =====
_QSS_PATH = _THEMES_DIR / "_templates" / "base.qss"
if not _QSS_PATH.is_file():
    # M0.6：导入期 IO 失败形态对齐 _load_theme 契约风格（RuntimeError 中文诊断，
    # 而非裸 FileNotFoundError/UnicodeDecodeError——打包场景下更易定位）
    raise RuntimeError(f"基础 QSS 模板缺失：{_QSS_PATH}")
try:
    _QSS_TEMPLATE = _QSS_PATH.read_text(encoding="utf-8")
except (OSError, UnicodeDecodeError, ValueError) as exc:
    # O3.5：读取/编码失败与缺失同策略转 RuntimeError 中文诊断（含路径）
    raise RuntimeError(f"基础 QSS 模板读取失败：{_QSS_PATH}（{exc}）") from None

_SC = get_static_config()

# 主题名常量（6A.3 R3：ui.json themes 数组派生，与 settings.THEMES 同源；
# 数组是注册顺序唯一权威——文件夹多出的未注册主题不加载仅警告）
THEME_NAMES = tuple(str(item) for item in _SC.ui["themes"])
# A3.5：主题名长度契约校验（数组被手改短会致索引越界，导入期即抛错）
if len(THEME_NAMES) < 2:
    raise RuntimeError(
        f"ui.json themes 数组至少需要 light/dark 两项，当前 {THEME_NAMES}"
    )

# O3.4：主题资源根目录整体缺失检查上移到注册循环之前（M0.6 设计意图——
# 打包/部署异常时显式中文诊断先于 _load_theme 的单主题缺失提示；原位置在
# 循环后属不可达死分支：能到达循环后则目录必然存在）
if not _THEMES_DIR.is_dir():
    raise RuntimeError(f"主题资源目录缺失：{_THEMES_DIR}")

# 配额窗口内动态色键集（PL003.1.d：运行时 setStyleSheet 覆盖不走 QSS 占位符，
# 残留检测兜不住，需显式契约：每主题 palette 必含全部动态色键）
_QUOTA_DYNAMIC_KEYS = (
    "chunk_ok",
    "chunk_warn",
    "chunk_danger",
    "quota_gray",
    "pie_bg",
    "pie_text",
)

# 配额阈值与托盘专用色（S8.3 外置 ui.json，静态配置解包）
QUOTA_WARN_PERCENT = int(_SC.ui["quota_warn_percent"])
QUOTA_DANGER_PERCENT = int(_SC.ui["quota_danger_percent"])
QUOTA_COLOR_OK = str(_SC.ui["colors"]["quota_ok"])


def _load_theme(name: str) -> dict:
    # 加载单主题 theme.json 并做结构契约校验（H3.1/I0.1 文件源适配）：
    # 缺文件/坏 JSON/根非对象/缺 display_name 或 palette 键/palette 非对象
    # 均抛 RuntimeError 中文提示（契约风格统一诊断，A3.5/B0.6 同机制）
    tj_path = _THEMES_DIR / name / "theme.json"
    if not tj_path.is_file():
        raise RuntimeError(f"主题 {name} 资源缺失：{tj_path}")
    try:
        data = json.loads(tj_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        # O3.5：编码失败与坏 JSON 同策略转中文诊断（含路径，M0.6/A3.5 口径）
        raise RuntimeError(
            f"主题 {name} 的 theme.json 编码非法（须为 UTF-8）：{tj_path}（{exc}）"
        ) from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"主题 {name} 的 theme.json 解析失败：{exc}") from None
    if not isinstance(data, dict):
        raise RuntimeError(
            f"主题 {name} 的 theme.json 必须是对象，当前 {type(data).__name__}"
        )
    for key in ("display_name", "palette"):
        if key not in data:
            raise RuntimeError(f"主题 {name} 的 theme.json 缺少必需键：{key}")
    if not isinstance(data["palette"], dict):
        raise RuntimeError(
            f"主题 {name} 的 palette 必须是对象，当前 {type(data['palette']).__name__}"
        )
    return data


def _build_theme(name: str, palette: dict[str, str]) -> str:
    # 按调色板构建 QSS（str.replace 注入占位符，避开 QSS 自身花括号；
    # A3.5：构建后检测残留 {占位符}——palette 缺键会静默残留无效值
    # （6A.1 chunk_ok 事故根因），发现即抛错防再犯）
    result = _QSS_TEMPLATE
    for key, value in palette.items():
        if not isinstance(value, str):
            # E3.9：palette 值非字符串（手改配置）→ 契约风格 RuntimeError；
            # M0.7：消息注入主题名，便于定位四主题中哪个 palette 被改坏
            raise RuntimeError(
                f"主题 {name} 调色板 {key} 值必须是字符串，当前 {type(value).__name__}"
            )
        result = result.replace("{" + key + "}", value)
    missing = re.findall(r"\{[a-zA-Z_]+\}", result)
    if missing:
        raise RuntimeError(f"调色板缺少占位符对应键：{sorted(set(missing))}")
    return result


# 注册制加载：按注册表顺序逐主题读取 → 动态色必含校验 → 收集调色板与显示名
_PALETTES: dict[str, dict[str, str]] = {}
THEME_DISPLAY_NAMES: dict[str, str] = {}
for _name in THEME_NAMES:
    _data = _load_theme(_name)
    _missing = [key for key in _QUOTA_DYNAMIC_KEYS if key not in _data["palette"]]
    if _missing:
        # PL003.1.d：配额动态色键必含契约（残留检测兜不住运行时覆盖色）
        raise RuntimeError(f"主题 {_name} 缺少配额动态色键：{_missing}")
    _PALETTES[_name] = {str(key): value for key, value in _data["palette"].items()}
    THEME_DISPLAY_NAMES[_name] = str(_data["display_name"])

# 文件夹多出未注册的主题目录：视为无效不加载，仅警告（注册表唯一权威；
# 根目录缺失检查已由 O3.4 上移至注册循环之前）
for _child in sorted(_THEMES_DIR.iterdir()):
    if (
        _child.is_dir()
        and (_child / "theme.json").is_file()
        and _child.name not in THEME_NAMES
    ):
        logger.warning(
            f"未注册主题文件夹已忽略：{_child.name}（不在 ui.json themes 数组）"
        )

# C0.6：注册表↔实际加载键序完全一致（E0.1 收紧语义保留——遍历即构建天然一致，
# 显式断言防未来改为 set 遍历或数组含重复名时静默错位）
if tuple(_PALETTES.keys()) != THEME_NAMES:
    raise RuntimeError(
        f"ui.json themes 数组与实际加载主题不一致：{THEME_NAMES} vs {list(_PALETTES)}"
    )

DEFAULT_THEME_NAME = THEME_NAMES[0]

# PL003.1.a：注册制构建 QSS 全集
_THEME_QSS: dict[str, str] = {
    name: _build_theme(name, palette) for name, palette in _PALETTES.items()
}


def get_theme(name: str) -> str:
    # 按主题名返回 QSS 样式字符串（字典查找；未知名回退默认主题，PL003.1.c）
    return _THEME_QSS.get(name, _THEME_QSS[DEFAULT_THEME_NAME])


def get_palette(name: str) -> dict[str, str]:
    # 按主题名返回调色板副本（quota 动态色/饼图色取色源；
    # 未知名回退默认主题，与 get_theme 回退语义一致）
    palette = _PALETTES.get(name, _PALETTES[DEFAULT_THEME_NAME])
    return dict(palette)


def quota_chunk_color(percent: int, theme_name: str | None = None) -> str:
    # 按配额使用百分比返回进度条颜色：>=QUOTA_DANGER_PERCENT 红、
    # >=QUOTA_WARN_PERCENT 黄、其余绿（阈值来自 ui.json；色值随主题 palette；
    # theme_name 缺省回退默认主题——托盘图标无主题语义）
    palette = _PALETTES.get(theme_name or "", _PALETTES[DEFAULT_THEME_NAME])
    if percent >= QUOTA_DANGER_PERCENT:
        return palette["chunk_danger"]
    if percent >= QUOTA_WARN_PERCENT:
        return palette["chunk_warn"]
    return palette["chunk_ok"]


# ===== ui/theme_loader.py 模块说明 =====
# 模块级常量：
#   _THEMES_DIR：主题资源根目录（Path(__file__).parent / "themes" 自定位）
#   _QSS_TEMPLATE：共享 QSS 结构模板（_templates/base.qss 文件加载，非 Python 常量）
#   _SC：静态配置解包（themes 注册表/quota_* 阈值/colors 节）
#   _PALETTES：注册制调色板全集（各主题 theme.json palette，N 主题泛化 PL003.1）
#   THEME_DISPLAY_NAMES：主题显示名映射（theme.json display_name，承接原 ui.json
#     THEME_DISPLAY_NAMES；公开导出供 main_window 引用）
#   _QUOTA_DYNAMIC_KEYS：配额窗口内动态色键集（chunk 三档/quota_gray/pie_bg/pie_text，
#     每主题必含契约校验——运行时 setStyleSheet 覆盖不走 QSS 占位符，残留检测兜不住）
#   QUOTA_WARN_PERCENT / QUOTA_DANGER_PERCENT：配额阈值（ui.json 驱动）
#   QUOTA_COLOR_OK：托盘专用正常色（PL003.1.e：与窗口主题无关，留 ui.json colors）
#   THEME_NAMES / DEFAULT_THEME_NAME：主题名常量（ui.json themes 数组派生）
#   _THEME_QSS：注册制构建的 QSS 全集（dict[theme_name, qss]）
# 函数：
#   _load_theme(name)：读 theme.json + 结构契约校验（缺文件/坏 JSON/根非对象/
#     缺 display_name 或 palette/palette 非对象均抛 RuntimeError 中文提示）
#   _build_theme(name, palette)：str.replace 注入占位符（残留占位符/非字符串值抛契约错，消息含主题名）
#   get_theme(name)：字典查找 + 未知名回退默认主题（PL003.1.c 消除"第三主题错位"）
#   get_palette(name)：调色板副本 + 未知名回退默认（quota/饼图取色源，PL007 新增）
#   quota_chunk_color(percent, theme_name=None)：三档色随主题 palette（阈值常量，
#     theme_name 缺省回退默认——托盘图标无主题语义）
# 设计理由：theme = 纯声明式资源（theme.json 不含 Python），新增主题 = 新建文件夹 +
#   一个 theme.json 重启即在 settings.THEMES 白名单外被拒（白名单仍由 ui.json 数组
#   权威控制）；样式结构集中在 base.qss 一处四主题同步生效
# 异常处理：全部导入期抛 RuntimeError（契约风格统一诊断，A3.5/B0.6/C0.6 同机制）；
#   未注册主题目录仅 logger.warning 不中断
# 关联配置：ui.json themes 数组（注册顺序唯一权威）+ quota_* 阈值 + colors 节；
#   各主题 theme.json（display_name/palette 含 font_family 与动态色六键）；
#   ui/themes/_templates/base.qss（共享样式模板）
