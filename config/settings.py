# 配置管理模块：AppConfig dataclass + JSON 持久化（~/.config/myboard/config.json）

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from utils.file_utils import read_json, write_json

CONFIG_DIR = Path.home() / ".config" / "myboard"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_REFRESH_INTERVAL_MS = 5 * 60 * 1000  # 默认刷新间隔：5 分钟


@dataclass
class AppConfig:
    # 应用配置聚合：窗口几何 / 主题 / 刷新间隔（缺省值与默认一致）

    window_geometry: str = ""  # QByteArray.toHex 的字符串（config 层不依赖 PyQt）
    theme: str = "light"
    refresh_interval_ms: int = DEFAULT_REFRESH_INTERVAL_MS

    def to_dict(self) -> dict[str, Any]:
        # 转为可 JSON 序列化的 dict
        return {
            "window_geometry": self.window_geometry,
            "theme": self.theme,
            "refresh_interval_ms": self.refresh_interval_ms,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AppConfig":
        # 从 dict 构建配置（宽容解析：缺字段/类型错误用默认值）
        config = cls()
        geometry = raw.get("window_geometry")
        if isinstance(geometry, str) and geometry:
            config.window_geometry = geometry
        theme = raw.get("theme")
        if theme in ("light", "dark"):
            config.theme = theme
        interval = raw.get("refresh_interval_ms")
        if isinstance(interval, int) and interval > 0:
            config.refresh_interval_ms = interval
        return config


def load_config() -> AppConfig:
    # 读取配置：文件不存在/损坏时返回默认配置（宽容降级，不崩溃）
    raw = read_json(CONFIG_FILE, default=None, use_cache=False)
    if not isinstance(raw, dict):
        return AppConfig()
    return AppConfig.from_dict(raw)


def save_config(config: AppConfig) -> None:
    # 保存配置：原子写 JSON 到 ~/.config/myboard/config.json
    write_json(CONFIG_FILE, config.to_dict())


# ===== config/settings.py 模块说明 =====
# 模块级常量：
#   CONFIG_DIR / CONFIG_FILE：配置路径（~/.config/myboard/config.json，与凭据
#     opencode-go.json 同目录，均为用户级私有文件）
#   DEFAULT_REFRESH_INTERVAL_MS：默认刷新间隔 5 分钟
# 类型：
#   AppConfig：配置聚合 dataclass（window_geometry/theme/refresh_interval_ms）
#     ——window_geometry 存 QByteArray.toHex 字符串，避免 config 层依赖 PyQt
#     （对齐 AccelWorld 修复 D3 的 base64 存储思路）
# 函数：
#   load_config()：read_json（use_cache=False 强制读最新，用户手改配置可生效）
#     → 宽容解析（非 dict/坏数据返回默认 AppConfig）
#   save_config(config)：write_json 原子写（.tmp + os.replace）
# 设计理由：配置聚合用 dataclass（AGENTS.md 约定）；失败永不崩溃
#   （z.plan 第四章宽容解析）；GUI 层只依赖本模块读写，几何序列化细节隔离
# 异常处理：读写异常全部由 file_utils 宽容消化
# 关联配置：文件可被用户手改（字段名与 from_dict 兼容）
