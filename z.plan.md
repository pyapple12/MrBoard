# myboard 项目方案报告

> 方案日期：2026-08-08（V2 修订：2026-08-08，依据 w.study.md 三项目研读结论）
> 项目定位：Windows 桌面应用，展示 OpenCode 用量统计与 OpenCode Go 配额使用情况的信息窗口
> 参考基准：AccelWorld 项目结构（utils/ → config/ → modules/ → ui/ → data/ 单向分层）与 AGENTS.md 代码规范；错误策略采用参考项目的当代模式（见第四章）
> 参考仓库：reference/ 目录下 3 个开源项目（研读笔记见 w.study.md）
> 实施状态：**S1-S8 + V0.08（P2-P8）+ V0.09（UI 改版）+ V0.10（二次审计整改）全部实现完成**（全量回归 596 项断言通过，V0.10 已就绪）；待评估项见 y.problem.md

---

## 观察项豁免定案清单（历轮汇总，2026-08-13 分级定稿）

> 分级规则（2026-08-13 修订）：历轮（A007-A013）参考级观察项经大会战与多轮复核，按确定性分三级——
> ①**永久豁免**：外部约束/设计定案/数据常量/性能可接受/并发理论/外观——后续轮次**不再报告、不再讨论**（除非外部依赖本身变更，如 Chrome 命名规则、opencode.db schema）
> ②**条件豁免**：需验证/理论不可达/数据语义——触发条件变化时重新评估（每项标注触发条件）
> ③**价值权衡**：可修但收益 < 成本——H 批次已消化 10 条，剩余列于此，未来批次按需排期
> 历史归档：A011/A012/A013 的"追加豁免 N 条"段落已并入本清单（附录内不再保留）；H 批次已修复 10 条从豁免移出

### ① 永久豁免（不再讨论）

- **外部约束**：browser_creds --remote-allow-origins=\*（Chrome 137+ 无此参数 CDP 必 403）/ DASHBOARD 请求参数硬编码 / CDP 探测族 3 固定值不入配置
- **数据/数学常量**：BUNDLED_PRICES 数据快照 / COST_COMPARE_DIGITS 浮点容差 / \_EPOCH_MS/\_DAY_MS 数学基准 / $ 硬编码（OpenCode 计费固定 USD）
- **设计定案**：retry 默认值语义分离 / retry 参数类型不校验（内部 API 调用方可控）/ 双份 themes 解析（各防护独立）/ toggle_theme 不即时持久化（退出即存设计）/ logger LOG_LEVEL 静默回退（B2 断言固化）/ convert 下划线字面量（B1 断言固化）/ restoreGeometry 静默回退（宽容策略一致）/ 本地覆盖缺字段按免费估算（B4 说明区记录）/ file_utils 缓存无业务写入方（C1）/ themes QUOTA_COLOR 常量名缩写（指代明确非失实）/ system_tray MENU_LABELS 依赖导入顺序（无可达路径）/ 浏览器: 文案硬编码（单次使用无调参场景）/ logger 注释措辞（字面仍成立）/ 说明区契约列举省略 dialog 组（已校验在位，叙述省略）/ 估算忽略 reasoning token（设计定案，w.study.md 记录，仅估算回退路径）/ 托盘不可用时 notify 无效调用（Qt 静默忽略无副作用）
- **性能可接受**：每 profile 整库复制（一次性引导流程）/ exporter 查询全量驻留（单次导出）/ network 每次 get_static_config（单例查找零 IO）/ ORDER BY 无索引（**外部库只读不可建索引**，仅 CLI 路径毫秒级）/ toggle 每次全量文件 IO（低频非热点）/ system_tray 每次重建 QPixmap（刷新间隔受限）/ \_show_columns_menu 每次 new QMenu（父挂载自动回收）
- **并发理论**：go_quota 模块级缓存无锁（worker 串行）/ static_config 无锁单例（import 期）/ browser_creds 模块级无锁（B0.8 已停定时器）/ ws.recv 不按 id 匹配（未 enable domain）/ sqlite_utils 线程契约（同线程消费）/ 导出无防重入（原子写保完整性）/ 连点启动 N 个 QuotaTask（go_quota 节流兜底）/ go_quota in-flight stage 与 UI 引导卡交互（已核对闭环）
- **外观**：main_window 绘制细节（饼图角度/内缩/截断/内联 QSS）/ system_tray 图标几何（比例）/ paintEvent 无显式 end（Qt 析构自动）/ PIE_FONT_SIZE / 托盘几何
- **2026-08-13 新增定案（profile 正则）**：\_profile_dirs 前缀匹配宽容为**刻意设计**——startswith("Profile") 兼容 Chrome 未来命名（官方命名 "Profile 1" 带空格，69 版起）；精确化收益（消除不可见毫秒级解析）< 规则依赖风险（未来命名变更致漏扫、凭据探测失效）；本机无 Profile 目录为验证盲区；误匹配目录已被单浏览器 try 兜底（无崩溃路径）
- **已修复记账**（历史记录防重复报告）：hidden_columns 非法 id 回写（D0.15）/ go_quota html 局部遮蔽（D0.14）/ parse_time_arg ISO 时区偏移（CLI 自测转文档）/ estimate 全表扫描（D0.11）/ write_json mkstemp 位置（D0.12）/ --version 在 PyQt import 后（D0.13）/ min_ts=0（E0.4）/ CREDS_CACHE_TTL（E2.2）/ refresh 连点（F0.2）/ UsageRow 契约（F0.3）/ UsageSummary 契约（G0.2）/ H0.3 fdopen 泄漏（I3.4 记账，原② 段条目移除）

### ② 条件豁免（触发条件变化时重新评估）

- 窗口销毁 in-flight 信号（触发：Qt 析构自动断连行为变化）
- settings themes 空数组回退（触发：ui.json themes 被手改为空）
- main.py:6 import 场景 argv 误触发（触发：第三方脚本 import main 且 argv 含 -V/--version）
- login_timeout minutes=0（触发：默认配置被手改为 0）
- pricing cost 空 dict 落入 pricing 分支（触发：models.dev schema 变更，B3 数据语义族）
- get_theme 第三主题静默错位（触发：配置合法扩展第三主题）
- \_TOKEN_SUM_SELECT 与字段无静态校验（触发：新增/删除 SQL 聚合列）
- 契约键集与说明区无自动联动（触发：新增 dataclass 字段流程变化）
- 契约块位置打断 dataclass 定义区（触发：新增需要契约的 dataclass）
- 失败路径 pending 不消费（触发：连点+失败场景需求变化）
- 阈值 warn>danger 无大小关系校验（触发：手改配置场景可达评估）
- reset_seconds 无上界（触发：外部 HTML 含 18 位 resetInSec，理论）
- 根键缺失裸 KeyError 家族（触发：全量根键契约化决策，33+ 根键覆盖成本评估）
- CSV 非原子写（触发：导出原子性需求提升评估；豁免条目表述修正为"JSON 原子写"）
- go_quota CLI quota_window_labels 容器无校验（触发：ui.json 键类型契约批次排期）
- colors 键族契约化（触发：全量根键契约化决策同上）
- RETRY_NETWORK_ERRORS HTTPError 语义（触发：调用方分类时序变更——当前已确证安全）

### ③ 价值权衡（未来批次按需排期，决策记录）

- notify 三级兜底链去留（H0.8 契约落地后评估是否删除过度防御链——2026-08-13 待评估，见 y.problem.md P24）
- \_CdpGuideTask 凭据写入不可注入（中成本依赖注入改造，全链路单测收益不确定）
- QUOTA_COLOR 常量名重命名（纯命名洁癖，多处引用 + 说明区联动，收益极低）
- \_TEMPLATE_MAP notify 两键 .get 冗余（契约已保证，删除收益小）/ limit 双兜底冗余 max(1,)（幂等，删除验证成本 > 收益）/ Popen 无 creationflags 注释（纯可读性）/ hidden_columns 双 strip / DEFAULT 不经区间钳制 / ui.json 数值键无类型契约（H0.4 范围限定 base）/ network 默认 UA / sqlite_utils 无自动 close / 内层 except fd 恒真 / base MAX < MIN 双改回退 / logger 说明区未列 system_tray
- exported_at 无时区标记（单机本地查看为主，收益极低）/ \_with_copied_db 异常契约依赖（当前成立 + 外层兜底）/ themes 改字符串逐字符迭代（理论手改）/ hidden_columns None 元素（理论手改，渲染层忽略）/ RotatingFileHandler 值域无校验（类型契约不校验值域）/ round_cost digits 无钳制（内部 API 统一传默认）/ I0.1 错误消息 get 重复调用（仅错误路径零 IO）/ 模块级标志多实例串扰（生产单实例定案）

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
- **消重抽取（D1-D14）**：flatten_tokens、SQL 模板、\_with_copied_db、fetch_go_quota 拆分、QSS 模板化等 —— 全部已落地 ✅
- **规范口径**：函数 `#` 注释 + 文件尾说明区已定案（verify_s11 自动检测，docstring 不承担注释职责）
- **CDP 真实闭环（2026-08-09）**：WebSocket 403（--remote-allow-origins=\*）、占位 cookie 误判（端到端验证）、多账户 workspace 保存错误、OpenAuth 登录页误报 decoding、API key 失效降级 —— 5 项修复并验证 ✅
- **二次审计**：排期在 V0.08 之后（P10）

---

## 十、V0.08 改造完成（P2-P8，2026-08-10 已实施）

> 原 P2-P8 详细方案已随实施落地，本节保留决策要点备查；实施细节与验证见 x.progress.md V0.08；遗留 P1/P9/P10/P11 见 y.problem.md

- **目录集中项目内**：凭据/日志/价格缓存移至 `data/` 下（base.json 的 `credentials_dir`/`logs_dir`/`prices_dir` 驱动），不再使用用户目录；utils 层（logger）允许 `get_static_config()` 引用（方案 C，AGENTS.md 分层放宽）
- **凭据安全**：删除 API key 链路（程序不接触任何 key，仅 dashboard 会话凭据）；凭据 DPAPI 加密存储（新增 `modules/credential_store.py`，`encrypted_v1` 格式 + 明文旧格式兼容读取）；手动填写改 GUI 对话框；win32crypt 缺失拒绝明文落盘
- **展示修正**：配额重置时间"月-日 时:分"；按日期统计由近到远
- **月度统计**：`by_month()` 分组（GUI 下拉"按月份" / CLI `--by month` / 导出 by_month.csv）
- **路径收敛**：凭据探测仅 env + 项目内（不读其他项目配置）
- **决策记录**：D1 目录集中项目内 / D2 手动填写对话框 / D3 win32crypt 缺失拒绝写入 / D4 连带导出 by_month / D5 提交由用户执行

---

## 十一、V0.09 UI 改版与维护完成（P12-P19/P21，2026-08-10 已实施）

> 人工审核 V0.08 后的一轮 UI 改版；实施细节与验证见 x.progress.md V0.09；遗留 P1/P9/P10/P11/P20 见 y.problem.md

- **基础修复**：配额重置时间转本地时区（P21，修复前 UTC 直出差 8 小时）；移除"dashboard 凭据"元信息行（P12）；自动更新链路排查确认正常（P14）
- **卡片区与总览**：卡片栏重排 总 tokens/输入/输出/缓存率/总费用，删除会话数（P17）；总览独立显示（千分位+亿单位）+ 点击弹总量明细，维度下拉移除总览（P15）
- **明细表格**：列顺序 标签/总 token/调用数/输入/输出/推理/缓存（读+写合并）/缓存率/费用（P13+P18）；"设置"按钮列开关（hidden_columns 持久化）
- **配额饼图**：原"最紧窗口"文字位改为剩余量饼图（P16，正常显示/异常隐藏让位警告）
- **会话维度**：`by_session()`（会话标题｜项目目录，LEFT JOIN session 表 + 旧库降级），GUI/CLI/导出齐全（P19）

---

## 十二、P10 二次审计整改完成（2026-08-10 已实施）

> 范围：全部 16 个 .py 文件，对照 AGENTS.md 规范 + 10 类问题清单（优化/抽象/过简函数/import/嵌套/小错误/硬编码/默认值/防御性代码/死代码）
> 结果：**59 条发现**（高价值 10 / 中价值 20 / 低价值 22）；无架构级问题，import 顶层化/注释规范/命名/可变默认参数均合规
> 实施明细见 x.progress.md V0.10；H1/M11 两项审计建议经实测证伪（以行为验证为准）

- **高价值 10 条**：审计误判证伪 1 项（`except GoQuotaError: raise` 必要——401/403 分类错误会被外层包装破坏，传播测试证实）；OpenAuth 死条件/`_add_seconds` 冗余/不可达 2xx 检查删除；`login_wait_seconds` 默认 None 走 base.json；refresh 网络失败回退 TTL 内旧缓存；UA 去硬编码；临时目录清理补全；预警阈值单一来源；说明区凭据路径修正
- **中价值 20 条**：8 处死代码删除（clear_cache/CONFIG_DIR/不可达 raise/REFRESH_INTERVAL_MS/\_quota_info/\_quota_status/调试与截断注释）；未用参数清理；3 处一行转发内联（`_status_bar_show` 为结构性整改：状态栏提前创建、信号连接统一前部）；重复逻辑抽取（Local State 读取/PRAGMA 缓存/维度名收敛）；`--restore-last-session` 无效参数移除；import 分组修正；说明区补齐 4 文件
- **低价值 22 条**：行宽/Path 冗余/缓存写入收敛单处；THEMES 单一来源；表格 limit/饼图参数/CDP 超时/图标几何/超时统一/app_name/日志级别等硬编码外置 base.json/ui.json；静默兜底改失败策略；`row["name"]` 数字索引修正

---

## 十三、第三轮全量审计整改完成（2026-08-11 审计，2026-08-12 已实施）

> 范围：全部 16 个 .py 文件，对照 AGENTS.md + 10 类问题清单 + **跨模块复用专项**；约 25 条为上轮遗留（pricing retries、Path 冗余、说明区漏项等），其余为新增
> 结果：**57 条发现**（跨模块复用 15 / 可优化 10 / 小错误 9 / 死代码 8 / 硬编码 6 / 规范 5 / 默认值 2 / 过度防御 2）
> 实施明细见 x.progress.md 第三/四轮章节（3A.1-3A.3）

- **跨模块复用 15 条（重点）**：新建 `utils/network.py` http_get 统一（go_quota 保留 401/403 分类）；`read_json`/`round_cost` ×5/异常元组/魔法字符串与凭据键/APP_NAME 收敛；双胞胎 dataclass 别名；阈值三分支复用；日志入口统一（retry 唯一例外）；公开入口去下划线；CSV 列名单一来源推导；`_by_field` 抽取三方法
- **死代码/冗余 8 条**：`_json_cache` 评估**保留**（通用 utils 能力，业务点显式 use_cache=False 属 TTL 语义，verify_s1 覆盖）；不可达分支删除（retry raise/HTTPError 401/403/rmtree 外层 except）；global 冗余；`_rate_from_raw` 去 try/except；说明区函数名修正
- **小错误/边界 9 条**：bool 语义对齐（to_float/settings 间隔防 true→1ms）；min_ts=0 纪元边界；cost_source 多币种修正；CLI 坏库中文提示；映射值类型校验；CDP 参数模块级解包；未用 import；注释补齐
- **硬编码 6 条 + 其他 19 条**：retries 走 base.json；BUNDLED_PRICES 评估**保留**（离线兜底有意设计）；DEFAULT_DB_PATH/气泡文案/布局/色值外置；延迟 import 顶层化；过度防御删除；`_load_rate_items` 合并/遍历合并/TTL 过期回退旧缓存/by_session 行构造复用优化；说明区补齐

---

## 十四、第四轮全量审计整改完成（2026-08-12 已实施）

> 范围：全部 17 个 .py 文件（含 utils/network.py、utils/windows.py），AST 精确扫描（函数内 import/嵌套 def）+ 三代理全文审读
> 结果：**47 条发现**（错漏 11 / 硬编码 10 / 重复实现 5 / 说明区不符 8 / 防御性 5 / 可优化 5 / 死代码 3）+ 专项结论（函数内嵌套 def 4 处）
> 实施明细见 x.progress.md 第四轮章节（4A.1-4A.3）

- **重复实现 5 条（重点）**：APP_NAME 四处重复解包统一（utils.logger 导出）；win32crypt try-import 降级提取 `utils/windows.py` 公共模块；DPAPI 解密同款调用收敛（真实往返验证）；去重键共享；UI 文案与 20+ 色调色板整体外置 ui.json（S8.3 颜色外置补齐）
- **函数内嵌套 def 4 处**：browser_creds 三处 `_with_copied_db` 回调闭包参数化提取（\*query_args 透传，163 捕获 aes_key 可传参保留亦正当）；go_quota add 闭包**保留合理**（累加器语义）；`_TaskProcess` 嵌套类提模块级
- **错漏 11 条**：exporter CSV 计数修正；3 处未用 import；to_optional_float bool 排除；缓存毒化修复 + unlink 竞态；parse strip 统一；sqlite URI 转义两处；show_guide 永真精简；v20 提示每会话一次；CDP 响应结构校验
- **硬编码 10 条**：调色板与 THEMES 枚举外置；login_url/CDP 探测超时收敛；cards_spacing/重置时间格式/角度魔法数/类型对齐；limit=100 第三套收敛；system_tray 注解补齐
- **防御性/可优化/死代码 13 条**：mapping 非 dict 抛 RuntimeError、retry assert、except 收窄；cost_source 分支合并、by_session 行构造复用、hidden 空白项 strip；rows 伪维度删除、used_percent getter **保留并记录**（测试专用）；说明区不符 8 处补齐

---

## 十五、第五轮全量审计整改完成（2026-08-12 审计，2026-08-13 已实施）

> 范围：全部 18 个 .py 文件（含 utils/network.py、utils/windows.py），AST 扫描 + 三代理全文审读 + 交叉引用核查；无逻辑错误、无高严重度
> 结果：**36 条发现**（硬编码/文案 10 / 防御性 7 / 错漏 6 / 重复实现 5 / 死代码 3 / 说明区 4 / 确认保留 1）
> 质量趋势：三轮整改后无"自写第二份公共工具"问题，无函数内 import，嵌套 def 仅剩 1 处确认保留
> 实施明细见 x.progress.md 第五轮章节（5A.1-5A.3）

- **重复实现 5 条**：DIMENSIONS 六键推导构建（day 特例 TABLE_LIMIT_DAY）；`QUOTA_WINDOW_KEYS` 统一三处窗口键 + CLI 文案引 ui.json；pricing 键映射复用 `_rate_from_raw`；windows.py 统一日志入口；标题/tooltip 常量外置 ui.json
- **错漏 6 条**：error_stage 枚举说明修正（decoding 归一为 provider）；CDP 引导**改案**（不再读 History——workspaceID 改从登录后页面 URL 提取，多 profile 漏检根源消除）；CDP 元素级 dict 校验；v20 提示模块级会话级去重；cost 浮点容差；说明区缺项补齐
- **防御性 7 条**：文件不存在不写缓存（与 E4 一致）；static_config data 非 dict 抛错；os_crypt 容错两处；error_stage 常量导出去字符串耦合；JSONDecodeError 冗余列举删除
- **硬编码/文案 10 条**：main_window 文案全量外置 ui.json（卡片/区域/按钮/状态栏/对话框/引导消息/明细行）；dark/light 与"总 token："收敛；timeout 族常量（subprocess/cdp）；DPAPI 描述串；Path.expanduser
- **死代码/说明区 7 条**：未用 import 删除；9222 与阈值注释失实修正；常量缺项补齐；add 闭包**确认保留**（去重键已共享，提模块级收益低）

## 十六、第六轮全量审计问题汇总（2026-08-13 审计完成）

> 范围：全部 24 个 .py 文件（4124 行）+ 2 个静态配置 JSON，AST 扫描 + 三代理全文审读 + 行为验证
> 结果：**38 条发现**（错漏 7 / 优化 6 / 防御性 6 / 硬编码 8 / 未用 import 5 / 重复实现 4 / 默认值 2）
> 质量趋势：函数内 import 零、嵌套 def 仅 1 处确认保留、docstring 零、timeout/sleep 魔法值零——但 C6"命名收敛"遗留说明区失实 + base.json 已定义字段未引用
> **整改状态：✅ 全部完成（2026-08-13）**——实施明细见 x.progress.md 第六轮章节（6A.1-6A.4 按批次执行）；新增 utils/sqlite_utils.py（只读连接收敛）、VERSION 单点导出 utils.logger、主题名/文案/容差/单位全量外置

- **错漏 7 条**：themes `{chunk_ok}` 占位符残留与 convert.to_int OverflowError 逃逸（行为验证真实缺陷）；browser_creds CDP 说明区失实且常量与配置数值冲突；launch 失败路径临时目录泄漏；parse_time_arg 注释失实；find_db_path CLI 分支静默；network 说明区失实
- **防御性 6 条**：by_session 缺列崩溃；system_tray QMenu 防 GC；刷新间隔无下限（1ms 疯狂刷新）；logger 初始化竞态；retry 参数校验；缺文件 WARNING 日志噪音
- **硬编码 8 条 + 未用 import 5 条**：CDP 探测族/round(10)/UNKNOWN_LABEL/凭据文案/DPAPI 双源/容差与亿单位/时间格式/任务文案 4 处；Path×3、to_float、Any
- **重复实现 4 条 + 优化 6 条**：sqlite 只读连接两处同构/窗口键字面量两处/主题名双源/标题格式不一致；time_clause 重算/estimate_cost 四段/缓存率组合/预警去重/日志轮转/to_float 合并存疑
- **确认保留 2 条**：go_quota add 闭包（第五轮确认项）；network HTTPError 重试有意设计（5xx/429 重试，401/403 已分类）

---

## 附录 A007：全量代码审计报告（第7轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON（2319 行业务代码 + 配置）；AST 扫描 + 三路代理全文审读（utils+config / modules / ui）+ 行为验证
> 结果：**P2 级 2 条 / P3 级 16 条 / 参考级观察项 15 条**——无 P0/P1（无确定性崩溃/错值）
> **整改状态：✅ 全部完成（2026-08-13）**——A 系列任务清单见 x.progress.md（A0-A3 已实施，A4 收尾）；新增契约校验（themes 残留占位符/数组长度）、\_SC 单点解包、build_app_title 标题单点

- **上轮复核（第六轮 38 条）**：38/38 在位（2 项断言格式误报已澄清，非回退）；发现 1 回归（CDP_PROBE_TIMEOUT 重名重复定义）+ 1 漏改（os_crypt 非 dict 容错只覆盖 None/空，truthy 非 dict 仍 AttributeError 逃逸，行为验证崩溃）
- **P2 修复 2 条**：CDP_PROBE_TIMEOUT 重名去重（删 47 行保留 70 行）；os_crypt isinstance 检查后 return None（167/322 两处）
- **P3 修复 16 条**：host_key 带点 domain cookie 兼容（需验证）；OpenAuth 特征收紧防误判（需验证）；进度条 None 分支重置格式（需验证）；CDP 引导期状态管理×2（定时刷新重现引导卡/手动填写并发写凭据，均需验证）；themes 契约校验（残留占位符检测 + 数组长度）；说明区漏 \_format_cache_rate_of；标题格式单点（build_app_title）；说明区失实 4 处（windows/main/settings/logger）；network 默认值双源；to_float("nan") 穿透（需验证）；opencode_usage 5 处 \_SC 单点；K/M/B/G 单位外置（争议决策）；跨组提示 3 条（settings.py:16 注释失实/default_theme 双源/CLI 时间格式）
- **参考级观察项 15 条**（用户确认均不提升）：browser_creds（--remote-allow-origins=\* 必需/每 profile 整库复制/CDP 探测族 3 固定值）；go_quota（DASHBOARD 请求参数/模块级缓存无锁）；pricing（BUNDLED_PRICES 快照/COST_COMPARE_DIGITS）；opencode_usage（时间基准常量）；exporter（查询全量驻留）；main_window/system_tray（绘制细节）；static_config/file_utils/retry/convert（无锁单例/缓存引用/默认值分离/下划线字面量——均无可达触发路径）
- **亮点**：无 P0/P1；无函数内 import/docstring/未用 import/配置死键（base.json 26 键、ui.json 42 键全有消费方）；弹性转换实测无崩溃路径；README 徽章与版本一致

---

## 附录 A008：全量代码审计报告（第8轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；AST 扫描 + 三路代理全文审读 + 行为验证
> 结果：**P2 级 1 条 / P3 级 13 条 / 参考级观察项 15 条**——无 P0/P1
> 状态：✅ 全部完成（2026-08-13）——B 系列任务清单见 x.progress.md（B0-B3 已实施，B4 收尾）；Edge 判定下沉双浏览器、刷新序号去重、配置契约校验等 15 项修复

- **上轮复核（A007 第 7 轮 19 项）**：27/27 全部在位、零回退；发现 1 处 A007 漏改分支（launch Popen OSError 未清理）+ 3 处 A3.1 漏改的说明区（main_window/system_tray/themes）
- **P2（1 条）**：main_window:343 只对 Chrome 调 has_v20_cookies——Edge-only v20 用户误判为 v10 收到无效指引，与 find_browser_credentials 双浏览器遍历口径不一致（建议判定下沉 browser_creds 遍历双浏览器）
- **P3（13 条）**：to_float/to_optional_float 缺 OverflowError（10\*\*400 实测逃逸，与 to_int 不对称）；pricing currency/source None → "None" 错值（实测）；launch Popen OSError 分支临时目录泄漏（A007 漏改）；刷新无 in-flight 去重（连点+定时叠加旧任务覆盖新数据）；ui.json 结构性键无契约校验（删键确定性 KeyError/IndexError）；说明区失实/残留 6 处（main_window VERSION、system_tray APP_NAME、themes 异常处理无、exporter/browser_creds/go_quota 关联配置）；notify 模板 .format 无防护（KeyError 逃逸）；settings \_themes/THEMES 重复构造
- **参考级观察项 15 条**（用户复核后**提升 6 条**入 B 系列：A1 键序排序/B7 托盘不可用/B6 引导定时器/B8 节流文案/D2 CLI 下界/D1 排序提函数；维持 9 条）：TOKEN_ABBR_UNITS 键序依赖、托盘不可用窗口不可恢复、导出无防重入、ws.recv 不按 id 匹配、pricing cache_write 单键映射、estimate 全表扫描、CLI --limit 无下界、节流文案滞后、跨节流并发、network 每次 get_static_config、write_json mkstemp 位置、sqlite_utils 线程契约、双份 themes 解析、paintEvent 无显式 end、hidden_columns 排序两处重复
- **亮点**：无 P0/P1；A007 零回退；无函数内 import/docstring/未用 import/配置死键（base.json 33 键、ui.json 44 键全有消费方）；README/ base.json / x.progress 三处 ver 0.14 一致

---

## 附录 A009：全量代码审计报告（第9轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；AST 扫描 + 三路代理全文审读 + 现网实测 + 行为验证
> 结果：**P1 级 1 条 / P2 级 2 条 / P3 级 9 条 / 参考级观察项 10 条**
> 状态：✅ 全部完成（2026-08-13）——C 系列任务清单见 x.progress.md（C0-C3 已实施，C4 收尾）；远程定价重构（P1）、信号序号去重、契约键集扩展、isfinite 终结修复等 13 项

- **上轮复核（A008 B 系列 16 项）**：22/22 全部在位、零回退；发现 3 处 B 系列遗留尾巴（opencode_usage 缩进错乱 B0.10 引入 / go_quota 说明区 60s B3.2 漏改 / main_window 说明区 VERSION 尾巴 B3.1 不彻底）
- **P1（1 条）**：pricing.py:261-289 远程定价确定性失效（**现网实测**：models.dev/api.json 顶层为 provider 键无 "models" 键、model key 无 "provider/" 前缀）——远程定价层死路径，非内置模型估算永远 unpriced；需遍历顶层 provider → models dict 重构整段
- **P2（2 条）**：main.py:55-65 B0.7 防护不完整（'{used'/'{used!q}' 抛 ValueError、'{}' 抛 IndexError 实测逃逸，fallback 无二次保护）；pricing.py:115 缓存写失败 OSError 传播拖垮 estimate 链路（缓存是加速项非正确性依赖）
- **P3（9 条）**：convert to_float("inf") 穿透（实测，与 nan 不对称）；quota_ready/error 信号无序号去重（B0.5 只覆盖 usage）；themes THEME_NAMES 顺序契约缺失（数组改序 → 名称与调色板错位）；TABLE_HEADERS 契约只防短不防长；缩进错乱 + 说明区残留/失实 4 处（go_quota 60s、main_window VERSION 尾巴、main_window PIE 归属、system_tray build_app_title 归类）
- **参考级观察项 10 条**（用户确认均不提升）：go_quota URL 模板 .format（**实测不抛，误报已排除**）、retry 参数类型、hidden_columns 脏 id、http_timeout 类型契约、logger LOG_LEVEL 回退、sqlite_utils busy_timeout、file_utils 缓存、static_config 无锁单例、network 每次 get_static_config、browser_creds 定案；ui.json 契约扩展（status_messages 等 7 组文案键 + 13 处 .format）代理建议下轮并入 B0.6
- **亮点**：A008 零回退；无函数内 import/嵌套 def/docstring/未用 import；ui.json 45 键、base.json 33 键全有消费方；README/base.json/x.progress 三处 ver 0.15 一致；现网实测首次抓出"配置活但路径死"类问题

---

## 附录 A010：全量代码审计报告（第10轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；AST 扫描 + 三路代理全文审读 + 行为验证
> 结果：**P1 级 1 条 / P2 级 3 条 / P3 级 11 条 / 参考级观察项 12 条**
> 状态：✅ 已修复（2026-08-13：D 系列 D0 P0 正确性 15 条 + D3 清理 2 条全部完成，D1/D2 无条目；探针 15/15 + 修复验收 18/18 + 全量回归 43/43；任务清单见 x.progress.md D 系列）

- **上轮复核（A009 C 系列 14 项）**：18/18 全部在位、零回退；但发现 3 处"C 系列修复不完整"实质缺口（C0.1 字段名漏网、C0.8 自证恒真、C0.6 不防顺序）——修复本身引入新缺陷，暴露"验证跟着实现走"的自证陷阱
- **P1（1 条）**：pricing.py:285 远程定价字段名待裁决（当前取 "pricing"，代理三方证据链指向现网为 "cost"——若成立则远程层仍死路径；本环境无法现网验证，probe 自证不可信）——建议兼容 get("cost") or get("pricing")
- **P2（3 条）**：main_window:170 status_messages 契约自证式恒真（ uple(STATUS_MESSAGES) 从被校验对象派生，删键不报错、启动 KeyError 崩构造）；main.py:48-79 节流缓存破坏预警去重（实测：缓存到达复位 \_notified_danger + 托盘置灰，超限重复弹气泡）；刷新无 in-flight 去重（C0.5 只解决乱序，网络并发叠加遗留）
- **P3（11 条）**：模板占位符校验漏 pie/detail_line 两组；usage_percent 无界（-5%/120% 错值）+ overall 无下界钳制；notify_title 无契约无防护；C0.6 不防顺序颠倒；save_state 无降级（磁盘满阻塞退出）；解析空结果无 warning（P1 潜伏放大器）；HTTP_TIMEOUT 死代码 + 说明区失实；说明区缺失/重复 4 处；窗口销毁 in-flight 信号（需验证）；palette 值非字符串 TypeError
- **参考级观察项 12 条**（用户复核后**提升 1 条**：凭据探测 TTL——每次刷新全量浏览器探测，未来提频前加缓存；维持 11 条）：历轮定案项 + html 局部遮蔽/时区偏移/本地覆盖缺字段/绘制参数等
- **亮点**：A009 零回退；无函数内 import/嵌套 def/docstring/未用 import；配置全键有消费方；三处 ver 0.16 一致；三路交叉验证抓出"自证恒真校验"类隐蔽缺陷

---

## 附录 A011：全量代码审计报告（第11轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读 + AST 扫描 + 行为验证（C0.6 实测复现）
> 结果：**P0-P3 级 15 条（中 3 / 低 12，含观察项提升 2 条）/ 参考级观察项 13 条（提升 2 条，维持豁免 11 条）**
> 状态：✅ 已修复（2026-08-13：E 系列 E0 正确性 4 条 + E2 配置化 2 条 + E3 清理 9 条全部完成，E1 无条目；探针 4/8/9 全 PASS + 修复验收 26/26 + 全量回归 43/43；E4 收尾含三项防漏损强制——同根因调用点全扫（write_json/save_config 全部调用点防护闭环）、说明区全量一致性扫描（补 4 处漂移：go_quota/opencode_usage/browser_creds/main_window）、配置键文档同步（credentials_ttl 三处一致）；任务清单见 x.progress.md E 系列）

- **上轮复核（A010 D 系列 17 项）**：D0.1-D0.15 + D3.1/D3.2 主体全部在位、零回退；发现 4 处"修复不完整"（main_window:1002 toggle save 漏 try、main.py 说明区未随 D0.13 同步、network.py 说明区残留 pricing 的 HTTP_TIMEOUT、pricing.py:342 关联配置漏 retry 两键）与 2 处"A010 已列未修"（C0.6 顺序契约、palette 值类型）
- **P0-P3（15 条）**：
  - 正确性：C0.6 顺序契约失效（改序导入不抛错，行为验证复现）；estimate LIMIT 无 ORDER BY（样本偏向最早消息）；\_on_column_toggle save_config 无 try（D0.10 同类漏改）；min_ts=0 天数爆炸（观察项提升，需验证）
  - 配置化：in-flight 提示文案硬编码（6A.3 H3 定案违反）；CREDS_CACHE_TTL 未走 base.json（观察项提升）
  - 清理：in-flight 分支冗余调用；嵌套闭包 def add()；WIN32CRYPT/AES 缺失不写缓存（TTL 失效 + 重复 warning）；说明区 5 处失实/缺失；palette 值类型校验
- **参考级观察项 13 条**（用户复核后**提升 2 条**：min_ts=0 天数爆炸、CREDS_CACHE_TTL 配置化；维持 11 条已并入豁免定案清单）：settings 无上限/理论 fd 泄漏/backoff clamp 语义/cost 空 dict/schema 语义依赖等
- **亮点**：无高严重度（无确定性崩溃/错值）；三路交叉再次抓出"修复自身引入残留"模式（D0.10/D0.13/D3.1 同类漏改）；行为验证探针自毁还原机制经实测验证（git 兜底无损）

---

## 附录 A012：全量代码审计报告（第12轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读 + AST 扫描 + 行为验证（契约缺口实测）
> 结果：**P0-P3 级 7 条（中 1 / 低 6，含观察项提升 2 条）/ 参考级观察项 10 条（提升 2 条，维持豁免 8 条）**
> 状态：✅ 已修复（2026-08-13：F 系列 F0 正确性 3 条 + F3 清理 4 条全部完成，F1/F2 无条目；探针 5/5 + 修复验收 15/15 + 全量回归 43/43；F4 收尾防漏损延续——契约组与消费方交叉（go_quota_error_messages/quota_window_labels 全在契约块）、说明区扩展扫描补 3 处漂移（main_window 契约组/\_usage 标志、opencode_usage 字段契约键集）、配置键无漂移；任务清单见 x.progress.md F 系列）

- **上轮复核（A011 E 系列 15 项）**：15/15 全部在位、零回退；E4 防漏损机制覆盖 5 文件但漏出 3 处"修复自身残留"（main.py 不在扫描范围漏网 ×2、pricing/themes 同文件漏改 ×2）；三处均为低危文档/死代码类
- **P0-P3（7 条）**：
  - 正确性：go_quota_error_messages 组未入契约键集（删 in_flight 键导入不抛，行为验证复现，运行时分支 KeyError——B0.6/C0.8 历史遗漏 + E2.1 未同步）；refresh 连点排队多任务（观察项提升）；UsageRow 字段与 \_render_table 硬绑定无契约（观察项提升）
  - 清理：main.py:19 VERSION 未使用 import（D0.13 残留，E3.4 只修说明区未清代码）；main.py 说明区漏 notify_message_fallback（main.py 不在 E4 扫描范围）；pricing 说明区缺 \_price_line/\_rate_from_raw；themes 说明区未同步 E0.1 键序语义
- **参考级观察项 10 条**（用户复核后**提升 2 条**：refresh 连点、UsageRow 契约；维持 8 条已并入豁免定案清单）：第三主题静默错位/palettes 容器类型/ORDER BY 无索引/usage_percent 未钳制/subprocess 无 CREATE_NO_WINDOW/CLI --limit 无上界/浏览器文案硬编码/\_profile_dirs 前缀过宽
- **亮点**：E 系列零回退；防漏损机制本轮当场抓出 3 处残留（证明机制有效，扩展扫描范围即可收敛）；credentials_ttl/in_flight 单点定义单点消费无漂移

---

## 附录 A013：全量代码审计报告（第13轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读 + AST 扫描 + 行为验证（F0.2 连点挂起实测复现）
> 结果：**P0-P3 级 6 条（中 1 / 低 5，含观察项提升 1 条）/ 参考级观察项 9 条（提升 1 条，维持豁免 8 条）**
> 状态：✅ 已修复（2026-08-13：G 系列 G0 正确性 2 条 + G3 清理 4 条全部完成，G1/G2 无条目；探针 3/7 + 修复验收 15/15 + 全量回归 43/43；G4 收尾防漏损升级——说明区无残留字样反向断言（F3.1 漏改三次同根因终结）、说明区语义准确性扫描（G3.1 教训）、G0.2 契约消费方交叉（main_window/exporter 属性全命中，排除布局方法/文件名误匹配）；任务清单见 x.progress.md G 系列）

- **上轮复核（A012 F 系列 7 项）**：F0.1 契约组三方一致在位；F0.3 字段契约 20 处消费点零失配；F3.1 顶层分支完整；但发现 F0.2 修复不完整（pending 丢弃路径不消费——连点数据挂起 + 残留重复查询，行为验证复现）与 F3.1/F3.3 说明区残留 3 处（同根因模式第三次记录）
- **P0-P3（6 条）**：
  - 正确性：F0.2 pending 丢弃路径不消费（seq 不匹配分支 return 前未补发，连点请求被吞、数据挂起、后续同 seq 重复查询——行为验证复现）；UsageSummary 未入字段契约（观察项提升，与 F0.3 同风险面）
  - 清理：pricing 说明区 \_price_line 主语写反 + \_rate_from_raw cache 缺省描述不精确（F3.3 引入）；main.py 说明区 VERSION 段失实（F3.1 漏改，同根因第三次）；main.py 说明区漏 \_SC/\_notified_danger；main_window 说明区 refresh 行未同步 F0.2 + 关联配置 VERSION 失实
- **参考级观察项 9 条**（用户复核后**提升 1 条**：UsageSummary 契约；维持 8 条已并入豁免定案清单）：\_TOKEN_SUM_SELECT 无静态校验/契约与说明区无联动/契约块位置/QUOTA_COLOR 缩写/MENU_LABELS 导入顺序/连点 N 个 QuotaTask/双分支复位风格/契约列举省略/dialog 组/settings themes 空数组回退/logger 注释措辞
- **亮点**：F0.1/F0.3 三方一致零失配；三路交叉 + 行为验证再次抓出"修复自身引入缺陷"（F0.2 挂起为确定性回归）

---

## 附录 A014：全量代码审计报告（第14轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读 + git show 逐行对比（abf3a23）
> 结果：**P 级 5 条（全低）/ 参考级观察项 20 条（用户复核全部维持豁免）**
> 状态：✅ 已修复（2026-08-13：I 系列 I0 正确性 1 条 + I3 清理 5 条全部完成，I1/I2 无条目；探针 1/6 + 修复验收 11/11 + 全量回归 43/43；I4 收尾防漏损——新增契约/校验块必进说明区交叉扫描（A014 教训落地：go_quota_error_messages/notify 两键/容器校验/数值键契约全在说明区）、说明区无残留 + 语义扫描（I 系列修改文件）、豁免清单状态一致性（fdopen 记账迁移）；附带修复 verify_s6 历史欠账（D0.8 注入缺失的 \_reset_creds 定义与缩进、4 处缓存串场）；任务清单见 x.progress.md I 系列）

- **上轮复核（H 批次 11 项）**：主体全部在位、零代码回归（白名单双向差集为空、fdopen 清理 5 路径矩阵全安全、三层钳制幂等收敛）；发现 5 处"修复自身引入"（全部文档/验证级）：G0.1 注释失实与 H0.6 finally 矛盾 + 验证盲区（路3 竞态推演经甄别不存在——跨线程队列连接下主线程处理必然晚于 worker finally）；palettes 根容器未校验（H3.1 不完整，裸 AttributeError）；file_utils 说明区未同步 fdopen（H0.3）；豁免清单 fdopen 条目未移入已修复记账（H 批次收尾遗漏）；main_window 契约块说明区未补 notify 两模板键（H0.8）
- **P0-P3（5 条，全低）**：
  - 防御：palettes 根容器类型未校验（themes.py:83，H3.1 不完整，C0.6 .keys() 连带）
  - 清理：G0.1 注释同步（main_window.py:842/846）+ 补发任务 run 链路行为探针；file_utils 说明区补 fdopen；豁免清单 fdopen 移入已修复记账；main_window 契约块说明区补 notify 两键
- **参考级观察项 20 条**（用户复核**全部维持豁免**，已并入豁免定案清单）：失败路径 pending 不消费/阈值 warn>danger 无校验/reset_seconds 无上界/根键缺失裸 KeyError 家族/\_TEMPLATE_MAP .get 冗余/limit 双兜底冗余/估算忽略 reasoning（设计定案）/Popen 无注释/托盘不可用 notify/路1 理论 6 条等
- **亮点**：H 批次零代码回归；三路交叉抓出 5 处文档/验证级残留——暴露"新增契约块必进说明区"扫描盲区（跨批次收尾流程改进点）

---

## 附录 A015：全量代码审计报告（第15轮收尾，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读 + git show 逐行对比（9b7ee3b）+ 跨组确证（HTTPError 分类时序）
> 结果：**P 级 4 条（全低）/ 参考级观察项 12 条（用户复核全部维持豁免）**
> 状态：✅ 已修复（2026-08-13：J 系列 J0 正确性 2 条 + J3 清理 2 条全部完成，J1/J2 无条目；探针 3/2 + 修复验收 10/10 + 全量回归 43/43；J4 收尾防漏损——顶层 import 常量与说明区覆盖率自动核对（A015 教训落地：抓出并补 QSystemTrayIcon 条目）、说明区无残留 + 语义扫描（J 系列修改文件）、豁免清单状态一致性（⑤ 段记录核对）；任务清单见 x.progress.md J 系列）

- **上轮复核（I 系列 8 项）**：8/8 全部在位、零回退、零漏改（三路均确认）；modules 组 6 文件 9b7ee3b 零连带改动；ui 组第 15 轮零 P 级
- **P0-P3（4 条，全低）**：
  - 正确性：parse_time_arg 相对时长数字无上界（`999999999d` 实测 OverflowError 逃逸，except ValueError 不捕 + 说明区失实连带——数值上界缺失家族第 3 例）；pricing 本地覆盖 key 大小写不归一（canonical_key 小写化消费，覆盖静默失效实测）
  - 清理：main.py 说明区漏 QUOTA_DANGER_PERCENT（A013 G3.3 同文件漏改模式第三次）；file_utils 说明区缺 get_project_root 函数条目（AGENTS.md 硬性要求）
- **参考级观察项 12 条**（用户复核**全部维持豁免**）：CSV 非原子写（豁免条目表述建议修正为"JSON 原子写"）/go_quota CLI quota_window_labels 容器（I0.1 同族）/exported_at 无时区/\_with_copied_db 异常契约/themes 逐字符迭代/hidden_columns None/RotatingFileHandler 值域/round_cost digits/I0.1 消息重复调用/模块级标志多实例/\_TEMPLATE_MAP .get/colors 键族契约化；跨组 R2（HTTPError 分类时序）**已确证安全**（调用方先分类再重试契约成立）
- **亮点**：I 系列零回退；ui 组零 P 级；modules 组历轮 15 轮持续保持无高/中严重度；五层校验链顺序正确、三层钳制幂等收敛、契约与消费点零失配

---

## PL001. 凭据指纹切换日志——多账户用量区分初步方案（2026-08-13）

> 来源：P1/P9 前置验证定案（精确区分物理不可行——session.workspace_id 100% NULL、account/credential 表全空、event 无账户事件，详见 y.problem.md P1/P9 已验证段）
> 状态：✅ 已实施（2026-08-13，版本 ver 0.213）；⚠ 统计侧与切换日志已随 PL004 退役（ver 0.240），配额侧保留并演进为单卡选择器（PL004/PL005）

- **目标**：换 OpenCode Go 账户后自动记录切换时间点，使启用之后的用量可按账户时段切片统计；配额侧支持多凭据轮询查看各账户余量
- **实施结果（三部分去向）**：
  - 一、凭据指纹切换日志（统计侧）：switch_log.json + detect_credential_switch（sha256 前 12 位指纹/启动+刷新成功双时机检测/同指纹去抖/半开区间闭合）→ **A0.16 前身 PL004 已整体退役删除**
  - 二、统计切片（消费侧）：\_time_clause 时段过滤 + GUI 账户下拉 + CLI --account + 导出标注列 → **随 PL004 整体退役删除**
  - 三、配额多凭据轮询（配额侧）：凭据文件数组格式 + fetch_go_quota 循环轮询 + 异 workspace 追加式保存 → **保留**，UI 由多卡并列演进为单卡+账户选择器+quota_account 记忆（PL004/PL005）
- **硬限制（退役根因）**：opencode.db 消息 JSON 无账号维度字段且多账号混写同一本地库——时间窗近似对"并行使用"物理不可分、对"串行切换"存在采样漏检（完整论证见 z.plan PL004 背景）；时间窗近似方案退役后不再以任何形式重新引入
- **决策记录（历史存档）**：全量实施一二三 / 日志独立 switch_log.json 存储（数据非配置）/ 配额多凭据需要；原始实施方案全文与工作量估算见 git 提交 4a59c19

---

## PL002. 模型数据页 + 官方动态页签实施方案（2026-08-13）

> 来源：P20 可行性研究（2026-08-10 定稿）+ 数据页实况核实——$R 数据块（2135 个，tokenCost/cacheRatio/sessionCost/country 四块齐全）与 top-models-bar HTML 属性双源确认；GitHub Releases API/RSS 可用性实测通过
> 状态：✅ 已实施（版本 ver 0.220）；全部保留运行中

- **目标**：新增"数据与动态"页签——官方动态（GitHub Releases）+ 数据页统计（热门模型每日用量/Token 成本/缓存比/会话成本/国家分布六区块）
- **实施结果（三层架构去向）**：
  - modules/opencode_data.py（纯数据层）：$R 引用展开器/四数据块锚点解析/时序正则/Releases JSON→RSS 回退链/60s 节流缓存 → **保留**；A0.16 整改四处（K1.1 失败保缓存/K2.2 timeout 走配置/K2.3 死键删除/K3 清理与说明区同步）
  - ui/data*page.py（纯展示层）：DataPage widget 懒加载 + set*\* 纯渲染入口 → **保留**
  - main_window.py（装配层）：QTabWidget 两页 + Tab2 首次切换懒加载触发（主刷新定时器隔离）→ **保留**
- **技术要点（历史存档）**：top-models-bar 为 SolidJS 渲染属性较脆，独立小解析失败不影响其他块；X/Twitter、小红书维持不可行结论不做
- **决策记录（历史存档）**：第一版六区块范围认可（聚合数字后补）；原方案全文见 git 提交 9e93009

---

## PL003. UI 整体重构：四主题注册制 + 拟物化扩展实施方案（2026-08-22）

> 来源：P25 立项（2026-08-13）+ 2026-08-22 两张参考风格图与四点拍板（双图皆做主题 / 命名按建议 / 下拉切换 / 配额阈值行为不变仅颜色随主题）
> 状态：✅ 已实施（2026-08-22，版本 ver 0.230）；遗留 PL003.3.e 截图对照参考图目检未做（需多模态模型）；A0.16/K0.1 修复渲染路径 quota_chunk_color 未传 theme_name 缺陷（PL003 改造遗漏）

- **目标主题集（4 主题，默认仍 light）**：light/dark 现有保留；console（深色终端控制台：近黑底/等宽字体/彩色描边/磷光屏）、panel（浅色工业面板：米灰绿底/细线胶囊/极简线框）
- **实施结果（五部分去向）**：
  - 一、主题注册制泛化：themes.py `_THEME_QSS` 注册制构建 + DEFAULT_THEME_NAME/get_theme 回退 + 动态色键契约校验（chunk 三档/quota_gray/pie_bg/pie_text 每主题必含）；quota_chunk_color 增加 theme_name 参 → **保留**
  - 二、切换交互：按钮改下拉，theme_labels 显示名外置，切换即存 + chunk 重着色 → **保留**
  - 三、双新主题包：{font_family} 占位符（console/panel 用 Consolas 族）+ 两套 palette 落地 → **保留**（截图目检遗留）
  - 四、列元数据外置：table_columns [{id,title}] + TABLE_HEADERS 从 title 派生 + 与 COLUMN_IDS 导入期严格相等校验 → **保留**（实测拦截过 cache 列 id 写错）
  - 五、收尾验收：verify_pl003_accept 反向断言 → **保留**
- **技术要点（历史存档）**：QSS 无 box-shadow 用双描边模拟立体；分段进度条自绘（M3b）可选追加不阻塞；配色标准"神似非复刻"
- **决策记录（历史存档）**：四主题皆做 / console·panel 定名 / 下拉切换切完即存 / 配额阈值行为不变仅颜色随主题；原始方案全文见 git 提交 56a8d9f

## PL004. 用量纯净视图回归：切换日志移除 + 配额单卡选择器实施方案（2026-08-23）

> 来源：人测反馈"接下来做 UI 与内容呈现完善"的前置收敛 + 2026-08-23 多轮对齐拍板。
> 背景根因：opencode.db 消息 JSON 无任何账号维度字段（实测顶层键仅 agent/cost/mode/
> modelID/parentID/path/providerID/role/time/tokens/variant），且多账号消息混写同一本地库
> ——PL001 时间窗近似方案对"并行使用"物理不可分、对"串行切换"存在采样漏检，实用价值
> 有限；用户诉求回归"整体 tokens"纯净视图，配额侧改为"选谁看谁"的单卡交互。
> 状态：✅ 已实施（2026-08-23，版本 ver 0.240）

### 目标形态

| 区域            | 现状                                               | 目标                                              |
| --------------- | -------------------------------------------------- | ------------------------------------------------- |
| tokens 用量统计 | 明细区账户时段下拉过滤 + 导出标注列 + 后台切换日志 | 纯净单视图（全量统计，无任何账户概念）            |
| Go 配额展示     | 多卡并列（每凭据一张卡）                           | 单卡 + 账号选择器下拉（选谁显示谁），选择持久化   |
| 凭据管理        | CDP 引导 / 手动填写；数组格式异账号追加            | **原样保留**（选择器的数据基础，不动）            |
| 托盘预警        | 取所有有效账户中用量最高者驱动                     | **原样保留**（只依赖 infos 列表，不依赖卡片形态） |

### 任务分解

#### PL004.1 删 A：切换日志体系（时间点记录）

- credential_store.py：删除 `SWITCH_LOG_FILENAME` 常量（:23）、`load_switch_log` /
  `save_switch_log` / `detect_credential_switch` 三函数（:111-182）及说明区对应条目
  （:214-235 相关行）；连带删除 `credential_fingerprint`（:103）——唯一消费者为切换日志
  与无 UI 消费的 GoQuotaInfo.fingerprint 字段
- go_quota.py：删除 `SWITCH_LOG_FILE` 常量（:50）、`record_credential_switch` 钩子
  （:103-112）、fetch 循环内调用点（:458-459 含 PL001.3 注释）、`GoQuotaInfo.fingerprint`
  字段定义（:140）与两处赋值（:396-408/:478）、说明区条目（:560/:570）
- main.py：删除 import（:15）与启动时调用（:38）
- ui/main_window.py：删除 `SWITCH_LOG_FILE` / `load_switch_log` import（:50/:65）
- 验证：IMPORT OK + offscreen init + 定向探针（被删符号 AttributeError 即 PASS）

#### PL004.2 删 B：时段截取链（intervals 参数 + 账户下拉 + 导出标注列）

- opencode*usage.py：删除 `intervals` 形参全链——totals（:230/:235/:272）、各 by*\*
  （:297-443 约 8 处签名与透传）、`_time_clause` 区间分支（:460-489 仅删 intervals 部分）、
  其余查询（:510/:554）、CLI `--account` 参数（:650-654）与切换日志解析块（:659-683）；
  import L18-19 一并删。**硬性注意**：since/until 形参是 `--since` 时间过滤，与账户无关，
  **严禁误删**
- exporter.py：删除 `account_intervals` / `account_label` 形参（:34-35）、六处查询传参
  （:40-65）、标注列写入块（:69-77 row["account"] 与 CSV_COLUMNS + ("account",)）、
  说明区条目（:132/:135）
- ui/main*window.py：删除账户下拉三常量（:98-100 ACCOUNT_ALL_LABEL/COMBO_TEMPLATE/
  DATE_FORMAT）、`_UsageTask.intervals` 字段与传参（:363/:380/:386）、
  `\_ExportTask.account*\*`（:474-475/:487-488）、`self.\_account_intervals`初始化（:737）、
  下拉构建与装配（:898-901/:930）、三方法整体`\_rebuild_account_combo`/`\_sync_account_intervals`/`\_on_account_changed`（:948-1019）、任务赋值点
  （:1042/:1274-1277）
- settings.py：删除 `account_filter` 字段（:40）、to_dict 输出（:49）、from_raw 解析块
  （:77-79）
- config/static/ui.json：删除 `account_filter_all_label` / `account_combo_template` /
  `account_label_date_format` 三键
- 验证：IMPORT OK + 全量回归（预期 pl001 系列脚本 FAIL，属预期涟漪，见 PL004.5）

#### PL004.3 配额区改造：单卡 + 账号选择器 + 选择记忆

- 数据层**零改动**：`fetch_go_quota` 保持全量轮询返回 `list[GoQuotaInfo]`——60s 节流、
  in-flight 去重、缓存兜底、占位错误项机制原样；这是"切换选择零延迟"的数据基础
  （选中项数据已在缓存列表，切下拉不发网络请求）
- 卡片结构回归单张：`_build_quota_section` 删除 `_quota_cards` 动态列表容器与
  `_build_quota_card(primary=True)` 兼容主卡模式（PL001.9 结构），恢复单个 `_quota_card`
  dict；`_render_quota` 改为按选中 workspace_id 从 infos 取项渲染单卡，
  失配（已删凭据/尚未刷出）回落首个有效项、全无效渲染 infos[0] 错误态
- 新增账号选择器：配额区顶部加一行 QLabel + QComboBox（userData = workspace_id，
  自然 ID 与凭据判重同源；标签文案外置 ui.json 新键 `quota_account_label`）；
  选项以每次刷新的 infos 为准重建（blockSignals 防回环），错误占位项照常入列
  （选中它显示该账号的错误文字，与其他账号互不影响）
- 选择记忆：settings.py 新增 `quota_account: str = ""` 字段（空 = 首个有效项）+
  to_dict 输出 + from_raw 解析（strip 宽容）；切换回调立即 save_config（失败仅 warning
  降级，与 E0.3/D0.10 同式）；启动恢复 blockSignals 包裹 setCurrentIndex
- 托盘零改动：main.py `_on_quota_updated` 取"所有有效账户中 overall_used_percent 最高者"
  驱动图标/预警的逻辑不动（多账号时仍按最紧的预警，保守语义合理）
- 验证：offscreen init + 探针断言（切换下拉 → 渲染项变化 + quota_account 落盘 +
  重启恢复；infos 失配回落路径）

#### PL004.4 清理与兼容性（残留物物理删除）

- config/user_config.json：物理删除 `"account_filter": "..."` 行（不留死键等运行时无视）
- data/credentials/switch_log.json：文件直接删除（gitignore 内纯死数据，无代码再读写）
- 凭据文件数组格式与追加式保存（go_quota.save_dashboard_credentials 同 workspaceId
  覆盖/异账号追加）**确认保留不动**——配额选择器的数据基础
- 验证：带旧残留键的临时 user_config 跑一次 offscreen init（from_raw 逐键 raw.get()
  天然容忍未知键，实证启动无错、其余配置正常生效）

#### PL004.5 回归脚本清理与新验收

- 必删（锚定被删代码必 FAIL）：`.temp/verify_pl001_accept.py`、`.temp/probe_pl001_*`
  系列、其他引用 intervals/account_filter/switch_log 的探针逐一排查清理
- 同步修：`.temp/verify_5a3.py` 白名单移除"保存账户过滤配置失败"条目及同类锚定点；
  `.temp/run_all_verify.py` 清单移除已删脚本
- 新建 `.temp/verify_pl004_accept.py` 反向断言：credential_store 无 switch_log 四函数 /
  opencode_usage 各查询无 intervals 参数 / exporter 无 account 标注 / main_window 无
  \_account_combo / quota_account 切换持久化回环 / 单卡按选中 workspace_id 渲染 /
  user_config 残留键已物理清除
- 验证：run_all_verify.py 全量回归 0 异常

#### PL004.6 文档同步与版本推进

- README：分账号用量章节改写为"配额账户切换"说明（选谁看谁 + 凭据引导入口指引）
- z.plan.md：本章节状态更新为已实施；y.problem.md 如有 PL001 关联条目同步标注退役
- x.progress.md：新增 PL004 任务清单（与本章任务分解一一对应，完成后勾选附验证结果）
- 版本推进：base.json version → ver 0.240（已定版）+ README 徽章 +
  x.progress 当前版本行三处同步；commit 草稿按 V2 规范给出

### 技术要点与硬限制

- 根因约束（不再回退）：opencode.db 消息无账号字段 + 多账号混写同库——时间窗近似方案
  退役后**不再以任何形式重新引入**用量侧账户区分；若未来官方提供账号维度数据再立项
- 账户标识统一用 workspace_id（自然 ID 可读、凭据判重同源）；指纹函数随切换日志退役，
  不留兼容层
- since/until 参数链与账户无关（--since 过滤），删除 intervals 时严禁连带误伤
- 托盘预警语义（最紧有效账户）独立于卡片形态，本次零改动
- 配额选择器选项来源 = infos（实际拉到的账户列表），不是凭据文件原文——解密失败的
  条目自然不出现在下拉里，避免"选了却永远加载不出"

### 工作量估算

| 部分               | 内容      | 估算                                             |
| ------------------ | --------- | ------------------------------------------------ |
| 删 A + 删 B        | PL004.1-2 | 1~1.5 小时（intervals 链约 15 处签名，机械但深） |
| 单卡化 + 选择器    | PL004.3   | 1~1.5 小时                                       |
| 清理 + 脚本 + 收尾 | PL004.4-6 | 1 小时                                           |
| 合计               |           | **半天以内**                                     |

### 已拍板决策（2026-08-23 记录在案）

1. 删除范围？ - A（切换日志）+ B（时段截取/账户下拉/导出标注列）全删，用量回归纯净单视图
2. 配额区形态？ - 多卡并列改单卡 + 账号选择器下拉，"选谁显示谁"，选择持久化（quota_account）
3. 凭据数组格式与追加式保存？ - 保留不动（选择器的数据基础；删则选择器退化为反复重抓凭据）
4. 残留物处理？ - user_config.json 的 account_filter 行与 switch_log.json 文件均物理删除，
   不留死键死文件
5. 托盘预警？ - 零改动，维持"最紧有效账户"保守语义
6. 版本号？ - 定版 **ver 0.240**（2026-08-23 用户指定）

## PL005. 配额区"添加账户"常驻入口实施方案（2026-08-23）

> 来源：PL004 实施后缺口盘点（2026-08-23）——引导卡片仅在"所有账户均无凭据/凭据失效"
> 时显示（main_window \_on_quota_ready 的 show_guide 条件），已有有效凭据时想引入新账户
> **没有任何 UI 入口**（托盘菜单仅刷新/退出；明细区按钮行无凭据项），唯一途径是删凭据文件
> 让引导卡重现（丢失已存账户）。
> 状态：📌 方案已确认，待实施

### 目标形态

| 项           | 现状                   | 目标                                                 |
| ------------ | ---------------------- | ---------------------------------------------------- |
| 添加账户入口 | 仅凭据缺失时引导卡可达 | 配额区选择器旁**常驻"添加账户"按钮**，随时可点       |
| 点击行为     | ——                     | 弹菜单两条路径：一键自动获取（CDP）/ 手动填写        |
| 添加后体验   | ——                     | 凭据追加 → 自动刷新 → 选择器出现新账号并**自动选中** |
| 托盘         | 刷新/退出              | 零改动（窗口常驻可达，避免托盘菜单膨胀——KISS）       |

### 任务分解

#### PL005.1 入口按钮与菜单

- ui.json 新键 `quota_add_account_button`（"添加账户"）；main_window 常量解包同式
- `_build_quota_section` 选择器行尾加 QPushButton；点击弹 QMenu 两项，文案复用既有
  GUIDE_AUTO_BUTTON / GUIDE_MANUAL_BUTTON（不新增重复键）；动作分别路由
  `_start_cdp_guide` / `_manual_guide`（既有引导流程与 A0.6/A0.7 并发防护原样复用）

#### PL005.2 复用适配与添加后闭环

- `_start_cdp_guide` 从非引导卡上下文触发适配：`_guide_frame.hide()` 幂等无害确认；
  **关键修复**：`_on_guide_failed` 无条件 `self._guide_frame.show()`（:1174）——已有有效
  凭据时从配额区触发失败会把引导卡弹出（界面语义混乱），改为按 show_guide 同款条件判断
  （全部账户凭据类错误且无缓存才显示）
- 手动填写路径确认：`_manual_guide` 保存后已调 refresh ✅ 原样复用
- 添加后自动选中新账户：一次性 pending 标志 `_pending_quota_account`；
  - 手动路径直接携带 workspace_id；
  - CDP 路径改 `_CdpGuideSignals.success` 信号签名携带 workspace_id（任务内已抓到），
    `_on_guide_success` 写入 pending；
  - `_render_quota` 重建选项后优先匹配 pending 选中并清除标志（匹配失败静默丢弃，
    回落既有选中逻辑）

#### PL005.3 验证与收尾

- 探针 probe_pl005_entry.py：按钮存在 + QMenu 两动作路由正确（offscreen 触发不崩）；
  手动路径 mock QInputDialog 输入 → 凭据数组追加 + refresh 触发 + pending 自动选中生效
  （行为级 mock 允许，结构断言用真实 save_dashboard_credentials 落盘验证）
- 全量回归 run_all_verify 0 异常 + IMPORT OK + offscreen 冒烟
- README 配额账户章节补"添加账户入口"说明；x.progress.md 勾选附验证结果
- 版本归属决策（并入未提交的 ver 0.240 或独立 ver 0.241，待用户定）+ commit 草稿

### 技术要点与硬限制

- 引导流程三件套（CDP 后台任务/手动对话框/并发防护标志）全部复用，不新建平行流程；
  新代码只有入口按钮、菜单路由、pending 选中、failed 显示条件修正四块
- `_on_guide_failed` 的显示条件修正必须与 `_on_quota_ready.show_guide` 同源逻辑，
  防双路径漂移（提取为 `_should_show_guide()` 私有方法单点维护）
- CDP 信号签名变更向后兼容（workspace_id 参数带默认值），旧消费方不破
- 凭据写入仍统一走 save_dashboard_credentials（DPAPI 加密 + 异账号追加），零新写路径

### 工作量估算

| 部分      | 内容    | 估算                           |
| --------- | ------- | ------------------------------ |
| 入口+菜单 | PL005.1 | 20 分钟                        |
| 适配+闭环 | PL005.2 | 30 分钟（failed 条件修正为主） |
| 验证收尾  | PL005.3 | 30 分钟                        |
| 合计      |         | **1~1.5 小时**                 |

### 已拍板决策（2026-08-23 记录在案）

1. 入口位置？ - 配额区选择器旁常驻"添加账户"按钮 + QMenu 两路径；托盘零改动
2. 添加后体验？ - 自动刷新并自动选中新账户（pending 标志机制）
3. 版本号？ - 独立 **ver 0.241**（2026-08-23 用户指定，不并入 ver 0.240）

## 附录 A016：全量代码审计报告（第16轮，2026-08-23）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读；重点覆盖 PL001-PL005 五个版本新增/删除代码
> 结果：**P 级 19 条（高 3 / 中 8 / 低 8）/ 参考级观察项 26 条（用户复核全部维持豁免）**
> 状态：✅ 已修复（2026-08-23，K 系列 22 条全部完成，版本 ver 0.242；汇总反向验收 verify_k_accept 7/7 + 全量回归 0 异常）

### 零、上轮修复复核清单

| 上轮条目                               | 现状   | 证据                  |
| -------------------------------------- | ------ | --------------------- |
| J0.a parse_time_arg 相对时长上界       | ✅仍在 | opencode_usage.py:571 |
| J0.b pricing local key 小写归一        | ✅仍在 | pricing.py:258-259    |
| J3 main.py 说明区 QUOTA_DANGER_PERCENT | ✅仍在 | main.py:116-117       |
| J3 file_utils 说明区 get_project_root  | ✅仍在 | file_utils.py:77-81   |

零回退零漏改；PL001-PL005 新演进产生新问题见下。

### 一、P0-P3 修复清单

**高（确定性复现）：**

| 文件:行号                           | 类型 | 描述                                                                                                                  | 建议                                                                    | 性质               | 影响面           |
| ----------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------ | ---------------- |
| ui/main_window.py:1310-1312         | ①⑬   | `_render_quota_card` 调 `quota_chunk_color(percent)` 未传 theme_name——非 light 主题下每次配额刷新进度条色重置回 light | 补第二参 `self._theme_name`                                             | 新增（PL003 遗漏） | UI 交互          |
| ui/main_window.py:807-813,1145-1155 | ②⑬   | 添加账户菜单绕过引导互斥：无 `_guide_active` 重入防护、按钮不禁用——可双 CDP 并发、手动填写与 worker 并发写凭据        | 入口重入早退；菜单动作随 `_guide_active` 禁用                           | 新增（PL005）      | UI 交互/凭据安全 |
| ui/main_window.py:1264（根因:723）  | ①    | `_rebuild_quota_account_combo` 用 `self._config` 一次性快照——会话内切换账户被下次刷新静默打回启动快照账户             | `_rebuild` 优先保持当前选中（在 infos 则不动），失配才回落持久化值/首项 | 新增（PL004）      | UI 交互          |

**中：**

| 文件:行号                                  | 类型 | 描述                                                                                                                 | 建议                                       | 性质               | 影响面          |
| ------------------------------------------ | ---- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | ------------------ | --------------- |
| modules/opencode_data.py:249-250           | ①⑬   | 失败快照无条件替换上次成功缓存并续期时间戳（断网刷新丢旧数据），与 ：226 注释"保留上次快照"不符                      | 仅含实质数据才写缓存，否则保留旧快照标错误 | 新增（PL002）      | 显示层/数据管线 |
| config/static/static_config.py:47-73       | ③⑫   | 数值白名单缺 `data_fetch_interval_sec`/`data_cache_ttl_sec` 两键（27 键实收 25，H0.4 契约第二次漏网）                | 白名单补两键+说明区计数同步                | 新增（PL002）      | 配置体系        |
| modules/opencode_data.py:234,327,349       | ③⑫   | 三处 `http_get(timeout=15)` 硬编码绕过 network 层 http_timeout 配置回退                                              | 删实参走配置回退                           | 新增（PL002）      | 配置体系        |
| modules/opencode_data.py:24 + base.json:36 | ⑤⑫   | CACHE_TTL 定义后零引用，"缓存 TTL"语义未实现，base.json 键无效                                                       | 实现 TTL 或删常量删键                      | 新增（PL002）      | 配置体系        |
| modules/go_quota.py:408-418                | ⑬    | in-flight 分支经 \_fallback 只返回单条首条副本——多账户 infos 缩水为 1 条选择器闪缩丢项；节流分支却返回全集行为不一致 | in-flight 分支返回全集标注副本对齐节流分支 | 新增（PL001.8 起） | UI 交互         |
| ui/main_window.py:1434,1480-1502           | ⑥    | 说明区 5 处失实 + 13 个新函数缺条目（\_should_show_guide/\_rebuild_quota_account_combo 等）                          | 按 PL004/PL005 后现状重写                  | 新增               | 文档            |
| x.progress.md:4                            | ⑥    | 版本行仍 ver 0.240 与 :525"三处同步完成"勾选矛盾（实际 0.241）                                                       | 改 ver 0.241                               | 新增               | 文档            |

**低：**

| 文件:行号                                                             | 类型    | 描述                                                                                             | 建议                                  | 性质                 | 影响面   |
| --------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------ | ------------------------------------- | -------------------- | -------- |
| ui/main_window.py:871-875                                             | ⑤       | `_quota_frame`/`_quota_status`/`_quota_reset` 三属性零消费孤儿；:869 注释失实；:821 返回值冗余   | 删三属性修注释                        | 新增（PL004 残留）   | 清理     |
| modules/opencode_data.py:43-51                                        | ⑤       | DataPageError 类零引用空壳                                                                       | 删除                                  | 新增（PL002）        | 清理     |
| modules/opencode_data.py:328,347                                      | ④⑥      | 两处函数内 import 标准库（json/xml.etree）非重依赖豁免口径                                       | 提到模块顶部                          | 新增（PL002）        | 规范     |
| modules/go_quota.py:370; opencode_usage.py:522                        | ⑥       | PL004 死注释："附指纹"/"含账户时段过滤 PL001.4"（所指代码已删）                                  | 改文案                                | 新增（PL004 漏网）   | 文档     |
| modules/opencode_data.py:415; go_quota.py:532,563; pricing.py:312-319 | ⑥       | 说明区四处失实/缺列（函数名错+九函数缺列/\_last_quotas 单数/fetch 描述旧/缺 PRICE_KEY_MAP 条目） | 同步现状                              | 新增                 | 文档     |
| modules/browser_creds.py:509,518                                      | ②       | CDP 响应 JSON 合法非 dict 时 .get() AttributeError 逃逸 modules 层（ui 兜底防崩但英文报错）      | isinstance 校验并入宽容路径           | 遗留（E11 同型漏网） | 引导流程 |
| main.py:129-131                                                       | ⑥       | 说明区 \_on_quota_updated 仍单账户时代口径                                                       | 补多账户口径一句                      | 新增                 | 文档     |
| modules/opencode_data.py:361                                          | ②       | RSS published_at 无 or "" 兜底（title/content 均有），None 显示字面量 "None"                     | 补兜底                                | 新增（PL002）        | 显示层   |
| ui/main_window.py:1240-1263                                           | ②需验证 | 同 workspace 双 cookie 凭据时 combo userData 重复选中错位                                        | userData 用索引或按 workspace_id 去重 | 新增，需验证         | UI 交互  |

### 二、参考级观察项（26 条，用户复核全部维持豁免）

并发类：模块级缓存无锁纯理论竞态（需验证定时/手动叠加）；\_manual_guide 模态期间定时刷新未暂停；\_json_cache 无锁（现调用方均 use_cache=False）；写缓存路径 GUI 线程假设。
展示类：选择器 workspace_id[:8] 截断；懒加载空 rows 占位消失；dark 主题托盘色固定 light palette（PL003.1.e 明示豁免）；pending 双渲染幂等微瑕；combo 失配脏值残留。
解析类：zip 数量不齐静默截断；时序排序无年份跨年理论错序（需验证）；\_time_clause 无前缀列名依赖 session 表结构；themes 残留检测正则花括号误报。
其他：logger 非法 level 静默回退 INFO；retry 计数口径歧义；settings themes 空数组三级回落不可达；ui.json 数值键无 H0.4 式契约（可选增强）；subprocess_timeout 一 float 一 int；CHROME_UA/\_BROWSER_UA 同串双定义；CDP 端口 TOCTOU；Edge-only 用户 CDP 前置体验；CLI --estimate 仅 total 生效 help 未声明。

### 三、亮点

A015 四条修复历经五个功能版本零回退；PL004 大删除结构性清零（约 15 处签名/四函数/字段级删除无一漏网）；ui.json 56 键/base.json 39 键双向零死键（data_cache_ttl_sec 一键例外已列 P 级）；themes 注册制契约校验顺序正确；\_should_show_guide 提取语义等价（布尔吸收律验证）。

---

## 附录 A017：全量代码审计报告（第17轮，2026-08-23）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读；重点覆盖 A016/K 系列 22 条修复代码的完整性与自身缺陷
> 结果：**P 级 16 条（中 1 / 低 15，无高）/ 参考级观察项 18 条合并维持豁免（用户复核确认）**
> 状态：✅ 已修复（2026-08-24，L 系列 19 条全部完成，版本 V0.2.4.3——自本版起启用四段式版本号；反向验收 verify_l_accept 20/20 + 汇总 verify_k_accept 7/7 + 全量回归 0 异常）

### 零、上轮修复复核清单

| 上轮条目                      | 现状                                                        | 证据                     |
| ----------------------------- | ----------------------------------------------------------- | ------------------------ |
| K0.1 chunk 两参               | ✅仍在（5 处调用点零漏网）                                  | main_window.py:1323 等   |
| K0.2 引导互斥早退             | ⚠️部分实现（入口早退在位；菜单禁用+静默反馈缺失→本轮 L1.1） | main_window.py:1147/1163 |
| K0.3 选择器重建               | ⚠️主场景已修（回落分支残留快照源→本轮 L1.2）                | main_window.py:1264/1277 |
| K1.1 失败保缓存               | ✅仍在（粒度边界→本轮 L1.4）                                | opencode_data.py:242     |
| K1.2 in-flight 全集           | ✅仍在（残余缩水→本轮 L1.3）                                | go_quota.py:408-430      |
| K1.3 isinstance 校验          | ✅顶层在位（深层缺口→本轮 L1.5）                            | browser_creds.py:508-512 |
| K1.4 published_at 兜底        | ⚠️RSS 在位（JSON 同字段漏网→本轮 L1.6）                     | opencode_data.py:333     |
| K1.5 索引化渲染               | ✅完整（窗口期错位经时序证明不存在）                        | main_window.py:1248/1298 |
| K2.1-K2.3 白名单/timeout/死键 | ✅全部在位（26 键差集为零）                                 | static_config.py:71 等   |
| K3.x 清理与说明区             | ✅在位（两处小漏网→本轮 L3 组）                             | 各文件                   |

### 一、P0-P3 修复清单

**中：**

| 文件:行号                             | 类型    | 描述                                                                                                                                                                          | 建议                                                                                                                                                            | 性质                              | 影响面          |
| ------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | --------------- |
| ui/main_window.py:510-542,1348        | ①⑥      | **饼图弧色恒绿**：\_arc_color 仅以 quota_chunk_color(0,...)（OK 绿）赋值，渲染不联动弧色——高用量账户进度条红色而饼图弧仍绿；:490 注释"双色圆弧"与 :520"分级色圆弧"自相矛盾    | **已裁定方案 A（分级色，2026-08-23 用户确认）**：控件持有 theme 名 + set_used_percent 内按 quota_chunk_color(percent, theme) 联动弧色三档变色；两处矛盾注释统一 | 遗留（P16 起）                    | UI 展示一致性   |
| **低：**                              |
| 文件:行号                             | 类型    | 描述                                                                                                                                                                          | 建议                                                                                                                                                            | 性质                              | 影响面          |
| ------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------                                                                                              | --------------------------------- | --------------- |
| ui/main_window.py:805-813,1147        | ②⑬      | K0.2 部分实现：菜单动作引导期间未禁用且早退静默 return 无反馈                                                                                                                 | \_guide_active 切换时同步 setEnabled 菜单动作；至少早退补状态栏提示                                                                                             | A016 修复自身缺陷（部分采纳）     | UX              |
| ui/main_window.py:1277                | ①需验证 | K0.3 回落分支仍读启动快照 self.\_config.quota_account（会话内切 B 后若 B 中途消失回落到 A；可达性窄）                                                                         | 回落改 load_config().quota_account 或切换回调回写 self.\_config                                                                                                 | A016 修复自身缺陷                 | UI 交互（边缘） |
| ui.json:90 + main_window.py:260       | ⑤⑫      | button_labels.theme 死键被契约反向固化（删键反触发 RuntimeError）                                                                                                             | ui.json 与 \_UI_STRUCT_KEYS 两处一体删除                                                                                                                        | 遗留（PL003.2 漏网）              | 配置卫生        |
| modules/go_quota.py:408-467           | ①⑬      | 失败占位项不入缓存（仅成功项 append）——部分账户失败时 in-flight/节流期"全集"缩为 M<N 条选择器闪缩丢失败项                                                                     | 占位项同样入缓存或缓存整份 results 快照                                                                                                                         | A016 修复自身缺陷（守卫范围不足） | 配额选择器      |
| modules/browser_creds.py:514,523      | ②       | isinstance 只到顶层：result 键值为 null 时默认 {} 不生效链式 .get() 可抛 AttributeError；cookie 元素非 dict 未过滤                                                            | (resp.get("result") or {}) 取值式 + 循环内 isinstance 过滤                                                                                                      | A016 修复自身缺陷（校验深度）     | 引导流程        |
| modules/opencode_data.py:240-248      | ①⑬      | has_data 整体守卫下单源失败空覆盖：Releases 失败宽容返回 [] 但整体有数据 → 空 releases 覆盖缓存（官方动态从有变空）                                                           | per-source 合并失败源沿用旧字段，最低限度 :240 注释声明取舍                                                                                                     | 遗留边界                          | 数据页官方动态  |
| modules/opencode_data.py:333          | ①②      | JSON 路径 release.get("published_at","") 遇显式 null 得 "None" 字面量（tag_name 同式；body 已有 or ""）——K1.4 同型漏网另一路径                                                | 改 str(release.get("published_at") or "")                                                                                                                       | A016 修复自身缺陷                 | 官方动态列表    |
| ui/main_window.py:1234                | ⑥       | \_render_quota 函数头注释失实："失配回落首个有效项"K0.3 后不可达（实际回落持久化值→保持首项不保证有效性）                                                                     | 按 K0.3 现状重写该句                                                                                                                                            | A016 修复自身缺陷                 | 文档            |
| ui/main_window.py:1466-1477,1441-1459 | ⑥       | 说明区类型清单缺 _DataSignals/\_DataPageTask；常量清单缺 USAGE_TAB_TITLE/THEME_LABELS/QUOTA_ACCOUNT_\* 六键                                                                   | 补条目                                                                                                                                                          | 遗留+A016 未完全覆盖              | 文档            |
| ui/main_window.py:1111-1116           | ⑧⑨      | error 路径 seq 失配直接 return 不清 \_usage_pending → 残留至下次成功后冗余补发一次全维度查询                                                                                  | seq 匹配分支追加 \_consume_pending()                                                                                                                            | 遗留（F0.2 边角）                 | 性能微小        |
| README.md:165-187                     | ⑥       | 配置参数表多处失实："ver 0.203"快照腐化/table_headers 键名错（实为 data_table_headers）/已删键 notify_message_fallback 仍在列/palettes 描述过时/base.json 表漏列 PL002 四新键 | 文档批次统一同步                                                                                                                                                | 新增                              | 文档            |
| modules/opencode_data.py:402          | ⑥       | 说明区 \_R_BLOCK_PATTERN 常量名失实（实际 \_R_OBJECT_PATTERN）——K3.5 重写漏网符号名                                                                                           | 改真实名                                                                                                                                                        | 新增                              | 文档            |
| modules/opencode_usage.py:744         | ⑥       | 说明区"关联配置"缺 base.json/ui.json 键列                                                                                                                                     | 补列                                                                                                                                                            | 遗留                              | 文档            |
| modules/go_quota.py:358 vs 412-419    | ①轻⑪    | in-flight 副本强制 ERROR_STAGE_NETWORK、节流副本不设——同为缓存语义元数据不一致（UI 当前无行为差异）                                                                           | 对齐其一                                                                                                                                                        | A016 修复引入（无害现状）         | 无直接影响      |
| modules/go_quota.py:396,428,440       | ⑧       | \_fetch_in_flight check-then-set 与缓存读写均在 QThreadPool 池线程（手动+定时叠加可真并发偶发重复拉取一轮），对照 usage 任务主线程标志模式不一致                              | threading.Lock 包裹状态段或对齐 usage 主线程模式                                                                                                                | 升级为低正式项（证据确凿后果轻）  | 配额刷新链路    |

### 二、参考级观察项（18 条合并，用户复核全部维持豁免）

并发细目（check-set 字节码间隔极小/后果上限多拉一轮）、双 cookie findData 取首条（save 覆盖语义使 UI 无法自然产生）、QInputDialog authCookie 明文回显、索引取目标同构逻辑两份、页签 index==1 魔法数字、errors[:2] 截断、\_apply_theme 构建期双重调用、colors 嵌套子键无契约、formatter 参数单实现、CDP source 中文硬编码、ui.json 数值标量无 H0.4 式契约、save_config 并发理论竞态、file_utils 缓存键大小写、logger 非法 level 静默回退、retry 计数口径、空数组块判真、\_quota_card dict frame/title 键零读取、UA 值外观。

### 三、亮点

A016 的 K 系列 22 条历经全文深挖**零回退**，三条高严重度修复主体质量扎实（K0.1 五处调用点零漏网、K1.5 两端对齐且窗口期错位经时序证明不存在、pending 生命周期闭环成立）；白名单 26 键机械比对零差集；版本三处一致 ver 0.242；新发现问题集中于"修复建议部分采纳"与"重写未同步注释"，无崩溃级/数据级回归。

## PL006. 前后端接口层：AppService 门面 + 统一任务运行器实施方案（2026-08-24）

> 来源：架构演进讨论（2026-08-24）——UI 作为前端、modules 功能实现作为后端，两者当前为
> "点对点直连"无正式接口；目标建立接口层使前端可整体替换（含远期 QML 评估）而后端不动。
> 现状诊断：main_window 直接 import 五个 modules 的 8 类符号，并自建 5 个 QRunnable 任务类
> （\_UsageTask/\_QuotaTask/\_DataPageTask/\_ExportTask/\_CdpGuideTask）+ 4 组 Signals 承载编排；
> 后端函数签名任何变更都会引发 UI 层大面积连带修改（PL001-PL005 历次连带即证据）。
> 状态：📌 方案已确认，待实施

### 架构设计

```
services/                  ← 纯 Python 后端门面（零 Qt——换前端时原样带走）
├── __init__.py            ← get_service() 单例入口 re-export
└── service.py             ← AppService + ServiceError：粗粒度方法聚合全部后端编排

ui/
├── task_runner.py         ← TaskRunner(QObject)：Qt 异步设施（线程池 + 信号回传）
├── main_window.py         ← from services import get_service；不再 import 任何 modules
└── ...                    ← 换前端 = 整个 ui/ 替换，task_runner 随之重写（内部零业务，成本≈0）
```

**归属判定规则**（A017 讨论定案）：一段代码是否归 ui/，看它**替换前端时是否必然重写**。
必然重写 = 归 ui/（TaskRunner 符合——Web 前端的异步设施是队列/WebSocket 而非 QThreadPool）；
可原样带走 = 归 services/（AppService 符合）。多前端并存形态（ui/qt6/ 与 ui/qml/ 并列 +
main.py --frontend 分发）为远期目标，**启用第二前端那天才执行结构搬迁**（YAGNI，现在不做）。

**三条纪律**：

1. **Service 纯 Python 零 Qt**——保持 modules 可测试性，QML/Web 前端未来可直接复用；
   services/ 目录零 PyQt6 import 可机械断言（对齐白名单机械比对思路）
2. **DTO 第一版直接透传 modules dataclass**（UsageData/list[GoQuotaInfo]/ModelDataSnapshot）——
   类型共享属弱耦合可接受；独立 DTO 层留待 QML 迁移需要可序列化结构时再建（避免无谓样板）
3. **UI 只 import services，不再直接 import 任何 modules 符号**（browser_creds 的 CDP 编排
   整体迁入 Service）

### 任务分解

#### PL006.1 services/service.py 门面

- AppService 单例（get_service()），方法聚合现散落 main_window 的编排逻辑：
  - `resolve_db_path() -> Path | None`（find_db_path 包装）
  - `get_usage(db_path: Path | None) -> UsageData`（内聚 OpenCodeDB 打开/totals/by\_\* 循环/
    DIMENSIONS 推导/TABLE_LIMIT 分档/close 全套，原 \_UsageTask.run 主体）
  - `get_quotas() -> list[GoQuotaInfo]`（= fetch_go_quota 直通）
  - `get_data_page() -> ModelDataSnapshot`（= refresh_data_page 直通）
  - `export_data(db_path, out_dir) -> None`（OpenCodeDB + export_all，原 \_ExportTask.run 主体）
  - `save_account(ws, cookie)`（= save_dashboard_credentials）
  - `add_account_via_cdp(login_wait_seconds=None) -> tuple[str, str]`（CDP 五步编排 +
    \_wait_for_login_cookie 整体迁入，返回 (auth_cookie, workspace_id)，失败抛 ServiceError）
- ServiceError(Exception)：业务错误基类（message 中文），UI catch 后按各自模板格式化
- services/**init**.py re-export get_service（消费方 from services import get_service）

#### PL006.2 ui/task_runner.py Qt 异步设施

- TaskRunner(QObject)：`finished = pyqtSignal(int, object)` / `failed = pyqtSignal(int, str)`
- `run(fn: Callable[[], Any], *, seq: int = 0)`：fn 提交 QThreadPool，成功发 finished(seq, 结果)、
  异常发 failed(seq, str(exc))
- 定位说明：随前端生灭的异步传输设施（内部零业务逻辑）；ui.json 文案格式化留在 UI 层
  （failed 载荷为原始异常串，模板归属展示层）

#### PL006.3 main_window 切换调用

- 四个数据任务类删除，改 TaskRunner.run(service.get_usage/. get_quotas / .get_data_page /
  lambda: service.export_data(...))；五组 Signals 收敛为 runner 一组（usage_ready/quota_ready/
  data_ready 由 finished(object) 载荷区分，handler 不变）
- \_CdpGuideTask 删除，改 TaskRunner.run(lambda: service.add_account_via_cdp(...))，
  success/failed 双语义由 on_done/on_error 回调承载（workspace_id 经结果元组携带）
- import 区收敛：删除全部 `from modules...` 行，仅保留 `from services import get_service`
  与 `from ui.task_runner import TaskRunner`
- MainWindow 可注入性保留（quota_fetcher/db_path 注入参数改为注入 service 或 stub 函数）

#### PL006.4 验证与收尾

- 探针：Service 各方法行为等价断言（对照迁移前输出）；TaskRunner 成功/异常双路径；
  offscreen GUI 冒烟全流程
- 全量回归 0 异常（重点盯 usage/export 相关历史脚本）
- README 项目结构段补 services/ 与 ui/task_runner 说明

### 技术要点与硬限制

- services/ 目录零 PyQt6 import（含类型注解）——AST 机械断言纳入验收
- in-flight/pending 等 UI 侧去重标志留在 main_window（它们是交互语义非业务逻辑）
- \_wait_for_login_cookie 迁入 Service 时其内部 fetch_dashboard_usage 依赖随迁
- 渐进可回滚：PL006 为纯重构行为不变，任一步回归不过即可回退 git
- 多前端并存（ui/qt6/ 与 ui/qml/ 并列 + main.py --frontend 分发）不在本批实施——启用第二
  前端那天执行结构搬迁，届时 services/ 无需任何改动

### 工作量估算

| 部分             | 内容      | 估算        |
| ---------------- | --------- | ----------- |
| Service+Runner   | PL006.1-2 | 半天        |
| main_window 切换 | PL006.3   | 半天        |
| 验证收尾         | PL006.4   | 2 小时      |
| 合计             |           | **约 1 天** |

### 已拍板决策（2026-08-24 记录在案）

1. 版本号？ - 定版 **V0.2.5.1**（2026-08-24 用户指定；四段式第三位=功能批次、第四位=批次内序号）

## PL007. 主题资源文件夹化：theme 与代码彻底解耦实施方案（2026-08-24）

> 来源：架构演进讨论（2026-08-24）——主题应作为纯声明式资源管理于独立文件夹，不含任何
> 代码或仅为自身存在的格式代码；新增主题不应要求修改 Python。
> 现状诊断：颜色数据已外置 ui.json palettes（✅），但两处耦合残留：①QSS 模板是
> themes.py 的 Python 字符串常量（样式结构写死在代码里）；②四主题共用一份模板且调色板
> 数据在 ui.json 而非主题自身——新主题无法表达结构性差异，且主题资产分散三处
> （themes.py 模板/ui.json palettes/ui.json theme_labels）。
> 状态：📌 方案已确认（A017 讨论修正：加载器与资源分离），待实施

### 目标结构

```
ui/
├── theme_loader.py          ← 唯一的 Python 代码：加载器 + 契约校验 + 导出 API
│                               （get_theme/quota_chunk_color/THEME_NAMES/DEFAULT_THEME_NAME/
│                                 QUOTA_WARN_PERCENT/QUOTA_DANGER_PERCENT/QUOTA_COLOR_OK）
└── themes/                  ← 纯声明式资源文件夹（零 .py 文件，不是 Python 包）
    ├── _templates/
    │   └── base.qss         ← 共享结构模板（{var} 变量语法）
    ├── light/
    │   └── theme.json       ← display_name/font_family/palette{全部色键含动态色六键}
    ├── dark/theme.json
    ├── console/theme.json
    └── panel/theme.json
```

**关键设计决策**：`themes.py` 与 `themes/` 不能同名共存（Python 硬约束）——
加载器改名 `theme_loader.py`，`themes/` 成为零 .py 的纯资源文件夹。
消费方 import 改为 `from ui.theme_loader import ...`（一次性替换）。

**解耦达成标准**：新增主题 = 新建文件夹 + 一个 theme.json，不改任何一行 .py 重启即在
下拉框出现；调整样式结构 = 编辑 base.qss 一处四主题同步生效。

### 任务分解

#### PL007.1 资源文件落地

- 新建 ui/themes/ 资源文件夹：\_templates/base.qss（\_QSS_TEMPLATE 内容平移）；
  四主题 theme.json（display_name 承接 ui.json theme_labels；font_family 并入 palette；
  palette 含全部色键含动态色六键）
- 删除 ui/themes.py（被 theme_loader.py 替代）
- ui.json 清理：palettes/theme_labels 键移除；**保留 "themes": [...] 数组**作为注册顺序
  权威（settings.THEMES/base.json default_theme 校验链零改动）
- theme.json schema：{display_name, font_family, palette:{30+ 色键含动态色六键}}

#### PL007.2 加载器改造

- 新建 ui/theme_loader.py：读 ui.json themes 注册表 → 逐主题加载 theme.json
  （json 解析错误/缺文件 RuntimeError）→ 契约校验链全部保留适配文件源：
  容器类型 H3.1/I0.1、值类型 E3.9、占位符残留 A3.5、themes↔注册表一致 C0.6、
  长度下限 A3.5、动态色必含 PL003.1.d
- 导出 API 同名同签名（get_theme/quota_chunk_color/THEME_NAMES/DEFAULT_THEME_NAME/
  QUOTA_WARN_PERCENT/QUOTA_DANGER_PERCENT/QUOTA_COLOR_OK）
- 消费方 import 行替换：from ui.themes → from ui.theme_loader（main_window/system_tray/settings）
- settings.py THEMES 白名单引用 _SC.ui["themes"] 不变 ✅

#### PL007.3 验证与收尾

- 探针：四主题 QSS 逐字节等价断言（对照迁移前黄金基线）；契约触发断言（删 theme.json
  动态色键/改坏占位符各抛 RuntimeError）
- 全量回归 0 异常 + offscreen 冒烟四主题切换
- README 主题章节补"自定义主题 = 新建文件夹"指引

### 技术要点与硬限制

- **themes.py 与 themes/ 不能同名共存**（Python 硬约束）——加载器必须用不同文件名
- ui.json themes 数组是注册顺序唯一权威；文件夹多出未注册的主题目录视为无效不加载
- 契约校验只增不减：A3.5/C0.6/E3.9/H3.1/I0.1/PL003.1.d 全部保留，文件源适配
- base.qss 中 QSS 自身花括号不受 {var} 替换影响的原机制照搬

### 工作量估算

| 部分            | 内容      | 估算            |
| --------------- | --------- | --------------- |
| 资源拆分+加载器 | PL007.1-2 | 半天            |
| 验证收尾        | PL007.3   | 2 小时          |
| 合计            |           | **约半天~一天** |

### 已拍板决策（2026-08-24 记录在案）

1. 版本号？ - 定版 **V0.2.5.2**（2026-08-24 用户指定；与 PL006 的 V0.2.5.1 同属 V0.2.5.x 功能批次，第四位为批次内序号）
2. 目录命名？ - 加载器 `theme_loader.py` + 纯资源文件夹 `themes/`（A017 讨论：themes.py 与 themes/ 不能同名共存，Python 硬约束；消费方 import 一次性替换为 from ui.theme_loader）

---

## 附录 A018：全量代码审计报告（第18轮，2026-08-25）

> 范围：main.py + modules×7 + services×1 + ui×5 + utils×7 + config×4 + JSON 资源×8；三路并行代理全文审读 + git 双提交回归比对 + AST 机械扫描 + offscreen 实测
> 重点：PL006 接口层重构（b562ad1）与 PL007 主题文件夹化（8dfe5d4）两批新代码连带
> 结果：**P 级 21 条（中 3 / 低 18，无高）/ 参考级观察项 23 条全部维持豁免（用户复核确认）**
> 状态：📌 待修复（M 系列任务清单见 x.progress.md）

### 零、上轮修复复核清单

| 上轮条目                                | 现状                       | 证据                           |
| --------------------------------------- | -------------------------- | ------------------------------ |
| L1.1 菜单禁用+早退反馈                  | ✅在位（启停对称完整）     | main_window.py:932-936/943-953 |
| L1.2 回落 load_config                   | ✅在位                     | main_window.py:1095            |
| L1.3 占位项入缓存                       | ✅在位                     | go_quota.py:463-473            |
| L1.5 CDP 深层校验                       | ⚠️在位但漏网一处→本轮中项② | browser_creds.py:508-535       |
| L1.6 published_at/tag_name 兜底         | ✅三键齐                   | opencode_data.py:334-338       |
| L1.7 状态锁                             | ⚠️在位但覆盖不全→本轮中项① | go_quota.py:401,413,477        |
| L2.1 饼图分级色联动                     | ✅在位（双触发点）         | main_window.py:340/346/349-353 |
| L2.x theme 死键删除                     | ✅无回归                   | ui.json button_labels          |
| L3.3 pending 消费                       | ⚠️半修复→本轮低项          | main_window.py:902-903         |
| ERROR_STAGE 对齐/说明区/README 参数表等 | ✅全部在位                 | 各文件                         |

### 一、P0-P3 修复清单

**中：**

| 文件:行号                                      | 类型 | 描述                                                                                                                                                                                                                                                                                                   | 建议                                                                                                                                                       | 性质                          | 影响面       |
| ---------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | ------------ |
| modules/go_quota.py:353-361,391-392,444 vs 413 | ①⑧   | **节流分支绕过 in-flight 挡板**：线程 B 刷新中每完成一账户即更新 _last_success_at 并渐进写缓存，线程 A 在 :410 先命中节流拿到只有部分账户的列表，提示误导为"距上次刷新不足 60 秒"——K1.2/L1.3 反复修的"选择器闪缩"残余通道，L1.7 锁只护标志未护缓存读写                                                 | (a) 节流检查感知 in-flight；或 (b) 整轮完成后一次性提交快照（循环内只填 results，return 前 _last_quotas=results 单次更新时间戳），顺带修正 L1.7 注释失实处 | A017 修复自身缺陷（覆盖不全） | 配额选择器   |
| modules/browser_creds.py:521-523               | ②⑬   | **CDP cookie 的 domain 显式 null 时 TypeError**：.get("domain","") 默认值仅键缺失时生效，null 返回 None → in None 抛 TypeError；该行在 try 块外异常逃逸打断登录轮询并外显英文原文（name/value 均已防护唯 domain 漏网）                                                                                 | 改 OPENCODE_HOST in (cookie.get("domain") or "")，一行闭合                                                                                                 | A017 修复自身缺陷（漏网）     | 引导流程     |
| ui/main_window.py:1008（连接 :483）            | ①⑪⑬  | **\_on_guide_failed(self, message) 与 TaskRunner.failed(int,str) 签名失配**：PL006 统一信号加 seq 后唯此 handler 未同步——offscreen 实测 PyQt6 位置截断使 message=7(int)，showMessage 抛 TypeError，任何一次引导失败状态栏都不显示原因且 stderr 打 traceback；漏测根因：verify 全部直调方法绕过信号机制 | 签名改 (self, seq, message)；verify 补经信号 emit 的端到端断言                                                                                             | 新增（PL006 重构漏网）        | 引导反馈链路 |

**低：**

| 文件:行号                                                                                      | 类型 | 描述                                                                                                                                                                                                      | 建议                                                                       | 性质                        | 影响面               |
| ---------------------------------------------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | --------------------------- | -------------------- |
| ui/main_window.py:902-903                                                                      | ①⑧⑬  | _on_load_error seq 失配分支直接 return 不清 _usage_pending（匹配分支 :804-808 已消费）——悬挂至下个刷新周期才冗余补发全维度查询                                                                            | 失配分支改 self._consume_pending(); return                                 | A017 整改半成品（遗留残余） | 用量刷新链路         |
| ui/main_window.py:302-307（关联 :55/:1287）                                                    | ④⑤⑥  | 本地 UsageData 死类遮蔽 services import：实测两类身份不等，import 失效、注解指向影子类、DTO 双源漂移风险；说明区宣称与现状矛盾                                                                            | 删本地类让 import 生效                                                     | 新增（PL006 残留）          | 类型体系             |
| ui/main_window.py:74-75,1261                                                                   | ⑤    | TABLE_LIMIT_GROUP/DAY 迁 services 后死常量（全文零使用）+ 说明区仍列                                                                                                                                      | 删除常量及条目                                                             | 新增（PL006 残留）          | 代码卫生             |
| ui/main_window.py:385-390,11,13                                                                | ⑤    | _CdpGuideSignals 死类（全项目零引用）连带 QObject/QRunnable 未使用 import                                                                                                                                 | 删类清 import                                                              | 新增（PL006 残留）          | 代码卫生             |
| system_tray.py:57,105,120 + main.py:116,139 + config/settings.py:26-27 + ui/main_window.py:681 | ⑥    | PL007 文档残留批次（同一根因七处合并）：注释/说明区仍写已删除的 ui.themes/ui/themes.py/theme_labels，现口径为 theme_loader 与 theme.json display_name                                                     | 一批次统一替换                                                             | 新增（PL007 连带漏网）      | 文档                 |
| ui/main_window.py:1258-1349                                                                    | ⑥    | 说明区缺 PL006 新函数条目：_usage_job/_consume_pending/_set_guide_actions_enabled；_RemainingPieChart 无方法条目                                                                                          | 补条目                                                                     | 新增（PL006 漏网）          | 文档                 |
| ui/task_runner.py（全文）                                                                      | ⑥    | 缺文件末尾 # ===== 模块说明区（硬规范）                                                                                                                                                                   | 补说明区                                                                   | 新增（PL006 漏网）          | 文档                 |
| services/service.py:94,112                                                                     | ③⑥   | db 缺失文案硬编码且缩水：迁移前读 ui.json no_db_found（含环境变量自救提示），现硬编码丢提示；:112 与 ui.json no_db_export 双处维护——说明区自我豁免不成立（UI 直接展示 message）                           | ServiceError 读 \_SC.ui["status_messages"] 对应键                          | 新增（PL006 迁移偏差）      | 错误提示             |
| modules/go_quota.py:359 + modules/opencode_data.py:66                                          | ③⑪   | 节流提示 f-string 硬编码两处，同族 no_credentials/in_flight 已外置 go_quota_error_messages——同组不同轨                                                                                                    | 并入该组模板共用                                                           | 新增                        | 配置一致性           |
| modules/opencode_data.py:215-250                                                               | ⑧⑪   | refresh_data_page 无 in-flight 去重（自称"对齐 go_quota 同式"只对齐一半）：双击刷新并发打三源接口白耗 GitHub 匿名限额，_last_snapshot 最后完成者胜旧覆新                                                  | 移植 D0.4/L1.7 标志+锁，或注释显式声明取舍                                 | 新增                        | 数据页刷新           |
| modules/opencode_data.py:327-329                                                               | ②    | GitHub API 限速返回 dict 时 data[:_RELEASE_LIMIT] 抛 TypeError 回退 RSS——限速期每轮浪费一次注定失败的 JSON 请求，失败原因仅 debug 日志                                                                    | 补 isinstance(data, list) 校验前置回退                                     | 新增                        | 数据页官方动态       |
| services/service.py:30 ↔ ui/main_window.py:108                                                 | ④    | DIMENSIONS 六维元组双份字面量（service 编排用 + main_window 契约校验/下拉构建用），加维度三点同步                                                                                                         | 由 services 导出 DIMENSIONS 单点                                           | 新增（PL006 收敛未竟）      | 跨模块               |
| ui/main_window.py:46-49,881,615 + .temp/verify_pl006_accept.py:61-63                           | ⑪⑥   | PL006 纪律 3 偏差：ERROR_STAGE_*/QUOTA_WINDOW_KEYS 以运行时逻辑用途直取 modules（非 DTO 注解），豁免注释覆盖不了；verify ③ 仅断言两个编排 import 字符串，x.progress"UI 零 modules import"表述宽于实际断言 | services 再导出这批常量（或判断函数下沉）；verify 升级白名单断言；措辞同步 | 新增（PL006 边界裁量）      | 架构纪律             |
| services/service.py:37,150,192                                                                 | ⑤⑥   | CDP_WAIT_TIMEOUT 常量定义后零使用（:150 裸读 base.json），且说明区常量清单漏列该符号——死代码与硬编码直读并存                                                                                              | :150 改用常量并补说明区条目                                                | 新增（PL006 迁移漏替换）    | 代码卫生             |
| AGENTS.md:8 + x.progress.md:15                                                                 | ⑥    | 导入验证命令假阳性：命令仍含 ui.themes（被 namespace package 机制解析为空模块静默假通过），缺 ui.theme_loader/services.service/ui.task_runner——IMPORT OK 对 PL007 加载器契约链零覆盖                      | 替换并补新层模块名                                                         | 新增（PL006/PL007 连带）    | 回归验证链路         |
| ui/theme_loader.py:19,105                                                                      | ②⑬   | 导入期 IO 失败形态不一致：base.qss 缺失抛裸 FileNotFoundError/UnicodeDecodeError，themes 目录整体缺失裸 OSError——对比 _load_theme 的中文契约 RuntimeError，违背自身声明的契约风格统一诊断                 | try 包装或 is_file 预检，消息对齐 _load_theme 口径                         | 新增（PL007）               | 可诊断性（打包场景） |
| ui/theme_loader.py:82-84                                                                       | ②    | E3.9 契约错误消息缺主题名前缀，四主题手改坏任一 palette 无法定位来源文件，与 _load_theme 消息风格不一                                                                                                     | _build_theme 增加 name 参数注入消息                                        | 新增（PL007）               | 多主题诊断           |
| README.md:42                                                                                   | ⑥    | 特性段"浅色/深色双主题一键切换"与 :109 四主题表述自相矛盾（PL007.3.c 只同步了结构树/配置表/指引三处）                                                                                                     | 改四主题表述                                                               | 新增（PL007 漏网）          | 文档                 |

### 二、参考级观察项（23 条合并，用户复核全部维持豁免）

ServiceError 分类退化（YAGNI 待 QML 诉求）、Chrome UA 字符串双份、SUBPROCESS_TIMEOUT float/int 风格、解密失败旧凭据缓慢膨胀、services 导入路径混用、Releases 拉 5 取 3、login_wait_seconds 负值文案无入口、save_account 空值落盘下游过滤、CLI fetched_at UTC 输出、quota_chunk_color 非数值裸 TypeError（调用点 int 保证）、get_static_config 无锁竞态不可达、"≥80%" 注释快照、AGENTS verify 计数漂移、退出时 QThreadPool waitForDone 阻塞（非回归需验证）、export 任务无消费者 seq、has_loaded 跨对象写公开属性、_live_tasks 无上限不可达、THEME_LABELS fallback 不可达、load_config 裸调缺口不可达、A017 已豁免 18 项维持、x.progress "29 键"措辞出入。

### 三、亮点

- 上轮 L 系列 19 条**零回退**（两处覆盖缺口升级为本轮正式项）；A016→A017→L 三代修复链完整
- PL006 门面迁移语义逐行等价验证通过（\_wait_for_login_cookie/get_usage/CDP 五步编排），services 零 PyQt6 机械断言达成，except ServiceError: raise 较迁移前更正确
- PL007 本体扎实：四主题 palette 30 键机械核对完全一致、base.qss 占位符 ⊆ palette 零残留、C0.6/E3.9/A3.5 契约链文件源适配完整保留
- 机械扫描干净：函数内 import/嵌套 def 零命中；utils 公共工具零重复实现；SQL mode=ro、DPAPI 对称、原子写、白名单 26 键双向零差集
- 本轮问题集中于新批次文档/说明区连带漏改与重构残尾，无运行时崩溃级缺陷、无安全项

---
