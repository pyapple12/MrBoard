# 统一日志配置模块

import logging
import logging.handlers  # RotatingFileHandler 子模块（logging.handlers 不随 logging 自动加载）
import sys
import threading

from config.static.static_config import get_static_config
from utils.file_utils import get_project_root

# 静态配置解包（P2：日志目录外置 base.json logs_dir，集中项目内，不使用用户目录；
# L16：应用名/日志级别同样由 base.json 驱动）
_SC = get_static_config()
APP_NAME = str(_SC.base["app_name"])
VERSION = str(_SC.base["version"])  # 6A.3 R4：版本号单点导出（main/main_window 共引）
LOG_LEVEL = str(_SC.base["log_level"])
LOG_MAX_BYTES = int(_SC.base["log_max_bytes"])  # 6A.3 O5：单文件上限（轮转阈值）
LOG_BACKUP_COUNT = int(_SC.base["log_backup_count"])  # 6A.3 O5：轮转保留份数
# A1.1：标题中段单一来源（ui.json app_subtitle，主窗口/托盘共引）
APP_SUBTITLE = str(_SC.ui["app_subtitle"])


def build_app_title() -> str:
    # 应用标题单点（主窗口标题与托盘 tooltip 共用，A1.1 消除跨文件重复拼接）
    return f"{APP_NAME} {APP_SUBTITLE} {VERSION}"


LOG_DIR = get_project_root() / _SC.base["logs_dir"]
LOG_FILE = LOG_DIR / f"{APP_NAME}.log"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False
# 6A.2 D4：初始化锁（UI 线程与线程池并发首次调用 get_logger 时防双挂 handler）
_config_lock = threading.Lock()


def get_logger(name: str) -> logging.Logger:
    # 获取统一配置的日志器：首次调用时初始化控制台+文件双 handler（幂等，
    # 双检查锁防并发竞态 6A.2 D4）
    global _configured
    if not _configured:
        with _config_lock:
            if not _configured:
                _setup_handlers()
                _configured = True
    return logging.getLogger(name)


def _setup_handlers() -> None:
    # 初始化根日志器：控制台 handler + UTF-8 文件 handler（文件失败时降级仅控制台）
    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root.addHandler(console_handler)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        # 6A.3 O5：RotatingFileHandler 防常驻应用日志无限增长（参数 base.json 驱动）
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        root.addHandler(file_handler)
    except OSError:
        # 文件日志不可用（权限/磁盘满）时仅保留控制台输出，不阻断应用启动
        pass


# ===== utils/logger.py 模块说明 =====
# 模块级常量：
#   LOG_DIR / LOG_FILE：日志文件路径（项目内 data/logs/myboard.log，由 base.json
#     logs_dir 字段 + get_project_root() 拼接，P2 决策：所有数据目录集中项目内，
#     不使用用户目录；utils 层允许依赖 config.static 读取配置，AGENTS.md 已放宽）
#   APP_NAME / LOG_LEVEL：应用名与日志级别（base.json 驱动，C14 补列）
#   VERSION：版本号单点导出（base.json version 字段，main/main_window 共引，6A.3 R4）
#   LOG_MAX_BYTES / LOG_BACKUP_COUNT：日志轮转参数（base.json 驱动，6A.3 O5）
#   APP_SUBTITLE：标题中段（ui.json app_subtitle，A1.1）
#   LOG_FORMAT / DATE_FORMAT：统一日志格式（时间 | 级别 | 模块名 | 消息）
#   _configured：模块级状态标记，保证 handler 只初始化一次（幂等）
#   _config_lock：初始化互斥锁（6A.2 D4：双检查锁防并发竞态）
# 函数：
#   build_app_title()：应用标题单点（APP_NAME + APP_SUBTITLE + VERSION，
#     主窗口标题与托盘 tooltip 共引，A1.1 消除跨文件重复拼接）
#   get_logger(name)：
#     输入：模块名（通常传 __name__）
#     输出：配置好的 logging.Logger 实例
#     逻辑步骤：首次调用触发 _setup_handlers()，返回 logging.getLogger(name)
#     设计理由：业务模块只需 get_logger(__name__) 即可获得统一格式的双通道日志，
#       修复"logger 无 handler 导致日志静默丢失"的经典问题（对齐 AccelWorld D12）
#     _setup_handlers()：
#     逻辑步骤：root logger 挂控制台 handler（stderr）+ 文件 handler（utf-8 编码，
#       中文不乱码），日志目录不存在则自动创建；文件路径不可用时降级仅控制台
#     设计理由：文件日志落盘便于排查常驻应用问题；控制台便于 CLI/开发调试
# 异常处理：文件 handler 创建失败（目录无权限/磁盘满）捕获 OSError 后仅保留
#   控制台输出，绝不阻断应用启动（z.plan 第四章"不崩溃"策略）
# 关联配置：config/static/base.json（logs_dir/app_name/log_level/log_max_bytes/log_backup_count）
#   + ui.json（app_subtitle）
