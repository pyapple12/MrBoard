# 网络请求统一工具模块：GET 请求构造 + 网络重试异常元组（3A.1 R1/R8 收敛三处自实现）

import urllib.error
import urllib.request

from config.static.static_config import get_static_config

# 网络类可重试异常元组（retry_call 的 exceptions 参数共用，R8）
RETRY_NETWORK_ERRORS: tuple[type[Exception], ...] = (
    urllib.error.URLError,
    TimeoutError,
)


def http_get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
) -> bytes:
    # 发送 GET 请求返回响应体；urlopen 对非 2xx 直接抛 HTTPError（3xx 自动跟随），
    # 网络异常原样传播（交 retry_call 重试或调用方分类）
    # （A2.4：默认 None 回退 base.json http_timeout——单一来源，调用方可显式覆盖）
    if timeout is None:
        timeout = float(get_static_config().base["http_timeout"])
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


# ===== utils/network.py 模块说明 =====
# 模块级常量：
#   RETRY_NETWORK_ERRORS：网络类可重试异常元组（URLError/TimeoutError），
#     go_quota/pricing 的 retry_call 共用（3A.1 R8：消除两处重复书写）
# 函数：
#   http_get(url, headers=None, timeout=None)：
#     输入：URL、可选请求头、超时秒数
#     输出：响应体 bytes
#     逻辑步骤：构造 Request → urlopen（带超时）→ 返回响应体
#     设计理由：三处自实现 urllib 请求收敛为单一工具（3A.1 R1：go_quota/pricing
#       _http_get 与 browser_creds 内联 urlopen）；401/403 等业务分类由调用方
#       捕获 HTTPError 处理（utils 层不依赖业务异常类型）
# 异常处理：非 2xx 抛 urllib.error.HTTPError；网络/超时异常原样传播，均交调用方
#   重试或分类（z.plan 第四章错误策略）
# 关联配置：timeout 默认 None 回退 base.json http_timeout（A2.4 单一来源），
#   调用方可显式覆盖（go_quota/pricing 的 HTTP_TIMEOUT）
