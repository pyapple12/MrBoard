# SQLite 只读连接工具：URI 转义 + row_factory 统一（6A.3 R1：opencode_usage/browser_creds 两处收敛）

import sqlite3
import urllib.parse
from pathlib import Path


def open_readonly(db_path: Path) -> sqlite3.Connection:
    # 打开 SQLite 只读连接（mode=ro 防误写；URI 路径转义防 #/? 解析错误；
    # row_factory 统一为 sqlite3.Row，查询可用列名取值）
    uri_path = urllib.parse.quote(str(db_path).replace("\\", "/"))
    conn = sqlite3.connect(f"file:{uri_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ===== utils/sqlite_utils.py 模块说明 =====
# 函数：
#   open_readonly(db_path)：
#     输入：数据库文件路径（Path）
#     输出：只读 sqlite3.Connection（row_factory=sqlite3.Row）
#     逻辑步骤：URI 路径转义（Windows 反斜杠转正斜杠 + quote 防 #/?）→
#       sqlite3.connect(file:...?mode=ro) → 设 row_factory
#     设计理由：opencode_usage.OpenCodeDB 与 browser_creds._with_copied_db 原两处
#       独立实现（4A.1 E7 各做一次转义），收敛为单点避免转义规则/row_factory 变更
#       时漏改其一（6A.3 R1）
# 异常处理：连接失败原样抛 sqlite3.Error，由调用方降级（宽容策略在业务层）
# 关联配置：无（通用工具）
