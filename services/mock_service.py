# 虚拟数据服务（PL008.4.a）：与 AppService 同签名的可插拔数据源
# 供 QML 前端演示版使用——不触库/不触网，返回构造的 DTO 样例；
# 三态样例（正常/错误占位/缓存标注）供 UI 各分支调试

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.service import ServiceError, UsageData
from modules.go_quota import ERROR_STAGE_NETWORK, GoQuotaInfo, GoQuotaWindow
from modules.opencode_data import ModelDataSnapshot
from modules.opencode_usage import TokenStats, UsageRow, UsageSummary
from utils.logger import get_logger

logger = get_logger(__name__)

# 三态场景常量（MockService 构造时选择，UI 调试各分支用）
SCENE_NORMAL = "normal"
SCENE_ERROR = "error"
SCENE_CACHED = "cached"

# 展示用维度键（对齐 services.service.DIMENSIONS 的查询顺序；mock 固定供应）
_DIMENSION_NAMES = ("month", "day", "model", "provider", "agent", "session")

# Releases 样例条数（对齐 opencode_data._RELEASE_LIMIT 的展示范围）
_RELEASE_COUNT = 3


def _make_usage_row(label: str, calls: int, total_tokens: int, cost: float) -> UsageRow:
    # 构造一条分组聚合样例（tokens 按总量拆分到输入/输出，其余缓存字段置 0）
    return UsageRow(
        label=label,
        calls=calls,
        tokens=TokenStats(
            input=total_tokens // 2,
            output=total_tokens // 2,
            total=total_tokens,
        ),
        cost=cost,
    )


def _make_quota_window(percent: float, days_until_reset: int) -> GoQuotaWindow:
    # 构造单个配额窗口样例（重置时间 = 当前时间 + 天数偏移）
    return GoQuotaWindow(
        usage_percent=percent,
        reset_in_sec=days_until_reset * 86400,
        reset_date=datetime.now(timezone.utc) + timedelta(days=days_until_reset),
    )


def _make_quotas(scene: str) -> list[GoQuotaInfo]:
    # 构造配额样例列表：normal 两账户三窗口；error 占位（error_stage=NETWORK）；
    # cached 保留数据 + is_cached 标注
    if scene == SCENE_ERROR:
        return [
            GoQuotaInfo(
                error="模拟：配额接口网络请求失败",
                error_stage=ERROR_STAGE_NETWORK,
                workspace_id="mock-workspace-err",
                fetched_at=datetime.now(timezone.utc),
            )
        ]
    base = [
        GoQuotaInfo(
            five_hour=_make_quota_window(35.0, 0),
            weekly=_make_quota_window(62.0, 3),
            monthly=_make_quota_window(81.0, 12),
            overall_used_percent=81,
            remaining_percent=19,
            credential_source="Mock",
            workspace_id="mock-workspace-1",
            fetched_at=datetime.now(timezone.utc),
        ),
        GoQuotaInfo(
            five_hour=_make_quota_window(12.0, 0),
            weekly=_make_quota_window(28.0, 5),
            monthly=_make_quota_window(44.0, 20),
            overall_used_percent=44,
            remaining_percent=56,
            credential_source="Mock",
            workspace_id="mock-workspace-2",
            fetched_at=datetime.now(timezone.utc),
        ),
    ]
    if scene == SCENE_CACHED:
        for item in base:
            item.is_cached = True
            item.error = "模拟：命中缓存（上次成功数据）"
    return base


def _make_data_page(scene: str) -> ModelDataSnapshot:
    # 构造数据页快照样例：normal 三源有值；error errors 非空 + 数据空；
    # cached 保留数据 + is_cached 标注
    if scene == SCENE_ERROR:
        snapshot = ModelDataSnapshot(fetched_at=datetime.now(timezone.utc))
        snapshot.errors.append("模拟：数据页接口请求失败")
        return snapshot
    snapshot = ModelDataSnapshot(
        model_blocks={
            "tokenCost": [
                {"model": "opencode-go/deepseek-v4-flash", "cost": 1.23},
                {"model": "opencode-go/claude-sonnet-4", "cost": 4.56},
            ],
            "cacheRatio": [{"model": "opencode-go/deepseek-v4-flash", "ratio": 0.72}],
            "sessionCost": [{"model": "opencode-go/deepseek-v4-flash", "cost": 9.99}],
            "country": [{"country": "CN", "count": 86}],
        },
        daily_usage=[
            {
                "date": "JUL 1",
                "total_t": 4.2,
                "models": {"opencode-go/deepseek-v4-flash": 55.0},
            },
            {
                "date": "JUL 2",
                "total_t": 6.8,
                "models": {"opencode-go/deepseek-v4-flash": 60.0},
            },
        ],
        releases=[
            {
                "tag_name": "v1.6.7",
                "published_at": "2026-08-01T00:00:00Z",
                "body": "示例 Release 说明（虚拟数据）",
            }
            for _ in range(_RELEASE_COUNT)
        ],
        fetched_at=datetime.now(timezone.utc),
    )
    if scene == SCENE_CACHED:
        snapshot.is_cached = True
        snapshot.errors.append("模拟：命中缓存（上次成功快照）")
    return snapshot


class MockService:
    # 虚拟数据门面：与 AppService 同签名（get_usage/get_quotas/get_data_page/
    # export_data/save_account/add_account_via_cdp），按 scene 返回三态样例；
    # 不触库/不触网，供 QML 演示版注入与 UI 分支调试

    def __init__(self, scene: str = SCENE_NORMAL) -> None:
        # 初始化场景选择（normal/error/cached），数据族按场景返回对应样例
        self.scene = scene

    def get_usage(self, db_path: Path | None) -> UsageData:
        # 返回构造的用量聚合（error 场景抛 ServiceError，对齐真服务 db_path=None 口径）
        if self.scene == SCENE_ERROR:
            raise ServiceError("模拟：数据库损坏无法读取用量")
        return UsageData(
            summary=UsageSummary(
                sessions=12,
                messages=245,
                days=5,
                tokens=TokenStats(
                    input=125000,
                    output=98000,
                    reasoning=30000,
                    cache_read=40000,
                    cache_write=8000,
                    total=301000,
                ),
                recorded_cost=12.34,
                cost_source="recorded",
                since=int(time.time()) - 5 * 86400,
                until=int(time.time()),
            ),
            rows={
                dim: [
                    _make_usage_row(f"{dim}-1", 60, 88000, 3.4),
                    _make_usage_row(f"{dim}-2", 35, 42000, 1.8),
                ]
                for dim in _DIMENSION_NAMES
            },
        )

    def export_data(self, db_path: Path | None, out_dir: Path) -> None:
        # 模拟导出：不落盘任何数据，仅记录日志（演示版无真实导出语义）
        logger.info("MockService.export_data 调用成功（out_dir=%s）", out_dir)

    def get_quotas(self) -> list[GoQuotaInfo]:
        # 返回配额样例列表（三态：正常两账户 / 错误占位 / 缓存标注）
        return _make_quotas(self.scene)

    def get_data_page(self) -> ModelDataSnapshot:
        # 返回数据页快照样例（三态：正常三源 / 错误占位 / 缓存标注）
        return _make_data_page(self.scene)

    def save_account(self, workspace_id: str, auth_cookie: str) -> None:
        # 模拟保存账户：不写凭据文件（演示版仅记录，避免污染真实凭据）
        logger.info(
            "MockService.save_account 调用成功（workspace_id=%s）", workspace_id
        )

    def add_account_via_cdp(
        self, login_wait_seconds: int | None = None
    ) -> tuple[str, str]:
        # 模拟 CDP 引导：正常返回假凭据对；error 场景抛 ServiceError（演示失败分支）
        if self.scene == SCENE_ERROR:
            raise ServiceError("模拟：CDP 引导失败（未检测到登录）")
        return "mock-auth-cookie", "mock-workspace-1"


# ===== services/mock_service.py 模块说明 =====
# 模块级常量：
#   SCENE_NORMAL / SCENE_ERROR / SCENE_CACHED：三态场景名（MockService 构造参数）
#   _DIMENSION_NAMES：展示用六维度键（对齐 services.service.DIMENSIONS 顺序）
#   _RELEASE_COUNT：Releases 样例条数（对齐 opencode_data._RELEASE_LIMIT）
# 函数：
#   _make_usage_row(label, calls, total_tokens, cost)：构造一条 UsageRow 样例
#     （tokens 按总量对半拆到 input/output，total 直接给总量）
#   _make_quota_window(percent, days_until_reset)：构造 GoQuotaWindow 样例
#     （重置时间 = 当前时间 + 天数偏移，reset_in_sec 同步）
#   _make_quotas(scene)：配额样例列表——normal 两账户三窗口；error 单占位
#     （error + error_stage=NETWORK + 三窗口 None）；cached 保留数据 + is_cached 标注
#   _make_data_page(scene)：数据页快照样例——normal 三源有值；error errors 非空 +
#     数据空；cached 保留数据 + is_cached 标注
# 类型：
#   MockService：虚拟数据门面（与 AppService 六方法同签名，scene 驱动三态）
# 设计理由：QML 演示版不接真实业务（PL008 验收定义），mock 提供可插拔数据源；
#   DTO 直接复用真服务同款 dataclass——isinstance 验证保证前端消费类型一致；
#   三态样例覆盖 UI 各分支（正常/错误占位/缓存标注）供调试
# 异常处理：get_usage 与 add_account_via_cdp 的 error 场景抛 ServiceError
#   （与真服务业务失败口径一致，UI 走同一状态栏模板）
# 关联配置：无（样例数据全部代码内构造，不读配置文件）
