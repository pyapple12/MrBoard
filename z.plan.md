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
> **整改状态：✅ 全部完成（2026-08-13）**——A 系列任务清单见 x.progress.md（A0-A3 已实施，A4 收尾）；新增契约校验（themes 残留占位符/数组长度）、_SC 单点解包、build_app_title 标题单点

- **上轮复核（第六轮 38 条）**：38/38 在位（2 项断言格式误报已澄清，非回退）；发现 1 回归（CDP_PROBE_TIMEOUT 重名重复定义）+ 1 漏改（os_crypt 非 dict 容错只覆盖 None/空，truthy 非 dict 仍 AttributeError 逃逸，行为验证崩溃）
- **P2 修复 2 条**：CDP_PROBE_TIMEOUT 重名去重（删 47 行保留 70 行）；os_crypt isinstance 检查后 return None（167/322 两处）
- **P3 修复 16 条**：host_key 带点 domain cookie 兼容（需验证）；OpenAuth 特征收紧防误判（需验证）；进度条 None 分支重置格式（需验证）；CDP 引导期状态管理×2（定时刷新重现引导卡/手动填写并发写凭据，均需验证）；themes 契约校验（残留占位符检测 + 数组长度）；说明区漏 _format_cache_rate_of；标题格式单点（build_app_title）；说明区失实 4 处（windows/main/settings/logger）；network 默认值双源；to_float("nan") 穿透（需验证）；opencode_usage 5 处 _SC 单点；K/M/B/G 单位外置（争议决策）；跨组提示 3 条（settings.py:16 注释失实/default_theme 双源/CLI 时间格式）
- **参考级观察项 15 条**（用户确认均不提升）：browser_creds（--remote-allow-origins=* 必需/每 profile 整库复制/CDP 探测族 3 固定值）；go_quota（DASHBOARD 请求参数/模块级缓存无锁）；pricing（BUNDLED_PRICES 快照/COST_COMPARE_DIGITS）；opencode_usage（时间基准常量）；exporter（查询全量驻留）；main_window/system_tray（绘制细节）；static_config/file_utils/retry/convert（无锁单例/缓存引用/默认值分离/下划线字面量——均无可达触发路径）
- **亮点**：无 P0/P1；无函数内 import/docstring/未用 import/配置死键（base.json 26 键、ui.json 42 键全有消费方）；弹性转换实测无崩溃路径；README 徽章与版本一致

---

## 附录 A008：全量代码审计报告（第8轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；AST 扫描 + 三路代理全文审读 + 行为验证
> 结果：**P2 级 1 条 / P3 级 13 条 / 参考级观察项 15 条**——无 P0/P1
> 状态：✅ 全部完成（2026-08-13）——B 系列任务清单见 x.progress.md（B0-B3 已实施，B4 收尾）；Edge 判定下沉双浏览器、刷新序号去重、配置契约校验等 15 项修复

- **上轮复核（A007 第 7 轮 19 项）**：27/27 全部在位、零回退；发现 1 处 A007 漏改分支（launch Popen OSError 未清理）+ 3 处 A3.1 漏改的说明区（main_window/system_tray/themes）
- **P2（1 条）**：main_window:343 只对 Chrome 调 has_v20_cookies——Edge-only v20 用户误判为 v10 收到无效指引，与 find_browser_credentials 双浏览器遍历口径不一致（建议判定下沉 browser_creds 遍历双浏览器）
- **P3（13 条）**：to_float/to_optional_float 缺 OverflowError（10**400 实测逃逸，与 to_int 不对称）；pricing currency/source None → "None" 错值（实测）；launch Popen OSError 分支临时目录泄漏（A007 漏改）；刷新无 in-flight 去重（连点+定时叠加旧任务覆盖新数据）；ui.json 结构性键无契约校验（删键确定性 KeyError/IndexError）；说明区失实/残留 6 处（main_window VERSION、system_tray APP_NAME、themes 异常处理无、exporter/browser_creds/go_quota 关联配置）；notify 模板 .format 无防护（KeyError 逃逸）；settings _themes/THEMES 重复构造
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
- **P2（3 条）**：main_window:170 status_messages 契约自证式恒真（ uple(STATUS_MESSAGES) 从被校验对象派生，删键不报错、启动 KeyError 崩构造）；main.py:48-79 节流缓存破坏预警去重（实测：缓存到达复位 _notified_danger + 托盘置灰，超限重复弹气泡）；刷新无 in-flight 去重（C0.5 只解决乱序，网络并发叠加遗留）
- **P3（11 条）**：模板占位符校验漏 pie/detail_line 两组；usage_percent 无界（-5%/120% 错值）+ overall 无下界钳制；notify_title 无契约无防护；C0.6 不防顺序颠倒；save_state 无降级（磁盘满阻塞退出）；解析空结果无 warning（P1 潜伏放大器）；HTTP_TIMEOUT 死代码 + 说明区失实；说明区缺失/重复 4 处；窗口销毁 in-flight 信号（需验证）；palette 值非字符串 TypeError
- **参考级观察项 12 条**（用户复核后**提升 1 条**：凭据探测 TTL——每次刷新全量浏览器探测，未来提频前加缓存；维持 11 条）：历轮定案项 + html 局部遮蔽/时区偏移/本地覆盖缺字段/绘制参数等
- **亮点**：A009 零回退；无函数内 import/嵌套 def/docstring/未用 import；配置全键有消费方；三处 ver 0.16 一致；三路交叉验证抓出"自证恒真校验"类隐蔽缺陷

---

## 观察项豁免定案清单（第 10 轮大会战，2026-08-13 定稿）

> 历轮（A007-A010）参考级观察项经大会战逐条评估：修复 5 条入 D 系列（D0.11-D0.15）、转资产 4 条（verify_s1 断言 ×2 + pricing 说明区 ×2）、**以下 29 条维持豁免定案**——后续轮次不再重复报告（除非触发条件变化）

- **安全必需**：browser_creds --remote-allow-origins=*（Chrome 137+ 无此参数 CDP 必 403）
- **历轮定案**：CDP 探测族 3 固定值不入配置 / DASHBOARD 请求参数硬编码 / BUNDLED_PRICES 数据快照 / COST_COMPARE_DIGITS 浮点容差 / _EPOCH_MS/_DAY_MS 数学基准 / file_utils 缓存无业务写入方（C1）/ retry 默认值语义分离 / 双份 themes 解析（各防护独立）
- **性能可接受**：每 profile 整库复制（一次性引导流程）/ exporter 查询全量驻留（单次导出）/ network 每次 get_static_config（单例查找零 IO）
- **并发理论**：go_quota 模块级缓存无锁（worker 串行）/ static_config 无锁单例（import 期）/ browser_creds 模块级无锁（B0.8 已停定时器）/ ws.recv 不按 id 匹配（未 enable domain）/ sqlite_utils 线程契约（同线程消费）/ 导出无防重入（原子写保完整性）
- **外观/风格**：main_window 绘制细节（饼图角度/内缩/截断/内联 QSS）/ system_tray 图标几何（比例）/ paintEvent 无显式 end（Qt 析构自动）/ $ 硬编码（OpenCode 计费固定 USD）/ PIE_FONT_SIZE / 托盘几何
- **宽容行为**：restoreGeometry 静默回退（宽容策略一致）/ 本地覆盖缺字段按免费估算（B4 说明区记录）
- **不可达/低价值**：login_timeout minutes=0（默认配置不可达）/ _CdpGuideTask 凭据写入不可注入（全链路难单测）/ toggle_theme 不即时持久化（退出即存设计）/ http_timeout 无类型契约（开发期暴露策略）/ retry 参数类型不校验（内部 API 调用方可控）/ logger LOG_LEVEL 静默回退（B2 断言固化）/ convert 下划线字面量（B1 断言固化）/ hidden_columns 非法 id 回写（D0.15 修复后）/ go_quota html 局部遮蔽（D0.14 修复后）/ parse_time_arg ISO 时区偏移（CLI 自测，转文档：相对时长为主流）/ estimate 全表扫描（D0.11 修复后）/ write_json mkstemp 位置（D0.12 修复后）/ --version 在 PyQt import 后（D0.13 修复后）
- **第 11 轮（A011）追加豁免 11 条**（用户复核，2 条已提升入 E 系列：min_ts=0、CREDS_CACHE_TTL）：settings refresh_interval_ms 无上限（仅手改配置可达）/ file_utils fdopen 理论 fd 泄漏（需验证）/ retry backoff clamp 宽于注释（内部 API 同族）/ main.py:6 import 场景 argv 误触发（无可达路径）/ pricing cost 空 dict 落入 pricing 分支（schema 数据语义 B3 族）/ go_quota in-flight stage 与 UI 引导卡交互（已核对闭环）/ notify 两模板未入契约组（三级兜底链）/ toggle 每次全量文件 IO（低频非热点）/ system_tray 每次重建 QPixmap（刷新间隔受限）/ 窗口销毁 in-flight 信号（Qt 析构自动断连）/ _show_columns_menu 每次 new QMenu（父挂载自动回收）

---

## 附录 A011：全量代码审计报告（第11轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读 + AST 扫描 + 行为验证（C0.6 实测复现）
> 结果：**P0-P3 级 15 条（中 3 / 低 12，含观察项提升 2 条）/ 参考级观察项 13 条（提升 2 条，维持豁免 11 条）**
> 状态：✅ 已修复（2026-08-13：E 系列 E0 正确性 4 条 + E2 配置化 2 条 + E3 清理 9 条全部完成，E1 无条目；探针 4/8/9 全 PASS + 修复验收 26/26 + 全量回归 43/43；E4 收尾含三项防漏损强制——同根因调用点全扫（write_json/save_config 全部调用点防护闭环）、说明区全量一致性扫描（补 4 处漂移：go_quota/opencode_usage/browser_creds/main_window）、配置键文档同步（credentials_ttl 三处一致）；任务清单见 x.progress.md E 系列）

- **上轮复核（A010 D 系列 17 项）**：D0.1-D0.15 + D3.1/D3.2 主体全部在位、零回退；发现 4 处"修复不完整"（main_window:1002 toggle save 漏 try、main.py 说明区未随 D0.13 同步、network.py 说明区残留 pricing 的 HTTP_TIMEOUT、pricing.py:342 关联配置漏 retry 两键）与 2 处"A010 已列未修"（C0.6 顺序契约、palette 值类型）
- **P0-P3（15 条）**：
  - 正确性：C0.6 顺序契约失效（改序导入不抛错，行为验证复现）；estimate LIMIT 无 ORDER BY（样本偏向最早消息）；_on_column_toggle save_config 无 try（D0.10 同类漏改）；min_ts=0 天数爆炸（观察项提升，需验证）
  - 配置化：in-flight 提示文案硬编码（6A.3 H3 定案违反）；CREDS_CACHE_TTL 未走 base.json（观察项提升）
  - 清理：in-flight 分支冗余调用；嵌套闭包 def add()；WIN32CRYPT/AES 缺失不写缓存（TTL 失效 + 重复 warning）；说明区 5 处失实/缺失；palette 值类型校验
- **参考级观察项 13 条**（用户复核后**提升 2 条**：min_ts=0 天数爆炸、CREDS_CACHE_TTL 配置化；维持 11 条已并入豁免定案清单）：settings 无上限/理论 fd 泄漏/backoff clamp 语义/cost 空 dict/schema 语义依赖等
- **亮点**：无高严重度（无确定性崩溃/错值）；三路交叉再次抓出"修复自身引入残留"模式（D0.10/D0.13/D3.1 同类漏改）；行为验证探针自毁还原机制经实测验证（git 兜底无损）

---

- **第 12 轮（A012）追加豁免 8 条**（用户复核，2 条已提升入 F 系列：refresh 连点、UsageRow 契约）：get_theme 第三主题静默错位（需验证，硬性 2 主题假设）/ palettes 容器类型非 dict 抛 ValueError（导入期即抛仅错误类型不统一）/ ORDER BY 无索引（仅 CLI 路径毫秒级）/ _parse_window usage_percent 未钳制（消费端双兜底 D0.6）/ subprocess 无 CREATE_NO_WINDOW（外观类）/ CLI --limit 无上界（自测路径）/ 浏览器: 文案硬编码（单次使用无调参场景）/ _profile_dirs 前缀匹配过宽（需验证，单浏览器 try 吞掉）

## 附录 A012：全量代码审计报告（第12轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读 + AST 扫描 + 行为验证（契约缺口实测）
> 结果：**P0-P3 级 7 条（中 1 / 低 6，含观察项提升 2 条）/ 参考级观察项 10 条（提升 2 条，维持豁免 8 条）**
> 状态：✅ 已修复（2026-08-13：F 系列 F0 正确性 3 条 + F3 清理 4 条全部完成，F1/F2 无条目；探针 5/5 + 修复验收 15/15 + 全量回归 43/43；F4 收尾防漏损延续——契约组与消费方交叉（go_quota_error_messages/quota_window_labels 全在契约块）、说明区扩展扫描补 3 处漂移（main_window 契约组/_usage 标志、opencode_usage 字段契约键集）、配置键无漂移；任务清单见 x.progress.md F 系列）

- **上轮复核（A011 E 系列 15 项）**：15/15 全部在位、零回退；E4 防漏损机制覆盖 5 文件但漏出 3 处"修复自身残留"（main.py 不在扫描范围漏网 ×2、pricing/themes 同文件漏改 ×2）；三处均为低危文档/死代码类
- **P0-P3（7 条）**：
  - 正确性：go_quota_error_messages 组未入契约键集（删 in_flight 键导入不抛，行为验证复现，运行时分支 KeyError——B0.6/C0.8 历史遗漏 + E2.1 未同步）；refresh 连点排队多任务（观察项提升）；UsageRow 字段与 _render_table 硬绑定无契约（观察项提升）
  - 清理：main.py:19 VERSION 未使用 import（D0.13 残留，E3.4 只修说明区未清代码）；main.py 说明区漏 notify_message_fallback（main.py 不在 E4 扫描范围）；pricing 说明区缺 _price_line/_rate_from_raw；themes 说明区未同步 E0.1 键序语义
- **参考级观察项 10 条**（用户复核后**提升 2 条**：refresh 连点、UsageRow 契约；维持 8 条已并入豁免定案清单）：第三主题静默错位/palettes 容器类型/ORDER BY 无索引/usage_percent 未钳制/subprocess 无 CREATE_NO_WINDOW/CLI --limit 无上界/浏览器文案硬编码/_profile_dirs 前缀过宽
- **亮点**：E 系列零回退；防漏损机制本轮当场抓出 3 处残留（证明机制有效，扩展扫描范围即可收敛）；credentials_ttl/in_flight 单点定义单点消费无漂移

---

- **第 13 轮（A013）追加豁免 8 条**（用户复核，1 条已提升入 G 系列：UsageSummary 契约）：_TOKEN_SUM_SELECT 与字段无静态校验（需验证，删列仅人工错误路径）/ 契约键集与说明区无自动联动（契约兜两环流程收敛）/ 契约块位置打断 dataclass 定义区（新增类时按 F0.3 模式即可）/ themes QUOTA_COLOR 常量名缩写（指代明确）/ system_tray MENU_LABELS 依赖导入顺序（无可达路径）/ 连点启动 N 个 QuotaTask（节流兜底）/ _UsageTask 双分支复位 vs finally 风格（当前正确，统一可选）/ 说明区契约列举省略 dialog 组（已校验在位）/ settings themes 空数组回退（配置错误理论级）/ logger 注释措辞（字面仍成立）

## 附录 A013：全量代码审计报告（第13轮，2026-08-13）

> 范围：全部 19 个 .py + 3 个 JSON；三路并行代理全文审读 + AST 扫描 + 行为验证（F0.2 连点挂起实测复现）
> 结果：**P0-P3 级 6 条（中 1 / 低 5，含观察项提升 1 条）/ 参考级观察项 9 条（提升 1 条，维持豁免 8 条）**
> 状态：✅ 已修复（2026-08-13：G 系列 G0 正确性 2 条 + G3 清理 4 条全部完成，G1/G2 无条目；探针 3/7 + 修复验收 15/15 + 全量回归 43/43；G4 收尾防漏损升级——说明区无残留字样反向断言（F3.1 漏改三次同根因终结）、说明区语义准确性扫描（G3.1 教训）、G0.2 契约消费方交叉（main_window/exporter 属性全命中，排除布局方法/文件名误匹配）；任务清单见 x.progress.md G 系列）

- **上轮复核（A012 F 系列 7 项）**：F0.1 契约组三方一致在位；F0.3 字段契约 20 处消费点零失配；F3.1 顶层分支完整；但发现 F0.2 修复不完整（pending 丢弃路径不消费——连点数据挂起 + 残留重复查询，行为验证复现）与 F3.1/F3.3 说明区残留 3 处（同根因模式第三次记录）
- **P0-P3（6 条）**：
  - 正确性：F0.2 pending 丢弃路径不消费（seq 不匹配分支 return 前未补发，连点请求被吞、数据挂起、后续同 seq 重复查询——行为验证复现）；UsageSummary 未入字段契约（观察项提升，与 F0.3 同风险面）
  - 清理：pricing 说明区 _price_line 主语写反 + _rate_from_raw cache 缺省描述不精确（F3.3 引入）；main.py 说明区 VERSION 段失实（F3.1 漏改，同根因第三次）；main.py 说明区漏 _SC/_notified_danger；main_window 说明区 refresh 行未同步 F0.2 + 关联配置 VERSION 失实
- **参考级观察项 9 条**（用户复核后**提升 1 条**：UsageSummary 契约；维持 8 条已并入豁免定案清单）：_TOKEN_SUM_SELECT 无静态校验/契约与说明区无联动/契约块位置/QUOTA_COLOR 缩写/MENU_LABELS 导入顺序/连点 N 个 QuotaTask/双分支复位风格/契约列举省略/dialog 组/settings themes 空数组回退/logger 注释措辞
- **亮点**：F0.1/F0.3 三方一致零失配；三路交叉 + 行为验证再次抓出"修复自身引入缺陷"（F0.2 挂起为确定性回归）
