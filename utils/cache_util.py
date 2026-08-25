# 缓存兜底标注共享工具（N1.1：收敛 opencode_data 与 go_quota 重复的 _mark_cached）
from dataclasses import replace


def mark_cached(
    obj: object,
    message: str,
    *,
    error_field: str = "error",
    list_field: str | None = None,
) -> object:
    # 缓存兜底标注：浅拷贝对象再标记 is_cached 为 True；list_field 非空时把 message
    # 追加到该列表字段（如 ModelDataSnapshot.errors），否则写入单值 error_field
    # （如 GoQuotaInfo.error）；浅拷贝防污染共享对象（UI 持有旧引用不受影响）
    kwargs = {"is_cached": True}
    if list_field:
        kwargs[list_field] = getattr(obj, list_field) + [message]
    else:
        kwargs[error_field] = message
    return replace(obj, **kwargs)


# ===== utils/cache_util.py 模块说明 =====
# 职责：缓存兜底标注的通用工具（跨模块去重 opencode_data/go_quota 的同构 _mark_cached）
# 导出函数：
#   mark_cached(obj, message, *, error_field="error", list_field=None)：
#     浅拷贝 obj 并置 is_cached=True；list_field 非空时追加 message 到该列表字段，
#     否则写入单值 error_field；返回新对象（不修改入参，防污染共享引用）
# 设计理由：两模块原各自定义结构相同的 _mark_cached，仅 errors 列表 vs error 单值之差；
#   抽此共享函数（error_field/list_field 参数化）消除重复且不引入过度抽象（单一小函数）；
#   依赖 dataclasses.replace，仅作用于 dataclass（GoQuotaInfo/ModelDataSnapshot 均满足）
# 异常处理：getattr 在 obj 缺 list_field 时抛 AttributeError（调用方保证字段存在）
