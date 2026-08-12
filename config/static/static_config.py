# 应用静态配置加载模块（S8.1 定案：config/static/ 命名，只读，json 驱动）

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from utils.file_utils import read_json

# 引导路径：static_config.py 所在目录（__file__ 自定位）
STATIC_DIR = Path(__file__).resolve().parent


@dataclass
class StaticConfig:
    # 应用静态配置聚合（base/ui 各为 dict，只读，供全项目引用）
    base: dict[str, Any]
    ui: dict[str, Any]


def _load_static_config() -> StaticConfig:
    # 私有加载：读引导映射表 → 遍历读取各分类 json → 聚合；缺失/损坏抛错暴露
    # use_cache=False：静态配置以本模块单例为唯一缓存层，避免 file_utils
    # 缓存导致"改了 json 不生效"（开发调参困惑）
    mapping = read_json(STATIC_DIR / "config.json", default={}, use_cache=False)
    result: dict[str, dict[str, Any]] = {}
    for key, rel_path in mapping.items():
        data = read_json(STATIC_DIR / rel_path, default=None, use_cache=False)
        if data is None:
            raise RuntimeError(f"静态配置文件缺失或损坏: {rel_path}")
        result[key] = data
    # L7：映射缺分类键与文件缺失同策略（不静默兜底，避免调用方后续 KeyError）
    for key in ("base", "ui"):
        if key not in result:
            raise RuntimeError(f"静态配置映射缺少分类: {key}")
    return StaticConfig(base=result["base"], ui=result["ui"])


_static_config_cache: StaticConfig | None = None


def get_static_config() -> StaticConfig:
    # 公开单例访问：缓存懒加载，首次调用后不再读文件
    global _static_config_cache
    if _static_config_cache is None:
        _static_config_cache = _load_static_config()
    return _static_config_cache


# ===== config/static/static_config.py 函数/常量说明 =====
# STATIC_DIR: 引导路径（唯一硬编码），static_config.py 所在目录，__file__ 自定位
# StaticConfig(dataclass): 静态配置聚合（base/ui 两个 dict 字段，只读）
# _load_static_config() -> StaticConfig: 私有加载
#   逻辑：读 config.json 映射表 → 遍历读取各分类 json → 聚合
#   异常：映射/文件缺失或损坏抛 RuntimeError（开发期快速暴露，不静默兜底，
#     对齐 AccelWorld static_config.py 的失败策略）
# get_static_config() -> StaticConfig: 公开单例访问（缓存懒加载，首次调用后
#   不再读文件；模块顶层 import 时调用一次，运行时零 IO）
#   设计理由：静态配置只读、json 驱动、代码零硬编码（S8 定案）；
#   与用户配置（config/settings.py）严格分离
#   关联配置：config/static/config.json 映射表、base.json 应用参数、
#     ui.json UI 参数（颜色/阈值）
