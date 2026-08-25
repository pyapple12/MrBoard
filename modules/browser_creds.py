# 浏览器凭据探测模块：从 Chrome/Edge 提取 opencode.ai 登录凭据（Windows DPAPI + AES-GCM + CDP）

import base64
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None

try:
    import websocket
except ImportError:  # 打包环境缺依赖时降级（CDP 获取不可用，不影响其他路径）
    websocket = None

try:
    import psutil
except ImportError:  # 打包环境缺依赖时降级（进程检测回退 tasklist，C12 顶层导入）
    psutil = None

from config.static.static_config import get_static_config
from utils.file_utils import read_json
from utils.logger import get_logger
from utils.network import http_get
from utils.sqlite_utils import open_readonly
from utils.windows import WIN32CRYPT_AVAILABLE, dpapi_unprotect

logger = get_logger(__name__)

T = TypeVar("T")

OPENCODE_HOST = "opencode.ai"
COOKIE_NAMES = ("auth",)
WORKSPACE_ID_RE = re.compile(r"/workspace/(wrk_[A-Za-z0-9]+)")
# C10：CDP 探测超时与默认登录页（消除魔法值/与 OPENCODE_HOST 重复；
# CDP_PROBE_TIMEOUT 定义在下方配置解包区，A0.2 去重）
DEFAULT_LOGIN_URL = f"https://{OPENCODE_HOST}/"


def credential_dedup_key(workspace_id: str, auth_cookie: str) -> str:
    # 凭据去重键（workspace_id::auth_cookie；go_quota 与浏览器探测共用，D4 消除重复实现）
    return f"{workspace_id}::{auth_cookie}"


# 静态配置解包（S8：参数外置 base.json）
_SC = get_static_config()
HISTORY_LIMIT = int(_SC.base["history_limit"])
CDP_PORT = int(_SC.base["cdp_port"])
ESENTUTL_TIMEOUT = int(_SC.base["esentutl_timeout"])
SUBPROCESS_TIMEOUT = int(_SC.base["subprocess_timeout"])  # 5A.3 C6：子进程超时统一
CDP_FETCH_TIMEOUT = int(
    _SC.base["cdp_fetch_timeout"]
)  # 6A.1 E3：/json 端点与登录会话超时
CDP_WAIT_TIMEOUT = int(_SC.base["cdp_wait_timeout"])  # 6A.1 E3：CDP 就绪/会话轮询总超时
V10_PREFIX = b"v10"
V20_PREFIX = b"v20"
CDP_HOST = "127.0.0.1"
# 5A.3 C6：CDP 探测族固定值（base.json 无对应字段，说明区如实标注；6A.1 E3 修正失实）
CDP_PROBE_TIMEOUT = 2.0  # 单次 /json/version 探测超时
CDP_POLL_DELAY = 0.5  # wait_cdp_ready 轮询间隔
CDP_PORT_CHECK_TIMEOUT = 1.0  # launch 前端口占用快速探测

# 模块级状态：CDP 引导用的临时 profile 目录（launch 创建，shutdown 清理）
_cdp_profile_dir: Path | None = None
# 模块级状态：v20 提示会话级去重（5A.1 E1：首次探测到才提示，防刷新/多 profile 刷屏）
_v20_warned = False


@dataclass
class BrowserCredential:
    # 浏览器探测到的凭据候选：workspace_id + auth_cookie + 来源标注

    workspace_id: str
    auth_cookie: str
    source: str


# D0.8：凭据探测结果短 TTL 缓存（刷新高频场景避免每轮复制多 profile 库 + DPAPI 解密）
_creds_cache: list[BrowserCredential] | None = None
_creds_cache_at: float = 0.0
# E2.2：TTL 走 base.json（观察项提升：避免修复规格自造硬编码）
CREDS_CACHE_TTL = float(_SC.base["credentials_ttl"])


def find_browser_credentials() -> list[BrowserCredential]:
    # 主入口：遍历 Chrome/Edge × profile，组合 workspaceID 与 auth cookie 候选
    # （D0.8：TTL 内直接返回缓存，避免高频刷新重复全量探测）
    global _creds_cache, _creds_cache_at
    if _creds_cache is not None and time.time() - _creds_cache_at < CREDS_CACHE_TTL:
        return _creds_cache
    if not WIN32CRYPT_AVAILABLE or AES is None:
        # E3.3：缺库也写空缓存——否则每次刷新重复 warning（TTL 对该场景失效，
        # 与 E2.2 配置化配套；对 credential_store 的 6A.2 D6 降级策略看齐）
        logger.warning("缺少 pywin32/pycryptodome，跳过浏览器凭据探测")
        _creds_cache = []
        _creds_cache_at = time.time()
        return []
    result: list[BrowserCredential] = []
    seen: set[str] = set()
    for browser_name, user_data in _browser_user_data_dirs():
        try:
            aes_key = _load_aes_key(user_data / "Local State")
            if aes_key is None:
                continue
            for profile_dir in _profile_dirs(user_data):
                cookies = _read_auth_cookies(
                    profile_dir / "Network" / "Cookies", aes_key
                )
                workspace_ids = read_workspace_ids(profile_dir / "History")
                if not cookies or not workspace_ids:
                    continue
                source = f"{browser_name}:{profile_dir.name}"
                for workspace_id in workspace_ids:
                    for cookie in cookies:
                        key = credential_dedup_key(workspace_id, cookie)
                        if key in seen:
                            continue
                        seen.add(key)
                        result.append(BrowserCredential(workspace_id, cookie, source))
        except Exception as exc:
            # 单浏览器异常不冒泡打断整个凭据链（降级不中断策略）
            logger.warning("浏览器 %s 凭据探测失败：%s", browser_name, exc)
    _creds_cache = result
    _creds_cache_at = time.time()
    return result


def _local_appdata() -> Path:
    # LOCALAPPDATA 目录（带默认值推导，多处路径构造共用）
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))


def _browser_user_data_dirs() -> list[tuple[str, Path]]:
    # 返回浏览器名与 User Data 目录（Chrome/Edge，Windows 标准路径；Chrome 项复用单点，R11）
    local_appdata = _local_appdata()
    return [
        ("Chrome", chrome_user_data_dir()),
        ("Edge", local_appdata / "Microsoft" / "Edge" / "User Data"),
    ]


def _profile_dirs(user_data: Path) -> list[Path]:
    # 枚举 profile 目录：Default + Profile*（按名称排序，Default 优先；目录不可读返回空）
    profiles = [user_data / "Default"]
    try:
        profiles.extend(
            sorted(
                d
                for d in user_data.iterdir()
                if d.is_dir() and d.name.startswith("Profile")
            )
        )
    except OSError as exc:
        # 目录无权限等异常不冒泡（降级不中断策略）
        logger.warning("枚举 profile 目录失败（%s）：%s", user_data, exc)
    return [p for p in profiles if p.is_dir()]


def _read_local_state_json(local_state_path: Path) -> dict[str, Any] | None:
    # 读取浏览器 Local State JSON（复用 read_json 宽容解析：缺失/损坏/非 dict 返回 None）
    raw = read_json(local_state_path, default=None, use_cache=False)
    return raw if isinstance(raw, dict) else None


def _load_aes_key(local_state_path: Path) -> bytes | None:
    # 从 Local State 提取 AES key：base64 解码 encrypted_key（去 DPAPI 前缀）后 DPAPI 解密
    if not WIN32CRYPT_AVAILABLE:
        return None
    local_state = _read_local_state_json(local_state_path)
    if not local_state:
        return None
    # A0.1：os_crypt 可能为 truthy 非 dict（Local State 损坏形态），isinstance 兜底防 AttributeError
    os_crypt = local_state.get("os_crypt")
    if not isinstance(os_crypt, dict):
        return None
    try:
        encrypted_key_b64 = os_crypt.get("encrypted_key")
        if not isinstance(encrypted_key_b64, str) or not encrypted_key_b64.startswith(
            "DPAPI"
        ):
            return None
        encrypted_key = base64.b64decode(encrypted_key_b64[5:])
        aes_key = dpapi_unprotect(encrypted_key)
        if aes_key is None:
            return None
        return aes_key
    except (ValueError, TypeError) as exc:
        logger.warning("提取浏览器 AES key 失败（%s）：%s", local_state_path, exc)
        return None


def _read_auth_cookies_query(
    conn: sqlite3.Connection, aes_key: bytes
) -> tuple[list[str], bool]:
    # 查询并解密 opencode.ai 的 auth cookie（返回 cookie 列表与是否含 v20；C4 提取模块级）
    rows = conn.execute(
        # A0.3：Chrome domain cookie 的 host_key 常带前导点（.opencode.ai），
        # 两种形态都查（上层按 workspace_id::cookie 去重，无重复风险）
        "SELECT name, encrypted_value FROM cookies WHERE host_key IN (?, ?)",
        (OPENCODE_HOST, f".{OPENCODE_HOST}"),
    ).fetchall()
    result: list[str] = []
    has_v20 = False
    for row in rows:
        if row["name"] not in COOKIE_NAMES:
            continue
        encrypted = row["encrypted_value"]
        if encrypted.startswith(V20_PREFIX):
            has_v20 = True
            continue
        value = _decrypt_cookie_value(encrypted, aes_key)
        if value:
            result.append(value)
    return result, has_v20


def _read_auth_cookies(cookie_db_path: Path, aes_key: bytes) -> list[str]:
    # 读取 opencode.ai 的 auth cookie 并解密（v10 解密 / v20 跳过；
    # v20 提示每进程会话仅一次防多 profile 多 cookie 刷屏，E10/E1）
    global _v20_warned
    result, has_v20 = _with_copied_db(
        cookie_db_path, _read_auth_cookies_query, aes_key
    ) or ([], False)
    if has_v20 and not _v20_warned:
        _v20_warned = True
        logger.warning(
            "检测到 Chrome v127+ app-bound 加密 cookie（v20），"
            "暂不支持自动解密，请手动配置凭据（见配置引导）"
        )
    return result


def _decrypt_cookie_value(encrypted_value: bytes, aes_key: bytes) -> str | None:
    # 解密 cookie 值：v10（AES-GCM + DPAPI key）；v20 返回 None（提示已上移到 _read_auth_cookies）
    if AES is None:
        return None
    if encrypted_value.startswith(V10_PREFIX):
        data = encrypted_value[3:]
        try:
            cipher = AES.new(aes_key, AES.MODE_GCM, nonce=data[:12])
            plaintext = cipher.decrypt_and_verify(data[12:-16], data[-16:])
            return plaintext.decode("utf-8", errors="replace")
        except ValueError as exc:
            logger.warning("cookie 解密校验失败：%s", exc)
            return None
    return None


def _workspace_ids_query(conn: sqlite3.Connection) -> list[str]:
    # 查询 History 中的 workspace 链接并正则提取 workspaceID（去重，limit 200；C4 提取模块级）
    rows = conn.execute(
        "SELECT url FROM urls WHERE url LIKE ? LIMIT ?",
        (f"%{OPENCODE_HOST}/workspace/%", HISTORY_LIMIT),
    ).fetchall()
    workspace_ids: list[str] = []
    for row in rows:
        match = WORKSPACE_ID_RE.search(row["url"] or "")
        if match and match.group(1) not in workspace_ids:
            workspace_ids.append(match.group(1))
    return workspace_ids


def read_workspace_ids(history_db_path: Path) -> list[str]:
    # 从 History 数据库的浏览记录正则提取 workspaceID（去重，limit 200；对外公开 R13；
    # v10 离线探测路径专用——CDP 引导已改从登录后页面 URL 提取，5A.1 E4 改案）
    return _with_copied_db(history_db_path, _workspace_ids_query) or []


def _with_copied_db(
    db_path: Path, query: Callable[..., T], *query_args: Any
) -> T | None:
    # 复制库到临时目录执行查询（自动连接/关闭/清理；复制失败或查询异常返回 None；
    # *query_args 透传查询函数参数，C4 支持模块级查询函数）
    copy_path = _safe_copy_db(db_path)
    if copy_path is None:
        return None
    try:
        # URI 转义与只读连接统一在 utils（6A.3 R1；临时目录名可能含 #/?）
        conn = open_readonly(copy_path)
        try:
            return query(conn, *query_args)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logger.warning("查询浏览器数据库失败（%s）：%s", db_path, exc)
        return None
    finally:
        shutil.rmtree(copy_path.parent, ignore_errors=True)


def _safe_copy_db(db_path: Path) -> Path | None:
    # 复制 SQLite 库到临时文件（浏览器运行中文件被独占锁定时降级返回 None；
    # 全部失败路径清理临时目录，防泄漏 H8）
    if not db_path.is_file():
        return None
    tmp_dir = Path(tempfile.mkdtemp(prefix="myboard_browser_"))
    copy_path = tmp_dir / db_path.name
    success = False
    try:
        try:
            shutil.copy2(db_path, copy_path)
            success = True
            return copy_path
        except OSError as exc:
            logger.warning("浏览器数据库被锁定（%s），尝试 esentutl：%s", db_path, exc)
            try:
                result = subprocess.run(
                    ["esentutl.exe", "/y", str(db_path), "/d", str(copy_path)],
                    capture_output=True,
                    text=True,
                    timeout=ESENTUTL_TIMEOUT,
                    # H0.7：无控制台环境不闪黑窗（非 Windows 无此属性，getattr 兜底）
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode == 0 and copy_path.is_file():
                    success = True
                    return copy_path
            except (OSError, subprocess.TimeoutExpired) as exc2:
                logger.warning("esentutl 兜底失败：%s", exc2)
            logger.warning(
                "浏览器数据库被独占锁定且无法备份（%s）：请关闭浏览器后重试",
                db_path,
            )
            return None
    finally:
        if not success:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def has_v20_cookies(user_data: Path | None = None) -> bool:
    # 检测 Chrome/Edge 是否为 v20（app-bound）环境：优先查 Local State 的
    # app_bound_encrypted_key 标记，缺失时回退扫描 cookie 库 v20 前缀
    # （B0.1：None 时遍历双浏览器任一命中即 True，消除 Edge-only 用户误判；
    #   显式传目录时保持单浏览器判定语义）
    if user_data is not None:
        return _has_v20_in_user_data(user_data)
    return any(_has_v20_in_user_data(ud) for _, ud in _browser_user_data_dirs())


def _has_v20_in_user_data(user_data: Path) -> bool:
    # 单用户数据目录的 v20 检测（Local State 标记优先，cookie 库扫描回退）
    if not user_data.is_dir():
        return False
    local_state = _read_local_state_json(user_data / "Local State")
    # A0.1：os_crypt 可能为 truthy 非 dict（Local State 损坏形态），isinstance 兜底防 AttributeError
    os_crypt = local_state.get("os_crypt") if local_state else None
    if isinstance(os_crypt, dict) and os_crypt.get("app_bound_encrypted_key"):
        return True
    return _scan_cookie_db_for_v20(user_data)


def _scan_v20_query(conn: sqlite3.Connection) -> bool:
    # 查询单库是否存在 v20 前缀条目（C4 提取模块级）
    row = conn.execute(
        "SELECT 1 FROM cookies WHERE CAST(substr(encrypted_value, 1, 3) AS TEXT) = 'v20'"
        " LIMIT 1"
    ).fetchone()
    return row is not None


def _scan_cookie_db_for_v20(user_data: Path) -> bool:
    # 扫描各 profile cookie 库是否存在 v20 条目（v10 老浏览器回退检测）
    for profile_dir in _profile_dirs(user_data):
        if _with_copied_db(profile_dir / "Network" / "Cookies", _scan_v20_query):
            return True
    return False


def is_chrome_running() -> bool:
    # 检测 Chrome 进程是否在运行（CDP 引导前必须关闭，单例模式下调试参数不生效）
    try:
        return any(
            proc.name().lower() == "chrome.exe" for proc in psutil_process_iter()
        )
    except Exception:
        return False


def launch_chrome_debug(
    port: int = CDP_PORT, login_url: str = DEFAULT_LOGIN_URL
) -> subprocess.Popen | None:
    # 以远程调试模式启动 Chrome（独立临时 profile，全新环境需重新登录，
    # --restore-last-session 对空 profile 无效已移除，M16）
    if wait_cdp_ready(port=port, timeout=CDP_PORT_CHECK_TIMEOUT):
        logger.warning("CDP 端口 %d 已被占用（可能已有调试实例），放弃启动", port)
        return None
    global _cdp_profile_dir
    if _cdp_profile_dir is None:
        _cdp_profile_dir = Path(tempfile.mkdtemp(prefix="myboard_cdp_"))
    executable = _chrome_executable()
    if executable is None:
        logger.warning("未找到 Chrome 可执行文件，无法启动调试模式")
        # 6A.1 E4：mkdtemp 后失败提前 return 前清理临时目录（防泄漏残留复用）
        shutil.rmtree(_cdp_profile_dir, ignore_errors=True)
        _cdp_profile_dir = None
        return None
    try:
        proc = subprocess.Popen(
            [
                str(executable),
                f"--remote-debugging-port={port}",
                f"--user-data-dir={_cdp_profile_dir}",
                # Chrome 137+ 校验 WebSocket Origin，不加则 CDP 连接 403 被拒
                "--remote-allow-origins=*",
                login_url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(
            "Chrome 调试模式已启动（pid=%s，临时 profile=%s）",
            proc.pid,
            _cdp_profile_dir,
        )
        return proc
    except OSError as exc:
        logger.warning("启动 Chrome 调试模式失败：%s", exc)
        # B0.4：Popen 启动失败同样清理临时目录（与 executable-None 分支对称，6A.1 E4 漏改）
        shutil.rmtree(_cdp_profile_dir, ignore_errors=True)
        _cdp_profile_dir = None
        return None


def wait_cdp_ready(port: int = CDP_PORT, timeout: float = CDP_WAIT_TIMEOUT) -> bool:
    # 轮询 CDP 端点直到就绪（Chrome 启动后调试端口开放）
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            http_get(
                f"http://{CDP_HOST}:{port}/json/version", timeout=CDP_PROBE_TIMEOUT
            )
            return True
        except (OSError, urllib.error.URLError, TimeoutError):
            time.sleep(CDP_POLL_DELAY)
    return False


def fetch_login_state_via_cdp(
    port: int = CDP_PORT, timeout: float = CDP_WAIT_TIMEOUT
) -> tuple[str | None, str | None]:
    # 通过 CDP 一次会话获取登录态 (auth cookie, workspaceID)：
    # Network.getAllCookies 拿 cookie + Runtime.evaluate 读当前页面 URL 提取 workspaceID；
    # workspaceID 来自登录后页面 URL 而非浏览历史（5A.1 E4 改案），
    # 不依赖用户真实 Chrome 的 profile 与历史记录
    if websocket is None:
        logger.warning("缺少 websocket-client，无法使用 CDP 获取凭据")
        return None, None
    try:
        targets = json.loads(
            http_get(
                f"http://{CDP_HOST}:{port}/json", timeout=CDP_FETCH_TIMEOUT
            ).decode("utf-8")
        )
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("连接 CDP 端点失败：%s", exc)
        return None, None
    if not isinstance(targets, list):
        # E11：端点返回非列表结构时提前退出（防迭代非 dict 抛 AttributeError 逃逸）
        logger.warning("CDP 端点返回异常结构（非列表）")
        return None, None
    page = next(
        (
            t
            for t in targets
            if isinstance(t, dict)
            and t.get("type") == "page"
            and t.get("webSocketDebuggerUrl")
        ),
        None,
    )
    if page is None:
        logger.warning("CDP 未找到可用的页面 target")
        return None, None
    try:
        ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=timeout)
        try:
            ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
            cookie_response = json.loads(ws.recv())
            ws.send(
                json.dumps(
                    {
                        "id": 2,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": "location.href",
                            "returnByValue": True,
                        },
                    }
                )
            )
            url_response = json.loads(ws.recv())
        finally:
            ws.close()
    except Exception as exc:
        logger.warning("CDP 会话失败：%s", exc)
        return None, None
    # A0.16/K1.3：响应体 isinstance 校验（合法 JSON 非 dict 时 .get() 会抛
    # AttributeError 逃逸本层——与 E11 targets 非列表同型，宽容返回不外溢）
    if not isinstance(cookie_response, dict) or not isinstance(url_response, dict):
        logger.warning("CDP 响应结构异常（非 dict），放弃本轮解析")
        return None, None
    auth_cookie = None
    # A017/L1.5：链式取值深度防御——result 键值为 null 时默认 {} 不生效，
    # (x or {}) 取值式 + 元素 isinstance 过滤杜绝 AttributeError/TypeError
    result_obj = cookie_response.get("result") or {}
    cookies = result_obj.get("cookies") or []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        if cookie.get("name") in COOKIE_NAMES and OPENCODE_HOST in (
            cookie.get("domain") or ""
        ):
            value = cookie.get("value")
            if isinstance(value, str) and value:
                auth_cookie = value
                break
    workspace_id = None
    url_result = url_response.get("result") or {}
    inner_result = url_result.get("result") or {}
    page_url = inner_result.get("value")
    if isinstance(page_url, str):
        match = WORKSPACE_ID_RE.search(page_url)
        if match:
            workspace_id = match.group(1)
    if auth_cookie is None:
        logger.warning(
            "CDP 未找到 opencode.ai 的 auth cookie（请确认已登录 opencode.ai）"
        )
    elif workspace_id is None:
        logger.warning(
            "已获取 cookie 但当前页面尚未跳转到 workspace（等待页面跳转后重试）"
        )
    return auth_cookie, workspace_id


def shutdown_chrome_debug(proc: subprocess.Popen | None) -> None:
    # 关闭调试模式启动的 Chrome 实例并清理临时 profile（用户后续自行正常启动）
    global _cdp_profile_dir
    if proc is not None:
        try:
            proc.terminate()
            proc.wait(timeout=SUBPROCESS_TIMEOUT)
            logger.info("Chrome 调试实例已关闭")
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("关闭 Chrome 调试实例失败：%s", exc)
    if _cdp_profile_dir is not None:
        # rmtree(ignore_errors=True) 不抛异常，无需 try/except（C6）
        shutil.rmtree(_cdp_profile_dir, ignore_errors=True)
        _cdp_profile_dir = None


def _chrome_executable() -> Path | None:
    # 定位 chrome.exe（Program Files / Program Files (x86) / LOCALAPPDATA 三路径）
    local_appdata = _local_appdata()
    program_files = Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
    program_files_x86 = Path(
        os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")
    )
    candidates = [
        program_files / "Google" / "Chrome" / "Application" / "chrome.exe",
        program_files_x86 / "Google" / "Chrome" / "Application" / "chrome.exe",
        local_appdata / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def chrome_user_data_dir() -> Path:
    # Chrome User Data 目录（保留登录态；对外公开，供 main_window 调用，R13）
    local_appdata = _local_appdata()
    return local_appdata / "Google" / "Chrome" / "User Data"


class _TaskProcess:
    # tasklist 输出的最小进程包装（仅暴露 name；C3 从函数内提为模块级）

    def __init__(self, name: str) -> None:
        # 初始化进程名
        self._name = name

    def name(self) -> str:
        # 返回进程名
        return self._name


def psutil_process_iter() -> list[Any]:
    # 遍历进程列表（psutil 可用时用之，否则回退 tasklist 解析，均失败返回空）
    if psutil is not None:
        return list(psutil.process_iter(["name"]))
    try:
        output = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            # H0.7：无控制台环境不闪黑窗（非 Windows 无此属性，getattr 兜底）
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        return [
            _TaskProcess(line.split('","')[0].strip('"'))
            for line in output.splitlines()
            if line.strip()
        ]
    except (OSError, subprocess.TimeoutExpired):
        return []


# ===== modules/browser_creds.py 模块说明 =====
# 模块级常量：
#   OPENCODE_HOST / COOKIE_NAMES：目标域名与 cookie 名（auth）
#   WORKSPACE_ID_RE：历史 URL 提取 workspaceID 的正则（wrk_ 前缀）
#   HISTORY_LIMIT：历史记录查询上限（参考 opencode-bar limit 200）
#   V10_PREFIX / V20_PREFIX：cookie 加密版本前缀
#   CDP_HOST / CDP_PORT：Chrome 远程调试端点（仅引导流程临时开放）
#   ESENTUTL_TIMEOUT / SUBPROCESS_TIMEOUT / CDP_FETCH_TIMEOUT / CDP_WAIT_TIMEOUT /
#     CDP_PROBE_TIMEOUT / CDP_POLL_DELAY / CDP_PORT_CHECK_TIMEOUT / DEFAULT_LOGIN_URL：
#     esentutl 超时、子进程超时、CDP 会话/就绪超时（base.json cdp_fetch/wait_timeout 驱动）、
#     探测族固定值（3 个，base.json 无对应字段）、默认登录页（C14 补列，6A.1 E3 修正失实）
# 模块级变量：_cdp_profile_dir——CDP 引导临时 profile（launch 创建，shutdown 清理）；
#   _v20_warned——v20 提示会话级去重标志（5A.1 E1：首测才提示）；
#   _creds_cache/_creds_cache_at/CREDS_CACHE_TTL——凭据探测短 TTL 缓存（D0.8 引入，
#   E3.7 补列；TTL 走 base.json credentials_ttl，E2.2）
# 模块级导入：AES/websocket/psutil 缺失时降级为 None；DPAPI 能力来自 utils.windows
#   （WIN32CRYPT_AVAILABLE/dpapi_unprotect，4A.2 D2 收敛 win32crypt 降级）
# 类型：BrowserCredential（workspace_id + auth_cookie + 来源标注）、
#   _TaskProcess（tasklist 输出的最小进程包装，C3 提为模块级）
# 函数：
#   credential_dedup_key()：凭据去重键（workspace_id::auth_cookie，D4 共享）
#   find_browser_credentials()：主入口——遍历 Chrome/Edge × profile，
#     AES key 提取 → cookie 解密 → 历史提取 workspaceID → 笛卡尔组合候选（去重）；
#     仅覆盖 v10（老 Chrome/Edge ≤126），v20 走 CDP 引导（见下）；
#     D0.8 TTL 缓存 + E3.3 缺库分支写空缓存（TTL 对缺库场景同样生效）
#   _local_appdata()：LOCALAPPDATA 目录（带默认值推导，多处路径构造共用）
#   _browser_user_data_dirs()：Chrome/Edge 的 User Data 标准路径
#   _profile_dirs()：Default + Profile* 枚举（Default 优先）
#   _read_local_state_json()：浏览器 Local State 宽容读取（复用 read_json）
#   _load_aes_key()：Local State → os_crypt.encrypted_key（DPAPI 前缀剥离 +
#     base64 解码）→ dpapi_unprotect 得到 AES-256 key
#   _read_auth_cookies_query()：查询并解密 auth cookie（返回列表与是否含 v20，C4 模块级）
#   _read_auth_cookies()：复制库 → 查 opencode.ai 的 auth cookie → 逐条解密；
#     v20 提示每进程会话一次（_v20_warned 去重，E10/E1）
#   _decrypt_cookie_value()：v10 = AES-GCM（nonce 12 + tag 16）；v20 无法离线解密
#     （app-bound encryption），返回 None 由 CDP 路径兜底
#   _workspace_ids_query() / read_workspace_ids()：History.urls 正则提取
#     workspaceID（去重，公开 R13；v10 离线探测路径专用，查询函数 C4 模块级）
#   _with_copied_db()：复制库到临时目录执行查询（*query_args 透传，C4）
#   _safe_copy_db()：复制到临时文件；浏览器运行中独占锁定时尝试 esentutl /y
#     兜底，仍失败则返回 None（降级提示关闭浏览器）
#   has_v20_cookies()：检测库内是否存在 v20 cookie（UI 判断是否走 CDP 引导）
#   _scan_v20_query() / _scan_cookie_db_for_v20()：单库 v20 检测（C4 模块级）
#   is_chrome_running()：Chrome 进程检测（CDP 引导前必须关闭，单例模式下
#     调试参数不生效）
#   launch_chrome_debug()：以 --remote-debugging-port 启动 Chrome（独立临时
#     profile，全新环境需重新登录；--remote-allow-origins=* 防 403）
#   wait_cdp_ready()：轮询 http://{CDP_HOST}:{CDP_PORT}/json/version 直到调试端口就绪
#   fetch_login_state_via_cdp()：CDP 一次会话获取登录态 (auth cookie, workspaceID)——
#     Network.getAllCookies 拿 cookie + Runtime.evaluate 读当前页面 URL 提取 workspaceID；
#     **Chrome 自行解密，v10/v20/v30 通吃、跨版本稳定**（S6.1 调研结论：比 SYSTEM
#     DPAPI 逆向 / DLL 注入更适合产品化）；workspaceID 不依赖浏览历史（5A.1 E4 改案）
#   shutdown_chrome_debug()：终止调试实例（用户后续自行正常启动 Chrome）
#   chrome_user_data_dir()：Chrome User Data 目录（公开入口，R13）
#   _chrome_executable()：chrome.exe 三路径定位
#   psutil_process_iter()：进程遍历（psutil 优先，回退 tasklist 解析）
# 设计理由：零配置体验（目标用户打包分发场景）；v10 离线解密免打扰；
#   v20 CDP 引导（重启 Chrome 调试模式）作为完整兜底；凭据只在本机流转；
#   所有失败路径宽容降级（错误策略：不崩溃不阻塞）
# 异常处理：DPAPI/JSON/SQLite/子进程/WebSocket 异常全部捕获降级；解密失败
#   （坏 key/校验失败）单条跳过不中断
# 关联配置：config/static/base.json（history_limit/cdp_port/esentutl_timeout/subprocess_timeout/
#   cdp_fetch_timeout/cdp_wait_timeout，B3.1 补列；credentials_ttl，E2.2 补列）+
#   LOCALAPPDATA 环境变量；被 modules/go_quota.py
#   的 find_dashboard_credentials 集成
