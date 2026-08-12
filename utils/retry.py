# 泛型重试工具模块

import logging
import time
from typing import Any, Callable

from utils.logger import get_logger

# 统一日志入口（3A.1 R5：与全项目一致，避免绕过 get_logger 的格式/落盘约定）
_logger = get_logger(__name__)


def retry_call(
    func: Callable[..., Any],
    *args: Any,
    retries: int = 3,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    delay: float = 1.0,
    backoff: float = 2.0,
    logger: logging.Logger | None = None,
    **kwargs: Any,
) -> Any:
    # 执行 func 并捕获指定异常时按指数退避重试，重试耗尽后抛出最后一次异常
    # （6A.2 D5：负值参数 clamp——retries<0 会空循环触发 assert，delay/backoff 负值
    #   time.sleep 抛 ValueError）
    retries = max(0, int(retries))
    delay = max(0.0, float(delay))
    backoff = max(1.0, float(backoff))
    log = logger or _logger
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as exc:
            last_error = exc
            if attempt >= retries:
                break
            wait = delay * (backoff**attempt)
            log.warning(
                "调用 %s 失败（第 %d/%d 次）：%s，%.1f 秒后重试",
                getattr(func, "__name__", str(func)),
                attempt + 1,
                retries,
                exc,
                wait,
            )
            time.sleep(wait)
    # 循环内成功即 return，异常必被捕获赋值 last_error（C9 assert 消除 Optional 语义）
    assert last_error is not None, "重试逻辑异常：未捕获到错误"
    raise last_error


# ===== utils/retry.py 模块说明 =====
# 模块级变量：
#   _logger：模块私有日志器（无业务依赖，符合 utils 层定位）
# 函数：
#   retry_call(func, *args, retries=3, exceptions=(Exception,), delay=1.0,
#              backoff=2.0, logger=None, **kwargs)：
#     输入：func 任意可调用对象；*args/**kwargs 透传给 func；retries 重试次数
#       （总尝试 retries+1 次）；exceptions 可捕获的异常元组；delay 首次等待秒数；
#       backoff 退避倍数；logger 可选日志器（默认模块私有 _logger）
#     输出：func 成功时的返回值；始终失败时抛出最后一次异常
#     逻辑步骤：循环尝试 → 成功立即返回 → 捕获指定异常且未耗尽重试次数则
#       time.sleep(delay * backoff ** attempt) 后继续 → 耗尽后抛出 last_error
#     设计理由：泛型化（异常元组参数化）与业务解耦（对齐 AccelWorld utils/retry 定位），
#       指数退避避免网络故障时高频轰炸接口（参考 opencode-usage 的退避重试经验）
# 异常处理：仅捕获调用方指定的 exceptions 元组（避免吞掉意外异常）；
#   重试耗尽重新抛出原始异常，由上层决定降级策略（z.plan.md 第四章：缓存兜底）
# 关联配置：无（go_quota 网络请求、config 读取等均可复用）
