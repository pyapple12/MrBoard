# myboard —— OpenCode 用量与 Go 配额监控

[![Version](https://img.shields.io/badge/Version-ver%200.16-blue.svg)](config/static/base.json)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 项目简介

Windows 桌面信息窗口应用，一站式监控 **OpenCode 用量统计** 与 **OpenCode Go 配额**。读取本地 opencode.db 展示 tokens/费用/会话等用量数据（与 `opencode stats` 全口径一致），抓取 OpenCode 官方 dashboard 展示 5 小时/每周/每月配额使用窗口。常驻系统托盘，配额紧张时图标变红并气泡预警。

## 目录

- [特性](#特性)
- [快速开始](#快速开始)
- [使用说明](#使用说明)
- [凭据配置](#凭据配置)
- [项目结构](#项目结构)
- [依赖](#依赖)
- [常见问题](#常见问题)
- [许可证](#许可证)

## 项目展示

启动应用即可同时查看用量总览卡片、Go 配额进度条与分组明细表格。

| 用量统计                                  | Go 配额                                                |
| ----------------------------------------- | ------------------------------------------------------ |
| 总 tokens / 输入 / 输出 / 缓存率 / 总费用 | 5 小时 / 每周 / 每月使用百分比 + 重置时间 + 剩余量饼图 |

---

## 特性

- **用量统计**：读取本地 opencode.db（只读连接防误写），展示会话/消息/活动天数/tokens/费用，支持按月份、日期、模型、Provider、Agent、会话分组（与 `opencode stats` 输出一致）
- **Go 配额监控**：5 小时/每周/每月三个窗口的已用百分比与重置时间，颜色分级（绿/黄/红），`max` 取最紧窗口
- **配额预警**：最紧窗口 ≥80% 时托盘图标变红 + 系统气泡通知
- **凭据三路径配置**：v10 自动探测（老 Chrome）→ CDP 一键获取（新 Chrome 一键登录）→ 手动填写，凭据缺失时主窗口引导
- **数据导出**：一键导出 8 个 CSV（UTF-8 BOM，Excel 直接打开）+ JSON
- **常驻托盘**：关闭按钮最小化到托盘，双击图标显示窗口，配额状态一眼可见
- **主题切换**：浅色/深色双主题一键切换
- **配置持久化**：自动保存窗口位置、主题、刷新间隔（5 分钟定时刷新）
- **宽容容错**：网络失败回退缓存、接口结构变更降级提示、数字字段弹性解析（不崩溃）

## 快速开始

### 环境要求

- Windows 10/11
- Python 3.12 或更高版本
- pip（Python 包管理器）

### 安装

```bash
# 克隆仓库
git clone git@takechance:pyapple12/MrBoard.git
cd MrBoard

# 创建虚拟环境并安装依赖
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 使用说明

### 图形界面（默认）

```bash
.\.venv\Scripts\python.exe main.py

# 查看版本
.\.venv\Scripts\python.exe main.py --version
```

### 命令行模式

```bash
# 用量统计总览（对照 opencode stats 用）
.\.venv\Scripts\python.exe -m modules.opencode_usage --json

# 按模型分组（最近 7 天）
.\.venv\Scripts\python.exe -m modules.opencode_usage --since 7d --by model

# Go 配额状态
.\.venv\Scripts\python.exe -m modules.go_quota
```

### 命令行参数

| 参数              | 说明                                                                 |
| ----------------- | -------------------------------------------------------------------- |
| `--version`, `-V` | 显示版本信息                                                         |
| `--db`            | 指定 opencode.db 路径（默认自动探测）                                |
| `--since`         | 时间范围：`7d`/`2w`/`3h` 或 ISO 日期                                 |
| `--by`            | 分组维度：`total`/`month`/`day`/`model`/`provider`/`agent`/`session` |
| `--json`          | JSON 输出                                                            |
| `--estimate`      | 对库 cost 缺失的消息做定价估算                                       |

### GUI 操作说明

- **刷新**：点击"刷新"按钮或等待 5 分钟定时自动刷新（刷新失败保留旧数据）
- **总量总览**：明细区"总 token"按钮显示千分位 + 亿单位总量，点击弹出总量明细（会话/消息/天数/tokens 分解）
- **切换维度**：明细区下拉框切换 按月份/按日期/按模型/按 Provider/按 Agent/按会话（会话显示"标题｜项目目录"）
- **列显示开关**：点击"设置"按钮勾选表格列（取消勾选 = 隐藏该列，状态自动保存）
- **配额剩余量**：配额区右侧饼图直观显示最紧窗口剩余量（缓存/错误时显示警告文字）
- **导出数据**：点击"导出"选择目录，生成 CSV + JSON
- **切换主题**：点击"主题"按钮切换浅色/深色
- **配置凭据**：凭据缺失时配额区显示引导卡片——"一键自动获取"或"手动填写"
- **托盘操作**：单击/双击图标显示窗口；托盘菜单"刷新/退出"；关闭窗口最小化到托盘

## 凭据配置

Go 配额用量需要浏览器登录凭据（workspaceId + authCookie）。首次启动未配置时，主窗口显示配置引导，三种方式按可用性选择：

1. **自动探测（Chrome/Edge ≤126）**：自动读取浏览器 cookie 离线解密，零配置
2. **一键自动获取（Chrome v127+，推荐）**：点击"一键自动获取"——程序启动**独立临时 Chrome 窗口**（不影响你正在使用的浏览器），登录 opencode.ai 后自动保存凭据并清理
3. **手动填写**：点击"手动填写"——弹出对话框输入 `workspaceId` 与 `authCookie`，程序自动保存

凭据统一 **DPAPI 加密存储**（绑定当前 Windows 用户，绑定当前用户 SID，文件泄露后他人无法解密使用），保存在项目内 `data/credentials/opencode-go.json`。同 Windows 用户下的恶意软件仍可解密（DPAPI 本限），换机迁移需重新获取凭据。

环境变量方式（高级）：设置 `OPENCODE_GO_WORKSPACE_ID` + `OPENCODE_GO_AUTH_COOKIE` 同样有效（探测链优先级：环境变量 → 配置文件 → 浏览器）。

## 项目结构

```
mrboard/
├── main.py                    # 主入口：GUI 分发，版本号 VERSION 单一来源（base.json version 字段）
├── modules/                   # 业务核心层（无 GUI 依赖，可独立测试）
│   ├── opencode_usage.py      # 用量统计：只读聚合 + 三级路径探测 + CLI
│   ├── go_quota.py            # Go 配额：凭据链 + HTML 抓取 + 节流缓存
│   ├── credential_store.py    # 凭据加密：DPAPI（CryptProtectData）+ 明文兼容
│   ├── pricing.py             # 定价：三级来源合并 + 多币种分桶
│   ├── exporter.py            # 导出：CSV(UTF-8 BOM) + JSON
│   └── browser_creds.py       # 浏览器凭据：v10 DPAPI + v20 CDP 引导
├── config/
│   ├── settings.py            # 用户配置读写（AppConfig，config/user_config.json）
│   └── static/                # 静态配置（只读，json 驱动）
│       ├── static_config.py   # StaticConfig 加载器 + 缓存单例
│       ├── base.json          # 应用参数（版本/间隔/端口/上限等）
│       └── ui.json            # UI 参数（颜色/阈值/表头）
├── ui/                        # GUI 层
│   ├── main_window.py         # 主窗口（卡片/配额/表格/引导 + 后台加载）
│   ├── system_tray.py         # 系统托盘（状态色图标/菜单/预警）
│   └── themes.py              # 浅色/深色主题 QSS（模板 + 调色板）
├── data/                      # 静态数据（预留）+ 运行数据（凭据/日志/价格缓存，已 gitignore）
├── utils/                     # 通用工具
│   ├── logger.py              # 统一日志（控制台 + 轮转文件，项目内 data/logs/myboard.log）
│   ├── file_utils.py          # JSON 读写（原子写）+ 缓存单例
│   ├── retry.py               # 泛型重试函数（指数退避）
│   ├── convert.py             # 弹性类型转换（宽容解析）
│   ├── network.py             # HTTP GET 统一请求 + 可重试异常元组
│   ├── windows.py             # DPAPI 加解密（win32crypt 可选降级）
│   └── sqlite_utils.py        # SQLite 只读连接（URI 转义 + row_factory 统一）
├── requirements.txt           # Python 依赖列表
├── LICENSE                    # MIT 许可证
└── README.md                  # 本文件
```

### 配置参数（config/static/，json 驱动）

可调参数一律外置于静态配置（代码零硬编码），按分类：

| 文件                        | 参数                                                                                                                                                        | 说明                                                |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `config/static/config.json` | 引导映射表                                                                                                                                                  | `base.json` / `ui.json` 分类对应关系                |
| `config/static/base.json`   | `version`                                                                                                                                                   | 版本号唯一来源（ver 0.16）                          |
|                             | `window_width/height`、`refresh_interval_ms`、`min_refresh_interval_ms`、`auto_load_delay_ms`                                                               | 窗口尺寸与刷新调度（含下限防护）                    |
|                             | `min_fetch_interval`、`retry_count`、`retry_delay`                                                                                                          | 配额接口节流与重试                                  |
|                             | `cdp_port`、`history_limit`、`esentutl_timeout`、`cdp_login_wait_seconds`、`cdp_poll_interval`、`cdp_fetch_timeout`、`cdp_wait_timeout`                     | 浏览器/CDP 引导参数与超时                           |
|                             | `export_limit`、`price_cache_ttl`、`models_dev_url`、`http_timeout`、`subprocess_timeout`                                                                   | 导出、定价与网络/子进程超时                         |
|                             | `credentials_dir`、`logs_dir`、`prices_dir`                                                                                                                 | 运行数据目录（项目内，相对路径）                    |
|                             | `table_limit_group`、`table_limit_day`                                                                                                                      | 明细表格行数上限                                    |
|                             | `app_name`、`log_level`、`log_max_bytes`、`log_backup_count`、`db_default_path`                                                                             | 应用名、日志级别/轮转与默认库路径                   |
|                             | `user_config_path`、`default_theme`                                                                                                                         | 用户配置路径与默认值                                |
| `config/static/ui.json`     | `colors.quota_*`（含饼图/托盘色）、`quota_warn_percent`、`quota_danger_percent`                                                                             | 配额颜色与阈值                                      |
|                             | `icon_size`、`notify_duration_ms`、`table_headers`、`pie_size`、`pie_font_size`                                                                             | 托盘图标/通知、表格表头与剩余量饼图                 |
|                             | `layout_*`、`cards_spacing`、`quota_name_width`、`reset_time_format`                                                                                        | 布局与重置时间显示格式                              |
|                             | `themes`、`dimension_labels`、`quota_window_labels`、`guide_*`、`notify_title`、`notify_message_template`、`notify_message_fallback`、`app_subtitle`        | 主题枚举与 UI 文案                                  |
|                             | `unknown_label`、`cost_zero_epsilon`、`total_tokens_unit`、`total_tokens_unit_threshold`、`status_time_format`、`token_abbr_units`、`cli_reset_time_format` | 分组缺失标签、费用容差、单位/K/M/B/G 缩写与时间格式 |
|                             | `status_messages`（含任务错误模板）、`go_quota_error_messages`、`menu_labels`、`tooltips`、`dialog_titles`、`dialog_prompts`                                | 状态栏/错误/菜单/对话框文案                         |
|                             | `palettes.light/dark`                                                                                                                                       | 浅/深主题调色板（含 chunk_ok，25 色）               |

修改 json 后重启应用生效（`get_static_config()` 缓存单例，进程内只读一次）。

## 依赖

| 包名             | 版本     | 说明                                                     |
| ---------------- | -------- | -------------------------------------------------------- |
| PyQt6            | >= 6.6.0 | GUI 框架                                                 |
| pywin32          | >= 306   | Windows DPAPI 凭据加密（CryptProtectData）与 cookie 解密 |
| pycryptodome     | >= 3.20  | AES-GCM cookie 解密                                      |
| websocket-client | >= 1.7   | CDP 调试协议 WebSocket 客户端                            |

## 常见问题

### Q1：Go 配额显示"未配置凭据"，怎么配置？

A：主窗口配额区会显示引导卡片。推荐点击"一键自动获取"——程序会打开一个独立的临时 Chrome 窗口（不影响你正在使用的浏览器），登录 opencode.ai 后自动保存凭据。也可点击"手动填写"在对话框输入凭据，详见[凭据配置](#凭据配置)。

### Q2：Chrome 正在运行时能使用"一键自动获取"吗？

A：能。CDP 引导使用独立临时 profile 启动 Chrome，与正在运行的 Chrome 互不干扰，无需关闭浏览器。

### Q3：我的 Chrome 是最新版，为什么不能自动读取凭据？

A：Chrome v127+ 的新 cookie 使用 App-Bound 加密（v20），无法离线解密（出于安全设计）。请使用"一键自动获取"（CDP 方式，Chrome 自行解密）或手动填写。

### Q4：用量统计的数字和 opencode 官方一致吗？

A：一致。本应用从 opencode.db 读取原始数据，聚合口径与 `opencode stats` 输出对齐（会话数/活动天数/tokens/费用全口径一致）。

### Q5：关闭程序后设置会丢失吗？

A：不会。窗口位置、主题、刷新间隔自动保存到项目内 `config/user_config.json`（随项目走，对齐 AccelWorld 模式），下次启动自动恢复。凭据保存在项目内 `data/credentials/opencode-go.json`（DPAPI 加密，已 gitignore）。

### Q6：数据会发送到第三方吗？

A：不会。用量统计全部本地读取；配额请求直连 opencode.ai 官方服务器；models.dev 仅拉取公开定价表（无凭据）。程序不读取 API key（无 key 链路），仅使用 dashboard 登录会话凭据（workspaceId + authCookie），凭据只在本机流转，日志不打印。

### Q7：配额接口不稳定怎么办？

A：程序已内置降级：接口失败回退显示上次缓存数据（标注"缓存数据"），单窗口解析失败仅警告，全部失败提示"页面结构可能已变更"并保留用量统计功能。

## 维护者

- 作者：[pyapple12](https://github.com/pyapple12)
- 邮箱：takechance_bao@188.com

## 许可证

本项目基于 [MIT 许可证](./LICENSE) 开源。
