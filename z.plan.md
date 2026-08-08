# myboard 项目初步方案报告

> 方案日期：2026-08-08
> 项目定位：Windows 桌面应用，展示 OpenCode 用量统计与 OpenCode Go 配额使用情况的信息窗口
> 参考基准：AccelWorld 项目结构（utils/ → config/ → modules/ → ui/ → data/ 单向分层）与 AGENTS.md 代码规范
> 参考仓库：reference/ 目录下 3 个开源项目（详见第五节）
> 状态：本报告仅为初步方案，**尚未编写任何功能代码**

---

## 一、项目目标

在 Windows 上以 Python 实现一个轻量桌面信息窗口（类似 opencode-bar 的 Windows 版），实现两项核心能力：

1. **OpenCode 用量统计**：读取本地 opencode.db（SQLite），统计 tokens（input/output/reasoning/cache）、费用、会话数，支持按天/模型/provider/agent 聚合
2. **OpenCode Go 配额监控**：读取 auth.json 中的 `opencode-go` 凭据，调用 OpenCode dashboard/API 获取 5 小时 / 每周 / 每月使用窗口的配额消耗

界面形态：主窗口 + 系统托盘常驻 + 定时刷新（参考 opencode-bar 的菜单栏模式在 Windows 上的落地）。

---

## 二、技术选型

| 项       | 选型                                | 理由                                                                    |
| -------- | ----------------------------------- | ----------------------------------------------------------------------- |
| 语言     | Python 3.12+                        | 用户熟悉；参考项目 rchardx/opencode-usage、OpenCode-Token 均为 Python   |
| GUI      | PyQt6                               | 与 AccelWorld 一致的技术栈；系统托盘（QSystemTrayIcon）成熟；QSS 样式化 |
| 数据源   | opencode.db（SQLite）+ auth.json    | 全部本地读取，无外部服务                                                |
| 配额接口 | opencode.ai dashboard / models 校验 | 移植 opencode-bar 的请求逻辑（Swift → Python）                          |
| 定价     | models.dev API（缓存本地）          | 参考 opencode-stats/OpenCode-Token 的定价表方案                         |

---

## 三、功能需求

### 3.1 用量统计（本地 SQLite）

| 需求     | 说明                                                                |
| -------- | ------------------------------------------------------------------- |
| 总览指标 | 总 tokens、总费用、会话数、消息数、Prompt 数                        |
| 时间范围 | 全部 / 最近 7 天 / 最近 30 天（参考 oc-stats 三档）                 |
| 分组维度 | 按 model、provider、agent（含子 agent）、日期                       |
| 费用计算 | 优先用数据库已记录的 cost；缺失时用 models.dev 定价估算             |
| 数据导出 | CSV / JSON（参考 OpenCode-Token 的 UTF-8 BOM CSV，便于 Excel 打开） |

### 3.2 Go 配额监控（在线接口）

| 需求     | 说明                                                                                                                                         |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 凭据来源 | auth.json 的 `opencode-go` 条目（key）；dashboard 使用量需 workspaceId + authCookie                                                          |
| 凭据获取 | 环境变量 `OPENCODE_GO_WORKSPACE_ID` / `OPENCODE_GO_AUTH_COOKIE`，或本地 `~/.config/myboard/opencode-go.json`（参考 opencode-bar 多路径探测） |
| key 校验 | 请求 `https://opencode.ai/zen/go/v1/models`（参考 OpenCodeGoProvider.swift:44）                                                              |
| 配额窗口 | 5 小时 / 每周 / 每月三个窗口的已用量与剩余量（百分比展示）                                                                                   |
| 刷新     | 手动 + 定时（如 5 分钟）；网络失败回退缓存数据                                                                                               |

### 3.3 界面（ui/）

- 主窗口：用量总览卡片 + 分组表格 + Go 配额进度条
- 系统托盘：常驻图标，菜单快捷查看 + 退出（退出前保存配置）
- 暗色/亮色主题：QSS 双主题（对齐 AccelWorld ui/themes.py 模式）

---

## 四、目标项目结构（对齐 AccelWorld）

```
mrboard/
├── main.py                      # 入口：GUI 分发 + VERSION 单一来源
├── __init__.py
│
├── modules/                     # 核心业务层（无 GUI 依赖，可独立测试）
│   ├── __init__.py
│   ├── opencode_usage.py        # opencode.db 读取 + tokens/费用聚合（参考 reference/opencode-usage）
│   ├── go_quota.py              # Go 配额接口封装：凭据探测/校验/配额拉取（移植 reference/opencode-bar）
│   └── pricing.py               # models.dev 定价表 + 本地缓存（可放 data/ 或此处）
│
├── config/                      # 配置管理
│   ├── __init__.py
│   └── settings.py              # AppConfig dataclass + pathlib + JSON 存储（~/.config/myboard/）
│
├── ui/                          # GUI 层
│   ├── __init__.py
│   ├── main_window.py           # 主窗口：装配面板 + QTimer 定时刷新
│   ├── system_tray.py           # 托盘：图标、菜单、通知
│   └── themes.py                # LIGHT/DARK 主题 QSS
│
├── utils/                       # 通用工具（无业务依赖）
│   ├── __init__.py
│   ├── logger.py                # 统一日志（控制台+文件 handler）
│   ├── file_utils.py            # pathlib JSON 读写 + 缓存单例
│   └── retry.py                 # 泛型重试（网络请求复用）
│
├── data/                        # 静态数据
│   └── __init__.py              # （后续：模型列表、常见问题对照等）
│
├── reference/                   # 参考项目（git clone，不入版本控制建议见 AGENTS.md）
│   ├── opencode-bar/            # Go 配额监控逻辑参考（Swift）
│   ├── opencode-usage/          # Python SQLite 用量统计参考
│   └── OpenCode-Token/          # Python GUI + 定价/导出参考
│
├── AGENTS.md
├── z.plan.md
├── requirements.txt             # PyQt6（其余按需）
└── .gitignore
```

依赖方向：`ui → modules/config → utils → 标准库`；`data` 无依赖。

---

## 五、参考项目选型与借鉴点

| 项目                      | 语言   | 借鉴内容                                                                                                      | 关键文件                                                                      |
| ------------------------- | ------ | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| opgginc/opencode-bar      | Swift  | **OpenCode Go 配额接口全链路**：auth.json 解析、key 校验、workspaceId/authCookie 多路径探测、5h/周/月窗口计算 | `CopilotMonitor/Providers/OpenCodeGoProvider.swift`、`TokenManager.swift:231` |
| rchardx/opencode-usage    | Python | opencode.db 读取、按天/model/agent/provider 聚合、时间过滤、JSON 导出                                         | 根目录 CLI 源码                                                               |
| Sakura1618/OpenCode-Token | Python | GUI 汇总展示（卡片/图表）、内置价格表 + 本地覆盖、UTF-8 BOM CSV 导出                                          | `opencode_token_app/`                                                         |

---

## 六、待确认问题

1. **Go 配额接口的稳定性**：opencode-bar 依赖 OpenCode dashboard 的会话 cookie（非官方公开 API），后续可能变更，需要做降级（失败时仅显示用量统计）
2. **PyQt6 依赖**：用户机器是否已有 Python 环境 / 是否接受安装 PyQt6（AccelWorld 同款技术栈）
3. **项目名**：英文名 myboard（目录当前为 mrboard，是否重命名目录待确认）
4. **是否需 git init**：当前目录不是 git 仓库，AGENTS.md 中 Git 规范依赖仓库初始化

---

## 七、实施路线图

| 阶段        | 内容                                                | 验证                            |
| ----------- | --------------------------------------------------- | ------------------------------- |
| S1 骨架     | 建包结构 + AGENTS.md + 空模块，安装 PyQt6           | 导入验证                        |
| S2 用量统计 | modules/opencode_usage.py：读 db + 聚合 + 定价估算  | 命令行输出对照 `opencode stats` |
| S3 配额模块 | modules/go_quota.py：凭据探测 + key 校验 + 配额拉取 | 打印 5h/周/月 数值              |
| S4 GUI      | 主窗口 + 托盘 + 主题 + 定时刷新                     | GUI 冒烟（offscreen 验证）      |
| S5 完善     | 配置持久化、CSV/JSON 导出、错误降级                 | 手工验证                        |
