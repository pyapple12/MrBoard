# 凭据加密存储模块：DPAPI（CryptProtectData）加密凭据 JSON，绑定当前 Windows 用户；
# 含凭据指纹与账户切换日志（PL001 多账户用量区分）

import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from utils.file_utils import read_json, write_json
from utils.logger import get_logger
from utils.windows import WIN32CRYPT_AVAILABLE, dpapi_protect, dpapi_unprotect

logger = get_logger(__name__)

# 加密格式标记：文件 dict 含该键时按 base64(DPAPI blob) 解密（P4）
ENCRYPTED_KEY = "encrypted_v1"
# 凭据字段键（R9：go_quota 的兼容集合首键引用本常量，单点维护）
WORKSPACE_ID_KEY = "workspaceId"
AUTH_COOKIE_KEY = "authCookie"
# 账户切换日志文件名（PL001：存 credentials_dir 下，与 opencode-go.json 同目录）
SWITCH_LOG_FILENAME = "switch_log.json"


class CredentialEncryptionError(Exception):
    # 凭据加密业务错误：win32crypt 缺失或加解密失败时抛出，携带中文提示

    def __init__(self, message: str) -> None:
        # 初始化错误提示，供 UI 状态栏展示
        super().__init__(message)
        self.message = message


def encrypt_credentials(workspace_id: str, auth_cookie: str) -> str:
    # 加密凭据 JSON 为 base64(DPAPI blob)；win32crypt 缺失时抛错误（安全优先，P4 D3=A）
    if not WIN32CRYPT_AVAILABLE:
        raise CredentialEncryptionError(
            "缺少 pywin32，无法加密保存凭据（安全策略：拒绝明文写入），请安装 pywin32 后重试"
        )
    payload = json.dumps(
        {WORKSPACE_ID_KEY: workspace_id, AUTH_COOKIE_KEY: auth_cookie},
        ensure_ascii=False,
    ).encode("utf-8")
    blob = dpapi_protect(payload)
    if blob is None:
        raise CredentialEncryptionError("DPAPI 加密凭据失败")
    return base64.b64encode(blob).decode("ascii")


def decrypt_credentials(encrypted_text: str) -> dict[str, Any] | None:
    # 解密 base64(DPAPI blob) 为凭据 dict；win32crypt 缺失或解密失败返回 None（宽容降级）
    if not WIN32CRYPT_AVAILABLE:
        logger.warning("缺少 pywin32，无法解密加密凭据")
        return None
    try:
        blob = base64.b64decode(encrypted_text)
        plaintext = dpapi_unprotect(blob)
        if plaintext is None:
            return None
        raw = json.loads(plaintext.decode("utf-8"))
    except (ValueError, TypeError) as exc:
        # JSONDecodeError 是 ValueError 子类，无需重复列举（5A.3 C10）
        logger.warning("解密凭据失败：%s", exc)
        return None
    return raw if isinstance(raw, dict) else None


def read_credentials_file(path: Path) -> list[dict[str, Any]]:
    # 读取凭据文件（宽容解析，复用 read_json 原子读；仅接受加密格式）：
    # 单对象（旧格式）或数组（PL001.7 多凭据）统一规范化为 list[dict]；
    # 缺失打 DEBUG 防日志噪音；坏元素过滤跳过；非加密条目 WARNING 拒绝（P11 口径）
    if not path.is_file():
        # 6A.2 D6：文件缺失是无凭据用户常态（每轮刷新都会走到），降级 DEBUG 防日志噪音
        logger.debug("读取凭据配置失败 %s：文件不存在", path)
        return []
    raw = read_json(path, default=None, use_cache=False)
    if isinstance(raw, list):
        entries: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            decrypted = _decrypt_entry(item, path)
            if decrypted is not None:
                entries.append(decrypted)
        return entries
    if not isinstance(raw, dict):
        return []
    decrypted = _decrypt_entry(raw, path)
    return [decrypted] if decrypted is not None else []


def _decrypt_entry(entry: dict[str, Any], path: Path) -> dict[str, Any] | None:
    # 单条加密条目解密：含 ENCRYPTED_KEY 走解密；明文/缺标记条目 WARNING 拒绝
    # （与写入路径"拒绝明文落盘"对称，P11 安全口径统一）
    encrypted_text = entry.get(ENCRYPTED_KEY)
    if not (isinstance(encrypted_text, str) and encrypted_text):
        logger.warning("凭据文件 %s 含非加密格式条目，已拒绝该条目", path)
        return None
    return decrypt_credentials(encrypted_text)


def credential_fingerprint(workspace_id: str, auth_cookie: str) -> str:
    # 凭据指纹：sha256("ws::cookie") 前 12 位 hex（拼接格式对齐 browser_creds.
    # credential_dedup_key，但做 hash 落盘——不存原始 key，P4 安全口径一致）
    return hashlib.sha256(f"{workspace_id}::{auth_cookie}".encode("utf-8")).hexdigest()[
        :12
    ]


def load_switch_log(path: Path) -> dict[str, Any]:
    # 读取账户切换日志（宽容解析）：缺失/坏 JSON/结构不符返回空结构 {"switches": []}
    raw = read_json(path, default=None, use_cache=False)
    if not isinstance(raw, dict):
        return {"switches": []}
    switches = raw.get("switches")
    if not isinstance(switches, list):
        return {"switches": []}
    valid = [s for s in switches if isinstance(s, dict)]
    return {"switches": valid}


def save_switch_log(path: Path, log: dict[str, Any]) -> None:
    # 原子写切换日志（复用 write_json）；调用方保证 log 结构
    write_json(path, log)


def detect_credential_switch(
    credentials_path: Path, log_path: Path, now_ms: int | None = None
) -> bool:
    # 检测账户切换并记录区间（PL001.2）：同指纹持续生效不记；切换/切回时闭合上一
    # 开放区间 + 新增生效区间。返回是否发生了记录。
    #   无凭据文件/解密失败 → False（不记不崩，错误策略：非核心子系统）
    raw = read_credentials_file(credentials_path)
    if not raw:
        return False
    # 当前生效账户 = 凭据文件第一条（多账户数组 PL001.7：首条为主用账户）
    first = raw[0]
    workspace_id = str(first.get(WORKSPACE_ID_KEY, "") or "")
    auth_cookie = str(first.get(AUTH_COOKIE_KEY, "") or "")
    if not workspace_id or not auth_cookie:
        return False
    if now_ms is None:
        # 默认当前时间：毫秒 epoch（对齐 opencode.db time.created 口径）
        now_ms = int(time.time() * 1000)
    fingerprint = credential_fingerprint(workspace_id, auth_cookie)
    log = load_switch_log(log_path)
    switches: list[dict[str, Any]] = log["switches"]
    record = next((s for s in switches if s.get("fingerprint") == fingerprint), None)
    intervals = record.get("intervals") if record is not None else None
    if (
        record is not None
        and isinstance(intervals, list)
        and intervals
        and intervals[-1].get("until") is None
    ):
        # 同一账户持续生效：去抖不重复记
        return False
    # 切换到新账户或切回旧账户：闭合所有生效中的末段（正常至多一条开放段，
    # 防御性全量闭合——历史脏数据自愈）
    for item in switches:
        item_intervals = item.get("intervals")
        if (
            isinstance(item_intervals, list)
            and item_intervals
            and item_intervals[-1].get("until") is None
        ):
            item_intervals[-1]["until"] = now_ms
    new_interval = {"since": now_ms, "until": None}
    if record is not None and isinstance(intervals, list):
        intervals.append(new_interval)
    else:
        switches.append(
            {
                "fingerprint": fingerprint,
                "workspace_id": workspace_id,
                "intervals": [new_interval],
            }
        )
    save_switch_log(log_path, log)
    return True


# ===== modules/credential_store.py 模块说明 =====
# 模块级常量：
#   ENCRYPTED_KEY：加密格式标记（文件 dict 含该键 = DPAPI 加密 blob）
#   WORKSPACE_ID_KEY / AUTH_COOKIE_KEY：凭据 JSON 字段键（workspaceId/authCookie，
#     go_quota 字段兼容集合共用，D4 消除重复字面量）
# 模块级导入：DPAPI 能力来自 utils.windows（WIN32CRYPT_AVAILABLE/dpapi_protect/dpapi_unprotect，
#   4A.2 D2 收敛 win32crypt 降级；写入路径拒绝明文落盘，读取路径返回 None）
# 类型：
#   CredentialEncryptionError：加密业务错误（win32crypt 缺失/DPAPI 失败），中文提示
# 函数：
#   encrypt_credentials(workspace_id, auth_cookie)：
#     输入：workspaceId 与 authCookie 明文
#     输出：base64(DPAPI blob) 字符串（加密后的凭据 JSON）
#     逻辑步骤：WIN32CRYPT_AVAILABLE 缺失抛 CredentialEncryptionError（D3=A 安全优先）→
#       json.dumps 明文凭据 → dpapi_protect（绑定当前 Windows 用户 SID）→ base64
#     设计理由：DPAPI 加密绑定当前 Windows 用户，他人换机/换用户无法解密；
#       加密粒度为整个凭据 JSON（workspaceId + authCookie 一起）
#   decrypt_credentials(encrypted_text)：
#     输入：base64(DPAPI blob) 字符串
#     输出：凭据 dict；win32crypt 缺失/解密失败返回 None（宽容降级不崩溃）
#     逻辑步骤：base64 解码 → CryptUnprotectData → json.loads → 校验 dict
#     设计理由：读取路径宽容降级（坏数据返回 None 由调用方跳过，z.plan 第四章）
#   read_credentials_file(path)：
#     输入：凭据文件路径
#     输出：凭据 dict 列表（单对象旧格式或数组统一规范化；仅加密格式解密；
#       缺失/损坏/坏元素过滤后为空列表）
#     逻辑步骤：json.loads → dict 走单条解密 / list 逐条解密（_decrypt_entry）→
#       非加密条目 WARNING 拒绝（P11 明文口径不变）
#     设计理由：PL001.7 多账户数组兼容；旧单对象文件零迁移照常读
#   _decrypt_entry(entry, path)：单条加密条目解密（缺 ENCRYPTED_KEY 拒绝该条目）
#   credential_fingerprint(workspace_id, auth_cookie)：
#     输入：明文 workspaceId 与 authCookie
#     输出：sha256("ws::cookie") 前 12 位 hex 字符串
#     设计理由：PL001 切换日志只存指纹不存原始 key（P4 口径）；拼接格式对齐
#       browser_creds.credential_dedup_key（同输入空间，语义可互查）
#   load_switch_log(path) / save_switch_log(path, log)：
#     输入/输出：switch_log.json 路径与 {"switches": [...]} 结构 dict
#     逻辑步骤：读宽容（缺失/坏 JSON/结构不符返回空结构）；写走 write_json 原子写
#     设计理由：日志是数据非配置（用户决策 2），独立文件存 credentials_dir 下；
#       坏数据容忍符合 z.plan 第四章宽容解析策略
#   detect_credential_switch(credentials_path, log_path, now_ms=None)：
#     输入：凭据文件路径 + 日志路径 + 可选注入时间戳（毫秒 epoch，测试用）
#     输出：bool 是否发生记录；异常由调用方捕获（本函数不抛）
#     逻辑步骤：读当前凭据 → 指纹 → 比对日志：无凭据返回 False；同指纹末段生效中
#       去抖返回 False；切换/切回时闭合所有开放区间 + 新增生效区间 → 原子保存 True
#     设计理由：每指纹一条记录 + intervals 区间列表（PL001.2 定案），统计切片直接查
#       intervals；程序未运行期间切换漏检属预期硬限制（下次启动才检测）
# 异常处理：读取全路径宽容（返回 None）；加密路径 win32crypt 缺失抛
#   CredentialEncryptionError（UI 状态栏提示，不弹窗）；detect 全路径宽容返回 False
# 关联配置：SWITCH_LOG_FILENAME 存 base.json credentials_dir 同目录；被 modules/
#   go_quota.py 集成（save_dashboard_credentials 加密写入 / read_credentials_file
#   仅读加密格式 / fetch_go_quota 成功后调 detect_credential_switch）
