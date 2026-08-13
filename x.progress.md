# 开发进度追踪（x.progress.md）

> 依据：`z.plan.md`（myboard 方案报告）
> 当前版本：ver 0.20（VERSION 单一来源在 config/static/base.json 的 version 字段）
> 记录格式：状态 [⏳ 待开发, ✅ 已完成] / 优先级 [高, 中, 低]
> 执行原则：每阶段完成后运行验证命令确认无回归，再进入下一阶段
> 错误策略：各模块开发时落实 z.plan.md 第四章约定（统一错误类型/降级不中断/缓存兜底/宽容解析/节流去重/保留旧数据/只读防误写）

---

## 阶段验证命令速查（AGENTS.md 运行与验证）

```powershell
# 导入验证（全量 19 个模块）
.\.venv\Scripts\python.exe -c "import main, modules.opencode_usage, modules.go_quota, modules.pricing, modules.exporter, modules.browser_creds, modules.credential_store, config.settings, config.static.static_config, ui.main_window, ui.system_tray, ui.themes, utils.logger, utils.file_utils, utils.retry, utils.convert, utils.network, utils.windows, utils.sqlite_utils"

# GUI 无头初始化验证（不弹窗）
$env:QT_QPA_PLATFORM="offscreen"; .\.venv\Scripts\python.exe -c "from PyQt6.QtWidgets import QApplication; from ui.main_window import MainWindow; app = QApplication([]); w = MainWindow(); print('GUI init OK')"

# 验证脚本（按轮次，全量回归 = 全部运行）
# 基线 S1-S8
.\.venv\Scripts\python.exe .temp\verify_s1.py   # S1 骨架：logger/file_utils/retry/main
.\.venv\Scripts\python.exe .temp\verify_s2.py   # S2 用量统计 + pricing
.\.venv\Scripts\python.exe .temp\verify_s3.py   # S3 Go 配额
.\.venv\Scripts\python.exe .temp\verify_s4.py   # S4 GUI（offscreen）
.\.venv\Scripts\python.exe .temp\verify_s5.py   # S5 配置/导出/文档
.\.venv\Scripts\python.exe .temp\verify_s6.py   # S6.1 浏览器凭据 + CDP
.\.venv\Scripts\python.exe .temp\verify_s7.py   # S6.2 凭据配置引导
.\.venv\Scripts\python.exe .temp\verify_s8.py   # S7.1 真实 Bug 修复
.\.venv\Scripts\python.exe .temp\verify_s9.py   # S7.2 中危问题修复
.\.venv\Scripts\python.exe .temp\verify_s10.py  # S7.3 消重与函数抽取
.\.venv\Scripts\python.exe .temp\verify_s11.py  # S7.4 注释规范检测
.\.venv\Scripts\python.exe .temp\verify_s12.py  # S8.1/S8.2 静态配置检验
.\.venv\Scripts\python.exe .temp\verify_s13.py  # S8.3/S8.4 UI 外置与用户配置
.\.venv\Scripts\python.exe .temp\verify_s14.py  # S8.5 VERSION 迁移与 constants 删除
# V0.08 P2-P8
.\.venv\Scripts\python.exe .temp\verify_v0808_p2.py  # 目录集中项目内
.\.venv\Scripts\python.exe .temp\verify_v0808_p3.py  # API key 链路删除
.\.venv\Scripts\python.exe .temp\verify_v0808_p4.py  # 凭据 DPAPI 加密
.\.venv\Scripts\python.exe .temp\verify_v0808_p5.py  # 重置时间显示
.\.venv\Scripts\python.exe .temp\verify_v0808_p6.py  # 跨项目探测移除
.\.venv\Scripts\python.exe .temp\verify_v0808_p7.py  # 按日期倒序
.\.venv\Scripts\python.exe .temp\verify_v0808_p8.py  # 月度统计
# V0.09 UI 改版
.\.venv\Scripts\python.exe .temp\verify_v0809_1.py  # 时区/元信息/自动更新
.\.venv\Scripts\python.exe .temp\verify_v0809_2.py  # 卡片区与总览
.\.venv\Scripts\python.exe .temp\verify_v0809_3.py  # 表格列开关
.\.venv\Scripts\python.exe .temp\verify_v0809_4.py  # 配额饼图
.\.venv\Scripts\python.exe .temp\verify_v0809_5.py  # 会话维度
# V0.10 二次审计三批
.\.venv\Scripts\python.exe .temp\verify_v1010_1.py  # 高价值 H1-H10
.\.venv\Scripts\python.exe .temp\verify_v1010_2.py  # 中价值 M1-M20
.\.venv\Scripts\python.exe .temp\verify_v1010_3.py  # 低价值 L1-L16
# 第三轮审计三批
.\.venv\Scripts\python.exe .temp\verify_v3a1.py  # 跨模块复用
.\.venv\Scripts\python.exe .temp\verify_v3a2.py  # 小错误/边界
.\.venv\Scripts\python.exe .temp\verify_v3a3.py  # 死代码/硬编码
# 第四轮审计三批
.\.venv\Scripts\python.exe .temp\verify_v4a1.py  # 错漏
.\.venv\Scripts\python.exe .temp\verify_v4a2.py  # 重复实现收敛
.\.venv\Scripts\python.exe .temp\verify_v4a3.py  # 清理/规范
# 第五轮审计三批（V0.12）
.\.venv\Scripts\python.exe .temp\verify_5a1.py      # 错漏 + CDP 引导改案冒烟
.\.venv\Scripts\python.exe .temp\verify_5a2.py     # 重复实现收敛（25 项）
.\.venv\Scripts\python.exe .temp\verify_5a3.py     # 清理/规范（26 项）
.\.venv\Scripts\python.exe .temp\verify_5a3_gui.py # GUI 文案实测
# 第六轮审计四批（V0.13）
.\.venv\Scripts\python.exe .temp\verify_6a1.py     # 错漏（27 项）
.\.venv\Scripts\python.exe .temp\verify_6a2.py     # 防御性（18 项）
.\.venv\Scripts\python.exe .temp\verify_6a3.py     # 硬编码/清理（32 项）
.\.venv\Scripts\python.exe .temp\verify_6a4.py     # 重复/优化（30 项）
```

## S1-S6 完成记录（简化）

> 结果：S1-S6 全量回归 195 项断言通过（verify_s1:17 / s2:30 / s3:39 / s4:29 / s5:29 / s6:33 / s7:18）

包结构（modules/config/ui/utils/data）+ AGENTS.md + z.plan.md + git 干净单线历史 + `.venv`（Python 3.14）+ `main.py` 入口；utils 层 logger（双 handler）/file_utils（原子写+缓存单例）/retry（指数退避）。`opencode_usage.py`：三级路径探测、只读连接、json_extract 聚合（兼容新旧格式）、分组、cost 优先 + estimate 回退；`pricing.py`：三级来源（缓存→models.dev→内置）+ 本地覆盖 + 多币种；真实库对照 `opencode stats` 一致。`go_quota.py`：凭据链（env→配置→浏览器）去重首成功、HTML 解析三窗口 + max 最紧、节流 + 缓存兜底 + 四分类错误（注：当时含 auth.json 链路，V0.08 P3 已删）。
GUI：themes 双主题 QSS + 三色分级；main_window 卡片/进度条/表格/后台加载/防双加载/保留旧 view/定时刷新/主题切换；system_tray 状态色图标 + 菜单 + 信号解耦。settings 持久化（宽容解析）；exporter 5 CSV + usage.json（现 6 个）+ GUI 导出；AGENTS.md 错误策略落地；README；closeEvent 托盘常驻。`browser_creds.py`：v10 DPAPI+AES-GCM 离线解密（实测确认 History/Local State 可读、Cookies 独占锁定）；v20 CDP 方案（临时 profile + getAllCookies，Chrome 自行解密跨版本稳定）；凭据引导（卡片 + 一键 CDP 后台全流程 + 手动填写，P4 后改对话框加密）；S6.3 多 provider 评估关闭。

---

## S7 审计整改（依据 z.plan.md 第九章审计结果）

> 目标：修复 4 个真实 bug + 8 个中危 + 消重抽取 + 注释规范定案；全量回归 279 项通过

4 个真实 bug：retry 重试失效（分类错误原样抛交 retry，401/403 不重试）、托盘预警未接线（quota_updated 信号 + main.py 接线）、估算混入范围外消息（\_time_clause 复用）、日志目录崩溃（FileHandler 保护）。8 个中危：VERSION 循环依赖（constants.py 持值）、数字强转（新建 utils/convert.py 弹性转换）、QSS 不重算（unpolish/polish）、引导卡片误导（error_stage 分类，CDP 可解决才显示）、浏览器探测冒泡（逐浏览器 try）、CDP 端口抢占检测、死代码接入（v10 预检 + is_chrome_running 日志）。
消重抽取 14 项（flatten_tokens/\_TOKEN_SUM_SELECT/write_json 复用/\_rate_from_raw/\_with_copied_db/fetch_go_quota 与 \_build_ui 拆分/\_wait_for_login_cookie/themes 模板化/\_mark_cached/\_local_appdata/阈值常量等）。注释规则定案：函数下 `#` 注释 + 文件尾 `# =====` 说明区，**禁止 docstring 顶替**（verify_s11 AST 检测 + 155 函数整改零残留）。

---

## S8 配置层对齐 AccelWorld（json 驱动静态配置）

> 目标：静态配置 json 驱动零硬编码；用户配置 dataclass + json 持久化，两类严格分离
> 决策：VERSION 移入 base.json 单一来源（constants.py 删除）；用户配置移项目内 `config/user_config.json`；`get_project_root()` 置 utils/file_utils.py

新建 `config/static/`（config.json 映射表 + 加载器 + 缓存单例 + 失败抛 RuntimeError）；base.json 外置窗口/刷新/节流/重试/CDP/导出/定价等 17 处参数；ui.json 外置颜色阈值/托盘图标/表头；settings 默认值从静态配置现取。7 个模块全部 `_SC` 顶层一次性解包（运行时零 IO）。全量回归 **328 项全部通过** + GUI offscreen OK；AGENTS.md 结构章节重写、README/z.plan.md 同步。

---

## V0.08 P2-P8 整体改造（依据 z.plan.md 第十章）

> 目标：P2-P8 七个问题一次整体改造（凭据/路径治理 + 展示修正 + 月度统计）；2026-08-10 完成；全量回归 409 项通过

路径治理：删跨项目凭据探测（P6，仅 env + 项目内）；凭据/日志/价格缓存集中项目内 data/（P2，base.json 三 dir 字段驱动，旧用户目录残留清理迁移）；删除 API key 链路（P3：models 接口与 auth.json 读取链全移除，主流程简化为"节流→凭据→三窗口"，grep 零残留）。
凭据 DPAPI 加密存储（P4：新增 credential_store.py，encrypted_v1 + 明文旧格式兼容读取，win32crypt 缺失拒绝明文落盘；真实验证适配 pywin32 两个返回结构怪癖——CryptProtectData 直接返回 bytes、CryptUnprotectData 数据在第二元素）；重置时间 %m-%d %H:%M（P5）；按日期倒序（P7）；月度统计 by_month（P8，GUI/CLI/导出 6 CSV，真实库月份与日期聚合一致）。版本 ver 0.08；README/AGENTS.md/z.plan/y.problem 同步；提交由用户执行。

---

## V0.09 UI 改版与维护（P12-P19 + P21，2026-08-10 规划）

> 目标：基础修复 + 卡片区与总览重构 + 表格列开关 + 配额饼图 + 会话维度；P20 属 V0.11；全量回归 506 项通过

基础修复：配额重置时间本地时区（UI + CLI 双处 astimezone，实测修复前差 8 小时）、删除凭据元信息行、自动更新链路排查（结论无 bug）。卡片重排（总tokens/输入/输出/缓存率/总费用）+ 总览独立按钮 + 总量明细弹窗（维度下拉移除 total 伪维度）；表格 9 列重构（缓存读+写合并 + 缓存率列）+ 列开关持久化；"最紧窗口"文字改 QPainter 小饼图（分级色 + 中心"剩余 Y%"，缓存/错误时隐藏）；新增 by_session 维度（LEFT JOIN session 取标题｜目录，缺列降级 session_id；CLI/GUI/导出 8 CSV）。版本 ver 0.09；README/y.problem/z.plan 同步。

---

## V0.10 二次审计整改（依据 z.plan.md 第十二章，2026-08-10 规划）

> 目标：59 条发现按三批整改（高 10 → 中 20 → 低 22）；全量回归 596 项通过

高价值：H1 审计误判证伪保留（`except GoQuotaError: raise` 必要——401/403 分类错误会被外层包装破坏，传播测试证实）；OpenAuth 死条件收敛、不可达 2xx 检查删除；login_wait_seconds 默认 None 走 base.json；refresh 远程失败回退旧缓存；UA 去硬编码；临时目录清理补全；阈值单一来源。中价值：8 处死代码删除；M11 `_status_bar` 结构性整改（状态栏在信号连接区提前创建、导出信号直连、转发方法删除——消除初始化顺序依赖）；一行转发内联；抽取复用（\_read_local_state_json/PRAGMA 缓存）；说明区补齐。
低价值：行宽/魔法数字/冗余清理；THEMES 单一来源；映射缺键抛 RuntimeError；base.json +8 参数（table_limit_group/day、cdp_fetch/wait_timeout、http_timeout、app_name、log_level）+ ui.json 饼图参数；托盘图标几何按比例。版本 ver 0.10。

---

## 第三轮审计整改（依据 z.plan.md 第十三章，2026-08-11 规划）

> 目标：57 条发现按三批整改（复用 15 → 小错误/边界 9 → 死代码/硬编码约 25）；全量回归 690 项通过

跨模块复用：新建 utils/network.py（http_get 统一，go_quota 保留 401/403 分类）；read_json/round_cost ×5/常量（SUBPROCESS_TIMEOUT/RETRY_NETWORK_ERRORS/OAUTH_REDIRECT_MARKER/凭据键/APP_NAME）收敛；公开入口去下划线；CSV 列名推导；\_by_field 抽取。小错误/边界：bool 语义对齐、min_ts=0 纪元边界、cost_source 修正、CLI 坏库中文提示、映射值类型校验。清理：死代码删除、\_load_rate_items 合并、过期缓存回退旧缓存、参数/文案外置（db_default_path/notify/布局/色值）；BUNDLED_PRICES 评估**保留**（离线兜底有意设计）；3A.4 收尾（版本 ver 0.11 与第四轮一并实施）。

---

## 第四轮审计整改（2026-08-12 规划）

> 目标：47 条发现按三批整改（错漏 11 → 重复实现 5 → 清理/规范约 20）；全量回归 788 项通过；版本 ver 0.11

错漏：exporter CSV 计数修正、缓存毒化修复（解析失败不写缓存）+ unlink 竞态、sqlite URI 转义两处、parse_time_arg strip 统一、show_guide 永真精简、v20 提示每会话一次、CDP 响应结构校验、to_optional_float bool 排除。重复实现：APP_NAME 单一来源（utils.logger 导出）、新建 utils/windows.py（win32crypt 降级 + WIN32CRYPT_AVAILABLE + DPAPI 三处收敛）、凭据去重键共享、文案与 24 色调色板外置 ui.json（S8.3 颜色外置补齐）。
清理/规范：rows 伪维度删除、闭包参数化提取（3 查询函数 + \*query_args 透传，AST 确认无嵌套 def）、limit 常量收敛、THEMES 外置、hidden_columns strip、防御补强（mapping 非 dict/retry assert）、说明区补齐、审计报告入 z.plan 第十四章。

### 历轮遗留

> P1/P9（多账户区分）、P11（明文兼容去留）、P22（测试专用接口）待评估；P20（模型数据页+社交跟踪）V0.11 实施，见 y.problem.md

---

## 第五轮审计整改完成（2026-08-12 审计，2026-08-13 已实施）

> 目标：36 条发现按三批整改（错漏 6 → 重复实现/复用 5 → 清理规范约 25）；基线回归 788 项
> 结果：三批全部完成——verify_5a1 + verify_5a2（25 项）+ verify_5a3（26 项）+ verify_5a3_gui 文案实测 + verify_s11 全回归通过

第一批错漏：v20 提示模块级会话级去重（`_v20_warned` 标志，刷新不再刷屏）；CDP 元素级 dict 校验；error_stage 枚举说明修正（decoding 归一为 provider）；**CDP 引导改案**（与用户对齐：不再读 History——workspaceID 改从登录后页面 URL 提取，`fetch_login_state_via_cdp` 一次会话拿 cookie + Runtime.evaluate location.href，多 profile 漏检根源消除；v10 离线路径 `read_workspace_ids` 保留）；cost 浮点容差（<0.00005）+ `_is_dark` 冗余初始化删除；说明区缺项补齐。
第二批重复实现：rows 按 DIMENSIONS 推导构建（day 特例 TABLE_LIMIT_DAY）；`QUOTA_WINDOW_KEYS` 统一三处窗口键 + CLI 文案引 ui.json（D5 唯一残留清零）；pricing 键映射复用 `_rate_from_raw`（PRICE_KEY_MAP）；windows.py 统一日志入口；标题/tooltip 常量外置 ui.json（app_subtitle）。
第三批清理规范：未用 import 删除；dark/light 与"总 token："收敛（LIGHT_THEME_NAME/TOTAL_TOKEN_PREFIX）；main_window 文案全量外置 ui.json（卡片/区域/按钮/状态栏/对话框/引导消息/明细行）+ 托盘菜单；timeout 族常量（SUBPROCESS_TIMEOUT + CDP 探测 3 个）；Path.expanduser；防御补强（文件不存在不写缓存、static_config data 非 dict 抛错、os_crypt 容错两处、error_stage 常量导出去字符串耦合）；异常元组去冗余、int(round) 提局部变量；DPAPI 描述串常量；说明区失实修正（9222→CDP_PORT、阈值注释引用配置）。round_cost digits 评估**保留**（口径稳定，说明区记录结论）。

---

## 第六轮审计整改完成（2026-08-13 审计，2026-08-13 已实施）

> 目标：38 条发现按四批整改（错漏 7 → 防御性 6 → 硬编码/清理 13 → 重复/优化 10 + 确认保留 2）；基线回归按批次验证
> 依据：z.plan.md 第十六章；执行原则：每项完成后运行对应验证
> 结果：四批全部完成——全量回归 43 个验证脚本零失败（s1-s14 + v0808/v0809/v1010/3A/4A/5A/6A 全系列）；同步修复 5A.1 遗留脚本欠账（s6/s7/s9/s10/v4a1 旧函数名）与 8 处历史脚本过期断言；README/AGENTS.md/z.plan.md 同步

第一批错漏（6A.1）：themes `{chunk_ok}` 占位符补键（ui.json palettes 双色）；convert.to_int 补 OverflowError（"inf"/"1e999" 崩溃逃逸）；CDP 探测族走 base.json（CDP_FETCH_TIMEOUT/CDP_WAIT_TIMEOUT 复用 cdp_fetch/wait_timeout，说明区失实修正）；launch_chrome_debug 失败路径清理临时目录；parse_time_arg 注释/help 补 m；find_db_path CLI 分支失败补 warning；network 说明区注明 15.0 兜底语义。
第二批防御性（6A.2）：by_session 缺 id 列降级不 JOIN（旧库缺列崩溃消除）；托盘 QMenu 存实例属性防 GC（QSystemTrayIcon 非 QWidget 不能挂父）；刷新间隔下限（base.json min_refresh_interval_ms，防手改 1ms 疯狂刷新）；logger 双检查锁防并发双挂 handler；retry 参数 clamp（retries/delay/backoff 负数不崩）；凭据缺文件 WARNING 降级 DEBUG。
第三批硬编码/清理（6A.3）：pricing 舍入位数常量（COST_COMPARE_DIGITS，浮点容差非展示精度）；UNKNOWN_LABEL/go_quota 凭据缺失文案/任务错误文案 4 处外置 ui.json；DPAPI 描述串从 base.json app_name 派生（消除双源）；费用容差/亿单位/时间格式外置；5 处未用 import 删除（Path×3/to_float/Any）。
第四批重复/优化（6A.4）：新建 utils/sqlite_utils.py（只读连接两处收敛，URI 转义行为保留）；配额窗口键/主题名/VERSION 单一来源（QUOTA_WINDOW_KEYS/THEME_NAMES 从 ui.json 派生/utils.logger 导出）；\_base_sql 共用 time_clause；estimate_cost 四段抽 \_price_line；缓存率复合函数；配额预警去重（持续超限只通知一次）；日志轮转（RotatingFileHandler，base.json 参数）；to_float 合并评估**不合并**（0/None 兜底语义不同，结论记录说明区）。
确认保留：go_quota add 闭包（第五轮确认项）；network RETRY_NETWORK_ERRORS 含 URLError 为有意设计（5xx/429 重试，401/403 已分类）——不整改

## A. 第7轮审计修复任务清单（依据 z.plan.md 附录 A007）——✅ 全部完成（2026-08-13，A0-A4）

> 目标：P2 2 + P3 16 = 18 条 P 级 + 跨组提示补充 1 条（settings.py:16 注释失实）按五组整改（正确性 → 去重 → 配置化 → 清理 → 验证收尾）；基线回归 43 个验证脚本
> 执行原则：每项完成后运行对应验证；全部完成后全量回归
> go_quota add 闭包（第五轮确认项）；network RETRY_NETWORK_ERRORS 含 URLError 为有意设计（5xx/429 重试，401/403 已分类）——不整改

### A0 P0 正确性

- [x] A0.1 os_crypt 非 dict 容错（browser_creds.py:167/322）——os_crypt = local_state.get("os_crypt"); if not isinstance(os_crypt, dict): return None；验证：verify 构造 {"os_crypt": "corrupted"} 断言 \_load_aes_key 返回 None 不抛
- [x] A0.2 CDP_PROBE_TIMEOUT 重名去重（browser_creds.py:47）——删除 47 行旧定义，保留 70 行；验证：AST 断言全文件仅 1 处定义
- [x] A0.3 host_key 兼容带点 domain cookie（browser_creds.py:187，需验证真实形态）——WHERE host_key IN (?, ?) 含 .opencode.ai；验证：构造带点 host_key 库断言命中
- [x] A0.4 OpenAuth 误判收敛（go_quota.py:206，需验证）——限定登录页特征（URL 或专属脚本片段）；验证：正常 HTML 含 OpenAuth 字样不误判
- [x] A0.5 进度条 None 分支重置格式（main_window.py:763-775）——补 bar.setFormat("") + 清 chunk 样式；验证：构造窗口值→None 过渡断言无旧百分比
- [x] A0.6 CDP 引导期定时刷新重现引导卡（main_window.py:695-700）——引导标志位抑制 show_guide；验证：引导期模拟刷新断言引导卡不重现
- [x] A0.7 引导期手动填写与 worker 并发写凭据（main_window.py:702-722）——引导期禁用手动按钮（与自动按钮对称）；验证：引导期手动按钮禁用断言
- [x] A0.8 to_float/to_optional_float nan 拦截（convert.py:27/40）——转换后 math.isnan 回落 default/None；验证：to_float("nan") 返回 0.0
- 状态：✅ 完成（2026-08-13，验证：probe_7a0 13 项全 PASS + 全量回归 43/43 + verify_s11 4/4；同步 verify_s5/v1010_1/6a4 断言）｜优先级：高

### A1 P1 去重

- [x] A1.1 标题格式单点（utils.logger 导出 build_app_title()）——main_window:452 + system_tray:31 改引用；验证：两处标题与函数输出一致断言
- 状态：✅ 完成（2026-08-13，验证：probe_7a1 9 项全 PASS + 全量回归 43/43 + GUI 标题三处一致；同步 6 个历史脚本导入源/断言）｜优先级：中

### A2 P2 配置化

- [x] A2.1 K/M/B/G 单位体系决策（main_window.py:373-381）——外置 ui.json 或记录"格式化约定不入配置"；验证：按决策断言
- [x] A2.2 default_theme 与 themes[0] 双源（base.json/config）——default_theme 从 themes[0] 派生或校验；验证：改 ui.json themes 后默认主题仍生效
- [x] A2.3 go_quota CLI 时间格式外置（go_quota.py:426）——引用 ui.json reset_time_format 或新增键；验证：CLI 输出格式与配置一致
- [x] A2.4 network.py 默认值双源（network.py:16）——默认改 None 强制显式传或注释锚定 base.json 键名；验证：调用方全部显式传参断言
- 状态：✅ 完成（2026-08-13，验证：probe_7a2 11 项全 PASS + A2.4 timeout 回退行为验证 + 全量回归 43/43；同步 verify_6a1 E7 断言）｜优先级：中

### A3 P3 清理

- [x] A3.1 说明区失实修正 4 处——windows.py:64（base.json app_name）/ main.py:98（ui.json）/ settings.py:95（min_refresh_interval_ms）/ logger.py:88（4 键）；验证：grep 说明区关键字
- [x] A3.2 settings.py:16 注释失实修正——"themes.py 引用本常量"改为"与 themes.py 同源于 ui.json themes 数组"；验证：grep 注释文本
- [x] A3.3 说明区漏 \_format_cache_rate_of（main_window.py:897-904）——补条目并标注被复合函数消费；验证：verify_s11 风格说明区全覆盖断言
- [x] A3.4 opencode_usage 顶层 \_SC 单点解包（:24-37 五处）——统一 \_SC = get_static_config()；验证：AST 断言无直取
- [x] A3.5 themes 契约校验（themes.py:89-94/104-106）——\_build_theme 后检测残留 {…} 抛 RuntimeError + THEME_NAMES 长度校验；验证：坏配置断言抛错
- 状态：✅ 完成（2026-08-13，验证：probe_7a3 9 项全 PASS + 契约校验行为验证（坏配置导入期抛错）+ 全量回归 43/43；settings 关联配置行拆行）｜优先级：低

### A4 验证与收尾

- [x] A4.1 全量回归 43 个验证脚本零失败 + GUI offscreen + 文档同步（README/z.plan 状态标注/版本推进决策）
- 状态：✅ 完成（2026-08-13，验证：全量回归 43/43 + import + GUI offscreen；README ui.json 参数表补键、z.plan 附录 A007 标注已修复）｜优先级：高

## B. 第8轮审计修复任务清单（依据 z.plan.md 附录 A008）——✅ 全部完成（2026-08-13，B0-B4）

> 目标：14 条 P 级（P2 1 + P3 13，说明区 6 处合并 1 条任务）+ 观察项提升 6 条（A1 键序/B7 托盘/B6 引导定时器/B8 节流文案/D2 CLI 下界/D1 排序）共 15 条修复任务 + B4 收尾；基线回归 43 个验证脚本
> 执行原则：每项完成后运行对应验证；全部完成后全量回归

### B0 P0 正确性

- [x] B0.1 Edge v20 判定下沉（main_window.py:343 + browser_creds.has_v20_cookies）——has_v20_cookies 改遍历 _browser_user_data_dirs() 任一命中即 True（复用既有单点）；验证：构造 Edge-only user data 断言判定 True
- [x] B0.2 to_float/to_optional_float 补 OverflowError（convert.py:32/48）——except 元组加 OverflowError（与 to_int 对齐）；验证：to_float(10**400) 返回 default 不抛
- [x] B0.3 pricing currency/source null 兜底（pricing.py:186-187）——item.get("currency") or "USD" / item.get("source") or default_source；验证：_rate_from_raw 传 None 断言非 "None"
- [x] B0.4 launch Popen OSError 分支清理（browser_creds.py:399-401）——except OSError 分支补 rmtree + 置 None（与 376-378 对称）；验证：AST 断言两失败分支均清理
- [x] B0.5 刷新 in-flight 去重（main_window.py:621-629/644-656）——refresh 递增序号，_on_usage_ready 校验丢弃过期结果；验证：模拟乱序完成断言旧任务不覆盖
- [x] B0.6 ui.json 结构性键契约校验（main_window 消费点）——仿 themes A3.5：导入期校验 card_titles 5 键/quota_window_labels 对齐/table_headers 长度 ≥ COLUMN_IDS；验证：删键配置断言导入期抛错
- [x] B0.7 notify 模板 .format 防护（main.py:55）——except KeyError 回退固定文案；验证：模板含未知占位符不抛
- [x] B0.8 引导期暂停定时刷新（main_window.py _start_cdp_guide/_on_guide_*）——引导启动 stop 刷新定时器、结束恢复 start（与按钮恢复同处配对）；验证：引导期模拟定时触发断言不执行
- [x] B0.9 托盘不可用检查（main.py:38）——tray.show 前 `QSystemTrayIcon.isSystemTrayAvailable()` 检查，不可用时 closeEvent 不 hide；验证：mock 不可用断言窗口不隐藏
- [x] B0.10 CLI --limit 下界（opencode_usage CLI）——`limit = max(1, args.limit)` 防 0/负数语义；验证：--limit 0 断言不崩且行数正常
- 状态：✅ 完成（2026-08-13，验证：probe_8b0 10 项 + 行为验证 8 项全 PASS + 全量回归 43/43；同步 verify_5a2/5a3/v3a1 断言）｜优先级：高

### B1 P1 去重

- [x] B1.1 settings _themes 重复构造（settings.py:17/26）——THEMES = _themes（保留两名称避免改数组双处同步）；验证：两常量值一致断言
- [x] B1.2 hidden_columns 排序提函数（main_window.py:838-841/873）——抽 `_sorted_hidden_columns()` 单点；验证：两处调用点输出一致断言
- 状态：✅ 完成（2026-08-13，验证：probe_8b1 4 项 + 行为验证 2 项 + 全量回归 43/43）｜优先级：中

### B2 P2 配置化

- [x] B2.1 TOKEN_ABBR_UNITS 键序排序（main_window.py:123-126）——解包时 `sorted(..., reverse=True)` 消除 JSON 键序契约（观察项提升）；验证：乱序配置断言缩略仍正确
- 状态：✅ 完成（2026-08-13，验证：probe_8b2 3 项 + 行为验证（乱序配置缩略仍正确）+ 全量回归 43/43）｜优先级：中

### B3 P3 清理

- [x] B3.1 说明区失实/残留修正 6 处——main_window.py:886（删 VERSION 条目）/ system_tray.py:103（删 APP_NAME/APP_SUBTITLE，补 build_app_title）/ themes.py:152（异常处理补 RuntimeError）/ exporter.py:107 + browser_creds.py:633 + go_quota.py:496（关联配置补 base.json/ui.json 键）；验证：grep 各说明区关键字
- [x] B3.2 节流文案动态化（go_quota.py:315）——"60 秒"改 f-string 引用 MIN_FETCH_INTERVAL（观察项提升）；验证：grep 无 "60 秒" 字面量
- 状态：✅ 完成（2026-08-13，验证：probe_8b3 10 项 + 全量回归 43/43；B3.2 运行时消息已动态化无需改，同步 verify_v3a1/v4a3 断言）｜优先级：低

### B4 验证与收尾

- [x] B4.1 全量回归 43 个验证脚本零失败 + GUI offscreen + 文档同步（README/z.plan 状态标注/版本推进决策）
- 状态：✅ 完成（2026-08-13，验证：全量回归 43/43 + import + GUI offscreen；README 补 notify_message_fallback、z.plan 附录 A008 标注已修复）｜优先级：高

## C. 第9轮审计修复任务清单（依据 z.plan.md 附录 A009）——✅ 全部完成（2026-08-13，C0-C4）

> 目标：P1 1 + P2 2 + P3 9 + 观察项提升 1（ui.json 契约扩展）共 13 条按五组整改；基线回归 43 个验证脚本
> 执行原则：每项完成后运行对应验证；全部完成后全量回归

### C0 P0 正确性

- [x] C0.1 pricing 远程定价结构重构（pricing.py:253-282，P1）——遍历顶层 provider → 其 models dict，canonical_key(provider, model) 构造 key（结构判断 + key 解析一起改）；验证：用现网 api.json 样例片段（openai/gpt-4o + anthropic/claude-sonnet-4-5）断言解析成功且 key 含 provider 前缀
- [x] C0.2 B0.7 防护补全（main.py:55-65）——except (KeyError, ValueError, IndexError) + fallback 二次 try 或纯静态拼接；验证：3 种坏模板（{used/!q/{}）实测不逃逸
- [x] C0.3 pricing 缓存写异常降级（pricing.py:115）——write_json 包 try/except OSError 仅 warning（与 _fetch_remote_prices 降级风格一致）；验证：mock write_json 抛 OSError 断言 load_price_map 仍返回内存表
- [x] C0.4 convert inf 拦截（convert.py:29-31/45-47）——if not math.isfinite(result) 统一覆盖 nan/inf/-inf；验证：to_float("inf") 返回 0.0、to_optional_float("inf") 返回 None
- [x] C0.5 quota/error 信号序号去重（main_window.py:192/252-254/745）——quota_ready/error 携带 seq 与 usage 同机制（或 go_quota in-flight 去重二选一）；验证：模拟乱序断言旧结果不覆盖
- [x] C0.6 themes 主题名-调色板顺序契约（themes.py:111-118）——校验 THEME_NAMES 与 palettes 键对齐且互异；验证：改序配置断言导入期抛错
- [x] C0.7 TABLE_HEADERS 严格相等校验（main_window.py:174-177）——!= 替代 <；验证：加列配置断言抛错
- [x] C0.8 ui.json 契约扩展（观察项 A1 提升）——B0.6 键集扩至全部消费键（status_messages 18 键/dialog_titles/dialog_prompts/guide_messages/tooltips/button_labels/menu_labels/notify_*）+ 模板类键占位符校验；验证：删键配置断言导入期抛错
- 状态：✅ 完成（2026-08-13，验证：probe_9c0 14 项 + 行为验证 C0.5/C0.6 + 全量回归 43/43；同步 verify_s4/s7/s8/s9/5a3/6a4 断言）｜优先级：高

### C1 P1 去重

- 无新增条目（观察项均不提升）
- 状态：— ｜优先级：—

### C2 P2 配置化

- 无新增条目（观察项均不提升）
- 状态：— ｜优先级：—

### C3 P3 清理

- [x] C3.1 opencode_usage 缩进修正（opencode_usage.py:586-589）——参数行与闭括号缩进对齐；验证：v1010_3 行宽/格式断言
- [x] C3.2 go_quota 说明区 60s 动态化（go_quota.py:308+481 两处）——"不足 60s" 改"不足 MIN_FETCH_INTERVAL 秒"；验证：grep 无 "60s" 字面量
- [x] C3.3 main_window 说明区 VERSION 尾巴清理（main_window.py:950）——删括号内 VERSION 说明；验证：grep 说明区无 VERSION
- [x] C3.4 main_window 说明区 PIE 归属修正（main_window.py:954-955）——PIE_START_ANGLE/FULL_CIRCLE_16 移出 ui.json 标注；验证：grep 说明区归属正确
- [x] C3.5 system_tray build_app_title 归类修正（system_tray.py:102-103）——移入函数区；验证：说明区结构断言
- 状态：✅ 完成（2026-08-13，验证：probe_9c3 5 项 + 全量回归 43/43；全部 edit 工具修改）｜优先级：低

### C4 验证与收尾

- [x] C4.1 全量回归 43 个验证脚本零失败 + GUI offscreen + 文档同步（README/z.plan 状态标注/版本推进决策）
- 状态：✅ 完成（2026-08-13，验证：全量回归 43/43 + import + GUI offscreen；z.plan 附录 A009 标注已修复）｜优先级：高

## D. 第10轮审计修复任务清单（依据 z.plan.md 附录 A010）

> 目标：P1 1 + P2 3 + P3 11 + 观察项提升 1（凭据探测 TTL）+ 大会战修复 5 条（A1-A5）共 21 条按五组整改；基线回归 43 个验证脚本
> 执行原则：每项完成后运行对应验证；全部完成后全量回归；修复验证用独立数据快照（防自证陷阱）；**每批完成后加修复验收（反向验证，写入 .temp/verify_d{批}\_accept.py，防修复引入新缺陷）**

### D0 P0 正确性

- [x] D0.1 pricing 字段名兼容（pricing.py:285，P1）——model_info.get("cost") or model_info.get("pricing")；验证：用真实 api.json 片段（cost 键 + 字符串/数字双形态）断言解析非空（禁用自证 mock）
- [x] D0.2 status_messages 契约去自证（main_window.py:170）—— uple(STATUS_MESSAGES) 改显式 18 键元组（与 menu_labels 同式）；验证：删键配置断言导入期抛错
- [x] D0.3 节流缓存不破坏预警去重（main.py:48-79）——缓存分支（is_cached）不复位 _notified_danger + 托盘按 overall_used_percent 更新而非置灰；验证：模拟缓存到达断言标志保持 + 不重复弹
- [x] D0.4 刷新 in-flight 去重（go_quota.fetch_go_quota）——模块级进行中标志/锁，在途请求直接返回等待或缓存；验证：并发两次调用断言实际请求一次
- [x] D0.5 模板占位符校验补全（main_window.py:212-240）——_TEMPLATE_PLACEHOLDERS 补 percent/value，_TEMPLATE_KEYS 并入 pie_remaining_template/detail_line_templates；验证：改坏占位符断言导入期抛错
- [x] D0.6 usage_percent 钳制（main_window.py:922 + go_quota.py:360）——render 前 clamp 0-100、overall_used_percent 对称钳制；验证：负值/超百断言显示钳制值
- [x] D0.7 notify_title 入契约 + 运行时防护（main.py:74 + main_window 契约）——契约组加 notify_title、main.py 74 行移入 try 链；验证：删键断言预警不逃逸
- [x] D0.8 凭据探测 TTL（观察项提升）——find_dashboard_credentials 结果加短 TTL 缓存（如 30s），刷新不重复全量探测；验证：两次调用断言探测一次
- [x] D0.9 解析空结果告警（pricing.py:298）——if not result: logger.warning(...) 与结构变更提示策略对齐；验证：空结果断言有 warning
- [x] D0.10 save_state 降级（main.py _quit_app + main_window closeEvent）——保存失败仅 warning 继续退出流程；验证：mock write_json 抛 OSError 断言退出路径执行
- [x] D0.11 estimate 查询加 LIMIT（opencode_usage _estimate_missing_costs，大会战 A1）——补 LIMIT 参数防大库拖死；验证：断言 SQL 含 LIMIT
- [x] D0.12 write_json mkstemp 移入 try（file_utils，大会战 A2）——防 fd 泄漏边缘；验证：异常路径断言临时文件清理
- [x] D0.13 --version 检查提前到 PyQt import 前（main.py，大会战 A3）——CLI 路径不加载 GUI 依赖；验证：--version 输出正常且不 import PyQt
- [x] D0.14 go_quota html 局部变量改名（大会战 A4）——`html` → `html_text` 消除模块名遮蔽；验证：grep 无遮蔽
- [x] D0.15 hidden_columns 脏 id 过滤（main_window _sorted_hidden_columns，大会战 A5）——保存点过滤不在 COLUMN_IDS 的 id；验证：脏 id 输入断言输出被过滤
- 状态：✅ 已完成（2026-08-13：D0.1-D0.15 全部实施，探针 15/15 + 修复验收 18/18 + 全量回归 43/43；含 main.py 嵌套修复——D0.3 缓存判断归位错误路径，6A4/S8 回归同步）｜优先级：高

### D1 P1 去重

- 无新增条目
- 状态：— ｜优先级：—

### D2 P2 配置化

- 无新增条目
- 状态：— ｜优先级：—

### D3 P3 清理

- [x] D3.1 HTTP_TIMEOUT 死代码 + 说明区失实（pricing.py:25/307/331）——删常量或显式传参统一；说明区补四级链路与关联配置键；验证：grep 无 HTTP_TIMEOUT 残留
- [x] D3.2 说明区缺失/重复修正 4 处——main_window（_format_cost 描述、契约校验块补列、_on_quota_ready 合并）、themes（异常处理补 C0.6）、system_tray（导入函数补 themes 两符号）；验证：grep 各说明区关键字
- 状态：✅ 已完成（2026-08-13：D3.1 删 pricing 死常量 + 说明区改四级链路（http_get timeout 回退单一来源）；D3.2 五处说明区修正；探针 13/13 + 全量回归 43/43；verify_v1010_3 同步删 pricing.HTTP_TIMEOUT 断言补 D3.1 语义）｜优先级：低

### D4 验证与收尾

- [x] D4.1 全量回归 43 个验证脚本零失败 + GUI offscreen + 文档同步（README/z.plan 状态标注/版本推进决策）
- 状态：✅ 已完成（2026-08-13：全量回归 43/43 + import 19 模块 + GUI offscreen；z.plan A010 附录状态更新为已修复；版本推进 ver 0.17——base.json/README 徽章/README 版本说明/x.progress 头部 4 处一致）｜优先级：高

## E. 第11轮审计修复任务清单（依据 z.plan.md 附录 A011）

### E0 P0 正确性

- [x] E0.1 C0.6 顺序契约修复（themes.py:117-125）——校验 tuple(palettes 键序) 与 THEME_NAMES 完全一致，否则导入期抛 RuntimeError；验证：真实改序 ui.json 导入断言抛错（probe_a011_c06 先 FAIL 后 PASS）
- [x] E0.2 estimate LIMIT 补 ORDER BY（opencode_usage.py:463-465）——LIMIT 前加 ORDER BY time.created DESC（估算优先最新消息）；验证：断言 SQL 含 ORDER BY 且位置在 LIMIT 前
- [x] E0.3 _on_column_toggle save_config 加 try（main_window.py:1000-1002）——与 D0.10 同式 try+warning 降级；验证：mock write_json 抛 OSError 断言槽函数不逃逸
- [x] E0.4 min_ts=0 天数爆炸排查（opencode_usage.py:196-198，观察项提升）——确认 time.created=0 记录的过滤或告警（缺失形态已覆盖，补 0 值形态）；验证：构造 created=0 数据断言结果可控
- 状态：✅ 已完成（2026-08-13：E0.1 键序完全一致校验（真实改序导入抛错）；E0.2 ORDER BY created DESC 先于 LIMIT；E0.3 列开关持久化降级 warning；E0.4 created=0 归零+告警。探针 4/4 + 修复验收 7/7 + 全量回归 43/43；测试资产同步：verify_6a4 版本断言 0.17、verify_v3a2 S3 days=0、verify_5a3 允许列表补 E0.3 文案）｜优先级：高

### E1 P1 去重

- 无新增条目
- 状态：— ｜优先级：—

### E2 P2 配置化

- [x] E2.1 in-flight 提示文案外置（go_quota.py:391 + ui.json）——go_quota_error_messages 加 in_flight 键，代码改读 _SC.ui 键；验证：verify_6a3 同步断言新键存在
- [x] E2.2 CREDS_CACHE_TTL 走 base.json（browser_creds.py:92，观察项提升）——常量改读 base.json 新键（credentials_ttl）；验证：grep 无硬编码 30.0 + 配置键有消费方
- 状态：✅ 已完成（2026-08-13：E2.1 ui.json 加 in_flight 键 + 代码改读；E2.2 base.json 加 credentials_ttl=30 + 常量改读；护栏③文档同步：browser_creds 说明区 + README 配置表；探针 8/8 + 验收 16/16（含 E0 段）+ 全量回归 43/43；verify_6a3 补 in_flight 断言）｜优先级：高

### E3 P3 清理

- [x] E3.1 in-flight 分支删冗余调用（go_quota.py:386-388）——直返 _fallback，删重复 _throttled_cache；验证：grep 分支内无二次调用
- [x] E3.2 嵌套闭包提为模块级函数（go_quota.py:127-137）——def add() 提为模块级私有函数（入参 seen/candidates）；验证：AST 扫描无 def 内 def
- [x] E3.3 WIN32CRYPT/AES 缺失分支写空缓存（browser_creds.py:101-103）——与成功路径同式缓存；验证：mock 缺库断言缓存被写
- [x] E3.4 main.py 说明区同步 D0.13（main.py:120-122）——main() 描述改"仅分发 run_gui()，--version 已顶层处理"；验证：grep 说明区关键字
- [x] E3.5 network.py 说明区删 pricing 引用（network.py:45）——改"go_quota 的 HTTP_TIMEOUT；pricing 走默认回退"；验证：grep 无 pricing 字样
- [x] E3.6 settings.py 说明区改写异常语义（settings.py:104）——补"写异常 re-raise 由调用方处理"；验证：grep 关键字
- [x] E3.7 browser_creds 说明区补缓存符号（600-611）——补 _creds_cache/_creds_cache_at/CREDS_CACHE_TTL；验证：grep 三符号
- [x] E3.8 pricing 关联配置补 retry 两键（pricing.py:342）——括号补 retry_count/retry_delay；验证：grep 两键
- [x] E3.9 palette 值类型校验（themes.py:96-100，A010 遗留）——替换前 isinstance str 校验抛 RuntimeError；验证：改数字配置导入断言抛错
- 状态：✅ 已完成（2026-08-13：E3.1 删冗余直返 _fallback；E3.2 _add_credential 模块级化；E3.3 缺库分支写空缓存；E3.4-E3.8 说明区 5 处同步 + go_quota 补 _add_credential 条目；E3.9 palette 值类型校验。探针 9/9 + 验收 26/26 + 全量回归 43/43）｜优先级：低

### E4 验证与收尾

- [x] E4.1 全量回归 43 个验证脚本零失败 + GUI offscreen + 修复验收（verify_e_accept 反向断言）+ 文档同步（README/z.plan/x.progress 状态 + 版本推进决策）——含三项防漏损强制（A011 分析结论，2026-08-13 定）：①同根因调用点全扫（grep 全部 write_json/save_config/写配置点，确认每个调用点都在异常防护内，不止 E0.3 目标一处）②说明区全量一致性扫描（本轮修改过的 themes/go_quota/browser_creds/opencode_usage/main_window 5 文件，说明区与实现 diff 逐行核对——含 E0.1/E0.2/E2.1/E2.2 修改处）③配置键文档同步检查（base.json 新键 → README 配置表/契约键集/说明区"关联配置"段三处一致；E2.1/E2.2 新增键必查）
- 状态：✅ 已完成（2026-08-13：全量回归 43/43 + 验收 26/26 + 冒烟；防漏损①全调用点防护闭环（exporter/go_quota 任务层与槽函数 try 已核实）；②说明区扫描补 4 处漂移（go_quota in_flight/opencode_usage ORDER BY+归零/browser_creds 缺库/main_window toggle 降级）；③credentials_ttl 三处一致；z.plan A011 状态已修复；版本推进 ver 0.18（base.json/README×2/x.progress/verify_6a4 五处一致））｜优先级：高

## F. 第12轮审计修复任务清单（依据 z.plan.md 附录 A012）

### F0 P0 正确性

- [x] F0.1 go_quota_error_messages 契约组（main_window.py:150-223 契约块 + go_quota.py:406/416）——_UI_STRUCT_KEYS 补 `("go_quota_error_messages", ("no_credentials","in_flight"), GO_QUOTA_ERROR_MESSAGES)` 组（含模块级解包与消费方同步）；验证：真实删 in_flight 键导入断言抛错（probe_a012_contract 先 FAIL 后 PASS）
- [x] F0.2 refresh 连点排队排查（main_window.py:759-767，观察项提升）——确认 _UsageTask 排队上限或 in-flight 去重（QThreadPool 有界 + 序号丢弃是否足够）；验证：并发调用断言任务不叠加（需验证后定案）
- [x] F0.3 UsageRow 契约校验（opencode_usage.py UsageRow + main_window.py:1015-1026，观察项提升）——dataclass 字段显式键集与 _render_table 消费属性比对（防字段改名 AttributeError 逃逸 Qt 槽）；验证：删字段断言导入/渲染抛契约错误
- 状态：✅ 已完成（2026-08-13：F0.1 契约组补 no_credentials/in_flight 两键（真实删键导入抛错）；F0.2 refresh 入口 in-flight 去重 + _UsageTask.run 提前复位 + _on_usage_ready pending 补发（行为验证：在途不叠加/pending 复位）；F0.3 TokenStats/UsageRow 显式字段键集契约（与 dataclass 字段比对，不一致导入期抛错）。探针 5/5 + 验收 10/10 + 全量回归 43/43；verify_s11 抓出 F0.2 的 global 声明插注释前违规并已修正）｜优先级：高

### F1 P1 去重

- 无新增条目
- 状态：— ｜优先级：—

### F2 P2 配置化

- 无新增条目
- 状态：— ｜优先级：—

### F3 P3 清理

- [x] F3.1 main.py:19 删未用 VERSION import（D0.13 残留，E3.4 同根因漏改）——import 改 `from utils.logger import APP_NAME, get_logger`；验证：grep main.py 函数体无 VERSION 引用
- [x] F3.2 main.py:132 说明区补 notify_message_fallback（main.py 不在 E4 扫描范围漏网）——关联配置段补列；验证：grep 关键字
- [x] F3.3 pricing.py:321-337 说明区补 _price_line/_rate_from_raw 两函数——函数段补两条（count/1e6*price 与弹性构建语义）；验证：grep 两符号
- [x] F3.4 themes.py:170-171 说明区同步 E0.1 键序语义——补"且顺序必须与 palettes 键序完全一致"；验证：grep 关键字
- 状态：✅ 已完成（2026-08-13：F3.1 删 VERSION import（同步 4 个测试资产 verify_s1/s9/s12/s14 改读 utils.logger 单点——main.VERSION 模块属性消费面确认仅测试资产）；F3.2 补 fallback 键；F3.3 补两函数；F3.4 键序语义。探针 5/5 + 验收 15/15 + 全量回归 43/43）｜优先级：低

### F4 验证与收尾

- [x] F4.1 全量回归 43 个验证脚本零失败 + GUI offscreen + 修复验收（verify_f_accept 反向断言）+ 文档同步（README/z.plan/x.progress 状态 + 版本推进决策）——防漏损延续：①同根因调用点全扫（契约组新增后 go_quota 消费方与契约键集交叉核对）②说明区全量一致性扫描扩展（覆盖 main.py/pricing/themes + 上轮 5 文件，含 F3 修改处）③配置键文档同步检查（无新增键，核对 E 系列键无漂移）
- 状态：✅ 已完成（2026-08-13：全量回归 43/43 + 验收 15/15 + 冒烟；防漏损①消费组×契约块交叉（go_quota_error_messages/quota_window_labels 全在契约块）；②说明区扩展扫描补 3 处漂移（main_window 契约组/_usage 标志、opencode_usage 字段契约键集——F0 三修复的说明区同步漏网）；③E 系列键无漂移（credentials_ttl 单点定义/消费、README 徽章==base.json）；z.plan A012 状态已修复；E4 残留状态行清理；版本推进 ver 0.19（五处一致））｜优先级：高

## G. 第13轮审计修复任务清单（依据 z.plan.md 附录 A013）

### G0 P0 正确性

- [x] G0.1 F0.2 pending 丢弃路径修复（main_window.py:817-819/833-835）——seq 不匹配分支 return 前消费 pending（用最新 _refresh_seq 启动补发，与渲染路径同逻辑；抽公共方法防双路径漂移）；验证：probe_a013_f02 连点场景断言 pending 被清空 + 补发一次（先 FAIL 后 PASS）
- [x] G0.2 UsageSummary 字段契约（opencode_usage.py:120-133，观察项提升）——与 F0.3 同机制补 _USAGE_SUMMARY_FIELDS 显式键集比对（sessions/messages/days/tokens/recorded_cost 等 10 字段）；验证：键集与实际字段一致 + 消费方（main_window/exporter/CLI）属性全命中
- 状态：✅ 已完成（2026-08-13：G0.1 _consume_pending 公共方法（过期丢弃/渲染两路径共用，无 pending 不补发防多余查询）；G0.2 _USAGE_SUMMARY_FIELDS 10 字段契约（类定义后比对，消费方全命中）。探针 3/3（行为验证：过期路径 pending 清空 + 补发最新序号）+ 验收 9/9 + 全量回归 43/43）｜优先级：高

### G1 P1 去重

- 无新增条目
- 状态：— ｜优先级：—

### G2 P2 配置化

- 无新增条目
- 状态：— ｜优先级：—

### G3 P3 清理

- [x] G3.1 pricing 说明区失实修正（pricing.py:327/329）——_price_line 改"price 为 None 计 0"、_rate_from_raw 改"input/output 按 0、cache 缺省 None 按无折扣"；验证：grep 关键字精确匹配
- [x] G3.2 main.py 说明区 VERSION 段改写（main.py:115-116）——删"模块级常量 VERSION"条目，改为"VERSION 由 utils.logger 单点导出（R4），main 仅 --version 分支局部 import（D0.13）"；验证：grep 无"模块级常量 VERSION"字样
- [x] G3.3 main.py 说明区补列（main.py:113-117）——模块级常量段补 _SC（静态配置解包）/ _notified_danger（预警去重标志）；验证：grep 两符号
- [x] G3.4 main_window 说明区两处同步（main_window.py:1151/1178）——refresh 行补"in_flight 时仅置 pending 并只启动配额任务"；关联配置 VERSION 改"utils.logger"；验证：grep 关键字
- 状态：✅ 已完成（2026-08-13：G3.1 主语修正（price 为 None 计 0）+ cache 缺省精确；G3.2 VERSION 条目改写为单点导出说明（同根因 F3.1 漏改第三次终结）；G3.3 补 _SC/_notified_danger；G3.4 refresh 行 pending 描述 + 关联配置 VERSION 改 utils.logger。探针 7/7 + 验收 15/15 + 全量回归 43/43）｜优先级：低

### G4 验证与收尾

- [x] G4.1 全量回归 43 个验证脚本零失败 + GUI offscreen + 修复验收（verify_g_accept 反向断言）+ 文档同步（README/z.plan/x.progress 状态 + 版本推进决策）——防漏损延续：①探针补"说明区无残留字样"反向断言（A013 教训：F3.1 漏改三次同根因，grep 存在性检查抓不到说明区失实）②说明区语义准确性扫描（非仅符号存在——P2 教训）③契约扩展后消费方交叉核对（G0.2 新增键集 vs main_window/exporter/CLI）
- 状态：✅ 已完成（2026-08-13：全量回归 43/43 + 验收 15/15 + 冒烟；防漏损①说明区无残留字样 4 处全过（F3.1 漏改三次终结）；②语义准确性扫描 4 处（_price_line/_rate_from_raw 说明与实现一致）；③契约消费方交叉（main_window/exporter/CLI 属性全命中，排除 row.addWidget/summary.csv 误匹配）；z.plan A013 状态已修复；版本推进 ver 0.20（五处一致））｜优先级：高
