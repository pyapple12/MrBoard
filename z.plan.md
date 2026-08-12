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

## 十二、P10 二次审计整改完成（2026-08-10 已实施）

> 范围：全部 16 个 .py 文件，对照 AGENTS.md 规范 + 10 类问题清单（优化/抽象/过简函数/import/嵌套/小错误/硬编码/默认值/防御性代码/死代码）
> 结果：**59 条发现**（高价值 10 / 中价值 20 / 低价值 22）；无架构级问题，import 顶层化/注释规范/命名/可变默认参数均合规
> 实施明细见 x.progress.md V0.10；H1/M11 两项审计建议经实测证伪（以行为验证为准）

- **高价值 10 条**：审计误判证伪 1 项（`except GoQuotaError: raise` 必要——401/403 分类错误会被外层包装破坏，传播测试证实）；OpenAuth 死条件/`_add_seconds` 冗余/不可达 2xx 检查删除；`login_wait_seconds` 默认 None 走 base.json；refresh 网络失败回退 TTL 内旧缓存；UA 去硬编码；临时目录清理补全；预警阈值单一来源；说明区凭据路径修正
- **中价值 20 条**：8 处死代码删除（clear_cache/CONFIG_DIR/不可达 raise/REFRESH_INTERVAL_MS/_quota_info/_quota_status/调试与截断注释）；未用参数清理；3 处一行转发内联（`_status_bar_show` 为结构性整改：状态栏提前创建、信号连接统一前部）；重复逻辑抽取（Local State 读取/PRAGMA 缓存/维度名收敛）；`--restore-last-session` 无效参数移除；import 分组修正；说明区补齐 4 文件
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
- **函数内嵌套 def 4 处**：browser_creds 三处 `_with_copied_db` 回调闭包参数化提取（*query_args 透传，163 捕获 aes_key 可传参保留亦正当）；go_quota add 闭包**保留合理**（累加器语义）；`_TaskProcess` 嵌套类提模块级
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