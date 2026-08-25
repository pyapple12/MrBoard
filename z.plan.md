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

- **外部约束**：browser_creds --remote-allow-origins=\*（Chrome 137+ 无此参数 CDP 必 403）/ DASHBOARD 请求参数硬编码 / CDP 探测族 3 固定值不入配置 / UA Chrome/126 版本号时效（2026-08-26 归并，A017——跟随 Chrome 升级手改，非代码缺陷）
- **数据/数学常量**：BUNDLED_PRICES 数据快照 / COST_COMPARE_DIGITS 浮点容差 / \_EPOCH_MS/\_DAY_MS 数学基准 / $ 硬编码（OpenCode 计费固定 USD）
- **设计定案**：retry 默认值语义分离（A019「retry 默认值与 base.json 不一致」观察项命中本条，2026-08-26 记账）/ retry 参数类型不校验（内部 API 调用方可控）/ 双份 themes 解析（各防护独立）/ toggle_theme 不即时持久化（退出即存设计）/ logger LOG_LEVEL 静默回退（B2 断言固化）/ convert 下划线字面量（B1 断言固化）/ restoreGeometry 静默回退（宽容策略一致）/ 本地覆盖缺字段按免费估算（B4 说明区记录）/ file_utils 缓存无业务写入方（C1）/ themes QUOTA_COLOR 常量名缩写（指代明确非失实）/ system_tray MENU_LABELS 依赖导入顺序（无可达路径）/ 浏览器: 文案硬编码（单次使用无调参场景）/ logger 注释措辞（字面仍成立）/ 说明区契约列举省略 dialog 组（已校验在位，叙述省略）/ 估算忽略 reasoning token（设计定案，w.study.md 记录，仅估算回退路径）/ 托盘不可用时 notify 无效调用（Qt 静默忽略无副作用）/ 配额选择器索引取目标同构不抽共享（2026-08-26 归并，A017+A019 已裁定抽象收益<成本）/ 托盘色固定 light palette 与 colors 双源并存（PL003.1.e 托盘无主题语义）/ Edge-only 用户 CDP 前置体验（产品范围定案仅支持 Chrome）/ CDP source 中文硬编码（单次内部诊断文案）/ http_get 不强制 UA（责任分散调用方取舍）/ formatter 参数单实现 YAGNI / go_quota/data 缓存存储差异 error vs errors（两模块数据形态不同）/ _wait_for_login_cookie worker 归属已核实（阻塞 sleep 仅存在于 QThreadPool worker）/ 配置契约键集人工维护（P23 契约层定案直接覆盖——显式声明+导入期校验为健康标准）/ 空数组块判真（Python truthy 有意依赖）/ export 任务 seq 统一签名代价 / has_loaded 公开属性 YAGNI 封装 / used_percent getter 供探针断言（删除致验收脚本失效）/ x.progress "29 键"历史措辞出入（历史文档 append-only 不回改）/ load_config 裸调缺口（四处调用点 try 全覆盖已核实闭环）/ _profile_dirs 前缀匹配宽容为刻意设计（2026-08-13 定案——startswith("Profile") 兼容 Chrome 官方命名及未来变更；精确化收益<规则依赖风险，本机无 Profile 目录属验证盲区；误匹配已被单浏览器 try 兜底）
- **性能可接受**：每 profile 整库复制（一次性引导流程）/ exporter 查询全量驻留（单次导出）/ network 每次 get_static_config（单例查找零 IO）/ ORDER BY 无索引（**外部库只读不可建索引**，仅 CLI 路径毫秒级）/ toggle 每次全量文件 IO（低频非热点）/ system_tray 每次重建 QPixmap（刷新间隔受限）/ \_show_columns_menu 每次 new QMenu（父挂载自动回收；O3.2 已补 deleteLater 加固）/ pending 双渲染幂等微瑕（2026-08-26 归并，A016）/ \_apply_theme 构建期双重调用（幂等无害冗余）/ pricing \_load_cached_prices TTL 失效重复读盘
- **并发理论**：go_quota 模块级缓存无锁（worker 串行）/ static_config 无锁单例（import 期）/ browser_creds 模块级无锁（B0.8 已停定时器）/ ws.recv 不按 id 匹配（未 enable domain）/ sqlite_utils 线程契约（同线程消费）/ 导出无防重入（原子写保完整性）/ 连点启动 N 个 QuotaTask（go_quota 节流兜底）/ go_quota in-flight stage 与 UI 引导卡交互（已核对闭环）/ go_quota 模块级缓存无锁理论竞态定时手动叠加（2026-08-26 归并，A016）/ in-flight check-set 字节码间隔极小（后果上限多拉一轮，A017）/ save_config 并发理论竞态（UI 单线程顺序触发，A017）/ 凭据 TTL 缓存 check-set 无锁（生产方受 in-flight 去重约束，A020）/ load_price_map 无锁并发双拉（write_json 原子替换最终一致，A020）/ get_service 单例无锁（AppService 无状态双初始化无害，A020）/ _live_tasks 无上限（固定 runner 数约束不可达，A018）/ Windows terminate 即 TerminateProcess 等价 kill 无需升级（A020）
- **外观**：main_window 绘制细节（饼图角度/内缩/截断/内联 QSS）/ system_tray 图标几何（比例）/ paintEvent 无显式 end（Qt 析构自动）/ PIE_FONT_SIZE / 托盘几何 / 选择器 workspace_id[:8] 截断（2026-08-26 归并，A016）/ 页签 index==1 魔法数字（addTab 顺序注释固定，A017）/ errors[:2] 诊断截断惯例（A017）/ rstrip 数值展示规整（A019）/ CLI fetched_at UTC 输出诊断口径（A018）
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
- 写缓存路径 GUI 线程假设（触发：写入路径迁至非 UI 线程）（2026-08-26 归并，A016）
- 凭据保存读改写非原子（触发：新增并发写凭据入口——当前 UI 主线程顺序执行物理不可达；若触发后果为丢失凭据条目，届时优先 service 层串行化）（2026-08-26 归并，A020）
- _manual_guide 模态期间定时刷新未暂停（触发：引导期间刷新错位复现）（2026-08-26 归并，A016）
- combo 失配脏值残留（触发：账户增删时序错位复现）（2026-08-26 归并，A016）
- 双 cookie findData 取首条（触发：多 cookie 共存场景出现）（2026-08-26 归并，A017）
- QInputDialog authCookie 明文回显（触发：安全要求提升——可选 Password 模式，涉"核对粘贴内容"UX 取舍需用户拍板）（2026-08-26 归并，A017）
- 时序排序无年份跨年理论错序（触发：跨年数据+排序异常复现）（2026-08-26 归并，A016）
- _time_clause 无前缀列名依赖 session 表结构（触发：session 表 schema 变更）（2026-08-26 归并，A016）
- themes 残留检测正则花括号误报（触发：palette 值含花括号）（2026-08-26 归并，A016+A019）
- to_int 浮点截断（触发：出现小数 token 输入）（2026-08-26 归并，A019）
- 三源全空不断流节流失效（触发：断网恢复期网络开销成为问题——per-source 合并评估）（2026-08-26 归并，A020）
- quota_chunk_color 非数值裸 TypeError（触发：调用链变更传入非数值）（2026-08-26 归并，A018）
- save_account 空值落盘下游过滤（触发：下游过滤被移除）（2026-08-26 归并，A018）
- login_wait_seconds 负值文案无入口（触发：负值配置）（2026-08-26 归并，A018）
- CDP 端口 TOCTOU（触发：端口冲突高频环境）（2026-08-26 归并，A016）
- CDP cookie domain 子串过滤（触发：连接非自启/远程调试实例——若触发存在取到他域 cookie 可能）（2026-08-26 归并，A020）
- CSV 公式注入（触发：导出文件对外分发场景——Excel 打开启用编辑可执行公式）（2026-08-26 归并，A020）
- retry nan/inf 理论路径（触发：json 手写 NaN 字面量）（2026-08-26 归并，A020）
- sqlite_utils UNC 路径 URI 解析失败（触发：网络盘路径支持需求）（2026-08-26 归并，A020）
- 退出 QThreadPool waitForDone 阻塞（触发：退出卡顿复现）（2026-08-26 归并，A018）
- 解密失败旧凭据缓慢膨胀（触发：凭据文件体积异常增长——清理涉凭据生命周期策略需谨慎）（2026-08-26 归并，A020）
- ServiceError 分类退化 YAGNI（触发：前端替换 QML/Web 需求出现）（2026-08-26 归并，A018）
- Releases 拉 5 取 3 数量语义双处（触发：数量语义变更需求）（2026-08-26 归并，A018+A020）
- file_utils 缓存键大小写（触发：路径大小写混用场景）（2026-08-26 归并，A017）

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

> 来源：人测反馈"UI 与内容呈现完善"前置收敛 + 2026-08-23 多轮对齐拍板。
> 背景根因：opencode.db 消息 JSON 无任何账号维度字段且多账号消息混写同一本地库——PL001 时间窗近似方案对"并行使用"物理不可分、对"串行切换"存在采样漏检，实用价值有限。
> 状态：✅ 已实施（2026-08-23，版本 ver 0.240）；原始方案全文见 git 提交 c4e6db9

- **目标形态**：tokens 用量回归纯净单视图（删账户时段下拉/导出标注列/后台切换日志，全量统计无任何账户概念）；Go 配额改"单卡 + 账号选择器下拉选谁显示谁 + 选择持久化"；凭据管理与托盘预警**原样保留**
- **实施结果（六部分去向）**：
  - 删 A 切换日志体系：credential_store/go_quota/main/main_window 四处 SWITCH_LOG 常量、load/save/detect 三函数、指纹链（credential_fingerprint 与 GoQuotaInfo.fingerprint——无 UI 消费者）、钩子调用点及说明区条目 → **保留**；定向探针被删符号 AttributeError 即 PASS
  - 删 B 时段截取链：opencode_usage intervals 形参全链与 CLI --account 参数及解析块 / exporter account_intervals+account_label 形参与 CSV 标注列 / main_window 账户下拉三常量+三方法+_UsageTask/_ExportTask 字段 / settings.account_filter 三件套 / ui.json 三键 → **保留**（since/until 为 --since 时间过滤与账户无关，原样保留严禁误删）
  - 配额区改造：数据层 fetch_go_quota 全量轮询零改动（60s 节流/in-flight 去重/缓存兜底原样——切换零延迟的数据基础）+ 卡片回归单张按选中 workspace_id 渲染（失配回落首个有效项，全无效渲染错误态）+ 选择器行 userData=workspace_id、标签外置 quota_account_label、选项按刷新 infos 重建 blockSignals 防回环 + quota_account 字段三件套切换即存失败 warning 降级 → **保留**
  - 清理与兼容：user_config account_filter 行与 switch_log.json 物理删除不留死键死文件；带旧残留键临时配置 offscreen 启动实证无错 → **保留**
  - 回归脚本清理与新验收：verify_pl001_accept/probe_pl001 系列删除 + verify_5a3/run_all_verify 白名单同步 + 新建 verify_pl004_accept 反向断言（无 switch_log 函数/无 intervals/无 account 标注/单卡按选中渲染等）→ **保留**
  - 文档同步与版本推进：README 改写"配额账户切换"说明 + 版本 ver 0.240 三处一致 → **保留**
- **技术要点（历史存档）**：时间窗近似方案退役后不再以任何形式重新引入用量侧账户区分（未来官方提供账号维度数据再立项）/ 账户标识统一 workspace_id 不留兼容层 / 托盘预警语义独立于卡片形态本次零改动 / 选择器选项来源=infos 实拉列表而非凭据原文（解密失败条目自然不出现避免选了加载不出）
- **决策记录（历史存档）**：A+B 全删纯净视图 / 单卡+选择器持久化 / 凭据数组追加式保存保留（删则选择器退化反复重抓凭据）/ 残留物物理删除 / 托盘零改动维持最紧有效账户保守语义 / 定版 ver 0.240

## PL005. 配额区"添加账户"常驻入口实施方案（2026-08-23）

> 来源：PL004 实施后缺口盘点——引导卡仅在全部账户凭据失效时显示，已有有效凭据时引入新账户没有任何 UI 途径（唯一途径是删凭据文件，丢失已存账户）。
> 状态：✅ 已实施（2026-08-23，版本 ver 0.241 独立定版）；原始方案全文见 git 提交 cf48728

- **目标形态**：配额区选择器旁常驻"添加账户"按钮随时可点 + QMenu 两路径（一键 CDP 自动获取/手动填写）+ 添加后自动刷新并自动选中新账户（pending 标志机制）；托盘零改动避免菜单膨胀
- **实施结果（三部分去向）**：
  - 入口按钮与菜单：ui.json 新键 quota_add_account_button + 选择器行尾 QPushButton 弹 QMenu 两项（文案复用 GUIDE_AUTO/MANUAL_BUTTON 不新增重复键）路由既有 _start_cdp_guide/_manual_guide → **保留**
  - 复用适配与闭环：**关键修复**——_on_guide_failed 原无条件 show 引导卡（已有有效凭据时从配额区触发失败界面语义混乱），提取 \_should_show_guide() 同源单点维护改按条件显示 / 添加后自动选中：一次性 pending 标志 _pending_quota_account，CDP 路径信号签名携带 workspace_id（带默认值向后兼容），\_render_quota 重建选项后优先匹配 pending 并清除 / 引导流程三件套全复用零平行流程，凭据写入统一走 save_dashboard_credentials 零新写路径 → **保留**
  - 验证与收尾：probe_pl005_entry 行为级探针（真实 save_dashboard_credentials 落盘验证）+ 全量回归 0 异常 + README 补说明 + 版本三处同步 → **保留**
- **决策记录（历史存档）**：入口位置配额区常驻按钮+QMenu 两路径托盘零改动 / 自动刷新自动选中 pending 机制 / 独立 ver 0.241 不并入 0.240

## 附录 A016：全量代码审计报告（第16轮，2026-08-23）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读；重点覆盖 PL001-PL005 五个版本新增/删除代码
> 结果：**P 级 19 条（高 3 / 中 8 / 低 8）/ 参考级观察项 26 条（用户复核全部维持豁免）**
> 状态：✅ 已修复（2026-08-23，K 系列 22 条全部完成，版本 ver 0.242；汇总反向验收 verify_k_accept 7/7 + 全量回归 0 异常；任务清单见 x.progress.md K 系列）

- **上轮复核（J 系列 4 项）**：4/4 全部在位零回退零漏改；PL001-PL005 新演进产生新问题见下
- **P0-P3（19 条）**：
  - 高（3 条确定性复现）：\_render_quota_card 的 quota_chunk_color 未传 theme_name——非 light 主题刷新进度条色重置回 light / 添加账户菜单绕过引导互斥（无 _guide_active 重入防护、按钮不禁用，可双 CDP 并发写凭据）/ \_rebuild_quota_account_combo 用 self._config 一次性快照——会话内切换账户被下次刷新静默打回启动快照账户
  - 中（8 条）：opencode_data 失败快照无条件替换成功缓存丢旧数据 / 数值白名单缺两键 H0.4 第二次漏网 / 三处 http_get(timeout=15) 绕过配置 / CACHE_TTL 死键语义未实现 / in-flight 分支经 _fallback 只返回单条致选择器闪缩丢项 / 说明区 5 处失实+13 函数缺条目 / 版本行 ver 0.240 与实际 0.241 矛盾
  - 低（8 条）：三孤儿属性+注释失实 / DataPageError 零引用空壳 / 两处函数内 import / PL004 死注释两条 / 说明区四处失实缺列 / CDP 响应非 dict AttributeError 逃逸 / 单账户时代口径 / RSS published_at 无兜底 / 双 cookie userData 错位（需验证）
- **参考级观察项 26 条**（用户复核全部维持豁免；2026-08-26 已归并入豁免定案清单与 Watch001）
- **亮点**：A015 四条修复历经五个功能版本零回退；PL004 大删除结构性清零无一漏网；ui.json/base.json 双向零死键；themes 注册制契约校验顺序正确；_should_show_guide 提取语义等价（布尔吸收律验证）

---

## 附录 A017：全量代码审计报告（第17轮，2026-08-23）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读；重点覆盖 A016/K 系列 22 条修复代码的完整性与自身缺陷
> 结果：**P 级 16 条（中 1 / 低 15，无高）/ 参考级观察项 18 条合并维持豁免（用户复核确认）**
> 状态：✅ 已修复（2026-08-24，L 系列 19 条全部完成，版本 V0.2.4.3——自本版起启用四段式版本号；反向验收 verify_l_accept 20/20 + 汇总 verify_k_accept 7/7 + 全量回归 0 异常；任务清单见 x.progress.md L 系列）

- **上轮复核（K 系列 22 条）**：主体在位零回退；四处部分实现/边界缺口升级为本轮 L 条目（K0.2 菜单禁用+静默反馈缺失→L1.1、K0.3 回落残留快照源→L1.2、K1.1 粒度边界→L1.4、K1.2 残余缩水→L1.3、K1.3 深层缺口→L1.5、K1.4 JSON 同字段漏网→L1.6、K3 两处小漏网→L3 组）
- **P0-P3（16 条）**：
  - 中（1 条）：饼图弧色恒绿——_arc_color 仅以 quota_chunk_color(0,...) 赋值渲染不联动，高用量账户进度条红而饼图弧仍绿且两处注释自相矛盾；**已裁定方案 A 分级色（用户确认）**控件持 theme 名按百分比联动三档变色
  - 低（15 条）：K0.2 部分实现菜单未禁用早退静默 / K0.3 回落分支读启动快照 / theme 死键被契约反向固化 / 失败占位项不入缓存全集缩水 / isinstance 只到顶层 result null 链式 .get() 可抛 / 单源失败空覆盖 Releases 从有变空 / JSON published_at 显式 null 得 "None" 字面量 / _render_quota 注释失实 / 说明区类型常量清单缺项 / error 路径 seq 失配不清 pending 冗余补发 / README 配置参数表多处失实 / _R_BLOCK_PATTERN 符号名失实 / opencode_usage 关联配置缺列 / in-flight 副本 error_stage 与节流分支不一致 / _fetch_in_flight check-then-set 池线程并发模式不一致
- **参考级观察项 18 条合并**（用户复核全部维持豁免；2026-08-26 已归并入豁免定案清单与 Watch001）
- **亮点**：A016 的 K 系列 22 条历经全文深挖零回退，三条高严重度修复主体质量扎实；白名单 26 键机械比对零差集；版本三处一致 ver 0.242；新发现问题集中于"修复建议部分采纳"与"重写未同步注释"，无崩溃级/数据级回归

## PL006. 前后端接口层：AppService 门面 + 统一任务运行器实施方案（2026-08-24）

> 来源：架构演进讨论——UI 作为前端、modules 作为后端，当前"点对点直连"无正式接口（main_window 直接 import 五个 modules 的 8 类符号 + 自建 5 个 QRunnable 任务类 + 4 组 Signals，后端签名任何变更引发 UI 大面积连带修改）。
> 状态：✅ 已实施（2026-08-24/25，版本 V0.2.5.1）；原始方案全文见 git 提交 b562ad1

- **架构设计**：services/ 纯 Python 后端门面（零 Qt 换前端时原样带走）+ ui/task_runner.py Qt 异步设施；归属判定规则 = 替换前端时必然重写归 ui/、可原样带走归 services/；多前端并存为远期目标启用第二前端那天才搬迁（YAGNI）
- **三条纪律**：Service 纯 Python 零 Qt（AST 机械断言）/ DTO 第一版直接透传 modules dataclass（独立层留待 QML 可序列化需求）/ UI 只 import services 不再 import 任何 modules 符号
- **实施结果（四部分去向）**：
  - services/service.py 门面：ServiceError 中文业务错误基类 + AppService 聚合 resolve_db_path/get_usage（原 _UsageTask.run 主体）/get_quotas/get_data_page/export_data（原 _ExportTask 主体）/save_account/add_account_via_cdp（CDP 五步编排 + _wait_for_login_cookie 整体迁入）→ **保留**
  - ui/task_runner.py：TaskRunner(QObject) finished(int, object)/failed(int, str) 双信号 + run(fn, seq) 提交 QThreadPool；ui.json 文案格式化留在 UI 层 → **保留**（PL006.2.c 实测教训落地：_live_tasks/_done_tasks deque 保引用防 wrapper GC 崩溃）
  - main_window 切换调用：四个数据任务类与 _CdpGuideTask 删除改 TaskRunner.run(service...)，五组 Signals 收敛为一组 finished 载荷区分；import 区删全部 from modules 编排行 → **保留**（M1.3 升级为白名单口径）
  - 验证与收尾：verify_pl006_accept 反向验收（services 零 Qt AST 断言/行为等价/modules 白名单）+ 全量回归 0 异常 + README 结构段补说明 → **保留**
- **技术要点（历史存档）**：in-flight/pending 等 UI 侧去重标志是交互语义留 main_window / 渐进可回滚纯重构行为不变
- **决策记录（历史存档）**：定版 V0.2.5.1（四段式第三位=功能批次、第四位=批次内序号）

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
- settings.py THEMES 白名单引用 \_SC.ui["themes"] 不变 ✅

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
> 状态：✅ 已修复（2026-08-25，M 系列 21 条全部完成，版本 V0.2.5.3；probe_m0/m1m2/m3 反向验收全 PASS + verify_m_accept 端到端 + 全量回归 63 脚本 0 失败；任务清单见 x.progress.md M 系列）

- **上轮复核（L 系列 19 条）**：零回退（两处覆盖缺口升级为本轮正式项）；L1.5 漏网一处、L1.7 锁覆盖不全、L3.3 半修复升级为正式项
- **P0-P3（21 条）**：
  - 中（3 条）：节流分支绕过 in-flight 挡板——线程 B 刷新中渐进写缓存致线程 A 节流期拿到部分列表（K1.2/L1.3"选择器闪缩"残余通道）/ CDP cookie domain 显式 null 时 TypeError 在 try 块外逃逸打断登录轮询 / _on_guide_failed 与 TaskRunner.failed(int,str) 签名失配——PyQt6 位置截断使 message=int 抛 TypeError，引导失败原因永不显示（漏测根因：verify 全部直调绕过信号机制）
  - 低（18 条）：_on_load_error 失配不清 pending / UsageData 本地死类遮蔽 services import / TABLE_LIMIT 死常量 / _CdpGuideSignals 死类连带未使用 import / PL007 文档残留七处同根因合并 / 说明区缺 PL006 新函数条目 / task_runner 缺说明区 / db 缺失文案硬编码且缩水丢自救提示 / 节流提示 f-string 两处硬编码同组不同轨 / refresh_data_page 无 in-flight 去重白耗 GitHub 限额旧覆新 / GitHub API 限速 dict 时 TypeError 浪费注定失败请求 / DIMENSIONS 六维元组双份 / ERROR_STAGE 直取 modules 违反纪律 3 且 verify 断言宽于实际 / CDP_WAIT_TIMEOUT 死常量裸读 base.json 并存 / 导入验证命令假阳性含 ui.themes 零覆盖加载器契约链 / theme_loader 导入期 IO 形态不一致违背自宣契约风格 / E3.9 消息缺主题名无法定位 / README 双主题表述矛盾
- **参考级观察项 23 条合并**（用户复核全部维持豁免；2026-08-26 已归并入豁免定案清单与 Watch001）
- **亮点**：上轮 L 系列 19 条零回退，A016→A017→L 三代修复链完整；PL006 门面迁移语义逐行等价验证通过、services 零 PyQt6 机械断言达成；PL007 四主题 palette 30 键机械核对一致、契约链文件源适配完整保留；机械扫描干净无崩溃级缺陷无安全项

---

## 附录 A019：全量代码审计报告（第19轮，2026-08-25）

> 范围：main.py + modules×7 + services×1 + ui×5 + utils×7 + config×4 + JSON 资源×8；三路并行代理全文审读 + 关键修复 grep 复核 + 重点段落人工核实
> 重点：A018（第18轮）21 条 P 级整改（M0-M4）的回归复核 + 新批次代码连带新问题的全量通读
> 结果：**P 级 11 条（中 6 / 低 5，无高）/ 参考级观察项 14 条全部维持豁免（用户复核确认）/ 0 安全项 / 0 确定性崩溃级缺陷**
> 状态：✅ 已修复（2026-08-26，N 系列 11 条全部完成，版本 V0.2.5.4；probe_n0 9/9 + probe_n1 7/7 + probe_n2/probe_n3 TDD 全 PASS + 全量回归 63 脚本 0 失败；任务清单见 x.progress.md N 系列）

- **上轮复核（A018 全部 21 条 M0-M4 修复）**：✅全部在位零回退零引入回归（go_quota 原子发布/browser_creds domain/main_window 签名/Releases 列表校验/task_runner 说明区/失配清 pending/文档残留零残留/导入命令更新）；一处误报经核实排除（quota_runner.run 缩进在 if/else 之外，无 db 时配额仍加载）
- **P0-P3（11 条）**：
  - 中（6 条）：配额预警气泡仅成功分支弹——缓存兜底超阈走 else 仅改托盘色违背"有提示"主线 / _on_guide_done 载荷直接解包无类型长度校验（契约变更时主线程 ValueError）/ _format_cell 三分支无 isinstance 守卫渲染期崩溃 / opencode_data 三处面向用户文案硬编码与 M2.2 外置口径不一致 / 缓存发布在状态锁外并发可观察新快照+旧时间戳瞬时错乱（理论级）/ 节流+浅拷贝标注逻辑两模块近同构
  - 低（5 条）：opencode_data 冗余 import urllib.error / pricing UA 版本号 _SC.base 直读未复用 logger.VERSION 单点 / 说明区漏 _on_quota_failed/_on_export_done 两方法条目 / data_page 空 rows 无视觉反馈 / system_tray 注释 themes.quota_chunk_color 路径残留
- **参考级观察项 14 条**（全部维持豁免；2026-08-26 已归并入豁免定案清单与 Watch001）
- **亮点**：A018 全部 21 条 P 级修复零回退三路独立 grep 确认，审计整改闭环完整；全量回归 63 脚本 0 失败 + 四主题冒烟全 OK；异步引用持有与引导失败信号端到端经实测验证；本轮新发现问题集中于逻辑边界，无安全项无确定性崩溃级缺陷

## 附录 A020：全量代码审计报告（第20轮，2026-08-26）

> 范围：main.py + modules×7 + services×1 + ui×5 + utils×8 + config×4 + JSON×3；三路并行代理全文审读 + 主会话逐项实证抽查（关键发现均动态探针/源码核对复现）
> 重点：A019（第19轮）N 系列整改（V0.2.5.4，提交 3c85e96）的回归复核 + 全量通读；**本轮问题集中于 N 整改的连带效应**（新整改代码自身引入或配套未同步）
> 结果：**P 级 22 条（中 9 / 低 10 / 文档 3，无高）/ 参考级观察项合并 18 条全部维持豁免（用户复核确认）/ 死键仅 1 / 0 安全项 / 0 确定性崩溃级缺陷**
> 状态：📌 待修复（O 系列任务清单见 x.progress.md）

### 零、上轮（A019）修复复核清单

| 上轮条目              | 现状                                                                               | 证据                                              |
| --------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------- |
| N0.1 解包守卫         | ⚠️ 在位，守卫分支引入次生缺陷（不恢复引导态→半死锁，见中-2）+ 契约漏同步（见中-4） | main_window.py:977                                |
| N0.2 类型守卫         | ✅ 在位无回归                                                                      | data_page.py:185/189/193                          |
| N1.1 mark_cached 共享 | ✅ 干净收敛，两模块零本地残留                                                      | cache_util.py:5 + 两模块各 3 处引用               |
| N2.1 文案外置         | ⚠️ 四键落地，同语义硬编码漏网 2 处（见中-7）                                       | opencode_data.py:256/260                          |
| N2.2 VERSION 单点     | ✅ 全项目 base["version"] 直读仅剩 logger 单点                                     | pricing.py:11/269                                 |
| N3.1 缓存气泡         | ⚠️ 功能在位，携带复制实现/硬编码文案/说明区失实三项连带                            | main.py:95-114                                    |
| N3.2 锁内发布         | ✅ 语义复核无损（空 captured 不发布，与基线一致）                                  | go_quota.py:486 / opencode_data.py:284            |
| N3.3-N3.6             | ✅ 全部在位                                                                        | import 已删 / 说明区:1308 / 占位:154 / 注释零残留 |
| 版本一致性            | ✅ README 徽章 == base.json == logger.VERSION = V0.2.5.4                           | 三处                                              |

### 一、P0-P3 修复清单

**中（9 条）**

| 文件:行号                                        | 类型 | 描述                                                                                                                                                                                                                                                  | 建议                                                                                                                  | 性质                                        | 影响面            |
| ------------------------------------------------ | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ----------------- |
| ui/data_page.py:158                              | ①⑬   | N3.5 占位分支 `setHorizontalHeaderLabels(英文键名)` 覆盖 `__init__:101/:111` 中文表头，且正常分支不重设 → 任一表出现空结果后该表表头永久变为英文键名（直到重启），确定复现                                                                            | 占位分支删除 setColumnCount/setHorizontalHeaderLabels 两行（列结构 **init** 已固定），仅保留 setRowCount(1)+占位 item | 新增（N3.5 连带）                           | 显示层/数据页     |
| ui/main_window.py:977-979                        | ①⑧   | N0.1 守卫命中只 showMessage+return，跳过正常/失败路径共有恢复序列（按钮启用、\_guide_active=False、\_refresh_timer 重启）→ 触发即半死锁：自动刷新永停、引导入口全禁；当前上游契约恒成立（理论可达 ≤中）                                               | 守卫分支复用 \_on_guide_failed 恢复序列后再提示                                                                       | 新增（N0.1 连带）                           | 凭据引导/UI 交互  |
| main.py:73、:104                                 | ②    | format 兜底 except (KeyError,ValueError,IndexError) 漏 AttributeError（`"{used.x}".format(used=80)` 实证抛 AttributeError）——模板含未知属性占位符时异常逃逸，PyQt6 槽内未捕获异常 abort 进程，突破 P24"任何损坏都兜得住"防线；:104 为 N3.1 复制扩散点 | except 元组补 AttributeError；随低-1 helper 抽取一并单点化                                                            | 成功路径遗留+缓存路径新增                   | GUI 进程稳定性    |
| ui/main_window.py:192-211                        | ③②   | B0.6/C0.8 契约 status_messages 必需键集（18 键）未纳入 N0.1 新消费键 guide_data_format_error（:978 消费）→ 删键导入期不拦截，运行时恰在防御路径抛 KeyError（槽内 abort）：防御代码自身成崩溃点                                                        | required 元组补 "guide_data_format_error"                                                                             | 新增（N0.1 连带）                           | 配置体系/契约防线 |
| utils/logger.py:55                               | ②    | getattr(logging, LOG_LEVEL, ...)：log_level 手改为小写（"info" 等）命中 logging 模块级函数对象（hasattr 实证），setLevel 抛 TypeError 且该行在 try 外 → 启动即崩裸异常无中文提示                                                                      | 显式级别映射 logging.getLevelNamesMapping().get(LOG_LEVEL.upper(), INFO) 或移入 try                                   | 遗留                                        | 启动/日志         |
| config/static/static_config.py:75-77             | ②⑬   | H0.4 数值键白名单只查"存在时的类型"，键缺失放行（实证删 http_timeout 导入期无报错，崩溃后移 network.py:24 裸 KeyError）；字符串键完全无存在性校验                                                                                                     | 白名单循环补 if \_v is None: raise RuntimeError                                                                       | 遗留                                        | 配置体系          |
| modules/opencode_data.py:256、:260 + main.py:109 | ③    | 三处用户可见文案硬编码未外置："数据页拉取失败：{exc}"、"官方动态拉取失败：{exc}"（与 N2.1 外置 fetch_failed 同语义不同源）、"（缓存数据）"（与 cached_prefix/cache_suffix 措辞三足鼎立）                                                              | 前两者外置 data_page_messages 补 {error} 模板键；缓存后缀复用 cache_suffix 统一措辞                                   | 新增发现（N2.1/N3.1 口径不齐）              | 数据页/托盘预警   |
| modules/opencode_data.py:237                     | ⑬⑧   | in-flight 去重且无缓存返回裸快照（is_cached=False/errors 空/三源空），UI 无法区分进行中与失败；对照 go_quota:430-437 同场景返回带 in_flight 文案占位项，行为分叉                                                                                      | 该快照追加 errors=[data_page_messages.in_flight]                                                                      | 遗留（M1.4 起）                             | 数据页            |
| ui/main_window.py:245-249                        | ③    | 契约双缺口：go_quota_error_messages required 漏 throttled_template（go_quota:362/opencode_data:74 裸读）；N1.1 新增 data_page_messages 整组不在任何契约（opencode_data:234/253/269 裸读）                                                             | required 补第三键；data_page_messages 四键照 F0.1 式样入 \_UI_STRUCT_KEYS                                             | 部分（throttled 遗留/data_page 组新增连带） | 配置体系/契约防线 |

**低（10 条）**

| 文件:行号                                          | 类型 | 描述                                                                                                                                  | 建议                                                    | 性质 |
| -------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- | ---- |
| main.py:96-114                                     | ④    | N3.1 整段复制成功路径气泡逻辑约 15 行，fallback 文案两份逐字相同（亦为中-3 扩散根源）                                                 | 提取 \_danger_notify(tray, info, suffix) 两路共用       | 新增 |
| modules/opencode_data.py:258(:409)                 | ⑤    | fetch_github_releases(force) 参数函数体从未读取，唯一调用传 force=True 无效果                                                         | 删参数及实参                                            | 遗留 |
| ui/main_window.py:1163-1179                        | ⑨    | \_show_columns_menu 每次 new QMenu+9 QAction popup 后局部 wrapper 被 GC、C++ 对象滞留 children → 常驻应用累积泄漏                     | aboutToHide.connect(menu.deleteLater) 或单实例复用      | 遗留 |
| ui/main_window.py:207 + ui.json:134                | ⑫⑤   | usage_failed_template 全仓唯一 .py 引用是其自身契约行（死键）；\_on_load_error 直显原始异常串不走模板                                 | \_on_load_error 改走模板统一口径（推荐）或删键+删契约行 | 遗留 |
| ui/theme_loader.py:111-114                         | ⑤    | is_dir 检查不可达死分支（其前 :101 循环经 \_load_theme 对缺失目录必先抛），M0.6 设计意图失效                                          | 检查上移到循环前恢复设计价值，或删除并修注释            | 遗留 |
| ui/theme_loader.py:24、:62                         | ⑥②   | read_text 遇非 UTF-8 资源裸抛 UnicodeDecodeError，违背 M0.6/A3.5 导入期 IO 失败转 RuntimeError 自宣口径                               | 包 try 转 RuntimeError（消息含路径）                    | 遗留 |
| ui/data_page.py:172-177                            | ④②   | \_populate_placeholder 未设 NoEditTriggers（启动空态占位格可编辑）；editTriggers/alternatingRowColors 两分支每次重复设置              | 表格静态属性收敛 **init** 单点一次                      | 遗留 |
| services/service.py:95-122                         | ⑬    | get_usage/export_data 对坏库 sqlite3.Error 不转 ServiceError，UI 直显英文异常串，与其他入口中文口径不一                               | 转 ServiceError                                         | 遗留 |
| services/service.py:64-84                          | ⑨⑥   | 登录等待单轮周期（CDP≤10s+验证重试链最长约 50s）远超 deadline 检查粒度，总等待显著超 login_wait_seconds，超时提示"{minutes} 分钟"失真 | deadline 检查下沉至验证步骤前，或注释声明               | 遗留 |
| modules/go_quota.py:26-29 ↔ opencode_data.py:36-39 | ④⑫   | CHROME_UA/\_BROWSER_UA 逐字符相同的 UA 字符串双处维护                                                                                 | 收敛 utils/network 单点导出                             | 遗留 |

**文档（3 条）**

| 位置                                   | 类型 | 描述                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| -------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 说明区失实/缺漏批（八处合并）          | ⑥    | main.py:149-152 未同步缓存分支气泡；utils/logger.py:97-99 \_setup_handlers 缩进挂错层级；go_quota.py:583 "\_build_info 更新缓存"与 M0.1 原子发布矛盾；opencode_usage.py:746 关联配置多列 retry_count/delay、:722 写死"10s"；services/service.py:196-198 残句排版错乱；browser_creds.py:582/:674 "对外公开供 main_window 调用(R13)"实无外部消费方；ui/main_window.py 方法清单漏 \_build_cards/:520、\_build_guide_card/:626、\_build_detail_section/:648、\_sorted_hidden_columns/:1227 且 \_on_guide_done 条目未反映 N0.1 守卫；ui/task_runner.py 说明区漏 \_task_done/\_FnTask.**init**/.run 条目 |
| modules/browser_creds.py:232-234、:277 | ⑥    | `_with_copied_db(...) or ([], False)`：查询成功返回 falsy 元组时走 or 分支属巧合等价，未来结构变化即成 bug                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| modules/pricing.py:291                 | ⑥    | 局部变量 pricing 与模块语义同名遮蔽（go_quota D0.14 同类已改名先例）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

### 二、参考级观察项（全部维持豁免，用户 2026-08-26 复核确认）

> 2026-08-26 归并：本章条目经三方分级后已并入「观察项豁免定案清单」（33 条永久 + 24 条条件，见本文件头部）与「观察项可修正批次方案」Watch001（12 条可直接修正，见本文件末尾），正文删除避免双处维护；历史数量以本行为准（原 18 条合并 + 死键专项一句——usage_failed_template 死键已随 O3.3 接入消费方消除）。

### 三、亮点

- **A019/N 系列 11 条修复主体质量良好零回退**：mark_cached 收敛干净、captured[0] 锁内发布语义经复核无损、版本三处一致
- convert.py 数值防护完备（nan/inf/bool/溢出四级拦截）；sqlite_utils mode=ro 与 URI 转义正确；file_utils 原子写 fd 泄漏闭环
- settings.py from_dict 宽容解析（bool 排除/clamp/themes 白名单）符合错误策略范本
- 本轮核心发现集中于 N 整改连带效应（表头覆盖/守卫状态机/契约漏同步），方向正确、一次收尾批次可闭环

## 观察项可修正批次方案 Watch001（2026-08-26 定稿）

> 来源：第 16-20 轮观察项三方分级（69 条 = 33 永久豁免 + 24 条件豁免 + 12 可直接修正）；
> 33/24 已并入「观察项豁免定案清单」①②两级，本节为可直接修正项的实施方案。
> 编号规则：Watch001 为本批次号，批内子项 .a-.l 字母序号；后续新批次递增 Watch002…
> 状态：📌 待修复（WTH001.a-l 任务清单见 x.progress.md，一一对应）

| 编号       | 内容                                           | 来源           | 修法                                                                 | 验证                                               |
| ---------- | ---------------------------------------------- | -------------- | -------------------------------------------------------------------- | -------------------------------------------------- |
| Watch001.a | \_quota_card dict frame/title 键零读取（死键） | A017           | 删除两键及写入处（先确认全仓零消费）                                 | grep 零引用 + IMPORT OK                            |
| Watch001.b | [\d.]+ 正则放行畸形数字丢整图                  | A020           | 时序解析数字正则收紧为 \d+(?:\.\d+)?                                 | probe 构造 "1.2.3" aria-label 断言跳过该条不丢整图 |
| Watch001.c | stack 扫描窗口魔数 6000 无注释                 | A020           | 补一行量纲注释（字符数窗口防 markup 变更超窗静默丢行）               | grep 注释在位                                      |
| Watch001.d | subprocess_timeout float/int cast 不一致       | A016+A018+A020 | opencode_usage/browser_creds 两处统一 int()                          | IMPORT OK + 全量回归                               |
| Watch001.e | services 导入路径混用                          | A018           | 全仓统一 from services.service import X 形式                         | grep 零混用 + IMPORT OK                            |
| Watch001.f | THEME_LABELS fallback 不可达死分支             | A018           | M3 改名 THEME_DISPLAY_NAMES 后原描述过时——重新定位确认不可达后删分支 | IMPORT OK + 四主题冒烟                             |
| Watch001.g | windows.py 内联 get_static_config 解包风格     | A020           | 改顶层 \_SC = get_static_config() 解包（对齐全项目约定）             | IMPORT OK                                          |
| Watch001.h | retry 计数口径注释歧义                         | A016+A017      | retry.py 计数语义注释澄清（retries 为尝试总轮次口径注明）            | 注释与实现一致性核对                               |
| Watch001.i | CLI --estimate 仅 total 生效 help 未声明       | A016           | argparse help 文案补注生效范围（定位实际参数名后措辞）               | --help 输出含说明                                  |
| Watch001.j | "≥80%" 注释快照失准                            | A018           | 相关注释改"≥ QUOTA_DANGER_PERCENT"符号表述                           | grep 全仓零 "≥80%" 残留                            |
| Watch001.k | AGENTS verify 脚本计数漂移                     | A018           | AGENTS.md 写死的脚本计数改动态表述"全部 verify\_\*.py 脚本"          | AGENTS.md 无具体计数残留                           |
| Watch001.l | zip 数量不齐静默截断                           | A016           | releases 双源合并处补 warning 日志（数量不一致时记录）               | probe mock 不齐断言 warning                        |

> 收尾：Watch001.a-l 完成后执行全量回归 + IMPORT OK + offscreen 冒烟（对应 x.progress WTH001.m）。
