# 弹性类型转换模块：外部数据（数据库/JSON）数字字段可能是字符串，宽容转换不崩溃

from typing import Any


def to_int(value: Any, default: int = 0) -> int:
    # 弹性整数转换：数字/数字字符串均可（str→float→int 两级），失败返回 default
    try:
        if isinstance(value, bool):
            return default
        return int(value)
    except (TypeError, ValueError):
        pass
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    # 弹性浮点转换：数字/数字字符串均可，失败返回 default（bool 语义非数值，S1 与 to_int 一致）
    try:
        if isinstance(value, bool):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def to_optional_float(value: Any) -> float | None:
    # 弹性浮点转换（可空）：None/空/非法时返回 None（区分"未记录"与 0；bool 语义非数值，E3）
    if value is None:
        return None
    try:
        if isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def round_cost(value: Any, digits: int = 4) -> float:
    # 成本舍入（库 cost 聚合口径统一，3A.1 R6：opencode_usage/exporter 5 处复用）
    return round(to_float(value), digits)


# ===== utils/convert.py 模块说明 =====
# 函数：
#   to_int(value, default=0)：str→int 失败再 str→float→int 两级兜底；
#     bool 是 int 子类但语义非数值，直接回 default；None/垃圾回 default
#   to_float(value, default=0.0)：单级 float() 兜底
#   to_optional_float(value)：None 与非法值返回 None——None 语义为"未记录"
#     （与 0 区分，对齐 z.plan 第四章宽容解析）
#   round_cost(value, digits=4)：成本舍入（to_float 后 round，聚合口径统一）
# 设计理由：opencode.db 的 token/cost 字段可能是字符串（真实库新旧格式混合），
#   pricing.py 原有私有 _to_float/_to_optional_float，本模块提升为公共 utils
#   层（无业务依赖，符合分层），opencode_usage 与 pricing 共同复用
#   （审计 M3/D5：消除 int() 直接强转崩溃风险）
# 异常处理：所有转换异常内部消化，绝不外抛
# 关联配置：无（通用工具）
