# pathlib 封装的 JSON 读写与缓存单例模块

import json
import os
import tempfile
from pathlib import Path
from typing import Any

# 项目根目录（utils/ 的父目录），get_project_root 校验用
_PROJECT_ROOT = Path(__file__).resolve().parents[1]

_json_cache: dict[Path, Any] = {}


def get_project_root() -> Path:
    # 获取项目根目录并校验 main.py 存在（防止目录层级偏移）
    if not (_PROJECT_ROOT / "main.py").is_file():
        raise RuntimeError(f"项目根目录检测失败：{_PROJECT_ROOT} 下缺少 main.py")
    return _PROJECT_ROOT


def read_json(path: Path | str, default: Any = None, use_cache: bool = True) -> Any:
    # 读取 JSON 文件（默认带内存缓存；use_cache=False 强制读最新文件），文件不存在或解析失败时返回 default
    # （E4：解析失败不写缓存，防坏 JSON 毒化——文件修复后默认调用即可读到新值；
    #   5A.3 C8：文件不存在同样不写缓存——文件创建后默认调用即可读到新值）
    path = Path(path)
    if use_cache and path in _json_cache:
        return _json_cache[path]
    if not path.is_file():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return default
    if use_cache:
        _json_cache[path] = data
    return data


def write_json(path: Path, data: Any) -> None:
    # 写入 JSON 文件（原子写：临时文件 + os.replace），并更新缓存
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=2)
    tmp_path: Path | None = None
    fd: int | None = None
    try:
        # D0.12（大会战 A2）：mkstemp 移入 try（fd 打开失败时 tmp_path 未定义，
        # 异常路径不会因 unlink 未绑定变量再抛）
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        # H0.3：fdopen 失败（内存不足等极端）时关闭 fd 防泄漏——fd 打开成功后
        # 才可能 fdopen 失败，close 包 OSError 吞掉（已关闭/无效 fd 场景）
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            raise
        os.replace(tmp_path, str(path))
    except Exception:
        # E5：unlink 自身可能抛 OSError（已被删/权限），包裹吞掉避免覆盖原异常
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise
    _json_cache[path] = data


# ===== utils/file_utils.py 模块说明 =====
# 模块级变量：
#   _PROJECT_ROOT：项目根目录（utils/ 的父目录，get_project_root 校验用）
#   _json_cache：缓存单例 dict[Path, Any]，避免高频读配置重复 IO
#     （对齐 AccelWorld 修复 D4"每次调用全量读文件"的思路）
# 函数：
#   read_json(path, default=None, use_cache=True)：
#     输入：path 文件路径（Path 或 str 均可），default 兜底值，
#       use_cache=False 时绕过缓存强制读最新文件（用户可手改的文件适用）
#     输出：解析后的数据；文件不存在/损坏/编码异常时返回 default
#     逻辑步骤：use_cache 且缓存命中直接返回 → 文件不存在返回 default
#       （use_cache 时写入缓存）→ 读取文本 → json.loads 解析，任一异常回退 default
#     设计理由：宽容解析（z.plan.md 第四章错误策略）：配置/数据文件损坏不崩溃，
#       由调用方决定处理方式；use_cache=False 解决"文件刚创建/被外部修改后
#       旧缓存遮蔽新内容"的问题（TTL 类缓存文件必须用它，否则缓存永不过期）
#   write_json(path, data)：
#     输入：path 目标路径，data 任意可 JSON 序列化对象
#     输出：无
#     逻辑步骤：确保父目录存在 → json.dumps（ensure_ascii=False 保中文，indent=2
#       便于人工查看）→ tempfile.mkstemp 写临时文件 → os.replace 原子替换 →
#       更新缓存
#     设计理由：原子写避免写一半崩溃产生损坏文件（参考 opencode-usage insights
#       缓存的 .tmp → os.rename 模式）
#     _json_cache 缓存机制说明（C1 评估）：业务调用点均显式 use_cache=False
#       （TTL 类文件必须绕过缓存），缓存保留供高频重复读同路径的调用方选用
#       （verify_s1 覆盖缓存命中行为），属通用 utils 能力非死代码
# 异常处理：write_json 失败时清理临时文件并重新抛出（调用方决定如何提示）；
#   read_json 内部消化所有解析异常
# 关联配置：无（通用工具，config/settings.py 复用）
