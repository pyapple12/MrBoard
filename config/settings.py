# 配置管理模块：用户配置 AppConfig dataclass + JSON 持久化（项目内 config/user_config.json，对齐 AccelWorld S9.5）

from dataclasses import dataclass
from typing import Any

from config.static.static_config import get_static_config
from utils.file_utils import get_project_root, read_json, write_json

# 静态配置解包（S8：参数外置 base.json，用户配置路径由 json 指定）
_SC = get_static_config()
CONFIG_FILE = get_project_root() / _SC.base["user_config_path"]
DEFAULT_REFRESH_INTERVAL_MS = int(_SC.base["refresh_interval_ms"])
# 6A.2 D3：刷新间隔最小下限（base.json 驱动，防手改 1ms 疯狂刷新）
MIN_REFRESH_INTERVAL_MS = int(_SC.base["min_refresh_interval_ms"])
# A2.2：default_theme 与 themes 数组一致性防护——base 默认值不在 themes 中时
# 回退 themes[0]（改 ui.json 主题名后默认主题仍生效，不静默失效）
_themes = tuple(str(item) for item in _SC.ui["themes"])
_base_default_theme = str(_SC.base["default_theme"])
DEFAULT_THEME = (
    _base_default_theme
    if _base_default_theme in _themes
    else (_themes[0] if _themes else _base_default_theme)
)
# 主题枚举单一来源（C6：外置 ui.json themes 数组；themes.py 从同一数组派生
# THEME_NAMES/LIGHT/DARK——两处同源，不互相引用，A3.2 注释修正）
THEMES = tuple(str(item) for item in _SC.ui["themes"])


@dataclass
class AppConfig:
    # 应用配置聚合：窗口几何 / 主题 / 刷新间隔 / 隐藏列（默认值从静态配置现取，零硬编码）

    window_geometry: str = ""  # QByteArray.toHex 的字符串（config 层不依赖 PyQt）
    theme: str = DEFAULT_THEME
    refresh_interval_ms: int = DEFAULT_REFRESH_INTERVAL_MS
    hidden_columns: tuple[str, ...] = ()  # 明细表格隐藏列 id（P13 列开关持久化）

    def to_dict(self) -> dict[str, Any]:
        # 转为可 JSON 序列化的 dict
        return {
            "window_geometry": self.window_geometry,
            "theme": self.theme,
            "refresh_interval_ms": self.refresh_interval_ms,
            "hidden_columns": list(self.hidden_columns),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AppConfig":
        # 从 dict 构建配置（宽容解析：缺字段/类型错误用默认值）
        config = cls()
        geometry = raw.get("window_geometry")
        if isinstance(geometry, str) and geometry:
            config.window_geometry = geometry
        theme = raw.get("theme")
        if theme in THEMES:
            config.theme = theme
        interval = raw.get("refresh_interval_ms")
        # type() is int 排除 bool（bool 是 int 子类，防 true → 1ms，S2）；
        # 6A.2 D3：低于下限的非法值丢弃（防手改 1ms 每秒千次刷新）
        if type(interval) is int and interval >= MIN_REFRESH_INTERVAL_MS:
            config.refresh_interval_ms = interval
        hidden = raw.get("hidden_columns")
        if isinstance(hidden, list):
            # C7：过滤空白项（strip 后非空才保留）
            config.hidden_columns = tuple(
                str(item).strip() for item in hidden if str(item).strip()
            )
        return config


def load_config() -> AppConfig:
    # 读取配置：文件不存在/损坏时返回默认配置（宽容降级，不崩溃）
    raw = read_json(CONFIG_FILE, default=None, use_cache=False)
    if not isinstance(raw, dict):
        return AppConfig()
    return AppConfig.from_dict(raw)


def save_config(config: AppConfig) -> None:
    # 保存配置：原子写 JSON 到项目内 config/user_config.json
    write_json(CONFIG_FILE, config.to_dict())


# ===== config/settings.py 模块说明 =====
# 模块级常量：
#   CONFIG_FILE：用户配置路径（项目内 config/user_config.json，
#     对齐 AccelWorld S9.5 定案；路径由 base.json user_config_path 指定，
#     get_project_root() 拼接）；凭据 opencode-go.json 在项目内
#     data/credentials/（P2 定案：所有数据目录集中项目内，不使用用户目录）
#   DEFAULT_REFRESH_INTERVAL_MS / MIN_REFRESH_INTERVAL_MS / DEFAULT_THEME：默认值与
#     刷新间隔下限从静态配置现取（零硬编码；下限防手改 1ms 疯狂刷新，6A.2 D3）
# 类型：
#   AppConfig：配置聚合 dataclass（window_geometry/theme/refresh_interval_ms/hidden_columns）
#     ——window_geometry 存 QByteArray.toHex 字符串，避免 config 层依赖 PyQt
#     （对齐 AccelWorld 修复 D3 的 base64 存储思路）；hidden_columns 为明细表格
#     隐藏列 id 元组（P13 列开关持久化，宽容解析非法项跳过）
# 函数：
#   load_config()：read_json（use_cache=False 强制读最新，用户手改配置可生效）
#     → 宽容解析（非 dict/坏数据返回默认 AppConfig）
#   save_config(config)：write_json 原子写（.tmp + os.replace）
# 设计理由：配置聚合用 dataclass（AGENTS.md 约定）；失败永不崩溃
#   （z.plan 第四章宽容解析）；GUI 层只依赖本模块读写，几何序列化细节隔离
# 异常处理：读写异常全部由 file_utils 宽容消化
# 关联配置：config/static/base.json（user_config_path/default_theme/refresh_interval_ms/
#   min_refresh_interval_ms）
#   + ui.json（themes 数组）
