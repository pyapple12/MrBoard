# 凭据加密存储模块：DPAPI（CryptProtectData）加密凭据 JSON，绑定当前 Windows 用户

import base64
import json
from pathlib import Path
from typing import Any

try:
    import win32crypt
except ImportError:  # 打包环境缺依赖时降级为 None（加密不可用，写入路径拒绝明文落盘）
    win32crypt = None

from utils.logger import get_logger

logger = get_logger(__name__)

# 加密格式标记：文件 dict 含该键时按 base64(DPAPI blob) 解密（P4）
ENCRYPTED_KEY = "encrypted_v1"


class CredentialEncryptionError(Exception):
    # 凭据加密业务错误：win32crypt 缺失或加解密失败时抛出，携带中文提示

    def __init__(self, message: str) -> None:
        # 初始化错误提示，供 UI 状态栏展示
        super().__init__(message)
        self.message = message


def encrypt_credentials(workspace_id: str, auth_cookie: str) -> str:
    # 加密凭据 JSON 为 base64(DPAPI blob)；win32crypt 缺失时抛错误（安全优先，P4 D3=A）
    if win32crypt is None:
        raise CredentialEncryptionError(
            "缺少 pywin32，无法加密保存凭据（安全策略：拒绝明文写入），请安装 pywin32 后重试"
        )
    payload = json.dumps(
        {"workspaceId": workspace_id, "authCookie": auth_cookie},
        ensure_ascii=False,
    ).encode("utf-8")
    try:
        # pywin32 的 CryptProtectData 直接返回加密 blob（bytes），非元组
        blob = win32crypt.CryptProtectData(
            payload, "myboard-credentials", None, None, None, 0
        )
    except Exception as exc:
        raise CredentialEncryptionError(f"DPAPI 加密凭据失败：{exc}") from exc
    return base64.b64encode(blob).decode("ascii")


def decrypt_credentials(encrypted_text: str) -> dict[str, Any] | None:
    # 解密 base64(DPAPI blob) 为凭据 dict；win32crypt 缺失或解密失败返回 None（宽容降级）
    if win32crypt is None:
        logger.warning("缺少 pywin32，无法解密加密凭据")
        return None
    try:
        blob = base64.b64decode(encrypted_text)
        # pywin32 怪癖：返回 (空/描述, 解密数据)——数据在第二个元素
        # （browser_creds 的 `_, aes_key = ...` 同款；文本数据可能返回 str，
        #   统一转 bytes 再解析）
        _, data = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
        if isinstance(data, str):
            data = data.encode("utf-8")
        raw = json.loads(data.decode("utf-8"))
    except Exception as exc:
        logger.warning("解密凭据失败：%s", exc)
        return None
    return raw if isinstance(raw, dict) else None


def read_credentials_file(path: Path) -> dict[str, Any] | None:
    # 读取凭据文件（宽容解析）：加密格式识别标记解密；明文旧格式原样返回；失败返回 None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("读取凭据配置失败 %s：%s", path, exc)
        return None
    if not isinstance(raw, dict):
        return None
    encrypted_text = raw.get(ENCRYPTED_KEY)
    if isinstance(encrypted_text, str) and encrypted_text:
        return decrypt_credentials(encrypted_text)
    return raw


# ===== modules/credential_store.py 模块说明 =====
# 模块级常量：
#   ENCRYPTED_KEY：加密格式标记（文件 dict 含该键 = DPAPI 加密 blob）
# 模块级导入：win32crypt 缺失时降级为 None（写入路径拒绝明文落盘，读取路径返回 None）
# 类型：
#   CredentialEncryptionError：加密业务错误（win32crypt 缺失/DPAPI 失败），中文提示
# 函数：
#   encrypt_credentials(workspace_id, auth_cookie)：
#     输入：workspaceId 与 authCookie 明文
#     输出：base64(DPAPI blob) 字符串（加密后的凭据 JSON）
#     逻辑步骤：win32crypt 缺失抛 CredentialEncryptionError（D3=A 安全优先）→
#       json.dumps 明文凭据 → CryptProtectData（绑定当前 Windows 用户 SID）→ base64
#     设计理由：DPAPI 加密绑定当前 Windows 用户，他人换机/换用户无法解密；
#       加密粒度为整个凭据 JSON（workspaceId + authCookie 一起）
#   decrypt_credentials(encrypted_text)：
#     输入：base64(DPAPI blob) 字符串
#     输出：凭据 dict；win32crypt 缺失/解密失败返回 None（宽容降级不崩溃）
#     逻辑步骤：base64 解码 → CryptUnprotectData → json.loads → 校验 dict
#     设计理由：读取路径宽容降级（坏数据返回 None 由调用方跳过，z.plan 第四章）
#   read_credentials_file(path)：
#     输入：凭据文件路径
#     输出：凭据 dict（加密格式解密 / 明文格式原样）；损坏/缺失返回 None
#     逻辑步骤：json.loads（异常打 WARNING 返回 None）→ 含 ENCRYPTED_KEY 走解密 →
#       否则按明文旧格式返回
#     设计理由：向后兼容明文旧格式（P4 前的文件直接可读），新写入一律加密
# 异常处理：读取全路径宽容（返回 None）；加密路径 win32crypt 缺失抛
#   CredentialEncryptionError（UI 状态栏提示，不弹窗）
# 关联配置：无（DPAPI 系统级，绑定当前用户）；被 modules/go_quota.py 集成
#   （save_dashboard_credentials 加密写入 / _read_credentials_json 兼容读取）
