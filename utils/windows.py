# Windows 平台工具模块：DPAPI 加解密 + win32crypt 可选导入降级（4A.2 D2/D3 收敛两模块重复）

try:
    import win32crypt
except ImportError:  # 打包环境缺依赖时降级为 None（调用方判空处理）
    win32crypt = None

from utils.logger import get_logger

logger = get_logger(__name__)  # R4：统一日志入口（原 logging.getLogger 直取，5A.2）

# DPAPI 加密描述串（CryptProtectData 的 description 参数，5A.3 C11 消除魔法字符串）
DPAPI_DESCRIPTION = "myboard"

# win32crypt 可用性标记（加载时固化；测试可通过 mock 本模块 win32crypt 模拟缺失）
WIN32CRYPT_AVAILABLE = win32crypt is not None


def dpapi_protect(data: bytes) -> bytes | None:
    # DPAPI 加密（CryptProtectData，绑定当前 Windows 用户）；win32crypt 缺失或失败返回 None
    if win32crypt is None:
        return None
    try:
        # pywin32 的 CryptProtectData 直接返回加密 blob（bytes）
        return win32crypt.CryptProtectData(data, DPAPI_DESCRIPTION, None, None, None, 0)
    except Exception as exc:
        logger.warning("DPAPI 加密失败：%s", exc)
        return None


def dpapi_unprotect(data: bytes) -> bytes | None:
    # DPAPI 解密（CryptUnprotectData）；win32crypt 缺失或失败返回 None（宽容降级）
    if win32crypt is None:
        return None
    try:
        # pywin32 怪癖：返回 (空/描述, 数据)——数据在第二个元素；文本数据可能返回 str
        _, plaintext = win32crypt.CryptUnprotectData(data, None, None, None, 0)
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")
        return plaintext
    except Exception as exc:
        logger.warning("DPAPI 解密失败：%s", exc)
        return None


# ===== utils/windows.py 模块说明 =====
# 模块级常量：DPAPI_DESCRIPTION——DPAPI 加密描述串（CryptProtectData description 参数）
# 模块级导入：win32crypt 缺失时降级为 None（WIN32CRYPT_AVAILABLE 供业务模块判空）
# 函数：
#   dpapi_protect(data)：
#     输入：明文 bytes
#     输出：加密 blob bytes；win32crypt 缺失/加密失败返回 None
#     逻辑步骤：判空 → CryptProtectData（绑定当前 Windows 用户）→ 返回 blob
#     设计理由：credential_store 加密写入复用（4A.2 D3 收敛两处 DPAPI 调用）
#   dpapi_unprotect(data)：
#     输入：加密 blob bytes
#     输出：明文 bytes；缺失/失败返回 None（宽容降级）
#     逻辑步骤：判空 → CryptUnprotectData → str 转 bytes（pywin32 文本怪癖）
#     设计理由：credential_store 解密与 browser_creds AES key 提取共用
#     （browser_creds 原 `_, aes_key = CryptUnprotectData(...)` 同款）
# 异常处理：加解密异常捕获并打 WARNING，返回 None（调用方决定降级策略）
# 关联配置：无（Windows 系统 DPAPI，绑定当前用户）
