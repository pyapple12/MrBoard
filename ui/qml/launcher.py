# QML 前端数据桥与启动器（PL008.4.b）
# 组装 context：service + usageModel/quotaModel/releasesModel + summary +
# 阈值/注册表/文案（contracts 单点注入）+ 资源路径 get_project_root 自定位；
# QML 前端不读任何配置文件，全部经此注入

import sys
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    Qt,
    Slot,
)
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from services.contracts import (
    CARD_TITLES,
    COST_ZERO_EPSILON,
    DATA_PAGE_TEXTS,
    DEFAULT_THEME_NAME,
    QUOTA_DANGER_PERCENT,
    QUOTA_WARN_PERCENT,
    TABLE_COLUMNS,
    THEME_NAMES,
    TOKEN_ABBR_UNITS,
    get_ui_texts,
)
from services.mock_service import MockService, SCENE_NORMAL
from services.service import ServiceError, UsageData
from modules.opencode_usage import UsageSummary
from utils.file_utils import get_project_root

# 各 model 的 role 字段（role 名 = 字段名，QML roleName 直接引用；
# 嵌套对象用点路径，如 tokens.total / five_hour.usage_percent）
_USAGE_ROLES = (
    "label",
    "calls",
    "cost",
    "tokens.input",
    "tokens.output",
    "tokens.reasoning",
    "tokens.cache_read",
    "tokens.cache_write",
    "tokens.total",
)
_QUOTA_ROLES = (
    "five_hour.usage_percent",
    "five_hour.reset_in_sec",
    "weekly.usage_percent",
    "weekly.reset_in_sec",
    "monthly.usage_percent",
    "monthly.reset_in_sec",
    "overall_used_percent",
    "remaining_percent",
    "credential_source",
    "workspace_id",
    "is_cached",
    "error",
    "error_stage",
)
_RELEASE_ROLES = ("tag_name", "published_at", "body")

# QML 前端消费的文案组（get_ui_texts 单点读取；组缺失导入期抛 RuntimeError）
_UI_TEXT_GROUPS = ("status_messages", "data_page_messages")


def _resolve(record, field_path: str):
    # 按点路径取值：record 为 dataclass 或 dict，路径形如 tokens.total；
    # 中间层取不到返回 None（宽容，不抛——缺字段不炸整行）
    value = record
    for part in field_path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = getattr(value, part, None)
        if value is None:
            return None
    return value


class ListModel(QAbstractListModel):
    # 通用只读列表模型：records 为 dataclass/dict 列表，roles 为展示字段名元组；
    # role 名与字段名一致（前端 roleName 直接引用字段名，P23 语义绑定）

    def __init__(self, records: list, roles: tuple[str, ...], parent=None) -> None:
        # 初始化：角色映射从 UserRole 起顺序编号，role 名即字段名
        super().__init__(parent)
        self._records = list(records)
        self._role_map = {
            Qt.ItemDataRole.UserRole + index: role for index, role in enumerate(roles)
        }

    @Property(int, constant=True)
    def count(self) -> int:
        # 行数属性（QML 侧 model.count 直读；QAbstractListModel 自身不暴露
        # count 到 QML，前端列表/卡片均依赖此属性）
        return len(self._records)

    def rowCount(self, parent=None) -> int:
        # 返回记录条数（QML View 内部行数来源）
        return len(self._records)

    def roleNames(self) -> dict:
        # 返回 role 编号 → 字段名（QML roleName 直读字段名）
        return {
            role: QByteArray(name.encode("utf-8"))
            for role, name in self._role_map.items()
        }

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        # 按角色返回字段值（点路径解析；越界/未知角色返回 None）
        if not index.isValid() or index.row() >= len(self._records):
            return None
        name = self._role_map.get(role)
        if name is None:
            return None
        return _resolve(self._records[index.row()], name)

    @Slot(int, str, result=float)
    def getNumber(self, row: int, field: str) -> float:
        # 任意行数值字段直读（QML 进度条/饼图 value 用）；
        # 混合类型经 Slot 返回会触发 Shiboken copy-convert 崩溃（PL008.6 实测），
        # 数值/字符串拆两个明确返回类型的 Slot；取不到返回 0
        if not (0 <= row < len(self._records)):
            return 0.0
        value = _resolve(self._records[row], field)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @Slot(int, str, result=str)
    def getString(self, row: int, field: str) -> str:
        # 任意行字符串字段直读（QML 状态文案/workspace 显示用）；
        # 取不到返回空串
        if not (0 <= row < len(self._records)):
            return ""
        value = _resolve(self._records[row], field)
        if value is None:
            return ""
        return str(value)


def _summary_to_dict(summary) -> dict:
    # 用量总览转 dict（QML 经 context property 读属性；dataclass 非 QObject 不可直读）
    return {
        "sessions": summary.sessions,
        "messages": summary.messages,
        "days": summary.days,
        "input": summary.tokens.input,
        "output": summary.tokens.output,
        "reasoning": summary.tokens.reasoning,
        "cache_read": summary.tokens.cache_read,
        "cache_write": summary.tokens.cache_write,
        "total": summary.tokens.total,
        "recorded_cost": summary.recorded_cost,
        "estimated_cost_total": summary.estimated_cost_total,
        "cost_source": summary.cost_source,
        "since": summary.since,
        "until": summary.until,
    }


def build_context(scene: str = SCENE_NORMAL) -> dict:
    # 组装全部 context property 值（注入逻辑与启动分离，便于无头探针复用）；
    # 三个 model 均包装 mock 样例（usage 取 month 维度 rows）；
    # error 场景 get_usage 抛 ServiceError（对齐真服务口径）——此处容错用
    # 空 UsageData 渲染占位（卡片显示 "-"，UI 各分支不崩）
    svc = MockService(scene)
    try:
        usage = svc.get_usage(None)
    except ServiceError:
        usage = UsageData(summary=UsageSummary(), rows={})
    quotas = svc.get_quotas()
    page = svc.get_data_page()
    return {
        "service": svc,
        "usageModel": ListModel(usage.rows.get("month", []), _USAGE_ROLES),
        "quotaModel": ListModel(quotas, _QUOTA_ROLES),
        "releasesModel": ListModel(page.releases, _RELEASE_ROLES),
        "usageSummary": _summary_to_dict(usage.summary),
        "warnPercent": QUOTA_WARN_PERCENT,
        "dangerPercent": QUOTA_DANGER_PERCENT,
        "themeNames": list(THEME_NAMES),
        "defaultTheme": DEFAULT_THEME_NAME,
        "cardTitles": CARD_TITLES,
        "tokenAbbrUnits": [
            [threshold, suffix] for threshold, suffix in TOKEN_ABBR_UNITS
        ],
        "costZeroEpsilon": COST_ZERO_EPSILON,
        "tableColumns": [dict(item) for item in TABLE_COLUMNS],
        "dataPageTexts": dict(DATA_PAGE_TEXTS),
        "uiTexts": {group: get_ui_texts(group) for group in _UI_TEXT_GROUPS},
    }


def prepare_engine(scene: str = SCENE_NORMAL) -> QQmlApplicationEngine:
    # 创建 QML 引擎并完成注入（含 FluentUI import path 注册 + 全部 context
    # property）；launch 与无头探针共用，避免各自漏注册 FluentUI；
    # 注入对象挂到 engine 保活（PySide6 对 context property 的 Python 对象
    # 无引用即 GC——QML 侧会读成 null，A017 教训同源）
    engine = QQmlApplicationEngine()
    import FluentUI

    FluentUI.init(engine)
    values = build_context(scene)
    for name, value in values.items():
        engine.rootContext().setContextProperty(name, value)
    engine._bridge_keepalive = values
    return engine


def launch(qml_path: Path | str | None = None, scene: str = SCENE_NORMAL) -> int:
    # QML 前端启动入口：默认加载 ui/qml/main.qml（PL008.5 起提供）；
    # qml_path 可传自定义文件（探针/演示用）；返回事件循环退出码
    # 用 QApplication 而非 QGuiApplication——QtCharts QML 插件在 PySide6 下
    # 需 QApplication（QGuiApplication 会 0xC0000005 崩溃，PL008.6.c 实测）
    app = QApplication(sys.argv)
    engine = prepare_engine(scene)
    target = (
        Path(qml_path)
        if qml_path is not None
        else get_project_root() / "ui" / "qml" / "main.qml"
    )
    engine.load(str(target))
    if not engine.rootObjects():
        print(f"QML 加载失败：{target}")
        return 1
    return app.exec()


# ===== ui/qml/launcher.py 模块说明 =====
# 模块级常量：
#   _USAGE_ROLES / _QUOTA_ROLES / _RELEASE_ROLES：三 model 的 role 字段元组
#     （role 名 = 字段名，嵌套用点路径；UsageRow/GoQuotaInfo/releases dict 字段对齐）
#   _UI_TEXT_GROUPS：QML 前端消费的文案组（contracts.get_ui_texts 单点读取）
# 类型：
#   ListModel：通用只读列表模型（records + roles，点路径取值，role 名即字段名；
#     count 属性供 QML 行数直读；get(row, field) Slot 供任意行字段直读）
# 函数：
#   _resolve(record, field_path)：点路径取值（dataclass/dict 通用，缺字段返回 None）
#   _summary_to_dict(summary)：用量总览转 dict（QML context property 直读属性）
#   build_context(scene)：组装全部 context property 值（service + 三 model +
#     summary + 阈值/注册表/卡片标题/token 缩写/费用容差/表格列/数据页文案/文案；
#     注入与启动分离便于无头探针复用）
#   prepare_engine(scene)：创建引擎 + FluentUI import path 注册 + 全量注入
#     （launch 与无头探针共用，防各自漏注册 FluentUI）
#   launch(qml_path, scene)：启动入口——QApplication + 注入 context + 加载 QML +
#     事件循环；默认 ui/qml/main.qml，资源路径经 get_project_root 自定位
# 设计理由：QML 前端零配置直读（不碰 config 文件），全部事实经 contracts 注入
#   （阈值/注册表/文案单点）；ListModel 通用化避免三份 model 类重复；role 名与
#   dataclass 字段一致满足 P23 语义绑定（前端 roleName 直引字段名）
# 异常处理：build_context 中 get_ui_texts 组缺失抛 RuntimeError（导入期契约校验）；
#   launch 加载失败返回 1 退出码（根对象为空）
# 关联配置：无直接读取（阈值/注册表/文案经 services.contracts 间接消费 ui.json）
