# 开发进度追踪（x.progress.md）

> 依据：`z.plan.md`（myboard 方案报告）
> 当前版本：ver 0.213（VERSION 单一来源在 config/static/base.json 的 version 字段；2026-08-13 起审计修复只提升第三位数字，功能批次按用户指定编号）
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

---

## 第七轮审计整改完成（A 系列，2026-08-13 审计，2026-08-13 已实施）

> 目标：18 条 P 级 + 跨组提示 1 条按五组整改（正确性 → 去重 → 配置化 → 清理 → 验证收尾）；全量回归 43/43
> 依据：z.plan.md 附录 A007；结果：五组全部完成（probe_7a0-7a3 全 PASS）

第一批正确性（A0）：os_crypt 非 dict 容错两处（构造 corrupted 数据断言返回 None 不抛）；CDP_PROBE_TIMEOUT 重名定义删除（保留后定义）；host_key 带点 domain cookie 兼容（WHERE host_key IN (?, ?) 含 .opencode.ai）；OpenAuth 登录页特征限定（正常 HTML 含 OpenAuth 字样不误判）；进度条 None 分支重置格式（setFormat("") + 清 chunk 样式，防旧百分比残留）；CDP 引导期定时刷新重现引导卡抑制（引导标志位）；引导期手动填写按钮禁用（防与 worker 并发写凭据）；to_float/to_optional_float nan 拦截（math.isnan 回落 default）。
第二批去重（A1）：标题格式单点 utils.logger.build_app_title() 导出（main_window/system_tray 两处引用收敛）。
第三批配置化（A2）：K/M/B/G 单位体系决策记录（格式化约定不入配置）；default_theme 从 themes[0] 回退防护（改 ui.json themes 后默认主题仍生效）；go_quota CLI 时间格式外置 ui.json；network 默认超时 None 回退 base.json http_timeout。
第四批清理（A3）：说明区失实修正 4 处（windows/main/settings/logger）；settings.py:16 注释失实修正（同源表述）；\_format_cache_rate_of 说明区补列；opencode_usage \_SC 单点解包（5 处直取消除）；themes 契约校验首建（\_build_theme 残留占位符检测 + THEME_NAMES 长度校验导入期抛错）。
收尾（A4）：全量回归 43/43 + README ui.json 参数表补键 + z.plan A007 标注已修复。

---

## 第八轮审计整改完成（B 系列，2026-08-13 审计，2026-08-13 已实施）

> 目标：15 条修复任务按五组整改；全量回归 43/43
> 依据：z.plan.md 附录 A008；结果：五组全部完成（probe_8b0-8b3 + 行为验证）

第一批正确性（B0）：Edge v20 判定下沉 browser_creds（has_v20_cookies 遍历双浏览器任一命中）；to_float/to_optional_float 补 OverflowError（10**400 实测逃逸封堵）；pricing currency/source null 兜底（防 "None" 字符串错值）；launch Popen OSError 分支清理临时目录；刷新序号 in-flight 去重（递增 seq，乱序完成丢弃过期结果）；ui.json 结构性键契约校验首建（删键导入期抛错）；notify 模板 .format 防护（未知占位符 KeyError 回退固定文案）；引导期暂停定时刷新（stop/start 配对恢复）；托盘不可用检查（isSystemTrayAvailable，closeEvent 不 hide）；CLI --limit 下界 max(1, ...)。
第二批去重（B1）：settings \_themes 复用（THEMES = _themes）；hidden_columns 排序抽 \_sorted_hidden_columns 单点。
第三批配置化（B2）：TOKEN_ABBR_UNITS 解包排序消除 JSON 键序依赖（乱序配置缩略仍正确）。
第四批清理（B3）：说明区失实/残留修正 6 处（main_window VERSION 条目/system_tray APP_NAME/themes 异常处理/exporter/browser_creds/go_quota 关联配置）；节流文案动态化评估（运行时已动态无需改）。

---

## 第九轮审计整改完成（C 系列，2026-08-13 审计，2026-08-13 已实施）

> 目标：13 条按五组整改；全量回归 43/43
> 依据：z.plan.md 附录 A009；结果：五组全部完成（probe_9c0/9c3 + 行为验证）

第一批正确性（C0）：**pricing 远程定价结构重构**（现网 api.json 实测：顶层 provider 键 → models dict、model key 无 provider/ 前缀——canonical_key 构造，死路径复活，P1）；B0.7 防护补全（`'{used'`/`'{used!q}'` ValueError、`'{}'` IndexError 实测逃逸封堵 + fallback 二次保护）；pricing 缓存写异常降级（OSError 仅 warning 不拖垮 estimate 链路）；convert inf 拦截（isfinite 统一 nan/inf/-inf）；quota/error 信号序号去重（与 usage 同机制）；themes 主题名-调色板顺序契约（改序导入期抛错）；TABLE_HEADERS 严格相等校验（防短防长，加列配置抛错）；ui.json 契约扩展至全部消费键（status_messages/dialog/guide/tooltips/button_labels/menu_labels + 模板占位符校验）。
清理（C3）：opencode_usage 缩进对齐；go_quota "60s" 动态化 MIN_FETCH_INTERVAL；main_window VERSION 尾巴清理/PIE 归属修正；system_tray build_app_title 归类移入函数区。

---

## 第十轮审计整改完成（D 系列，2026-08-13 审计，2026-08-13 已实施，版本 ver 0.17）

> 目标：15 条 P 级 + 大会战 5 条共 21 条按五组整改；全量回归 43/43
> 依据：z.plan.md 附录 A010；结果：五组全部完成（探针 15/15 + 修复验收 18/18——修复验收机制自本轮起强制）

正确性（D0×15）：pricing 字段名兼容现网 cost 键（真实 api.json 片段断言，禁自证 mock，P1 死路径终结）；status_messages 契约去自证（tuple(STATUS_MESSAGES) 改显式 18 键元组）；节流缓存不破坏预警去重（is_cached 分支不复位标志 + 托盘按数据更新）；go_quota in-flight 并发请求去重（模块级标志）；模板占位符校验补全（percent/value + pie/detail_line 两组并入）；usage_percent 双侧钳制（render clamp + overall 对称）；notify_title 入契约 + main.py 运行时防护双保险；凭据探测 TTL 缓存（防刷新重复全量探测）；解析空结果告警（结构变更不再静默，P1 潜伏放大器消除）；save_state 降级（磁盘满 warning 继续退出）；estimate LIMIT 防大库拖死；write_json mkstemp 移入 try（fd 泄漏边缘）；--version 提前于 PyQt import（CLI 不加载 GUI 依赖）；html_text 改名消模块遮蔽；hidden_columns 脏 id 过滤（保存点过滤非 COLUMN_IDS 的 id）。
清理（D3）：HTTP_TIMEOUT 死代码删除 + 说明区四级网络链路（http_get timeout 单一来源）；说明区缺失/重复修正 5 处。版本 ver 0.17。

---

## 第十一轮审计整改完成（E 系列，2026-08-13 审计，2026-08-13 已实施，版本 ver 0.18）

> 目标：15 条 P 级按四组整改；全量回归 43/43
> 依据：z.plan.md 附录 A011；结果：四组全部完成（探针 + 修复验收 26/26——防漏损三项强制自本轮落地）

正确性（E0）：C0.6 顺序契约补全（键序完全一致校验，真实改序 ui.json 导入抛错——上轮修复不完整收尾）；estimate ORDER BY created DESC（LIMIT 前排序，估算样本优先最新消息）；\_on_column_toggle save_config 加 try 降级（磁盘满槽函数不逃逸）；min_ts=0 天数归零告警（time.created=0 虚高 20676 天终结）。
配置化（E2）：in-flight 提示文案外置 ui.json（in_flight 键）；CREDS_CACHE_TTL 走 base.json credentials_ttl。
清理（E3）：in-flight 冗余节流查询删除（直返 \_fallback）；\_add_credential 闭包提为模块级函数；缺库分支写空缓存（TTL 全场景生效）；说明区同步 5 处 + \_add_credential 条目；palette 值类型 isinstance 校验。
防漏损三项强制首次落地：同根因调用点全扫（write_json/save_config 全点防护核实）、说明区一致性扫描补 4 处漂移、credentials_ttl 三处一致。

---

## 第十二轮审计整改完成（F 系列，2026-08-13 审计，2026-08-13 已实施，版本 ver 0.19）

> 目标：7 条 P 级按四组整改；全量回归 43/43
> 依据：z.plan.md 附录 A012；结果：四组全部完成（探针 5/5 + 修复验收 15/15）

正确性（F0）：go_quota_error_messages 契约组补齐（no_credentials/in_flight 删键导入期抛错）；refresh 连点 in-flight 去重 + pending 补发机制（在途不叠加任务，行为验证：在途不叠加/pending 复位）；TokenStats/UsageRow 显式字段键集契约（防字段改名 AttributeError 逃逸 Qt 槽）。
清理（F3）：未用 VERSION import 删除（4 测试资产同步改读 utils.logger 单点——main.VERSION 消费面确认仅测试资产）；说明区补列 3 处（fallback 键/pricing 两函数/themes 键序语义）。
防漏损扩展扫描：消费组×契约块交叉核对、说明区扫描覆盖 main.py/pricing/themes。

---

## 第十三轮审计整改完成（G 系列，2026-08-13 审计，2026-08-13 已实施，版本 ver 0.20）

> 目标：6 条 P 级按四组整改；全量回归 43/43
> 依据：z.plan.md 附录 A013；结果：四组全部完成（探针 3/3 行为验证 + 修复验收 15/15）

正确性（G0）：F0.2 pending 丢弃路径修复（\_consume_pending 公共方法——过期丢弃/渲染两路径共用，连点数据挂起终结，行为验证复现：过期路径 pending 清空 + 补发最新序号）；UsageSummary 10 字段契约（\_USAGE_SUMMARY_FIELDS 与 dataclass 比对，消费方属性全命中）。
清理（G3）：pricing 说明区语义修正（\_price_line 主语改 price 为 None 计 0/\_rate_from_raw cache 缺省 None 精确）、main.py VERSION 段改写为单点导出说明（同文件漏改第三次终结）、常量段补 \_SC/\_notified_danger、main_window refresh 行补 pending 描述 + 关联配置 VERSION 改 utils.logger。
防漏损升级：说明区无残留字样反向断言（漏改三次同根因终结）+ 语义准确性扫描 + 契约消费方交叉。

---

## 豁免清理批次完成（H 系列，2026-08-13 盘点立项，2026-08-13 已实施，版本 ver 0.201）

> 目标：56 条豁免定案盘点后 13 条低成本可修项中 8 条零风险项一次修完；全量回归 43/43
> 依据：2026-08-13 豁免盘点报告；结果：H0×8 + H3×3 全部完成（探针 10/10 + 修复验收 20/20），另 4 条验证项行为验证后 2 条并入（H0.6/H0.7）

正确性（H0×8）：refresh 上限区间钳制（base.json max_refresh_interval_ms=3600000，超大值回退默认）；配额解析层百分比钳制（max(0.0, min(100.0, ...))——三层幂等收敛首层）；fdopen 异常路径关 fd（理论泄漏终结）；数值键白名单类型契约（\_NUMERIC_BASE_KEYS 25 键，type() is int 排 bool，字符串键导入期抛契约错误）；CLI limit 钳制 [1,10000]；\_UsageTask 复位统一 finally（异常路径不再残留标志）；subprocess CREATE_NO_WINDOW 三处（getattr 跨平台兜底，无控制台环境不闪黑窗）；notify 两模板键入契约（删键导入期报错）。
清理（H3×3）：palettes 容器类型校验（裸 ValueError→契约 RuntimeError）；retry backoff 注释语义对齐（<1 递减退避也被归一 ≥1.0，以实现为准）；logger 注释措辞精确化。
关键发现：坏模板导入期被占位符校验拦截——三级兜底链运行时近乎不可达（P24 记录）。

---

## 第十四轮审计整改完成（I 系列，2026-08-13 审计，2026-08-13 已实施，版本 ver 0.202）

> 目标：5 条 P 级按三组整改；全量回归 43/43
> 依据：z.plan.md 附录 A014；结果：三组全部完成（探针 + 修复验收 11/11）

正确性（I0.1）：palettes 根容器类型前置校验（真实改根容器为 str 导入抛 RuntimeError——裸 AttributeError 终结，C0.6 .keys() 连带受益）。
清理（I3×5）：G0.1 注释措辞与 H0.6 finally 实现对齐（"复位由 finally 保证"）；补发任务 run 链路行为探针（H0.6 验证盲区闭合——真实启动补发任务断言无 pending 挂起）；file_utils 说明区补 fdopen close 语义；豁免清单 fdopen 移入已修复记账；契约块说明区补 notify 两模板键。
附带修复 verify_s6 历史欠账：D0.8 注入缺失的 \_reset_creds 定义（NameError）/缩进错误/4 处缓存串场。

---

## 第十五轮收尾审计整改完成（J 系列，2026-08-13 审计，2026-08-13 已实施，版本 ver 0.203）

> 目标：4 条 P 级按三组整改；全量回归 43/43
> 依据：z.plan.md 附录 A015；结果：三组全部完成（探针 3/3 含实测复现 + 修复验收 10/10）

正确性（J0×2）：parse_time_arg 相对时长上界钳制 min(amount, 100000) + except (ValueError, OverflowError) 双捕（999999999d 实测 OverflowError 逃逸终结——数值上界缺失家族第 3 例）；pricing 本地覆盖 key 归一（{k.lower(): v} 入口归一，canonical 小写索引一致——大小写写错覆盖静默失效终结，实测 FAIL→PASS）。
清理（J3×2）：main.py 说明区常量段补 QUOTA_DANGER_PERCENT（同文件漏改模式第三次终结）；file_utils 补 get_project_root 函数条目；QSystemTrayIcon 导入条目补列。
15 轮审计全部闭环。

## PL001 凭据指纹切换日志——多账户用量区分（依据 z.plan.md PL001 方案，2026-08-13 规划）

> 目标：账户切换自动记录时间点，启用后用量按账户时段切片统计；配额侧多凭据轮询看各账户余量
> 决策（用户已确认）：全量实施（一二三）；日志存独立 data/credentials/switch_log.json；多凭据需要（今后两三个账号同时用）
> 硬限制（文档明示）：启用前历史不可划分；程序未运行期间切换漏检（下次启动才检测）；新账户从首个检测点起算

### 统计侧核心——凭据指纹切换日志

- [x] PL001.1 指纹计算与 switch_log.json 读写（2026-08-22 完成：探针 16/16 PASS）
- [x] PL001.2 切换检测与去抖（2026-08-22 完成：A→B→A 两记录三区间断言 PASS）
- [x] PL001.3 检测钩子接入（2026-08-22 完成：fetch 成功处 + 启动时，探针 5/5 PASS）

### 统计切片（消费侧）

- [x] PL001.4 _time_clause 账户时段过滤（2026-08-22 完成：内存库边界探针 8/8 PASS + s10 回归）
- [x] PL001.5 GUI 账户时段选择器（2026-08-22 完成：offscreen 探针 15/15×2 零配置污染）
- [x] PL001.6 CLI --account 与导出标注（2026-08-22 完成：探针 7/7 PASS + _ExportTask 连带）

### 配额侧多凭据轮询

- [x] PL001.7 opencode-go.json 数组兼容（2026-08-22 完成：单对象/数组/追加不覆盖三断言 6/6 PASS）
- [x] PL001.8 fetch_go_quota 循环轮询（2026-08-22 完成：mock 一好一坏 6/6 PASS；破坏性变更连带 main_window/main/go_quota.main 适配，全量回归涟漪 26 个脚本清零）
- [x] PL001.9 GUI 配额区并列账户卡（2026-08-22 完成：offscreen 三账户探针 10/10 PASS；_set_status_style 孤儿删除）

### 验证收尾

- [x] PL001.10 verify_pl001_accept 反向断言（2026-08-22 完成：六项 11/11 PASS）+ README 同步 + 版本定案 **ver 0.213**

## PL002 模型数据页 + 官方动态页签（依据 z.plan.md PL002 方案，2026-08-13 规划）

> 目标：数据页六区块（热门模型时序/Token 成本/缓存比/会话成本/国家分布/GitHub Releases）以新页签展示；UI 与功能三层分离
> 架构：modules/opencode_data.py 零 Qt / ui/data_page.py 纯展示零解析 / main_window 装配最小侵入
> 关键预研结论：go_quota._capture_object_body 仅支持单层对象（[^{}]* 不容嵌套），$R 数组引用链须新写独立展开器；异步对齐 QRunnable+signal+seq 模式

### PL002.1 配置外置与模块骨架（z.plan.md PL002.1）

- [ ] PL002.1.a base.json 新增五键：data_url / gh_releases_api_url / gh_releases_rss_url / data_fetch_interval_sec(60) / data_cache_ttl_sec(300)
- [ ] PL002.1.b modules/opencode_data.py 骨架：_SC 一次性解包 + DataPageError(category, message) 异常分类（network/decoding，对齐 GoQuotaError 模式）+ 文件尾 # ===== 说明区框架
- [ ] PL002.1.c 验证：import modules.opencode_data 冒烟 + 常量断言（URL/间隔与 base.json 一致）

### PL002.2 节流缓存基础设施

- [ ] PL002.2.a _last_snapshot/_last_success_at 模块态 + _throttled_snapshot(force) 对齐 go_quota._throttled_cache:326 同式（窗口内返回标注缓存 is_cached）
- [ ] PL002.2.b probe：注入时间断言窗口内返缓存/窗外重拉取（行为 mock 合规）

### PL002.3 $R 引用展开器（z.plan.md PL002.2 前半）

- [ ] PL002.3.a _extract_r_objects(body) -> dict[int, str]：正则提取全部 `$R[N]={...}` 单对象（实测 2135 个规模，嵌套大括号防御跳过畸形块）
- [ ] PL002.3.b _parse_loose_object(text) -> dict：JS 对象字面量宽容解析（键无引号 model:"x"/数值/字符串/null）——轻量手写分词（顶层逗号拆分 + 首个冒号切键值 + 类型推断），禁 eval
- [ ] PL002.3.c probe 结构样例独立性：真实页面片段快照断言解析字段齐全（禁止手写与实现同源 mock 自证）

### PL002.4 四数据块锚点提取（z.plan.md PL002.2 后半）

- [ ] PL002.4.a fetch_model_data()：`tokenCost:$R[N]=` 等四锚点正则定位根 ID → 数组引用链展开
- [ ] PL002.4.b _expand_array_ref(array_text) -> list[dict]：`[$R[1868]={...},$R[1869]={...}]` 拆元素查表拼装
- [ ] PL002.4.c 缺块容忍：锚点缺失返回部分结果 + errors 追加 decoding 警告，不抛异常中断
- [ ] PL002.4.d probe：真实页面断言四块非空 + 字段齐全（model/total/input/output/cached/ratio/country/share 等）+ 行数量级合理

### PL002.5 热门模型时序解析（z.plan.md PL002.3）

- [ ] PL002.5.a parse_daily_usage(body)：top-models-bar 的 aria-label 提取（`JUN 29 3.2T 总计` → 日期+总量 T 浮点）
- [ ] PL002.5.b stack 分段配对：grid-template-rows 百分比序列 × data-model 名单按序 zip → models dict
- [ ] PL002.5.c 月份缩写映射排序（JAN=1…DEC=12）保证时序升序
- [ ] PL002.5.d probe：真实页面断言条数 ≥7 + 日期升序 + 各 bar 百分比和≈100%（容差 1%）

### PL002.6 GitHub Releases 拉取（z.plan.md PL002.4）

- [ ] PL002.6.a _fetch_releases_json()：api.github.com releases?per_page=5（User-Agent 头必须）→ 最新 3 条 {tag_name, published_at, body}
- [ ] PL002.6.b _fetch_releases_rss() 回退：releases.atom entry 解析 title/updated/content（xml.etree 命名空间）
- [ ] PL002.6.c fetch_github_releases(force)：JSON 优先异常回退 RSS；接入 _throttled_snapshot 节流
- [ ] PL002.6.d probe：mock http_get 抛错断言 RSS 回退（行为 mock）+ 真实拉取断言 tag_name 匹配 v\d+ 格式

### PL002.7 快照聚合入口（数据层收口）

- [ ] PL002.7.a ModelDataSnapshot dataclass：model_blocks/daily_usage/releases/is_cached/fetched_at/errors
- [ ] PL002.7.b refresh_data_page(force)：三源独立 try 互不拖垮；整体失败保留上次快照标 is_cached（缓存兜底策略）
- [ ] PL002.7.c probe：mock 两源失败一源成功断言部分快照可用

### PL002.8 DataPage widget 骨架（z.plan.md PL002.5 前半）

- [ ] PL002.8.a ui/data_page.py：QWidget + QVBoxLayout + QScrollArea；objectName="dataPage" 系列命名供 QSS（P25 拟物化取舍点集中此处）
- [ ] PL002.8.b Releases 卡片区：版本号粗体 + 发布日期 + 正文只读展示
- [ ] PL002.8.c 五表格区：时序表（日期/总 tokens(T)/Top 模型占比）+ 四数据表（列头常量显式声明 + 导入期校验，对齐 P23 契约层惯例）

### PL002.9 渲染入口与占位（z.plan.md PL002.5 后半）

- [ ] PL002.9.a set_releases/set_daily_usage/set_model_data 三纯渲染方法（快照结构直接灌入零解析）
- [ ] PL002.9.b 空数据占位文案（"尚未获取/暂无数据"）
- [ ] PL002.9.c probe：offscreen 构造断言零网络调用 + mock 快照灌入行列数正确

### PL002.10 懒加载后台任务（z.plan.md PL002.5 尾）

- [ ] PL002.10.a needs_load 标志：首次 showEvent 置位触发
- [ ] PL002.10.b _DataPageTask(QRunnable) + _DataSignals(data_ready/error) 对齐 main_window 异步模式（seq 防竞态）
- [ ] PL002.10.c probe：offscreen show 多次断言仅首次拉取（幂等）

### PL002.11 QTabWidget 改造（z.plan.md PL002.6）

- [ ] PL002.11.a _build_ui：central 改 QTabWidget，「用量监控」页容器承载现有卡片区/配额区/明细区（只换父容器逻辑不动）
- [ ] PL002.11.b 「数据与动态」挂 DataPage；currentChanged 首次切换触发拉取
- [ ] PL002.11.c 主刷新定时器隔离：_refresh_timer 仅驱动原 refresh()，不触达 DataPage
- [ ] PL002.11.d probe：offscreen 双页切换断言 + DataPage 拉取计数 == 1

### PL002.12 验证收尾（z.plan.md PL002.7）

- [ ] PL002.12.a verify_pl002_accept 反向断言：$R 坏 JSON 容忍（截断 body 不崩）/缺块部分返回/懒加载幂等/RSS 回退生效/节流窗口命中
- [ ] PL002.12.b 全量回归 43 脚本 + GUI offscreen 双页冒烟
- [ ] PL002.12.c README 功能段同步 + y.problem P20 标注已实施 + z.plan PL002 状态更新
- [ ] PL002.12.d 版本推进决策（待用户确认 ver 0.204）

## PL003 UI 整体重构：四主题注册制 + 拟物化扩展（依据 z.plan.md PL003 方案，2026-08-22 规划）

> 目标：主题注册制泛化（light/dark 保留 + console 终端控制台/panel 工业面板新增）+ 下拉切换即持久化 + 列元数据外置（P23 收尾）
> 已拍板（2026-08-22）：四主题皆做/命名 console·panel/下拉切换切完即存/配额阈值行为不变仅颜色随主题
> 硬限制：QSS 无 box-shadow 用双描边模拟立体；配色神似不逐像素；QProgressBar::chunk 无法分段（首版退化普通圆角条，M3b 自绘可选追加不阻塞）

### PL003.1 主题注册制泛化（先行，视觉零变化）

- [ ] PL003.1.a themes.py 删硬编码双主题段（_LIGHT/_DARK_PALETTE:94-95、LIGHT/DARK_THEME:124-125、LIGHT/DARK_THEME_NAME:148-149 四常量）→ 泛化遍历 palettes 全键导入期构建 `_THEME_QSS: dict[str, str]` + `DEFAULT_THEME_NAME = THEME_NAMES[0]`
- [ ] PL003.1.b A3.5/C0.6 校验泛化保留：逐主题占位符残留检测 + palettes 键集==THEME_NAMES 严格相等（天然兼容 N 键）
- [ ] PL003.1.c get_theme(name) 改字典查找 + 未知名回退 DEFAULT_THEME_NAME（消除"第三主题静默错位"豁免项）
- [ ] PL003.1.d 配额窗口内动态色迁 palette：quota_chunk 三档/quota_gray/pie_bg/pie_text 进各 palette 节 + 导入期必含显式契约校验（不走 QSS 占位符，残留检测兜不住）；quota_chunk_color(percent) → (percent, theme_name)，连带 main_window:441/1006 两调用点
- [ ] PL003.1.e ui.json 顶层 colors 节瘦身为纯托盘色节（QUOTA_OK/GRAY/pie_dot 与窗口主题无关）——system_tray:15-16 消费方式基本不动
- [ ] PL003.1.f main_window._is_dark 布尔 → _theme_name 字符串（:625/:810/:818 三处 + :63 import 连带）；_apply_theme/save_state 同步改造；settings.py 零改动（白名单+回退已支持 N 主题，外置红利兑现）
- [ ] PL003.1.g 验证：offscreen init 视觉零变化（light/dark 渲染不变）+ 全量回归 43 脚本

### PL003.2 切换交互：按钮改下拉

- [ ] PL003.2.a 删 _theme_button/toggle_theme（:749-750/:768/:808）；明细区新增主题 QComboBox（维度下拉 combo_* 样式复用）
- [ ] PL003.2.b ui.json 新增 theme_labels 显示名映射（浅色/深色/终端/面板）+ 导入期键集与 themes 数组一致校验（C0.6 同机制防错位）
- [ ] PL003.2.c currentTextChanged → 应用 → 立即 save_config（常驻托盘长期不关，切完即存防丢）；启动恢复 blockSignals 防回环
- [ ] PL003.2.d 连带修复：进度条 chunk 动态色切主题后统一重着色（现状 toggle 即有残留旧主题色问题）
- [ ] PL003.2.e 验证：offscreen 切换断言 QSS 变化 + 持久化落盘 + 回归

### PL003.3 双新主题包数据落地（console + panel）

- [ ] PL003.3.a _QSS_TEMPLATE 新增 {font_family} 占位符；light/dark 补 Segoe UI、console/panel 补 Consolas 族（占位符残留检测自动强制旧 palette 补齐，机制兜底）
- [ ] PL003.3.b console palette：近黑底 #0a0e14 族 / 卡片深底 + 强调色描边 / 绿磷光文字 / 等宽字体；qlineargradient 表达式直接作 palette 值（无需模板变体）
- [ ] PL003.3.c panel palette：米灰绿底 / 近黑文字细线描边 / 胶囊大圆角极简线框
- [ ] PL003.3.d 能力边界落地：分段进度条首版退化普通圆角条（M3b 自绘可选追加单独评估不阻塞）；panel 圆形进度环复用 QPainter 饼图换色对齐
- [ ] PL003.3.e 截图对照参考图目检（标准：风格气质到位非逐像素复刻；读图核对需切换多模态模型）

### PL003.4 列元数据外置（P23 关联收尾）

- [ ] PL003.4.a ui.json table_headers 升级 `"table_columns": [{id, title, width?, visible?}]`，数组顺序即展示顺序
- [ ] PL003.4.b TABLE_HEADERS 从 title 派生单源化（删除平行数组防错位）；COLUMN_IDS 保持代码内显式声明（P23 契约定案不推翻——键名仍在代码）
- [ ] PL003.4.c 导入期校验 columns id 集合与 COLUMN_IDS 严格相等；hidden_columns 用户持久化语义不变（运行时覆盖默认 visible）；width 缺省走 Qt 默认
- [ ] PL003.4.d 验证：全量回归

### PL003.5 收尾

- [ ] PL003.5.a .temp/verify_pl003_theme.py 反向断言：_THEME_QSS 键集==THEME_NAMES / get_theme 未知名回退默认 / quota 三档随主题取色 / theme_labels 与 table_columns 契约校验可触发
- [ ] PL003.5.b README 主题章节 / ui.json 参数表 / z.plan P25 状态 / y.problem P25 状态同步
- [ ] PL003.5.c 版本推进决策
