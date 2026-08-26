# myboard —— OpenCode 用量与 Go 配额监控

[![Version](https://img.shields.io/badge/Version-V0.2.6.1-blue.svg)](config/static/base.json)
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

> **QML 演示版（开发预览，PL008）**：并行孵化的 QML+FluentUI 前端，基于虚拟数据
> （mock_service 三态样例），不接真实业务，用于查看全页面效果与动效/光影/阴影/粒子
> 能力展示。启动命令：
>
> ```powershell
> .\.venv\Scripts\python.exe -c "import ui.qml.launcher as l; l.launch()"
> ```

---

## 特性

- **用量统计**：读取本地 opencode.db（只读连接防误写），展示会话/消息/活动天数/tokens/费用，支持按月份、日期、模型、Provider、Agent、会话分组（与 `opencode stats` 输出一致）
- **Go 配额监控**：5 小时/每周/每月三个窗口的已用百分比与重置时间，颜色分级（绿/黄/红），`max` 取最紧窗口
- **配额预警**：最紧窗口 ≥80% 时托盘图标变红 + 系统气泡通知
- **凭据三路径配置**：v10 自动探测（老 Chrome）→ CDP 一键获取（新 Chrome 一键登录）→ 手动填写，凭据缺失时主窗口引导
- **数据导出**：一键导出 8 个 CSV（UTF-8 BOM，Excel 直接打开）+ JSON
- **常驻托盘**：关闭按钮最小化到托盘，双击图标显示窗口，配额状态一眼可见
- **主题切换**：浅色/深色/控制台/面板四主题一键切换
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
- **导出数据**：点击"导出"选择目录，生成 CSV + JSON（全量数据）
- **切换主题**：明细区"主题"下拉选择 浅色/深色/终端/面板 四主题（切换即保存；终端=深色磷光屏气质、面板=浅色工业线框）
- **配额账户切换**：配额区顶部下拉选择要监控的账户（选谁显示谁的配额，选择自动记忆）；"添加账户"按钮随时引入新账户（一键自动获取或手动填写，添加后自动选中）；用量统计始终为全量整体视图
- **数据与动态页**：第二个页签展示官方动态（GitHub Releases 版本/公告）与数据页统计（热门模型每日用量/Token 成本/缓存比/会话成本/国家分布），首次切换到该页时自动拉取
- **配置凭据**：凭据缺失时配额区显示引导卡片——"一键自动获取"或"手动填写"
- **托盘操作**：单击/双击图标显示窗口；托盘菜单"刷新/退出"；关闭窗口最小化到托盘

## 凭据配置

Go 配额用量需要浏览器登录凭据（workspaceId + authCookie）。首次启动未配置时，主窗口显示配置引导，三种方式按可用性选择：

1. **自动探测（Chrome/Edge ≤126）**：自动读取浏览器 cookie 离线解密，零配置
2. **一键自动获取（Chrome v127+，推荐）**：点击"一键自动获取"——程序启动**独立临时 Chrome 窗口**（不影响你正在使用的浏览器），登录 opencode.ai 后自动保存凭据并清理
3. **手动填写**：点击"手动填写"——弹出对话框输入 `workspaceId` 与 `authCookie`，程序自动保存

凭据统一 **DPAPI 加密存储**（绑定当前 Windows 用户，绑定当前用户 SID，文件泄露后他人无法解密使用），保存在项目内 `data/credentials/opencode-go.json`。同 Windows 用户下的恶意软件仍可解密（DPAPI 本限），换机迁移需重新获取凭据。

**多账户**：手动填写/一键获取新账户时自动追加（同 workspace 覆盖更新），文件为加密数组格式；配额区下拉可切换查看任一已存账户的配额（选择自动记忆）。

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
├── services/                   # 应用服务门面（A017/PL006）：UI 唯一后端入口，纯 Python 零 Qt
│   ├── service.py             # AppService：聚合用量/配额/导出/凭据编排，前端可整体替换
│   └── mock_service.py        # 虚拟数据门面（QML 演示版数据源，normal/error/cached 三态样例）
├── config/
│   ├── settings.py            # 用户配置读写（AppConfig，config/user_config.json）
│   └── static/                # 静态配置（只读，json 驱动）
│       ├── static_config.py   # StaticConfig 加载器 + 缓存单例
│       ├── base.json          # 应用参数（版本/间隔/端口/上限等）
│       └── ui.json            # UI 参数（颜色/阈值/表头）
├── ui/                        # GUI 层（双前端并存：qt6 默认 / qml 演示版）
│   ├── qt6/                   # QtWidgets 前端（默认 GUI，PL008 迁入）
│   │   ├── main_window.py     # 主窗口（卡片/配额/表格/引导 + 后台加载）
│   │   ├── task_runner.py     # 统一后台任务运行器（QThreadPool 封装，A017/PL006）
│   │   ├── system_tray.py     # 系统托盘（状态色图标/菜单/预警）
│   │   ├── theme_loader.py    # 主题加载器：读 qt6/themes/ 资源 + 契约校验（PL007）
│   │   └── themes/            # 主题纯资源文件夹（零 .py；新增主题=新建子文件夹+theme.json）
│   │       ├── _templates/base.qss  # 共享 QSS 结构模板（{色键} 占位符）
│   │       └── light|dark|console|panel/theme.json  # 各主题 display_name + palette
│   └── qml/                   # QML 前端（PL008 虚拟数据演示版：PySide6 + FluentUI）
│       ├── launcher.py        # 数据桥与启动器（context 注入 mock 数据/阈值/文案）
│       ├── main.qml           # FluWindow + FluNavigationView 两页导航
│       ├── UsagePage.qml      # 用量监控页（卡片区 + 配额区 + 饼图 + 粒子）
│       ├── DataPage.qml       # 数据与动态页（用量明细表 + Releases 时间线）
│       ├── theme/             # 单基础主题单例色板（Theme.qml + qmldir）
│       └── effects/           # 动效组件（CardShadow：MultiEffect 阴影/光晕）
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
| `config/static/base.json`   | `version`                                                                                                                                                   | 版本号唯一来源                                      |
|                             | `window_width/height`、`refresh_interval_ms`、`min_refresh_interval_ms`、`max_refresh_interval_ms`、`auto_load_delay_ms`                                    | 窗口尺寸与刷新调度（含上下限防护，H0.1 补列）       |
|                             | `min_fetch_interval`、`retry_count`、`retry_delay`、`credentials_ttl`                                                                                       | 配额接口节流与重试、凭据探测缓存时长                |
|                             | `cdp_port`、`history_limit`、`esentutl_timeout`、`cdp_login_wait_seconds`、`cdp_poll_interval`、`cdp_fetch_timeout`、`cdp_wait_timeout`                     | 浏览器/CDP 引导参数与超时                           |
|                             | `export_limit`、`price_cache_ttl`、`models_dev_url`、`http_timeout`、`subprocess_timeout`                                                                   | 导出、定价与网络/子进程超时                         |
|                             | `data_url`、`gh_releases_api_url`、`gh_releases_rss_url`、`data_fetch_interval_sec`                                                                         | 数据页抓取源与刷新节流（PL002）                     |
|                             | `credentials_dir`、`logs_dir`、`prices_dir`                                                                                                                 | 运行数据目录（项目内，相对路径）                    |
|                             | `table_limit_group`、`table_limit_day`                                                                                                                      | 明细表格行数上限                                    |
|                             | `app_name`、`log_level`、`log_max_bytes`、`log_backup_count`、`db_default_path`                                                                             | 应用名、日志级别/轮转与默认库路径                   |
|                             | `user_config_path`、`default_theme`                                                                                                                         | 用户配置路径与默认值                                |
| `config/static/ui.json`     | `colors.quota_*`（含饼图/托盘色）、`quota_warn_percent`、`quota_danger_percent`                                                                             | 配额颜色与阈值                                      |
|                             | `icon_size`、`notify_duration_ms`、`data_table_headers`、`pie_size`、`pie_font_size`                                                                        | 托盘图标/通知、数据页表格表头与剩余量饼图           |
|                             | `layout_*`、`cards_spacing`、`quota_name_width`、`reset_time_format`                                                                                        | 布局与重置时间显示格式                              |
|                             | `themes`（注册顺序权威）、`dimension_labels`、`quota_window_labels`、`guide_*`、`notify_title`、`notify_message_template`、`app_subtitle`                   | 主题枚举与 UI 文案                                  |
|                             | `unknown_label`、`cost_zero_epsilon`、`total_tokens_unit`、`total_tokens_unit_threshold`、`status_time_format`、`token_abbr_units`、`cli_reset_time_format` | 分组缺失标签、费用容差、单位/K/M/B/G 缩写与时间格式 |
|                             | `status_messages`（含任务错误模板）、`go_quota_error_messages`、`menu_labels`、`tooltips`、`dialog_titles`、`dialog_prompts`                                | 状态栏/错误/菜单/对话框文案                         |
|                             | `table_columns`                                                                                                                                             | 明细表格列元数据                                    |
| `ui/qt6/themes/`            | 各主题 `theme.json`（display_name + palette 约 30 色）、`_templates/base.qss` 共享模板                                                                      | 四主题调色板/显示名/QSS 结构（PL007 资源文件夹化）  |

**自定义主题**：新建 `ui/qt6/themes/<名字>/theme.json`（复制现有主题改色值），并在
`ui.json` 的 `themes` 数组登记主题名，重启即在主题下拉框出现——无需修改任何 `.py`
文件；调整所有主题的样式结构只需编辑 `_templates/base.qss` 一处。

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
