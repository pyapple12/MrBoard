# myboard 项目方案报告

> 方案日期：2026-08-08（V2 修订：2026-08-08，依据 w.study.md 三项目研读结论）
> 项目定位：Windows 桌面应用，展示 OpenCode 用量统计与 OpenCode Go 配额使用情况的信息窗口
> 参考基准：AccelWorld 项目结构（utils/ → config/ → modules/ → ui/ → data/ 单向分层）与 AGENTS.md 代码规范；错误策略采用参考项目的当代模式（见第四章）
> 参考仓库：reference/ 目录下 3 个开源项目（研读笔记见 w.study.md，详见第六节）
> 实施状态：**S1-S6.2 全部实现完成**（验证脚本 195 项断言通过），见第九章审计结果与第十章整改计划

---

## 一、项目目标

在 Windows 上以 Python 实现一个轻量桌面信息窗口（类似 opencode-bar 的 Windows 版），实现两项核心能力：

1. **OpenCode 用量统计**：读取本地 opencode.db（SQLite），统计 tokens（input/output/reasoning/cache）、费用、会话数，支持按天/模型/provider/agent 聚合
2. **OpenCode Go 配额监控**：读取 auth.json 中的 `opencode-go` 凭据，抓取 OpenCode dashboard 获取 5 小时 / 每周 / 每月使用窗口的配额消耗

界面形态：主窗口 + 系统托盘常驻 + 定时刷新（参考 opencode-bar 的菜单栏模式在 Windows 上的落地）。

---

## 二、技术选型

| 项       | 选型                                             | 理由                                                                             |
| -------- | ------------------------------------------------ | -------------------------------------------------------------------------------- |
| 语言     | Python 3.12+                                     | 用户熟悉；参考项目 rchardx/opencode-usage、OpenCode-Token 均为 Python            |
| GUI      | PyQt6                                            | 与 AccelWorld 一致的技术栈；系统托盘（QSystemTrayIcon）成熟；QSS 样式化          |
| 数据源   | opencode.db（SQLite）+ auth.json                 | 全部本地读取，无外部服务                                                         |
| 配额接口 | opencode.ai dashboard（HTML 抓取）+ models 校验  | 移植 opencode-bar 的请求逻辑（Swift → Python）                                   |
| 定价     | 库 cost 优先；缺失时 models.dev 估算（本地缓存） | 与 opencode-usage 一致：库值优先，估算仅作回退（参考 OpenCode-Token 价格表机制） |

---

## 三、功能需求（已实现，细节见代码）

### 3.1 用量统计（modules/opencode_usage.py，已实现 ✅）

- 总览指标（会话/消息/活动跨度天数/tokens/费用）+ 分组维度（日期/模型/provider/agent）
- 只读连接（`mode=ro`）+ `json_extract` + `COALESCE(SUM)` 聚合；时间过滤毫秒半开区间；不依赖 `tokens.total` 存在（兼容新旧格式混合）
- 数据库路径三级探测：`OPENCODE_DB` 环境变量 → `opencode db path` 子进程 → XDG 默认路径
- 费用：库 `$.cost` 优先（recorded），`estimate=True` 时对 cost=0 且 token 非零消息走定价估算，`cost_source` 标注
- 导出（modules/exporter.py ✅）：5 个 CSV（UTF-8 BOM）+ usage.json

### 3.2 Go 配额监控（modules/go_quota.py，已实现 ✅）

- dashboard HTML 抓取（实体反转义 + 正则兼容 `$R[NN]=` 赋值）→ `usagePercent`/`resetInSec` → 5h/周/月三窗口；单窗口缺失仅警告、全缺才报错
- 凭据探测链：环境变量 → 配置文件（key 兼容集合）→ 浏览器（v10 离线解密 + CDP 引导）；候选去重键 `workspaceID::authCookie`，首成功返回
- key 校验（models 接口，data[]/models[]/裸数组三形态）+ 60s 节流 + 缓存兜底 + `GoQuotaError` 四分类（auth/network/decoding/provider）
- 浏览器凭据（modules/browser_creds.py ✅）：v10 DPAPI+AES-GCM 离线解密；**v20（Chrome 127+ app-bound）走 CDP 方案**（独立临时 profile + `Network.getAllCookies`，Chrome 自行解密，跨版本稳定，无需关闭用户浏览器）

### 3.3 界面（ui/，已实现 ✅）

- 主窗口：用量总览卡片 + 分组表格（维度切换零查询）+ Go 配额进度条（颜色分级）+ 凭据缺失引导卡片（一键 CDP 获取 / 手动填写）
- 系统托盘：状态色图标 + 菜单（显示/刷新/退出）；常驻模式（关闭隐藏到托盘）
- 亮暗主题 QSS；后台加载（QThreadPool + 信号回传）+ 启动延迟加载防双加载 + 失败保留旧 view；QTimer 定时刷新
- 配置持久化（config/settings.py ✅）：窗口几何/主题/刷新间隔

---

## 四、错误策略（已落地 AGENTS.md，仍为指南）

> 本项目原有规范只约束"怎么写异常"（不裸 except、指定异常类型）；以下**策略层**约定来自三个参考项目的共同实践，比传统做法更适用于常驻 GUI 应用：

| 策略         | 来源               | 约定                                                                                         |
| ------------ | ------------------ | -------------------------------------------------------------------------------------------- |
| 统一错误类型 | opencode-bar       | 业务错误定义分类异常（如 auth/network/decoding/provider），携带中文消息；UI 只认分类不认细节 |
| 降级不中断   | 三项目共识         | 多数据源/多 provider 任一失败不影响整体；非核心子系统失败仅状态栏提示，不弹窗                |
| 缓存兜底     | opencode-bar       | 网络失败返回上次缓存数据 + 标注来源（`[cached]`），不显示空白                                |
| 宽容解析     | opencode-bar/Token | 数字字段可能是字符串（弹性转换）、坏 JSON 返回空不崩溃、None 语义区分"未记录"与 0            |
| 节流 + 去重  | opencode-bar       | minimumFetchInterval 节流 + in-flight 并发去重，防频繁刷新打爆接口                           |
| 保留旧数据   | OpenCode-Token     | 刷新失败保留旧 view；加载成功后视图才替换                                                    |
| 只读防误写   | opencode-usage     | 数据库一律只读连接（mode=ro），从源头杜绝误写                                                |

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
├── config/                      # 配置（S8 对齐 AccelWorld：静态 json 驱动 + 用户配置分离）
│   ├── settings.py              # 用户配置 AppConfig（项目内 config/user_config.json，可读写）
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
│   ├── logger.py / file_utils.py（含 get_project_root）/ retry.py / convert.py
├── data/                        # 静态数据（预留）
├── reference/                   # 参考项目（不入版本控制）
├── AGENTS.md / z.plan.md / x.progress.md / w.study.md
└── requirements.txt
```

依赖方向：`ui → modules/config → utils → 标准库`；`data` 无依赖。

---

## 六、参考项目选型与借鉴点（详见 w.study.md）

| 项目                      | 语言   | 借鉴内容                                                                                                         | 关键文件                                                                                              |
| ------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| opgginc/opencode-bar      | Swift  | **Go 配额接口全链路**：凭据多路径探测、models Bearer 校验、dashboard HTML 正则抓取、窗口计算、节流/去重/缓存兜底 | `Providers/OpenCodeGoProvider.swift`、`Services/TokenManager.swift`、`Services/ProviderManager.swift` |
| rchardx/opencode-usage    | Python | opencode.db 只读读取、json_extract 聚合 SQL、路径三级探测（子进程优先）、库 cost 优先、dataclass 模型            | `src/opencode_usage/db.py`、`_opencode_cli.py`、`cli.py`                                              |
| Sakura1618/OpenCode-Token | Python | GUI 管道分层 + `*_display` 追加字段、三层价格表合并 + 多币种分桶、UTF-8 BOM CSV、启动线程化 + 保留旧 view        | `opencode_token_app/pricing.py`、`data_loader.py`、`viewmodels.py`、`exporter.py`                     |

---

## 七、待确认问题（状态更新）

1. **Go 配额接口稳定性**：dashboard 为非官方 HTML，已内置降级（窗口缺失容忍/缓存兜底/全缺报错提示 markup 变更）✅ 已处理
2. **浏览器 cookie 探测**：已实现（v10 离线 + v20 CDP 引导，无需关闭用户浏览器）✅ 已处理；Chrome v127+ 全量 v20 时自动探测不可用是已知限制（CDP 引导兜底）
3. **PyQt6 依赖**：已安装并实现 ✅
4. **项目名**：英文名 myboard（目录当前为 mrboard，是否重命名目录待确认）

---

## 八、实施路线图（S1-S6.2 已完成）

| 阶段        | 内容                                                     | 状态 |
| ----------- | -------------------------------------------------------- | ---- |
| S1 骨架     | 包结构 + AGENTS.md + utils 基础 + main.py 入口           | ✅   |
| S2 用量统计 | 只读聚合 + 定价 + 导出（对照 opencode stats 全口径一致） | ✅   |
| S3 配额模块 | 凭据链 + HTML 抓取 + 节流缓存 + 错误分类                 | ✅   |
| S4 GUI      | 主窗口 + 托盘 + 主题 + 后台加载 + 保留旧 view            | ✅   |
| S5 完善     | 配置持久化 + 导出 + 错误策略落地 + README                | ✅   |
| S6 增强     | 浏览器 v10 解密 + v20 CDP 引导 + 凭据配置引导面板        | ✅   |
| S7 审计整改 | 依据第九章审计结果修复 bug 与消重                        | ⏳   |

---

## 九、代码审计结果（2026-08-08，全量 13 文件）

> 依据 AGENTS.md 全量审计；详细问题定位见审计过程记录，以下为整改清单

### 9.1 真实 Bug（优先）

| 编号 | 位置                     | 严重度 | 问题                                                                                                                      |
| ---- | ------------------------ | ------ | ------------------------------------------------------------------------------------------------------------------------- |
| B1   | go_quota.py              | 高     | `retry_call` 重试从未生效：`_http_get` 将网络异常转成 `GoQuotaError`，retry 匹配不到；顺带删除不可达的 HTTPError 兜底分支 |
| B2   | system_tray.py + main.py | 高     | 托盘配额预警未接线：`update_quota_status`/`notify_quota` 零调用点，图标永远绿色                                           |
| B3   | opencode_usage.py        | 高     | `_estimate_missing_costs` 无时间过滤，估算混入范围外消息（费用偏大）                                                      |
| B4   | logger.py + settings.py  | 高     | 日志目录异常可致应用启动崩溃：FileHandler 无异常保护 + settings 未使用 logger 的 import 副作用                            |

### 9.2 中危问题

| 编号 | 位置              | 问题                                                                                                |
| ---- | ----------------- | --------------------------------------------------------------------------------------------------- |
| M1   | main.py           | `_quit_app` 注解引用未顶层导入名字（Python ≤3.13 下 import main 即崩，当前靠 PEP 649 惰性注解）     |
| M2   | main.py           | 函数内延迟 import 违反顶层 import 约定（根因：VERSION 归属 main.py 造成循环依赖，建议抽 constants） |
| M3   | opencode_usage.py | 数字强转违反宽容解析（`int(row[...])` 直接强转，库中字符串数字会崩；缺弹性 int 转换）               |
| M4   | main_window.py    | 配额状态标签颜色切换不生效（`setObjectName` 后 QSS 不重算，需 unpolish/polish）                     |
| M5   | main_window.py    | 引导卡片误导：API key 缺失（CDP 解决不了）时也显示"一键自动获取"                                    |
| M6   | browser_creds.py  | 浏览器探测异常冒泡打断整个凭据链（降级不彻底，`_profile_dirs` 无 try）                              |
| M7   | browser_creds.py  | CDP 9222 端口抢占：误连他人调试实例写入错误凭据                                                     |
| M8   | browser_creds.py  | 死代码：`has_v20_cookies`/`is_chrome_running`/`psutil_process_iter` 未接入引导流程                  |

### 9.3 消重与抽取清单

| 编号 | 位置                      | 建议                                                                                                      |
| ---- | ------------------------- | --------------------------------------------------------------------------------------------------------- |
| D1   | opencode_usage + exporter | token 六字段平铺 ×4 → `flatten_tokens(tokens, prefix)`                                                    |
| D2   | opencode_usage            | SQL 聚合列模板 ×2 → 模块常量 `_TOKEN_SUM_SELECT`                                                          |
| D3   | exporter                  | `_write_json` 与 file_utils 重复且更弱（非原子）→ 复用 `write_json` 删除私有版                            |
| D4   | pricing                   | RateInfo 弹性构建 ×3 → `_rate_from_raw(item, default_source)`                                             |
| D5   | utils 层                  | 弹性数字转换缺位 → `to_int(value, default)`（pricing 有 `_to_float` 缺 int）                              |
| D6   | browser_creds             | "复制库→连接→查询→清理"骨架 ×3 → `_with_copied_db(db_path, query)`（顺带修复句柄泄漏）                    |
| D7   | go_quota                  | `fetch_go_quota` 80 行 → 拆 `_throttled_cache`/`_fetch_usage_with_fallback`/`_build_info`                 |
| D8   | main_window               | `_build_ui` 130 行 → 拆 `_build_cards`/`_build_quota_section`/`_build_guide_card`/`_build_detail_section` |
| D9   | main_window               | `_CdpGuideTask.run` 42 行 → 抽 `_wait_for_login_cookie(deadline)`                                         |
| D10  | themes                    | LIGHT/DARK QSS 60 行重复 → `_build_theme(palette)` 模板化                                                 |
| D11  | go_quota                  | 缓存标注逻辑重复 → `_mark_cached(info, message)`（浅拷贝防污染）                                          |
| D12  | browser_creds             | LOCALAPPDATA 推导 ×3 → `_local_appdata()`                                                                 |
| D13  | themes + system_tray      | 配额阈值 80/50 重复 → `QUOTA_WARN_PERCENT`/`QUOTA_DANGER_PERCENT` 常量                                    |
| D14  | system_tray               | `_quota_status` 死状态变量 → 删除（或接入通知阈值）                                                       |

### 9.4 规范口径

- AGENTS.md"函数定义下方紧跟 `#` 注释"与全项目 docstring 风格冲突（16 个函数仅 docstring）——待决策：补 `#` 注释或修改 AGENTS.md 认可 docstring

### 9.5 整改顺序建议

1. B1-B4 四个 bug → 2. M1-M8 中危 → 3. 消重 D3/D5/D6/D13/D14（改动小收益大）→ 4. AGENTS.md 注释口径决策
