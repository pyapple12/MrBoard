# 共享事实层（PL008.1）：阈值/主题注册表/面向用户文案的单一解包点
# 所有前端（qt6/qml）经此模块消费共享语义，前端不各自读取配置文件；
# 解包逻辑收敛到此一处，键名校验在此统一进行（契约层 P23 定案）

from config.static.static_config import get_static_config

_SC = get_static_config()

# 配额阈值（S8.3 外置 ui.json，静态配置解包）
QUOTA_WARN_PERCENT = int(_SC.ui["quota_warn_percent"])
QUOTA_DANGER_PERCENT = int(_SC.ui["quota_danger_percent"])
# 托盘专用正常色（PL003.1.e：与窗口主题无关，仅 system_tray 使用，挂起项归属定案
# 不影响解包位置——统一经本模块读取）
QUOTA_COLOR_OK = str(_SC.ui["colors"]["quota_ok"])

# 主题注册表（ui.json themes 数组为注册顺序唯一权威）
THEME_NAMES = tuple(str(item) for item in _SC.ui["themes"])
# A3.5：主题名长度契约校验（数组被手改短会致索引越界，导入期即抛错）
if len(THEME_NAMES) < 2:
    raise RuntimeError(
        f"ui.json themes 数组至少需要 light/dark 两项，当前 {THEME_NAMES}"
    )
DEFAULT_THEME_NAME = THEME_NAMES[0]

# 卡片标题（ui.json card_titles，P17 卡片顺序唯一权威）
CARD_TITLES = dict(_SC.ui["card_titles"])
# token 缩写单位（ui.json token_abbr_units；阈值降序 (threshold, suffix)，
# 对齐 qt6 TOKEN_ABBR_UNITS 的格式化口径）
TOKEN_ABBR_UNITS = tuple(
    (int(threshold), str(suffix))
    for threshold, suffix in sorted(
        ((int(key), value) for key, value in _SC.ui["token_abbr_units"].items()),
        reverse=True,
    )
)
# 费用近零容差（ui.json cost_zero_epsilon；qt6 _format_cost 同源）
COST_ZERO_EPSILON = float(_SC.ui["cost_zero_epsilon"])

# 用量明细列元数据（ui.json table_columns：id/title 展示元数据，数组顺序即展示顺序）
TABLE_COLUMNS = tuple(
    {"id": str(item["id"]), "title": str(item["title"])}
    for item in _SC.ui["table_columns"]
)
# 列字段键集（P23 契约：代码内声明，ui.json 展示元数据导入期与之比对，防错位）
TABLE_COLUMN_IDS = (
    "label",
    "total",
    "calls",
    "input",
    "output",
    "reasoning",
    "cache",
    "cache_rate",
    "cost",
)
if tuple(item["id"] for item in TABLE_COLUMNS) != TABLE_COLUMN_IDS:
    raise RuntimeError(
        f"ui.json table_columns id 序列与 TABLE_COLUMN_IDS 不一致："
        f"{[item['id'] for item in TABLE_COLUMNS]} vs {TABLE_COLUMN_IDS}"
    )

# 数据与动态页文案（ui.json 顶层键，QML DataPage 展示用——非文案组故显式解包）
DATA_PAGE_TEXTS = {
    "detail_title": str(_SC.ui["detail_section_title"]),
    "releases_title": str(_SC.ui["data_releases_title"]),
    "releases_empty": str(_SC.ui["data_releases_empty"]),
    "table_empty": str(_SC.ui["data_empty_text"]),
}


def get_ui_texts(group: str) -> dict:
    # 按组名返回 ui.json 文案组的浅拷贝字典（共享层唯一文案读取点；
    # 组不存在或非对象抛 RuntimeError 中文诊断，对齐 H0.4/_UI_STRUCT_KEYS 契约风格）
    if group not in _SC.ui:
        raise RuntimeError(f"ui.json 缺少文案组：{group}")
    value = _SC.ui[group]
    if not isinstance(value, dict):
        raise RuntimeError(
            f"ui.json 文案组 {group} 必须是对象，当前 {type(value).__name__}"
        )
    return dict(value)


# ===== services/contracts.py 模块说明 =====
# 模块级常量：
#   _SC：静态配置解包（ui.json 节）
#   QUOTA_WARN_PERCENT / QUOTA_DANGER_PERCENT：配额阈值（ui.json quota_*_percent 驱动）
#   QUOTA_COLOR_OK：托盘专用正常色（ui.json colors.quota_ok，仅 system_tray 使用）
#   THEME_NAMES：主题名元组（ui.json themes 数组派生，注册顺序唯一权威）
#   DEFAULT_THEME_NAME：默认主题（注册表首项）
#   CARD_TITLES：用量卡片标题（ui.json card_titles，P17 顺序唯一权威）
#   TOKEN_ABBR_UNITS：token 缩写单位（ui.json token_abbr_units，阈值降序）
#   COST_ZERO_EPSILON：费用近零容差（ui.json cost_zero_epsilon）
#   TABLE_COLUMNS：用量明细列元数据（ui.json table_columns，id/title，顺序即展示顺序）
#   TABLE_COLUMN_IDS：列字段键集（代码内声明，导入期与 ui.json 比对防错位）
#   DATA_PAGE_TEXTS：数据与动态页顶层文案（detail_section_title/data_releases_*/
#     data_empty_text，非文案组故显式解包）
# 函数：
#   get_ui_texts(group)：按组名返回文案组浅拷贝字典（组缺失/非对象抛 RuntimeError）
# 设计理由：阈值/注册表/文案原本分散在 theme_loader 与未来 qml 各自解包，
#   存在键名双处维护与校验分散风险；PL008 统一为单一解包点（契约层 P23 定案）
# 异常处理：导入期主题数组过短/table_columns 错位抛 RuntimeError；get_ui_texts
#   运行时校验组存在性与类型
# 关联配置：ui.json（quota_warn_percent/quota_danger_percent/colors/themes/
#   card_titles/token_abbr_units/cost_zero_epsilon/table_columns/
#   detail_section_title/data_releases_title/data_releases_empty/data_empty_text/各文案组）
