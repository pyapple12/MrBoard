# myboard 项目方案报告

> 方案日期：2026-08-08（V2 修订：2026-08-08，依据 w.study.md 三项目研读结论）
> 项目定位：Windows 桌面应用，展示 OpenCode 用量统计与 OpenCode Go 配额使用情况的信息窗口
> 参考基准：AccelWorld 项目结构（utils/ → config/ → modules/ → ui/ → data/ 单向分层）与 AGENTS.md 代码规范；错误策略采用参考项目的当代模式（见第四章）
> 参考仓库：reference/ 目录下 3 个开源项目（研读笔记见 w.study.md）
> 实施状态：**S1-S8 + V0.08（P2-P8）+ V0.09（UI 改版）+ V0.10（二次审计整改）全部实现完成**（全量回归 596 项断言通过，V0.10 已就绪）；待评估项见 y.problem.md

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

## 十二、P10 二次审计问题汇总（2026-08-10 审计完成）

> 范围：全部 16 个 .py 文件，对照 AGENTS.md 规范 + 10 类问题清单（优化/抽象/过简函数/import/嵌套/小错误/硬编码/默认值/防御性代码/死代码）
> 结果：**59 条发现**（高价值 10 / 中价值 20 / 低价值 22）；无架构级问题，import 顶层化/注释规范/命名/可变默认参数均合规
> **整改状态：✅ 全部完成（2026-08-10，V0.10）**——实施明细见 x.progress.md V0.10；H1/M11 两项审计建议经实测证伪（以行为验证为准）

### 高价值（行为相关，10 条）

- go_quota.py:183-184：`except GoQuotaError: raise` 死分支——retry_call 的 exceptions 不含 GoQuotaError，无拦截对象
- go_quota.py:195：`"OpenAuth" in html or "<title>OpenAuth</title>" in html` 死条件——后者蕴含于前者
- go_quota.py:254-258：`_add_seconds` if/else 两分支返回完全相同表达式，纯冗余
- go_quota.py:287-288：`_http_get` 中 `if not 200 <= response.status < 300` 不可达（urlopen 对 4xx/5xx 直接抛 HTTPError）
- main_window.py:289-299：`_CdpGuideTask` 默认 `login_wait_seconds=180` 硬编码，base.json `cdp_login_wait_seconds` 形同虚设（改 json 不生效）
- pricing.py:96-109：`load_price_map(refresh=True)` 网络失败回退内置表（5 条）而非 TTL 内旧缓存——违反"网络失败返回上次缓存"策略
- pricing.py:282：UA `"myboard/0.1"` 硬编码，与 base.json version 不一致（违反"版本号唯一来源"）
- browser_creds.py:231-257：`_safe_copy_db` 失败路径（copy2 + esentutl 均失败）临时目录从不删除，资源泄漏
- main.py:42：预警阈值 `>= 80` 魔法数字，ui.json `quota_danger_percent` 与 themes 导出的 `QUOTA_DANGER_PERCENT` 未复用
- settings.py:72：说明区"凭据在 ~/.config/myboard/"失效（实际已迁移项目内 data/credentials/，P2）

### 中价值（死代码/冗余/过简函数/规范，20 条）

- **死代码（8 处）**：file_utils.py:59 `clear_cache()` 无调用；settings.py:12 `CONFIG_DIR` 无引用；retry.py:42 不可达 raise；main_window.py:67 `REFRESH_INTERVAL_MS` 未使用；main_window.py:412/666 `_quota_info` 只写不读；main_window.py:214 `_RemainingPieChart.used_percent()` 无调用；system_tray.py:32/60-71 `_quota_status` 只写不读；main_window.py:254/277/331/337 四处"调试："遗留注释；browser_creds.py:261/304 两处截断注释
- **未用参数**：go_quota.py:299 `_throttled_cache(now, force)` 的 `now` 未使用
- **过简函数（3 处）**：go_quota.py:150 `_read_credentials_json` 一行转发；pricing.py:287 `json_loads` 一行；main_window.py:684 `_status_bar_show` 一行转发（可选内联）
- **重复逻辑（3 处）**：browser_creds.py `_load_aes_key` 与 `has_v20_cookies` 重复读 Local State JSON；opencode_usage.py:169-190 `totals()` 的 `_time_clause` 调用 6 次；opencode_usage.py:265 `_has_session_columns` 每次 PRAGMA 无缓存；exporter.py:49-80 维度名手写 3 次
- **无效参数/说明不符**：browser_creds.py:302-325 `--restore-last-session` 对全新临时 profile 无效，说明区"保留登录态"与 9222 写死与实际不符
- **import 分组**：browser_creds.py:20-38 第三方 try-import 位于本地模块之后、`T = TypeVar` 插在 import 中间；credential_store.py:12-15 同（win32crypt 位置）
- **说明区不全/不符（4 文件）**：opencode_usage（"五个聚合入口"实为 7 个，漏 by_session 等）；go_quota（漏 9 函数 + CREDENTIALS_FILE）；main_window（漏 P13/P16 新增组件，`QTimer.singleShot(10)` 应为常量）；system_tray（漏常量）

### 低价值（行宽/魔法数字/冗余包装，22 条）

- **行宽 5 处超 100**：opencode_usage:173/188/544、go_quota:263、main_window:781
- **`Path(str(...))` 冗余包装 3 处**：logger:12、settings:13、go_quota:36-38
- **file_utils**：:22 注解 `path: Path` 与实现（接受 str）不符；:64 说明区漏 `_PROJECT_ROOT`；:27-39 缓存写入重复 3 次
- **硬编码（多处）**：settings.py:44 主题枚举与 themes.py 重复；main_window.py:143-148 表格 limit=50/200；main_window.py:199-235 饼图色值/尺寸/字号；main_window.py:256/323 CDP 超时；system_tray.py:80-94 图标几何按 32×32 推算；opencode_usage.py:181/334/339 `86400_000`/`/1000` 与 `_EPOCH_MS` 重复；opencode_usage:127/go_quota:281/pricing:283 timeout 不统一（10/15）；main.py:27 应用名；logger.py:32-33 日志级别/文件名
- **其他**：static_config.py:31 `result.get("base", {})` 静默兜底与失败策略不一致；exporter.py:46 `Path(out_dir)` 重复构造；opencode_usage.py:268 `row[1]` 数字索引应改 `row["name"]`

---

## 十四、第四轮全量审计问题汇总（2026-08-12 审计完成）

> 范围：全部 17 个 .py 文件（含 utils/network.py、utils/windows.py），AST 精确扫描（函数内 import/嵌套 def）+ 三代理全文审读
> 结果：**47 条发现**（错漏 11 / 硬编码 10 / 重复实现 5 / 说明区不符 8 / 防御性 5 / 可优化 5 / 死代码 3）+ 专项结论（函数内嵌套 def 4 处）
> **整改状态：✅ 全部完成（2026-08-12，V0.11）**——实施明细见 x.progress.md 第四轮章节（4A.1-4A.3）

### 重复实现（5 条，重点）

- **APP_NAME 四处重复解包**：logger.py/main.py/system_tray.py/main_window.py 同一 base.json 键——logger 导出统一引用
- **win32crypt try-import 降级逐字重复**：credential_store/browser_creds——提取 utils/windows.py 公共模块
- **DPAPI 解密同款调用**：credential_store（str 转 bytes 怪癖）与 browser_creds AES key 提取——公共 dpapi_unprotect 工具
- **去重键逐字同构**：go_quota add 闭包 vs browser_creds 内联去重——credential_dedup_key 共享
- **UI 文案跨模块重复**：维度标签/卡片标题/配额窗口名（"5 小时/每周/每月"与 CLI 打印重复）——外置 ui.json；themes 调色板 20+ 色值整体迁入

### 函数内嵌套 def（AST 扫描，4 处）

- browser_creds.py:163/206/294 三处 `_with_copied_db` 回调闭包（206/294 无捕获可参数化提取；163 捕获 aes_key 可传参，保留亦正当）
- go_quota.py:109 add 闭包（捕获 candidates/seen，累加器语义保留合理）；browser_creds _TaskProcess 嵌套类提模块级

### 错漏（11 条）

- exporter.py:57 日志 CSV 计数 `len(datasets)-1`=6 但实际 7 个 CSV（summary 也是 CSV）
- 3 处未用 import（go_quota/browser_creds urllib.request、exporter json）
- convert.to_optional_float 缺 bool 排除；file_utils 解析失败结果写缓存（毒化）；write_json unlink 竞态
- opencode_usage parse_time_arg strip 不一致；sqlite URI 未转义（两处）；show_guide 永真判断
- pricing 说明区 _deserialize 残留；browser_creds v20 逐条 WARNING 刷屏；CDP 响应解析在 try 外

### 硬编码（10 条）

- themes 调色板 20+ 色值全部硬编码（S8.3 颜色外置只做配额色）；settings THEMES 枚举
- browser_creds login_url 与 OPENCODE_HOST 重复、CDP 探测 timeout=2
- main_window cards_spacing=8、重置时间格式与 CLI 不一致、drawPie 角度魔法数、quota_chunk_color 传 float
- opencode_usage 8 处签名 limit=100 第三套无来源数字；system_tray **init** 缺注解

### 防御性/可优化/死代码（13 条）

- static_config mapping 非 dict 裸 AttributeError；retry raise Optional；browser_creds except Exception 过宽
- opencode_usage cost_source 重复分支可合并；by_session 手写行构造；settings hidden 空白项
- **rows["total"] 伪维度从未消费**（弹窗读 summary）；used_percent getter 测试专用
- 说明区不符 8 处（browser_creds/main_window/system_tray/logger/main 漏常量与函数；go_quota/themes 阈值字面量与配置脱钩）

---

## 十三、第三轮全量审计问题汇总（2026-08-11 审计完成）

> 范围：全部 16 个 .py 文件，对照 AGENTS.md + 10 类问题清单 + **跨模块复用专项**
> 结果：**57 条发现**（跨模块复用 15 / 可优化 10 / 小错误 9 / 死代码 8 / 硬编码 6 / 规范 5 / 默认值 2 / 过度防御 2）
> 与上轮对比：约 25 条为上轮遗留（pricing retries、Path 冗余、说明区漏项等），其余为新增（重点：跨模块复用 15 条）
> **整改状态：✅ 全部完成（2026-08-12，V0.11）**——实施明细见 x.progress.md 第三/四轮章节

### 跨模块复用（15 条，重点）

- **HTTP GET 三处自实现**：go_quota._http_get / pricing._http_get / browser_creds 内联 urlopen ×2——抽 `utils/http_get(url, headers, timeout, auth_error_codes=None)`
- **宽容读文件重复**：credential_store.read_credentials_file 与 browser_creds._read_local_state_json 手写"读文件 + json.loads + 三异常捕获"——复用 `read_json(path, default=None, use_cache=False)`
- **双胞胎 dataclass**：go_quota.DashboardCredentials 与 browser_creds.BrowserCredential 字段完全相同——复用或抽公共类型
- **阈值三分支重复**：system_tray.update_quota_status 重复 themes.quota_chunk_color 逻辑——直接调用（None→灰分支保留）
- **日志入口绕过**：retry._logger 用 logging.getLogger 未走统一 get_logger（唯一例外）
- **成本舍入口径 5 处**：opencode_usage ×3 + exporter ×2 的 round(to_float(x), 4)——抽公共 _round_cost
- **配置键重复解包**：HTTP_TIMEOUT 三模块重复（opencode_usage 用于 subprocess 命名名不副实）——统一命名或 config 层代理
- **retry 异常元组重复**：(URLError, TimeoutError) go_quota/pricing 两处——utils 公共常量
- **魔法字符串/字段名散落**：OpenAuth 标记、"workspaceId/authCookie" 键名重复维护——公共常量收敛
- **窗口标题/托盘 tooltip 文案重复**：两处独立维护——app_name 拼接或公共常量
- **Chrome User Data 路径重复**：_browser_user_data_dirs 与 _chrome_user_data_dir 重复构造——单点维护
- **弹窗费用口径不一致**：main_window 总量明细 $0.0000 vs 卡片 -（_format_cost 未复用）
- **\_ 前缀私有函数跨模块调用**：main_window 调 browser_creds._chrome_user_data_dir/_read_workspace_ids（违反私有约定）——提供公开入口
- **CSV 列名/键多处方维护**：exporter 两表 + flatten_tokens 键——单一来源推导
- **三方法完全相同**：opencode_usage by_model/by_provider/by_agent——抽 `_by_field(json_expr, unknown_label)`

### 死代码/冗余（8 条）

- file_utils `_json_cache` 缓存形同虚设（业务调用点全 use_cache=False，仅测试用默认缓存）；说明区"clear_cache"条目残留不符
- retry.py 不可达 `if last_error is not None: raise`（注释自认）
- go_quota except HTTPError 内 401/403 分支不可达（_http_get 已转 GoQuotaError）
- go_quota fetch_go_quota 的 global 声明冗余（读写均在 _build_info/_fallback）
- pricing _rate_from_raw try/except 永不触发 + 调用方 is not None 恒真
- browser_creds rmtree(ignore_errors=True) 外层 except OSError 永不可达
- credential_store 说明区引用不存在的 _read_credentials_json 函数名
- main_window 弹窗费用未复用 _format_cost（口径不一致）

### 小错误/边界（9 条）

- convert.to_float 未排除 bool（to_float(True)→1.0，to_int(True)→default，语义矛盾）
- settings isinstance(interval, int) 未排除 bool（true → 1ms 刷新间隔）
- opencode_usage `if min_ts and max_ts` truthiness（min_ts=0 边界）→ is not None
- opencode_usage cost_source 多币种边缘（estimated_cost_total=None 时混标 recorded）
- opencode_usage CLI 未捕获 sqlite3.Error（坏库英文 traceback）
- static_config 映射值非 str 抛裸 TypeError
- main_window cdp_poll_interval/cdp_login_wait_seconds 未模块级解包（违反一次性解包约定）
- system_tray QApplication import 未使用
- TokenStats 类注释漏 total 字段

### 硬编码（6 条）

- pricing retries=2/delay=1.0（base.json 已有 retry_count/retry_delay，上轮 L13 漏改）
- pricing BUNDLED_PRICES 约 20 个价格数字源码内（可选外置）
- opencode_usage DEFAULT_DB_PATH 未走 base.json
- main.py 气泡文案
- main_window 布局边距/spacing/固定宽
- system_tray 白色圆点 #ffffff（其余颜色已外置）

### 其他（规范/默认值/防御/可优化，约 19 条）

- 规范：pricing Path(str(...)) 冗余（上轮 L2 漏此）；opencode_usage/go_quota/pricing/exporter 说明区漏 HTTP_TIMEOUT/_DAY_MS/PRICE_CACHE_DIR/RETRY_COUNT/_SC 等常量
- 默认值：browser_creds import psutil 函数内延迟导入（与 try-import 风格不一致，违反顶层 import 约定）
- 过度防御：go_quota _capture_number 的 float() try/except 永不触发
- 可优化：pricing _deserialize 与 _apply_local_overrides 可合并；exporter datasets 遍历两遍可合并；_fetch_usage_with_fallback 成功路径携带前序失败残留；pricing 非 refresh 路径 TTL 过期应回退旧缓存（旧缓存优先于内置表）；opencode_usage by_session 手写 UsageRow 与 _row_to_usage_row 重复
