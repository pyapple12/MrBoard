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
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")

from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import win32crypt
except ImportError:  # 打包环境缺依赖时降级（不阻断 go_quota 主流程）
    win32crypt = None

try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None

try:
    import websocket
except ImportError:  # 打包环境缺依赖时降级（CDP 获取不可用，不影响其他路径）
    websocket = None

OPENCODE_HOST = "opencode.ai"
COOKIE_NAMES = ("auth",)
WORKSPACE_ID_RE = re.compile(r"/workspace/(wrk_[A-Za-z0-9]+)")
HISTORY_LIMIT = 200
V10_PREFIX = b"v10"
V20_PREFIX = b"v20"
CDP_HOST = "127.0.0.1"
CDP_PORT = 9222  # Chrome 远程调试端口（仅引导流程使用，临时开放）

# 模块级状态：CDP 引导用的临时 profile 目录（launch 创建，shutdown 清理）
_cdp_profile_dir: Path | None = None


@dataclass
class BrowserCredential:
    # 浏览器探测到的凭据候选：workspace_id + auth_cookie + 来源标注

    workspace_id: str
    auth_cookie: str
    source: str


def find_browser_credentials() -> list[BrowserCredential]:
    # 主入口：遍历 Chrome/Edge × profile，组合 workspaceID 与 auth cookie 候选
    if win32crypt is None or AES is None:
        logger.warning("缺少 pywin32/pycryptodome，跳过浏览器凭据探测")
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
                workspace_ids = _read_workspace_ids(profile_dir / "History")
                if not cookies or not workspace_ids:
                    continue
                source = f"{browser_name}:{profile_dir.name}"
                for workspace_id in workspace_ids:
                    for cookie in cookies:
                        key = f"{workspace_id}::{cookie}"
                        if key in seen:
                            continue
                        seen.add(key)
                        result.append(BrowserCredential(workspace_id, cookie, source))
        except Exception as exc:
            # 单浏览器异常不冒泡打断整个凭据链（降级不中断策略）
            logger.warning("浏览器 %s 凭据探测失败：%s", browser_name, exc)
    return result


def _local_appdata() -> Path:
    # LOCALAPPDATA 目录（带默认值推导，多处路径构造共用）
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))


def _browser_user_data_dirs() -> list[tuple[str, Path]]:
    # 返回浏览器名与 User Data 目录（Chrome/Edge，Windows 标准路径）
    local_appdata = _local_appdata()
    return [
        ("Chrome", local_appdata / "Google" / "Chrome" / "User Data"),
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


def _load_aes_key(local_state_path: Path) -> bytes | None:
    # 从 Local State 提取 AES key：base64 解码 encrypted_key（去 DPAPI 前缀）后 DPAPI 解密
    if win32crypt is None or not local_state_path.is_file():
        return None
    try:
        local_state = json.loads(local_state_path.read_text(encoding="utf-8"))
        encrypted_key_b64 = local_state.get("os_crypt", {}).get("encrypted_key")
        if not isinstance(encrypted_key_b64, str) or not encrypted_key_b64.startswith(
            "DPAPI"
        ):
            return None
        encrypted_key = base64.b64decode(encrypted_key_b64[5:])
        _, aes_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)
        return aes_key
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("提取浏览器 AES key 失败（%s）：%s", local_state_path, exc)
        return None


def _read_auth_cookies(cookie_db_path: Path, aes_key: bytes) -> list[str]:
    # 读取 opencode.ai 的 auth cookie 并解密（v10 解密 / v20 跳过降级）

    def query(conn: sqlite3.Connection) -> list[str]:
        # 在复制库连接上查询并解密 auth cookie
        rows = conn.execute(
            "SELECT name, encrypted_value FROM cookies WHERE host_key = ?",
            (OPENCODE_HOST,),
        ).fetchall()
        result: list[str] = []
        for row in rows:
            if row["name"] not in COOKIE_NAMES:
                continue
            value = _decrypt_cookie_value(row["encrypted_value"], aes_key)
            if value:
                result.append(value)
        return result

    return _with_copied_db(cookie_db_path, query) or []


def _decrypt_cookie_value(encrypted_value: bytes, aes_key: bytes) -> str | None:
    # 解密 cookie 值：v10（AES-GCM + DPAPI key）；v20 为 app-bound 加密，跳过并提示
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
    if encrypted_value.startswith(V20_PREFIX):
        logger.warning(
            "检测到 Chrome v127+ app-bound 加密 cookie（v20），暂不支持自动解密，"
            "请手动配置凭据（见配置引导）"
        )
        return None
    return None


def _read_workspace_ids(history_db_path: Path) -> list[str]:
    # 从 History 数据库的浏览记录正则提取 workspaceID（去重，limit 200）

    def query(conn: sqlite3.Connection) -> list[str]:
        # 在复制库连接上查询 workspace 链接并正则提取
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

    return _with_copied_db(history_db_path, query) or []


def _with_copied_db(
    db_path: Path, query: Callable[[sqlite3.Connection], T]
) -> T | None:
    # 复制库到临时目录执行查询（自动连接/关闭/清理；复制失败或查询异常返回 None）
    copy_path = _safe_copy_db(db_path)
    if copy_path is None:
        return None
    try:
        conn = sqlite3.connect(f"file:{copy_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            return query(conn)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logger.warning("查询浏览器数据库失败（%s）：%s", db_path, exc)
        return None
    finally:
        shutil.rmtree(copy_path.parent, ignore_errors=True)


def _safe_copy_db(db_path: Path) -> Path | None:
    # 复制 SQLite 库到临时文件（浏览器运行中文件被独占锁定时降级返回 None）
    if not db_path.is_file():
        return None
    tmp_dir = Path(tempfile.mkdtemp(prefix="myboard_browser_"))
    copy_path = tmp_dir / db_path.name
    try:
        shutil.copy2(db_path, copy_path)
        return copy_path
    except OSError as exc:
        logger.warning("浏览器数据库被锁定（%s），尝试 esentutl：%s", db_path, exc)
        try:
            result = subprocess.run(
                ["esentutl.exe", "/y", str(db_path), "/d", str(copy_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and copy_path.is_file():
                return copy_path
        except (OSError, subprocess.TimeoutExpired) as exc2:
            logger.warning("esentutl 兜底失败：%s", exc2)
        logger.warning(
            "浏览器数据库被独占锁定且无法备份（%s）：请关闭浏览器后重试",
            db_path,
        )
        return None


def has_v20_cookies(user_data: Path) -> bool:
    # 检测 Chrome/Edge 是否为 v20（app-bound）环境：优先查 Local State 的
    if not user_data.is_dir():
        return False
    local_state_path = user_data / "Local State"
    try:
        local_state = json.loads(local_state_path.read_text(encoding="utf-8"))
        if local_state.get("os_crypt", {}).get("app_bound_encrypted_key"):
            return True
    except (OSError, json.JSONDecodeError):
        pass
    return _scan_cookie_db_for_v20(user_data)


def _scan_cookie_db_for_v20(user_data: Path) -> bool:
    # 扫描各 profile cookie 库是否存在 v20 条目（v10 老浏览器回退检测）

    def query(conn: sqlite3.Connection) -> bool:
        # 查询单库是否存在 v20 前缀条目
        row = conn.execute(
            "SELECT 1 FROM cookies WHERE CAST(substr(encrypted_value, 1, 3) AS TEXT) = 'v20'"
            " LIMIT 1"
        ).fetchone()
        return row is not None

    for profile_dir in _profile_dirs(user_data):
        if _with_copied_db(profile_dir / "Network" / "Cookies", query):
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
    port: int = CDP_PORT, login_url: str = "https://opencode.ai/"
) -> subprocess.Popen | None:
    # 以远程调试模式启动 Chrome（独立临时 profile：Chrome 136+ 仅非默认
    if wait_cdp_ready(port=port, timeout=1.0):
        logger.warning("CDP 端口 %d 已被占用（可能已有调试实例），放弃启动", port)
        return None
    global _cdp_profile_dir
    if _cdp_profile_dir is None:
        _cdp_profile_dir = Path(tempfile.mkdtemp(prefix="myboard_cdp_"))
    executable = _chrome_executable()
    if executable is None:
        logger.warning("未找到 Chrome 可执行文件，无法启动调试模式")
        return None
    try:
        proc = subprocess.Popen(
            [
                str(executable),
                f"--remote-debugging-port={port}",
                f"--user-data-dir={_cdp_profile_dir}",
                "--restore-last-session",
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
        return None


def wait_cdp_ready(port: int = CDP_PORT, timeout: float = 30.0) -> bool:
    # 轮询 CDP 端点直到就绪（Chrome 启动后调试端口开放）
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://{CDP_HOST}:{port}/json/version", timeout=2
            ) as response:
                if response.status == 200:
                    return True
        except (OSError, urllib.error.URLError):
            time.sleep(0.5)
    return False


def fetch_auth_cookie_via_cdp(
    port: int = CDP_PORT, timeout: float = 30.0
) -> str | None:
    # 通过 CDP 获取 opencode.ai 的 auth cookie 明文（Chrome 自行解密，v10/v20 通吃）
    if websocket is None:
        logger.warning("缺少 websocket-client，无法使用 CDP 获取凭据")
        return None
    try:
        with urllib.request.urlopen(
            f"http://{CDP_HOST}:{port}/json", timeout=5
        ) as response:
            targets = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        logger.warning("连接 CDP 端点失败：%s", exc)
        return None
    page = next(
        (
            t
            for t in targets
            if t.get("type") == "page" and t.get("webSocketDebuggerUrl")
        ),
        None,
    )
    if page is None:
        logger.warning("CDP 未找到可用的页面 target")
        return None
    try:
        ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=timeout)
        try:
            ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
            response = json.loads(ws.recv())
        finally:
            ws.close()
    except Exception as exc:
        logger.warning("CDP 会话失败：%s", exc)
        return None
    cookies = response.get("result", {}).get("cookies", [])
    for cookie in cookies:
        if cookie.get("name") in COOKIE_NAMES and OPENCODE_HOST in cookie.get(
            "domain", ""
        ):
            value = cookie.get("value")
            if isinstance(value, str) and value:
                return value
    logger.warning("CDP 未找到 opencode.ai 的 auth cookie（请确认已登录 opencode.ai）")
    return None


def shutdown_chrome_debug(proc: subprocess.Popen | None) -> None:
    # 关闭调试模式启动的 Chrome 实例并清理临时 profile（用户后续自行正常启动）
    global _cdp_profile_dir
    if proc is not None:
        try:
            proc.terminate()
            proc.wait(timeout=10)
            logger.info("Chrome 调试实例已关闭")
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("关闭 Chrome 调试实例失败：%s", exc)
    if _cdp_profile_dir is not None:
        try:
            shutil.rmtree(_cdp_profile_dir, ignore_errors=True)
        except OSError as exc:
            logger.warning("清理临时 profile 失败：%s", exc)
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


def _chrome_user_data_dir() -> Path:
    # Chrome User Data 目录（与 _browser_user_data_dirs 同路径，保留登录态）
    local_appdata = _local_appdata()
    return local_appdata / "Google" / "Chrome" / "User Data"


def psutil_process_iter() -> list[Any]:
    # 遍历进程列表（psutil 存在时用之，否则回退 tasklist 解析，均失败返回空）
    try:
        import psutil

        return list(psutil.process_iter(["name"]))
    except ImportError:
        try:
            output = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout

            class _TaskProcess:
                # tasklist 输出的最小进程包装（仅暴露 name）

                def __init__(self, name: str) -> None:
                    # 初始化进程名
                    self._name = name

                def name(self) -> str:
                    # 返回进程名
                    return self._name

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
# 模块级导入：win32crypt/AES/websocket 缺失时降级为 None（打包环境不阻断主流程）
# 类型：BrowserCredential（workspace_id + auth_cookie + 来源标注）
# 函数：
#   find_browser_credentials()：主入口——遍历 Chrome/Edge × profile，
#     AES key 提取 → cookie 解密 → 历史提取 workspaceID → 笛卡尔组合候选（去重）；
#     仅覆盖 v10（老 Chrome/Edge ≤126），v20 走 CDP 引导（见下）
#   _browser_user_data_dirs()：Chrome/Edge 的 User Data 标准路径
#   _profile_dirs()：Default + Profile* 枚举（Default 优先）
#   _load_aes_key()：Local State → os_crypt.encrypted_key（DPAPI 前缀剥离 +
#     base64 解码）→ CryptUnprotectData 得到 AES-256 key
#   _read_auth_cookies()：复制库 → 查 opencode.ai 的 auth cookie → 逐条解密
#   _decrypt_cookie_value()：v10 = AES-GCM（nonce 12 + tag 16）；v20 无法离线解密
#     （app-bound encryption），返回 None 由 CDP 路径兜底
#   _read_workspace_ids()：History.urls 正则提取 workspaceID（去重）
#   _safe_copy_db()：复制到临时文件；浏览器运行中独占锁定时尝试 esentutl /y
#     兜底，仍失败则返回 None（降级提示关闭浏览器）
#   has_v20_cookies()：检测库内是否存在 v20 cookie（UI 判断是否走 CDP 引导）
#   is_chrome_running()：Chrome 进程检测（CDP 引导前必须关闭，单例模式下
#     调试参数不生效）
#   launch_chrome_debug()：以 --remote-debugging-port 启动 Chrome（保留登录态
#     与上次会话，--restore-last-session）
#   wait_cdp_ready()：轮询 http://127.0.0.1:9222/json/version 直到调试端口就绪
#   fetch_auth_cookie_via_cdp()：CDP Network.getAllCookies 获取 opencode.ai
#     auth cookie 明文——**Chrome 自行解密，v10/v20/v30 通吃、跨版本稳定**
#     （S6.1 调研结论：比 SYSTEM DPAPI 逆向 / DLL 注入更适合产品化）
#   shutdown_chrome_debug()：终止调试实例（用户后续自行正常启动 Chrome）
#   _chrome_executable()：chrome.exe 三路径定位
#   psutil_process_iter()：进程遍历（psutil 优先，回退 tasklist 解析）
# 设计理由：零配置体验（目标用户打包分发场景）；v10 离线解密免打扰；
#   v20 CDP 引导（重启 Chrome 调试模式）作为完整兜底；凭据只在本机流转；
#   所有失败路径宽容降级（错误策略：不崩溃不阻塞）
# 异常处理：DPAPI/JSON/SQLite/子进程/WebSocket 异常全部捕获降级；解密失败
#   （坏 key/校验失败）单条跳过不中断
# 关联配置：无（路径来自 LOCALAPPDATA 环境变量）；被 modules/go_quota.py
#   的 find_dashboard_credentials 集成
