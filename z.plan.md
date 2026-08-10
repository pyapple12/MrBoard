# myboard 项目方案报告

> 方案日期：2026-08-08（V2 修订：2026-08-08，依据 w.study.md 三项目研读结论）
> 项目定位：Windows 桌面应用，展示 OpenCode 用量统计与 OpenCode Go 配额使用情况的信息窗口
> 参考基准：AccelWorld 项目结构（utils/ → config/ → modules/ → ui/ → data/ 单向分层）与 AGENTS.md 代码规范；错误策略采用参考项目的当代模式（见第四章）
> 参考仓库：reference/ 目录下 3 个开源项目（研读笔记见 w.study.md）
> 实施状态：**S1-S8 + V0.08（P2-P8）全部实现完成**（全量回归通过，V0.08 已就绪）；当前计划见第十章 P2-P8 整体修改方案（已实施）

---

## 一、项目目标

在 Windows 上以 Python 实现一个轻量桌面信息窗口（类似 opencode-bar 的 Windows 版），两项核心能力：

1. **OpenCode 用量统计**：读取本地 opencode.db（SQLite），统计 tokens/费用/会话数，支持按天/模型/provider/agent 聚合
2. **OpenCode Go 配额监控**：读取 dashboard 凭据（workspaceId + authCookie），抓取 OpenCode dashboard 获取 5 小时/每周/每月使用窗口

界面形态：主窗口 + 系统托盘常驻 + 定时刷新。

---

## 二、技术选型

| 项       | 选型                                             | 理由                                         |
| -------- | ------------------------------------------------ | -------------------------------------------- |
| 语言     | Python 3.12+                                     | 用户熟悉；参考项目同为 Python                |
| GUI      | PyQt6                                            | 与 AccelWorld 一致；托盘成熟；QSS 样式化     |
| 数据源   | opencode.db（SQLite，只读）+ dashboard 凭据      | 全部本地读取 + 官方 dashboard，无外部服务    |
| 配额接口 | opencode.ai dashboard（HTML 抓取）               | 移植 opencode-bar 请求逻辑（Swift → Python） |
| 定价     | 库 cost 优先；缺失时 models.dev 估算（本地缓存） | 库值权威，估算仅作回退                       |

---

## 三、功能架构（已实现，细节见代码注释）

| 模块                   | 职责要点                                                                                            |
| ---------------------- | --------------------------------------------------------------------------------------------------- |
| modules/opencode_usage | 只读聚合（json_extract + COALESCE）、时间过滤毫秒半开区间、路径三级探测、库 cost 优先 + 估算回退    |
| modules/go_quota       | 凭据探测链（env → 配置文件 → 浏览器）+ dashboard 解析 + 节流缓存 + GoQuotaError 分类                |
| modules/browser_creds  | 浏览器凭据：v10 DPAPI+AES-GCM 离线解密；v20（Chrome 127+ app-bound）走 CDP 方案（独立临时 profile） |
| modules/pricing        | 三级价格来源合并（缓存 → models.dev → 内置）+ 多币种分桶                                            |
| modules/exporter       | 5 个 CSV（UTF-8 BOM）+ usage.json                                                                   |
| config/settings        | 用户配置 AppConfig（窗口几何/主题/刷新间隔，项目内 user_config.json）                               |
| config/static          | 静态配置 json 驱动（base/ui + 引导映射表），代码零硬编码；版本号唯一来源 base.json                  |
| ui/main_window         | 卡片 + 配额进度条 + 分组表格 + 凭据引导卡片；QThreadPool 后台加载；失败保留旧 view                  |
| ui/system_tray         | 状态色图标 + 菜单 + ≥80% 预警；常驻模式                                                             |
| ui/themes              | LIGHT/DARK QSS + 配额颜色分级                                                                       |
| utils/                 | logger / file_utils（含 get_project_root）/ retry / convert（无业务依赖）                           |

---

## 四、错误策略（已落地 AGENTS.md，仍为指南）

> 常驻桌面应用主线：**不崩溃、不阻塞、有提示、能自愈**（来自参考项目共同实践）

| 策略         | 约定                                                                                      |
| ------------ | ----------------------------------------------------------------------------------------- |
| 统一错误类型 | 业务错误定义分类异常（auth/network/decoding/provider），携带中文消息；UI 只认分类不认细节 |
| 降级不中断   | 多数据源任一失败不影响整体；非核心子系统失败仅状态栏提示，不弹窗                          |
| 缓存兜底     | 网络失败返回上次缓存 + 标注来源（is_cached + 错误原因），不显示空白                       |
| 宽容解析     | 外部数据数字可能是字符串（弹性转换）、坏 JSON 返回空不崩溃                                |
| 节流 + 去重  | 非官方接口设 minimumFetchInterval 节流 + in-flight 去重                                   |
| 保留旧数据   | 刷新失败保留旧 view，成功后视图才替换                                                     |
| 只读防误写   | opencode.db 一律只读连接（mode=ro）                                                       |

---

## 五、目标项目结构（已按此实现）

```
mrboard/
├── main.py                      # 入口：GUI 分发 + VERSION（base.json version 字段）
├── modules/                     # 业务核心（无 GUI 依赖，可独立测试）
│   ├── opencode_usage.py        # 用量统计：只读聚合 + 三级探测 + CLI
│   ├── go_quota.py              # Go 配额：凭据链 + HTML 抓取 + 节流缓存
│   ├── pricing.py               # 定价：三级来源合并 + 多币种分桶
│   ├── exporter.py              # 导出：CSV(UTF-8 BOM) + JSON
│   └── browser_creds.py         # 浏览器凭据：v10 DPAPI + v20 CDP
├── config/                      # 配置（静态 json 驱动 + 用户配置分离）
│   ├── settings.py              # 用户配置 AppConfig（项目内 config/user_config.json）
│   └── static/                  # 静态配置（只读，json 驱动，代码零硬编码）
│       ├── static_config.py     # StaticConfig 加载器 + get_static_config() 缓存单例
│       ├── config.json          # 引导映射表
│       ├── base.json            # 应用参数（版本/间隔/端口/上限/路径/默认值）
│       └── ui.json              # UI 参数（颜色/阈值/表头）
├── ui/                          # 界面
│   ├── main_window.py           # 主窗口：卡片/配额/表格/引导 + 后台加载
│   ├── system_tray.py           # 托盘：状态色图标 + 菜单
│   └── themes.py                # LIGHT/DARK QSS + 颜色分级
├── utils/                       # 通用工具（无业务依赖）
│   ├── logger.py / file_utils.py / retry.py / convert.py
├── data/                        # 静态数据（预留）+ 运行数据（凭据/日志/价格缓存，路径由 base.json 指定，已 gitignore）
├── reference/                   # 参考项目（不入版本控制）
├── AGENTS.md / z.plan.md / x.progress.md / w.study.md / y.problem.md
└── requirements.txt
```

依赖方向：`ui → modules/config → utils → 标准库`；`data` 无依赖。

---

## 六、参考项目（研读笔记见 w.study.md）

| 项目                      | 语言   | 借鉴内容                                                            | 关键文件                                         |
| ------------------------- | ------ | ------------------------------------------------------------------- | ------------------------------------------------ |
| opgginc/opencode-bar      | Swift  | Go 配额接口全链路：凭据探测、models 校验、dashboard 解析、节流/缓存 | `OpenCodeGoProvider.swift`、`TokenManager.swift` |
| rchardx/opencode-usage    | Python | opencode.db 只读读取、json_extract 聚合、库 cost 优先、dataclass    | `src/opencode_usage/db.py`、`cli.py`             |
| Sakura1618/OpenCode-Token | Python | GUI 分层、三层价格表合并 + 多币种分桶、UTF-8 BOM CSV、保留旧 view   | `pricing.py`、`exporter.py`                      |

---

## 七、待确认问题

1. Go 配额接口为非官方 HTML：已内置降级（窗口缺失容忍/缓存兜底/全缺报错）✅
2. 浏览器 cookie：v10 离线 + v20 CDP 引导 ✅；Chrome v127+ 全量 v20 时自动探测不可用是已知限制（CDP 兜底）
3. PyQt6 依赖 ✅
4. **项目名**：英文名 myboard（目录当前为 mrboard，是否重命名目录待确认）

---

## 八、实施路线图（S1-S8 已完成）

| 阶段    | 内容                                                                    | 状态 |
| ------- | ----------------------------------------------------------------------- | ---- |
| S1 骨架 | 包结构 + AGENTS.md + utils + main.py                                    | ✅   |
| S2 用量 | 只读聚合 + 定价 + 导出（对照 opencode stats 一致）                      | ✅   |
| S3 配额 | 凭据链 + HTML 抓取 + 节流缓存 + 错误分类                                | ✅   |
| S4 GUI  | 主窗口 + 托盘 + 主题 + 后台加载                                         | ✅   |
| S5 完善 | 配置持久化 + 导出 + 错误策略落地 + README                               | ✅   |
| S6 增强 | 浏览器 v10 解密 + v20 CDP 引导 + 凭据引导面板                           | ✅   |
| S7 审计 | 依据第九章清单整改 bug 与消重                                           | ✅   |
| S8 配置 | 静态配置 json 驱动对齐 AccelWorld + VERSION 迁移                        | ✅   |
| S9 CDP  | 真实闭环修复（WebSocket 403/占位 cookie 误判/多账户保存/OpenAuth 识别） | ✅   |
| V0.08   | 第十章 P2-P8 整体修改方案                                               | ⏳   |

---

## 九、代码审计与整改（2026-08-08 首轮 + 2026-08-09 CDP 修复）

- **真实 Bug（B1-B4）**：retry 未生效 / 托盘预警未接线 / 估算混入范围外消息 / 日志目录异常崩溃 —— 全部已修复 ✅
- **中危问题（M1-M8）**：循环依赖、宽容解析、QSS 不重算、引导卡误导、CDP 端口抢占等 —— 全部已整改 ✅
- **消重抽取（D1-D14）**：flatten_tokens、SQL 模板、_with_copied_db、fetch_go_quota 拆分、QSS 模板化等 —— 全部已落地 ✅
- **规范口径**：函数 `#` 注释 + 文件尾说明区已定案（verify_s11 自动检测，docstring 不承担注释职责）
- **CDP 真实闭环（2026-08-09）**：WebSocket 403（--remote-allow-origins=*）、占位 cookie 误判（端到端验证）、多账户 workspace 保存错误、OpenAuth 登录页误报 decoding、API key 失效降级 —— 5 项修复并验证 ✅
- **二次审计**：排期在 V0.08 之后（P10）

---

## 十、P2-P8 整体修改方案（V0.08，2026-08-10 研究定稿）

> 范围：y.problem.md 的 P2-P8 七个问题，合并为一次整体改造；决策已定案（见 10.4）
> **实施状态：✅ 已全部完成（2026-08-10，V0.08）**——实施细节与验证见 x.progress.md V0.08.1-V0.08.8；新增 P11（明文兼容去留）见 y.problem.md

### 10.1 总体判断：三个主题

| 主题       | 问题                                                                            | 关联点                                                     |
| ---------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| 凭据/路径  | P2（目录集中项目内）+ P3（删 API key 链路）+ P4（凭据加密）+ P6（删跨项目探测） | 集中在 go_quota.py / main_window.py / 新加密模块，改动交织 |
| 展示层修正 | P5（重置时间）+ P7（日期倒序）                                                  | 各一行改动                                                 |
| 统计层新增 | P8（月度统计）                                                                  | opencode_usage.py + UI + CLI + 导出                        |

### 10.2 逐项方案

#### P2. 配置与数据目录集中到项目内（不再使用用户目录）

- **原则（用户定案）**：任何配置和目录都不使用用户目录，全部集中在项目目录；每个模块（含 utils）统一用 `get_static_config()` 引用（对齐 AccelWorld：get config 生成 dataclass，各程序引用）
- 现状：`go_quota.py` CREDENTIALS_FILE、`pricing.py` PRICE_CACHE_DIR、`utils/logger.py` LOG_DIR 硬编码 `Path.home()/...`
- 方案：base.json 新增 `credentials_dir` / `logs_dir` / `prices_dir`（相对项目根），代码 `get_project_root() / Path(_SC.base[...])` 拼接：
  - 凭据 → `data/credentials/opencode-go.json`（目录名经用户确认）
  - 日志 → `data/logs/myboard.log`
  - 价格缓存 → `data/prices/prices.json` / `prices.local.json`
- **utils 层读取配置的结论**：utils 层"不读配置"只是 AGENTS.md 的分层约定（防未来循环依赖），非技术限制；当前已核实无环（file_utils/static_config 均不依赖 logger）。定案为**方案 C**：logger.py 顶层 `_SC = get_static_config()` 直接读 logs_dir——原注入方案 A/B（static_config 自动设置 / main.py 显式调用）全部废弃，不再需要 `set_log_dir()`
- 保留的用户目录用法（数据源探测，非本程序配置目录）：浏览器 User Data 探测、OPENCODE_DB / OPENCODE_GO_CONFIG_FILE 环境变量
- 连带：AGENTS.md 分层描述放宽（utils 允许依赖 config.static 读取配置，不依赖其他业务模块）+ 路径约定更新（S8 决策反转）；.gitignore 增加 `data/credentials/` `data/logs/` `data/prices/` 并清理冲突残留（`>>>>>>> origin/main`）；影响文件：base.json、logger.py、pricing.py、go_quota.py、main_window.py（example.json 派生）；verify_s12 同步
- 注意：迁移后旧凭据（`~/.config/myboard/opencode-go.json`）不再自动读取，需重新走"一键自动获取"或手动复制到 `data/credentials/`

#### P3. 删除 API key 链路（程序不接触任何 key）

- 删除：MODELS_URL/AUTH_KEY_FIELDS 常量；find_auth_file/read_auth_json/strip_json_comments/get_opencode_go_key/fetch_model_count 五函数；GoQuotaInfo.model_count/auth_source 字段；no_key 分支；fetch_go_quota 中 key 校验段
- 保留：find_dashboard_credentials（workspaceId + authCookie 链路）、_http_get 的 401/403 分类
- 展示：删"模型数：未知"、CLI 删"API key 来源/模型数"
- 测试：verify_s3 删 auth 解析整组 + models 断言；verify_s4/s5/s7/s8/s9 相关断言删改；README/AGENTS.md 同步

#### P4. 凭据加密存储（DPAPI，新增 modules/credential_store.py）

- 格式：写入 `{"encrypted_v1": "<base64(DPAPI blob(JSON))>"}`，CryptProtectData 绑定当前 Windows 用户；读取识别格式标记解密，明文旧格式兼容读取
- 写入点：save_dashboard_credentials（CDP 引导）+ 手动填写统一走加密
- **决策（2026-08-10）**：手动填写改 GUI 对话框（D2=A，加密写入，删除模板/示例文件逻辑）；win32crypt 缺失时拒绝写入 + 提示（D3=A，安全优先）
- 局限：同 Windows 用户下恶意软件仍可解密；换机迁移需重新获取凭据（可接受）

#### P5. 配额重置时间显示

- `_render_quota` 中 `strftime('%H:%M')` → `'%m-%d %H:%M'`（"重置于 08-12 06:30"）；CLI 已是完整格式

#### P6. 移除跨项目凭据路径探测

- `_dashboard_config_paths` 的 sub 循环仅保留 `("myboard",)`（删 opencode-bar/opencode-quota）；保留 `$OPENCODE_GO_CONFIG_FILE` 与 XDG 变体；消除 WARNING 噪音

#### P7. 按日期倒序

- `by_day()`：`order="label ASC"` → `"label DESC"`；GUI/CLI/导出自动同步；verify_s2 无需改

#### P8. 月度用量统计

- 数据层：新增 `by_month()`——`strftime('%Y-%m', datetime(ts/1000,'unixepoch','localtime'))` 分组，`order="label DESC"`（%Y-%m 字符串排序 = 时间排序）
- 展示层：DIMENSIONS 加 "month"（按月份）、_UsageTask 加载 limit=50；CLI `--by` 加 month
- **决策（2026-08-10）**：连带导出 by_month.csv + usage.json 字段（D4=A，verify_s5 同步为 6 个 CSV）

### 10.3 实施顺序

P6 → P2 → P3 → P4 → P5 → P7 → P8 → 更新 verify（s2/s3/s4/s5/s7/s8/s9/s12）→ 全量回归 → README/AGENTS.md/.gitignore 同步 → 交付代码（提交由用户执行）

### 10.4 用户决策记录（2026-08-10 定案）

| 编号 | 决策项             | 定案                                                                                                                                                                                                                                                                     |
| ---- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1   | 配置/目录位置      | **所有配置与数据目录集中在项目内**（data/credentials、data/logs、data/prices，目录名经用户确认），不再使用用户目录；utils 层（logger）统一 `get_static_config()` 引用（方案 C，原注入方案 A/B 废弃），放宽 AGENTS.md 分层描述；.gitignore 清理冲突残留并增加运行数据忽略 |
| D2   | P4 手动填写        | **A**：GUI 对话框 + 加密写入，删除模板/示例文件逻辑                                                                                                                                                                                                                      |
| D3   | P4 win32crypt 缺失 | **A**：拒绝写入 + 提示（安全优先）                                                                                                                                                                                                                                       |
| D4   | P8 导出 by_month   | **A**：连带导出 by_month.csv（verify_s5 同步为 6 个 CSV）                                                                                                                                                                                                                |
| D5   | 提交规划           | 不适用：提交由用户本人执行，不设提交规划                                                                                                                                                                                                                                 |

### 10.5 风险预判

- P3+P4 同时改动 go_quota 主流程与 6 个 verify 脚本，测试改动量最大
- P8 月份 SQL 需用真实 opencode.db 验证（strftime 本地时区分组）
- 其余均为低风险
