# 应用服务门面（A017/PL006）：粗粒度方法聚合全部后端编排，UI 只认本包；
# 纯 Python 零 Qt——换前端（QML/Web）时本目录原样带走

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.static.static_config import get_static_config
from modules import browser_creds
from modules.exporter import export_all
from modules.go_quota import (
    DashboardCredentials,
    ERROR_STAGE_AUTH,
    ERROR_STAGE_NETWORK,
    ERROR_STAGE_NO_CREDS,
    ERROR_STAGE_PROVIDER,
    GoQuotaError,
    GoQuotaInfo,
    QUOTA_WINDOW_KEYS,
    fetch_dashboard_usage,
    fetch_go_quota,
    save_dashboard_credentials,
)
from modules.opencode_data import ModelDataSnapshot, refresh_data_page
from modules.opencode_usage import OpenCodeDB, UsageRow, UsageSummary, find_db_path
from utils.logger import get_logger

logger = get_logger(__name__)

_SC = get_static_config()

# 用量查询维度与分档上限（原 main_window/_UsageTask 编排依赖随迁；
# TABLE_LIMIT 与 opencode_usage 模块内同源 base.json）
DIMENSIONS = ("month", "day", "model", "provider", "agent", "session")
TABLE_LIMIT_GROUP = int(_SC.base["table_limit_group"])
TABLE_LIMIT_DAY = int(_SC.base["table_limit_day"])

# CDP 引导参数（原 main_window 常量随编排迁入；wait_cdp_ready 超时由调用方显式
# 传入以与迁移前行为完全一致）
CDP_FETCH_TIMEOUT = int(_SC.base["cdp_fetch_timeout"])
CDP_WAIT_TIMEOUT = int(_SC.base["cdp_wait_timeout"])
CDP_POLL_INTERVAL = int(_SC.base["cdp_poll_interval"])
CDP_LOGIN_WAIT_SECONDS = int(_SC.base["cdp_login_wait_seconds"])


class ServiceError(Exception):
    # 业务错误基类：message 中文提示，UI catch 后按各自模板格式化展示

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class UsageData:
    # 后台任务返回的完整用量数据（内存驻留，维度切换不再查库）；
    # 原 main_window.UsageData 随编排迁入（A017/PL006.1）

    summary: UsageSummary
    rows: dict[str, list[UsageRow]]


def _wait_for_login_cookie(deadline: float) -> tuple[str | None, str | None]:
    # 端到端轮询：CDP 拿 cookie + 登录后当前页面 URL 提取 workspaceID，实测 dashboard
    # 可解析才算登录完成（防占位 cookie 误判：打开登录页时页面会种匿名 auth cookie）
    # 返回 (cookie, 验证通过的 workspace_id)——多账户场景保存时须用验证通过的
    while time.time() < deadline:
        candidate, workspace_id = browser_creds.fetch_login_state_via_cdp(
            timeout=CDP_FETCH_TIMEOUT
        )
        if candidate and workspace_id:
            # O3.8：dashboard 验证是单轮最贵步骤（重试链最长约 50s），启动前
            # 复查 deadline，避免轮询条件通过后仍进入长验证拖高总等待
            if time.time() >= deadline:
                break
            try:
                usage = fetch_dashboard_usage(
                    DashboardCredentials(workspace_id, candidate, "cdp验证")
                )
                if usage:
                    logger.info("cookie 验证通过（dashboard 可解析）")
                    return candidate, workspace_id
            except GoQuotaError:
                # 占位 cookie/页面未跳转：dashboard 返回登录页或解析失败，继续轮询
                pass
        time.sleep(CDP_POLL_INTERVAL)
    return None, None


class AppService:
    # 应用服务门面：UI 层唯一后端入口（A017/PL006 三纪律——纯 Python 零 Qt、
    # DTO 透传 modules dataclass、方法粒度对齐 UI 用例）

    def resolve_db_path(self) -> Path | None:
        # 三级探测 opencode.db 路径（环境变量 → CLI → 默认路径）；探测不到返回 None
        return find_db_path()

    def get_usage(self, db_path: Path | None) -> UsageData:
        # 用量统计全量聚合：totals + 全部分组查询（原 _UsageTask.run 主体迁入）；
        # db_path 为 None 时抛 ServiceError（UI 转状态栏提示）
        if db_path is None:
            raise ServiceError(str(_SC.ui["status_messages"]["no_db_found"]))
        db: OpenCodeDB | None = None
        try:
            # O3.7：连接建立（OpenCodeDB 构造即 open_readonly）与查询统一纳入
            # sqlite3.Error 防护——坏库/锁库转业务错误统一中文口径（原裸异常串
            # 直通 UI 英文直显；复用 usage_failed_template 与 _on_load_error 同键）
            db = OpenCodeDB(db_path)
            summary = db.totals()
            rows = {
                dim: getattr(db, f"by_{dim}")(
                    limit=TABLE_LIMIT_DAY if dim == "day" else TABLE_LIMIT_GROUP,
                )
                for dim in DIMENSIONS
            }
        except sqlite3.Error as exc:
            raise ServiceError(
                str(_SC.ui["status_messages"]["usage_failed_template"]).format(
                    error=exc
                )
            ) from None
        finally:
            if db is not None:
                db.close()
        return UsageData(summary=summary, rows=rows)

    def export_data(self, db_path: Path | None, out_dir: Path) -> None:
        # 全量导出：独立只读连接 + exporter 落盘（原 _ExportTask.run 主体迁入）；
        # db_path 为 None 时抛 ServiceError
        if db_path is None:
            raise ServiceError(str(_SC.ui["status_messages"]["no_db_export"]))
        db: OpenCodeDB | None = None
        try:
            # O3.7：连接与导出统一转业务错误中文口径（复用 export_failed_template）
            db = OpenCodeDB(db_path)
            export_all(db, out_dir)
        except sqlite3.Error as exc:
            raise ServiceError(
                str(_SC.ui["status_messages"]["export_failed_template"]).format(
                    error=exc
                )
            ) from None
        finally:
            if db is not None:
                db.close()

    def get_quotas(self) -> list[GoQuotaInfo]:
        # 多账户配额快照（节流/缓存兜底/in-flight 去重在 go_quota 内部）
        return fetch_go_quota()

    def get_data_page(self) -> ModelDataSnapshot:
        # 数据页六区块快照（节流/缓存兜底在数据层内部）
        return refresh_data_page()

    def save_account(self, workspace_id: str, auth_cookie: str) -> None:
        # 手动填写凭据落盘（DPAPI 加密；异 workspace 追加/同 workspace 覆盖）
        save_dashboard_credentials(workspace_id, auth_cookie)

    def add_account_via_cdp(
        self, login_wait_seconds: int | None = None
    ) -> tuple[str, str]:
        # CDP 一键获取凭据全流程编排（原 _CdpGuideTask.run 主体迁入）：
        # 环境预检 → 启动调试 Chrome → 轮询登录（cookie+workspaceID 双验证）→
        # 写凭据 → 清理；返回 (auth_cookie, workspace_id)，失败抛 ServiceError
        proc = None
        wait_seconds = (
            CDP_LOGIN_WAIT_SECONDS if login_wait_seconds is None else login_wait_seconds
        )
        try:
            if browser_creds.is_chrome_running():
                logger.info("检测到用户 Chrome 正在运行（独立临时 profile 不冲突）")
            if not browser_creds.has_v20_cookies():
                raise ServiceError(str(_SC.ui["guide_messages"]["v10_detect"]))
            proc = browser_creds.launch_chrome_debug()
            if proc is None:
                raise ServiceError(str(_SC.ui["guide_messages"]["launch_failed"]))
            if not browser_creds.wait_cdp_ready(timeout=CDP_WAIT_TIMEOUT):
                raise ServiceError(str(_SC.ui["guide_messages"]["cdp_not_ready"]))
            auth_cookie, workspace_id = _wait_for_login_cookie(
                time.time() + wait_seconds
            )
            if not auth_cookie or not workspace_id:
                raise ServiceError(
                    str(
                        _SC.ui["guide_messages"]["login_timeout_template"].format(
                            minutes=wait_seconds // 60
                        )
                    )
                )
            save_dashboard_credentials(workspace_id, auth_cookie)
            return auth_cookie, workspace_id
        except ServiceError:
            raise
        except Exception as exc:
            raise ServiceError(
                str(_SC.ui["guide_messages"]["auto_fetch_failed"]).format(error=exc)
            ) from exc
        finally:
            if proc is not None:
                browser_creds.shutdown_chrome_debug(proc)


_service: AppService | None = None


def get_service() -> AppService:
    # 门面单例入口（消费方 from services import get_service）
    global _service
    if _service is None:
        _service = AppService()
    return _service


# ===== services/service.py 模块说明 =====
# 模块级常量：
#   DIMENSIONS / TABLE_LIMIT_GROUP / TABLE_LIMIT_DAY：用量查询维度与行数分档
#     （base.json 驱动；原 main_window 编排依赖随迁）
#   CDP_FETCH_TIMEOUT / CDP_POLL_INTERVAL / CDP_LOGIN_WAIT_SECONDS：CDP 引导参数
#   CDP_WAIT_TIMEOUT：CDP 就绪等待超时（base.json 驱动；wait_cdp_ready 调用处复用此
#     常量而非裸读 base.json，防死常量漂移，M3.6）
# 类型：
#   ServiceError：业务错误基类（message 中文，UI catch 后按模板格式化）
#   UsageData：用量聚合结果（summary + 各维度 rows；原 main_window.UsageData 迁入）
#   AppService：应用服务门面（UI 层唯一后端入口）
# 函数：
#   _wait_for_login_cookie(deadline)：CDP 登录轮询（cookie+workspaceID 双验证，
#     dashboard 可解析才算完成；防占位 cookie 误判）
#   resolve_db_path()：三级探测数据库路径（None 表示探测失败）
#   get_usage(db_path)：totals + 六维度分组聚合（原 _UsageTask.run 主体）
#   export_data(db_path, out_dir)：全量 CSV/JSON 导出（原 _ExportTask.run 主体）
#   get_quotas()：多账户配额快照（go_quota 直通）
#   get_data_page()：数据页六区块快照（opencode_data 直通）
#   save_account(ws, cookie)：手动凭据落盘（DPAPI 加密包装）
#   add_account_via_cdp(login_wait_seconds)：CDP 一键获取全流程编排
#     （原 _CdpGuideTask.run 主体；成功返回 (auth_cookie, workspace_id)）
#   get_service()：AppService 单例入口
# 设计理由：UI 只认本包不 import 任何 modules 符号（前端可整体替换）；
#   纯 Python 零 Qt（services/ 目录零 PyQt6 import 可 AST 机械断言）；
#   DTO 第一版直接透传 modules dataclass（独立 DTO 留待 QML 迁移再建）
# 异常处理：业务失败统一抛 ServiceError（中文消息由调用方模板化展示）；
#   CDP 流程的浏览器生命周期在 finally 清理
# 关联配置：base.json（cdp_*/table_limit_*）；ui.json（guide_messages 组文案经
#   _SC.ui 直读——错误消息属技术诊断口径，与 STATUS_MESSAGES 展示层分离）
