# 开发进度追踪（x.progress.md）

> 依据：`z.plan.md`（myboard 方案报告）
> 当前版本：V0.2.6.2（VERSION 单一来源在 config/static/base.json 的 version 字段；**2026-08-24 起启用四段式版本号规则 V0.2.4.3 形式**，此前为 ver 0.NNN 两段式）
> 记录格式：状态 [⏳ 待开发, ✅ 已完成] / 优先级 [高, 中, 低]
> 执行原则：每阶段完成后运行验证命令确认无回归，再进入下一阶段
> 错误策略：各模块开发时落实 z.plan.md 第四章约定（统一错误类型/降级不中断/缓存兜底/宽容解析/节流去重/保留旧数据/只读防误写）

---

## 阶段验证命令速查（AGENTS.md 运行与验证）

```powershell
# 导入验证（全量 19 个模块）
.\.venv\Scripts\python.exe -c "import main, modules.opencode_usage, modules.go_quota, modules.pricing, modules.exporter, modules.browser_creds, modules.credential_store, config.settings, config.static.static_config, ui.qt6.main_window, ui.qt6.system_tray, ui.qt6.theme_loader, services.service, ui.qt6.task_runner, utils.logger, utils.file_utils, utils.retry, utils.convert, utils.network, utils.windows, utils.sqlite_utils"

# GUI 无头初始化验证（不弹窗）
$env:QT_QPA_PLATFORM="offscreen"; .\.venv\Scripts\python.exe -c "from PyQt6.QtWidgets import QApplication; from ui.qt6.main_window import MainWindow; app = QApplication([]); w = MainWindow(); print('GUI init OK')"

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

第一批正确性（B0）：Edge v20 判定下沉 browser_creds（has_v20_cookies 遍历双浏览器任一命中）；to_float/to_optional_float 补 OverflowError（10\*\*400 实测逃逸封堵）；pricing currency/source null 兜底（防 "None" 字符串错值）；launch Popen OSError 分支清理临时目录；刷新序号 in-flight 去重（递增 seq，乱序完成丢弃过期结果）；ui.json 结构性键契约校验首建（删键导入期抛错）；notify 模板 .format 防护（未知占位符 KeyError 回退固定文案）；引导期暂停定时刷新（stop/start 配对恢复）；托盘不可用检查（isSystemTrayAvailable，closeEvent 不 hide）；CLI --limit 下界 max(1, ...)。
第二批去重（B1）：settings \_themes 复用（THEMES = \_themes）；hidden_columns 排序抽 \_sorted_hidden_columns 单点。
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

## PL001 凭据指纹切换日志——多账户用量区分（依据 z.plan.md PL001 方案，2026-08-22 已实施，版本 ver 0.213）

> 目标：账户切换自动记录时间点，启用后用量按账户时段切片统计；配额侧多凭据轮询看各账户余量
> 决策：全量实施（一二三）；日志存独立 data/credentials/switch_log.json；多凭据需要
> 依据：z.plan.md PL001 方案；结果：三部分全部完成（各子项探针全 PASS + verify_pl001_accept 六项 11/11 + 全量回归清零）；⚠ 统计侧与切换日志已随 PL004 退役（ver 0.240），配额侧保留并演进为单卡选择器

统计侧核心（PL001.1-3）：指纹计算与 switch_log.json 读写（探针 16/16）+ 切换检测去抖（A→B→A 两记录三区间断言）+ 双时机钩子接入（fetch 成功处+启动时，5/5）——**已随 PL004 整体退役删除**。
统计切片（PL001.4-6）：_time_clause 时段过滤（内存库边界 8/8）+ GUI 账户下拉（offscreen 15/15×2 零配置污染）+ CLI --account 与导出标注列（7/7 + _ExportTask 连带）——**已随 PL004 整体退役删除**。
配额侧多凭据轮询（PL001.7-9）：opencode-go.json 数组兼容（单对象/数组/追加不覆盖 6/6）+ fetch_go_quota 循环轮询（mock 一好一坏 6/6；破坏性变更涟漪 26 个脚本清零）+ 并列账户卡（三账户探针 10/10）——**保留**，UI 演进为单卡选择器+quota_account 记忆（PL004/PL005）。
验证收尾（PL001.10）：verify_pl001_accept 六项 11/11 + README 同步 + 版本定案 ver 0.213（该验收脚本随退役一并清理）。

## PL002 模型数据页 + 官方动态页签（依据 z.plan.md PL002 方案，2026-08-22 已实施，版本 ver 0.220）

> 目标：数据页六区块（热门模型时序/Token 成本/缓存比/会话成本/国家分布/GitHub Releases）以新页签展示；UI 与功能三层分离
> 架构：modules/opencode_data.py 零 Qt 纯数据层 / ui/data_page.py 纯展示零解析 / main_window 装配最小侵入
> 关键预研结论：go_quota._capture_object_body 仅支持单层对象不容嵌套，$R 数组引用链须新写独立展开器

数据层解析链（PL002.1-7）：base.json 五键外置与模块骨架（探针 16/16）+ 节流缓存对齐 go_quota 同式 + $R 引用展开器（_extract_r_objects 实测 1783 对象块/176 数组块 + _parse_loose_object 手写分词禁 eval）+ 四数据块锚点配平捕获（14/14）+ 时序正则 aria-label/stack/data-model（6/6）+ Releases JSON→RSS 双路径回退（8/8）+ refresh_data_page 三源独立聚合缺块容忍（6/6）——**保留**。
UI 与装配（PL002.8-11）：DataPage widget 骨架（objectName 系列 P25 取舍点 + Releases 卡片 + 五表格列头契约）+ set_* 三纯渲染入口空态占位（14/14）+ has_loaded 懒加载幂等 + QTabWidget 两页装配主定时器隔离（拉取计数==1 断言 14/14）——**保留**。
验证收尾（PL002.12）：verify_pl002_accept 反向五项 7/7 + 全量回归 0 异常 + README 同步 + 版本定案 ver 0.220。
A0.16 整改索引：K1.1 失败保缓存 / K2.2 timeout 走配置回退 / K2.3 死键删除 / K3.2-K3.5 清理与说明区同步。

## PL003 UI 整体重构：四主题注册制 + 拟物化扩展（依据 z.plan.md PL003 方案，2026-08-22 已实施，版本 ver 0.230）

> 目标：主题注册制泛化（light/dark 保留 + console 终端控制台/panel 工业面板新增）+ 下拉切换即持久化 + 列元数据外置（P23 收尾）
> 已拍板：四主题皆做/命名 console·panel/下拉切换切完即存/配额阈值行为不变仅颜色随主题
> 硬限制：QSS 无 box-shadow 用双描边模拟立体；配色神似不逐像素；chunk 无法分段首版退化普通圆角条（M3b 自绘可选追加不阻塞）

主题注册制泛化（PL003.1）：themes.py 删硬编码双主题 → `_THEME_QSS` 注册制构建 + DEFAULT_THEME_NAME/get_theme 未知名回退 + 动态色键迁 palette 必含契约校验（chunk 三档/quota_gray/pie_bg/pie_text）+ quota_chunk_color 加 theme_name 参 + colors 节瘦身为纯托盘色节 + _is_dark→_theme_name——视觉零变化回归清零。
切换交互（PL003.2）：按钮改下拉 + theme_labels 显示名外置键集校验 + 切换即存 blockSignals 防回环 + chunk 动态色重着色连带修复（探针 14/14）。
双新主题包（PL003.3）：{font_family} 占位符 + console 近黑磷光/panel 米灰线框两套 palette 落地；**遗留 PL003.3.e 截图对照参考图目检（需多模态模型）**。
列元数据外置（PL003.4）：table_columns [{id,title}] + TABLE_HEADERS 从 title 派生单源化 + 与 COLUMN_IDS 导入期严格相等校验（实测拦截 cache 列 id 写错）。
验证收尾（PL003.5）：verify_pl003_accept 反向断言 5/5 + 文档四处同步 + 版本定案 ver 0.230。A0.16/K0.1 连带修复渲染路径 quota_chunk_color 未传 theme_name 缺陷（PL003 改造遗漏）。

## PL004 用量纯净视图回归：切换日志移除 + 配额单卡选择器（依据 z.plan.md PL004 方案，2026-08-23 已实施，版本 ver 0.240）

> 目标：用量统计删除账户概念回归纯净单视图；Go 配额改"单卡 + 账号选择器 + 选择记忆"；凭据管理入口与托盘预警原样保留
> 根因：opencode.db 消息 JSON 无账号维度字段且多账号混写同库——时间窗近似对并行使用物理不可分、对串行切换有采样漏检，实用价值有限
> 已拍板（2026-08-23）：删 A+B 全量/配额单卡选择器选谁显示谁/凭据数组格式与追加式保存保留/残留物物理删除/托盘零改动/版本 ver 0.240
> 硬限制：since/until 形参是 --since 时间过滤与账户无关严禁误删；时间窗近似方案退役后不再以任何形式重新引入

删 A 切换日志体系（PL004.1）：credential_store 删 SWITCH_LOG 常量与 load/save/detect 三函数及说明区条目 + 连带删指纹链（credential_fingerprint/GoQuotaInfo.fingerprint 无 UI 消费者，账户标识统一 workspace_id）+ go_quota 钩子与调用点 + main/main_window import 与启动调用；定向探针访问被删符号 AttributeError 即 PASS。

删 B 时段截取链（PL004.2）：opencode_usage 删 intervals 形参全链（totals/by_* 八处签名透传/_time_clause 区间分支/CLI --account 参数与切换日志解析块；since/until 时间过滤原样保留）/ exporter 删 account_intervals/account_label 形参与 CSV account 标注列 / main_window 删账户下拉常量+三方法+_UsageTask/_ExportTask 相关字段 / settings 删 account_filter 字段三件套 / ui.json 删三键。

配额区改造（PL004.3）：_build_quota_section 回归单卡 + _render_quota 按选中 workspace_id 渲染（失配回落首个有效项，全无效渲染错误态）+ 顶部新增账号选择器行（QComboBox userData=workspace_id，标签外置 quota_account_label）+ 选项按刷新 infos 重建（blockSignals 防回环，错误占位项照常入列）+ settings 新增 quota_account 字段三件套切换即存（失败 warning 降级同 E0.3 式）+ 托盘/数据层零改动确认（fetch_go_quota 全量轮询是切换零延迟的数据基础）；行为探针覆盖切换渲染/落盘/重启恢复/失配回落。

清理与兼容（PL004.4）：user_config 物理删除 account_filter 死键 + switch_log.json 文件直接删除 + 凭据数组追加式保存确认保留（选择器数据基础）+ 兼容实证：带旧残留键的临时 user_config offscreen 启动无错。

回归脚本清理与新验收（PL004.5）：删 verify_pl001_accept 与 probe_pl001 系列 + 排查清理 intervals/account_filter/switch_log 引用脚本 + verify_5a3/run_all_verify 白名单同步移除失效条目 + 新建 verify_pl004_accept 反向断言（无 switch_log 四函数/无 intervals 参数/无 account 标注/无 _account_combo/quota_account 持久化回环/单卡按选中渲染/残留键已清除）。

文档同步与版本推进（PL004.6）：README 改写"配额账户切换"说明 + z.plan/y.problem 状态同步 + 版本 ver 0.240 三处一致 + commit 草稿给出。收尾验证：removal 探针 26→0 失败、quota 行为探针 5/5、legacy 兼容实证 6/6、verify_pl004_accept 18/18、全量回归 0 异常（2026-08-23 完成）。

## PL005 配额区"添加账户"常驻入口（依据 z.plan.md PL005 方案，2026-08-23 已实施，版本 ver 0.241）

> 目标：已有有效凭据时提供随时可点的"添加账户"入口（现状引导卡仅在凭据全失效时显示，引入新账户无 UI 途径）
> 已拍板：入口放配额区选择器旁常驻按钮 + QMenu 两路径复用既有引导流程；托盘零改动；添加后自动选中新账户
> 硬限制：引导流程三件套（CDP 任务/手动对话框/并发防护）全部复用不建平行流程；\_on_guide_failed 显示条件修正必须与 show_guide 同源逻辑防双路径漂移

入口按钮与菜单（PL005.1）：ui.json 新键 quota_add_account_button + 选择器行尾 QPushButton 弹 QMenu 两项（文案复用 GUIDE_AUTO/MANUAL_BUTTON 不新增重复键）路由 _start_cdp_guide/_manual_guide；A0.6/A0.7 并发防护与按钮禁用对配额区入口同样生效（同一 _guide_active 状态）。

复用适配与闭环（PL005.2）：**关键修复**——_on_guide_failed 原无条件 show 引导卡（已有凭据时从配额区触发失败语义混乱），提取 _should_show_guide() 同源单点维护 failed 回调改按条件显示 / 添加后自动选中：一次性 pending 标志 _pending_quota_account，CDP 路径 _CdpGuideSignals.success 签名携带 workspace_id（带默认值向后兼容），_render_quota 重建选项后优先匹配 pending 选中并清除。

验证与收尾（PL005.3）：probe_pl005_entry 10/10 PASS（幂等自清理+测后还原凭据文件）+ 全量回归 0 异常 + README 补"添加账户入口"说明 + 版本 ver 0.241 三处同步 + commit 草稿给出（2026-08-23 完成）。

## K. 第16轮审计修复任务清单（依据 z.plan.md 附录 A016，2026-08-23 已实施，版本 ver 0.242）

> 范围：P 级 19 条（高 3/中 8/低 8）；观察项 26 条经用户复核全部维持豁免
> 硬限制：只修 A016 清单条目；高严重度三条先行；每批完成后跑反向验收再全量回归

P0 正确性高严重度（K0）：_render_quota_card 的 quota_chunk_color 补 theme_name 参（console 主题样式随主题）/ 添加账户菜单双入口 _guide_active 早退防重入（假池断言零任务提交+定时器不停）/ _rebuild_quota_account_combo 改"当前选中在 infos 则保持不动失配才回落"并修正 clear 前读 currentData 顺序。

P1 数据与防御一致性（K1）：opencode_data 失败快照不覆盖成功缓存（has_data 实质数据守卫+_mark_cached 标注副本）/ go_quota in-flight 分支返回全集逐条标注副本与节流分支对齐 / browser_creds CDP 响应 isinstance 校验先于 .get() 消费 / RSS published_at 补 or "" 兜底 / 选择器 userData 错位修复——渲染目标改按 combo 当前索引取，同 workspace 双 cookie 按索引区分不再恒匹配首项。

P2 配置化（K2）：_NUMERIC_BASE_KEYS 补 data_fetch_interval_sec（25→26 键，反向断言差集为空+bool 伪装导入抛错）/ opencode_data 三处删 timeout=15 实参走 network 层 http_timeout 回退 / CACHE_TTL 死键采纳删除路线（常量+base.json 键+说明区一并删）。

P3 清理与文档（K3）：main_window 删三孤儿属性+注释如实化 / 删 DataPageError 死类 / 两处函数内 import 提模块顶部 / PL004 死注释清理 / 说明区五处同步（opencode_data 重写九缺列补齐/main_window 重写补 13 缺失函数条目等）/ 版本行 ver 0.240→0.241 / MW-6 键集契约机械比对确认。

验证与收尾（K4）：新建 verify_k_accept 汇总反向验收串联 K0-K3 七个子脚本统一出口 7/7 PASS + 全量回归 0 异常 + 版本推进 ver 0.242 三处同步（审计修复第三位数字惯例）+ commit 草稿给出。

## L. 第17轮审计修复任务清单（依据 z.plan.md 附录 A017，2026-08-23 已实施，版本 V0.2.4.3）

> 范围：P 级 16 条（中 1 / 低 15，无高）；观察项 18 条经用户复核全部维持豁免
> 重点：中级别饼图弧色需用户先裁定意图方向；多条为 A016/K 系列修复的边界补全
> 硬限制：只修 A017 清单条目；每批完成后跑反向验收再全量回归

展示语义裁定与修复（L0）：饼图弧色分级色改造——**已裁定方案 A（2026-08-23 用户确认）**，_RemainingPieChart 持有 theme 名 + set_used_percent 按 quota_chunk_color(percent, theme) 联动重算三档弧色与进度条一致，两处矛盾注释统一为"分级色圆弧"；探针断言 panel 主题 usage=90 弧色==quota_chunk_color(90,"panel")。

数据与交互一致性（L1）：K0.2 补全——_start_cdp_guide 早退分支补状态栏提示 + 新增 _set_guide_actions_enabled 随引导态启停菜单动作 / K0.3 回落换源 load_config() 同源 / G1 失败占位项同步 append 进 _last_quotas 全集不再丢失败项 / K1.1 粒度声明补注释（per-source 待评估）/ B1 深度校验 (resp.get("result") or {}) 式+cookie isinstance 过滤 / O2 JSON null 兜底 (x or "") 对齐 RSS 口径 / G2 新增 _FETCH_STATE_LOCK 护 in-flight check-set 与复位路径（网络 IO 不持锁）/ error_stage 对齐——in-flight 全集副本删赋值行。

配置卫生（L2）：theme 死键双侧删除（ui.json button_labels 行 + _UI_STRUCT_KEYS 元组同步）。

清理与文档（L3）：注释失实修正 / 说明区补类型两行与常量六键 / pending 冗余补发——_on_load_error seq 匹配分支追加 _consume_pending / README 配置表同步（ver 快照删除/四主题描述/base.json 表补四键）/ 符号名修正 _R_OBJECT_PATTERN / opencode_usage 关联配置补列。

验证与收尾（L4）：新建 verify_l_accept 反向验收 20 断言全 PASS + 全量回归 0 异常（连带适配 verify_k0_accept/k1_accept/5a3 三处过时断言）+ 版本推进三处同步并**启用四段式版本号规则 V0.2.4.3 形式（2026-08-24 用户指定）** + commit 草稿给出。

## PL006 前后端接口层：AppService 门面 + 统一任务运行器（依据 z.plan.md PL006 方案，2026-08-24 已实施，版本 V0.2.5.1）

> 目标：建立 services/service.py 门面与 ui/task_runner.py 异步设施，main_window 与 modules 解耦——UI 只 import services 不再直接触碰任何 modules 符号；前端可整体替换而后端不动
> 现状诊断：点对点直连——直接 import 五个 modules 的 8 类符号 + 自建 5 个 QRunnable 任务类 + 4 组 Signals 承载编排
> 三条纪律：Service 纯 Python 零 Qt / DTO 第一版直接透传 modules dataclass（独立 DTO 留待 QML 迁移）/ UI 只 import services
> 归属判定规则：替换前端时必然重写 = 归 ui/（TaskRunner）；可原样带走 = 归 services/（AppService）。多前端并存（ui/qt6 与 ui/qml 并列+main.py --frontend 分发）为远期形态，启用第二前端那天才搬迁
> 版本归属：**V0.2.5.1**（2026-08-24 用户定版；四段式第三位=功能批次、第四位=批次内序号）

services 门面（PL006.1）：新建 services/service.py——ServiceError 中文业务错误基类 + AppService（resolve_db_path/get_usage 内聚 OpenCodeDB 全套原 _UsageTask.run 主体/get_quotas/get_data_page 直通/export_data 原 _ExportTask 主体/save_account/add_account_via_cdp CDP 五步编排与 _wait_for_login_cookie 整体迁入，失败抛中文 ServiceError）；UsageData dataclass 随迁；全程零 PyQt6 import AST 断言通过。

Qt 异步设施（PL006.2）：ui/task_runner.py——TaskRunner(QObject) finished/failed 双信号构造注入 QThreadPool，run(fn, seq) 提交线程池异常转 failed(seq, str(exc))；**实测教训落地**：QRunnable wrapper worker 运行期被 GC 触发 0xC0000409 崩溃——_live_tasks 持执行引用 + _done_tasks deque(maxlen=16) 保完成引用 + setAutoDelete(False)，s4/s7/s9 全链路零崩溃。

main_window 切换调用（PL006.3）：删四个数据任务类与对应 Signals 改 TaskRunner.run(service...) finished 载荷区分 / _CdpGuideTask 删除改 lambda 调 service.add_account_via_cdp 双语义回调承载 / import 区收敛删全部 from modules 编排行仅留 DTO 类型注解用途 / L3.3 pending 消费语义新信号体系下保持核对；offscreen 冒烟 + 历史脚本全部适配。

验证与收尾（PL006.4）：verify_pl006_accept 反向验收（services 零 Qt AST 断言/行为等价/runner 双路径/modules import 白名单口径）+ 全量回归 0 异常 + run_all_verify 超时放宽 120→300 秒（CDP mock 场景偶超）+ README 结构段补 services/task_runner 说明 + commit 草稿 V0.2.5.1 已给出。

## PL007 主题资源文件夹化：theme 与代码彻底解耦（依据 z.plan.md PL007 方案，2026-08-24 规划）

> 目标：主题作为纯声明式资源管理于 ui/themes/ 文件夹（theme.json 纯数据 + base.qss 共享模板），不含任何 Python；新增主题 = 新建文件夹不改任何 .py
> 现状诊断：颜色已外置 ui.json palettes 但两处耦合残留——QSS 模板是 themes.py 的 Python 字符串常量；主题资产分散三处（themes.py 模板/ui.json palettes/ui.json theme_labels）
> 硬限制：themes.py 与 themes/ 不能同名共存（Python 硬约束）→ 加载器改 theme_loader.py + themes/ 纯资源文件夹（零 .py）；消费方 import 一次性替换 from ui.theme_loader
> 版本归属：**V0.2.5.3**（PL007 原 2026-08-24 用户定版 V0.2.5.2；M 批次审计整改后推进至 V0.2.5.3）

### PL007.1 资源文件落地

- [x] PL007.1.a 新建 ui/theme_loader.py（加载器，替代旧 ui/themes.py）；_QSS_TEMPLATE 内容平移至 ui/themes/_templates/base.qss（{var} 变量语法不变）——**2026-08-25** base.qss 含前导换行与旧模板逐字节一致
- [x] PL007.1.b 四主题资源文件：ui/themes/{light,dark,console,panel}/theme.json——schema {display_name, font_family, palette:{全部色键含动态色六键}}；ui.json palettes 数据拆分迁入（display_name 承接 theme_labels、font_family 并入 palette）——**2026-08-25** 每主题 29 键（font_family 并入 palette 后 schema 实为 display_name+palette 两顶层键）
- [x] PL007.1.c 删旧 ui/themes.py；ui.json 清理：palettes/theme_labels 键移除；保留 "themes": [...] 数组作为注册顺序权威（settings.THEMES/base.json default_theme 校验链零改动）——**2026-08-25**

### PL007.2 加载器改造

- [x] PL007.2.a theme_loader.py 加载流程：读注册表 → 逐主题加载 theme.json（json 解析错误/缺文件 RuntimeError 中文提示）→ 构建 _THEME_QSS——**2026-08-25**
- [x] PL007.2.b 契约校验链文件源适配并全套保留：theme.json 结构校验；值类型 E3.9；占位符残留 A3.5（对 base.qss）；注册表↔加载主题键序一致 C0.6；长度下限 A3.5；动态色六键必含 PL003.1.d——**2026-08-25**
- [x] PL007.2.c 导出 API 同名同签名：get_theme/quota_chunk_color/THEME_NAMES/DEFAULT_THEME_NAME/QUOTA_WARN_PERCENT/QUOTA_DANGER_PERCENT/QUOTA_COLOR_OK——**2026-08-25** 新增 get_palette(name)（承接 main_window._DEFAULT_PALETTE/_theme_palette）+ THEME_DISPLAY_NAMES（承接 THEME_LABELS）
- [x] PL007.2.d 消费方 import 行替换：from ui.themes → from ui.theme_loader（main_window/system_tray/settings）；未注册主题目录不加载 + logger.warning——**2026-08-25** 另含 main.py QUOTA_DANGER_PERCENT 一处

### PL007.3 验证与收尾

- [x] PL007.3.a 探针：四主题 QSS 逐字节等价断言（对照迁移前黄金基线）；契约触发断言（删动态色键/改坏占位符各抛 RuntimeError）——**2026-08-25** probe_pl007 22/22 PASS + verify_pl007_accept 反向验收 R1-R4 共 13/13 PASS
- [x] PL007.3.b 全量回归 0 异常 + offscreen 冒烟四主题切换 + IMPORT OK——**2026-08-25** run_all_verify 43 脚本 0 异常（18 个历史脚本已适配 theme_loader/theme.json 新源）；offscreen 四主题 app 级 QSS 各 1653 字符与黄金基线一致
- [x] PL007.3.c README 补自定义主题指引 + x.progress 勾选 + commit 草稿——**2026-08-25** README 结构树/配置参数表/自定义主题指引三处同步；版本推进 V0.2.5.2 三处一致

## M. 第18轮审计修复任务清单（依据 z.plan.md 附录 A018，2026-08-25 已实施，版本 V0.2.5.3）

> 来源：第 18 轮全量审计（PL006 接口层重构 + PL007 主题文件夹化两批新代码连带）；P 级 21 条（中 3 / 低 18，无高），观察项 23 条全部维持豁免
> 主线：中项三条 = 节流绕过挡板（A017 覆盖不全）/ domain null TypeError（A017 漏网）/ 引导失败签名失配（PL006 漏网）

正确性与防御（M0）：go_quota 节流绕过 in-flight 挡板——整轮完成后一次性原子发布快照消除渐进写 / browser_creds domain null 改 (cookie.get("domain") or "") 防 TypeError / _on_guide_failed 签名补 seq 对齐其他 handler（emit 式端到端探针防直调绕过）/ _on_load_error 失配分支补消费 pending / Releases JSON 非 list 校验前置走 RSS 回退 / theme_loader 导入期 IO 包装 RuntimeError 中文提示 / E3.9 错误消息补主题名；probe_m0 8/8 PASS + verify_s7/l_accept 适配。

去重与架构收敛（M1）：UsageData 本地死类删除统一 import 自 services / DIMENSIONS 单点导出全项目仅 service.py 一处定义 / ERROR_STAGE 与 QUOTA_WINDOW_KEYS 门面导出且 verify_pl006_accept 升级为 modules import 白名单口径 / opencode_data 移植 go_quota 同款标志+锁 in-flight 去重；probe_m1m2 7/7 PASS。

配置化（M2）：no_db 提示文案回归 ui.json 单源删硬编码 / 节流提示外置 go_quota_error_messages.throttled_template 两处模板化。

清理（M3）：TABLE_LIMIT 死常量与 _CdpGuideSignals 死类删除 / PL007 文档残留七处批次替换（grep 零 themes.py 残留）/ main_window 说明区补三条目+task_runner 补说明区 / CDP_WAIT_TIMEOUT 死常量激活 / README 双主题表述修正四主题；probe_m3 9/9 PASS + verify_v1010_3/v4a3 适配。

验证与收尾（M4）：AGENTS/x.progress 导入验证命令更新（theme_loader/services/task_runner）+ 新建 verify_m_accept 端到端信号断言 5 断言 + 全量回归 63 脚本 0 失败 + 四主题冒烟全 OK。**版本推进决策（用户修订）**：M 批次虽为审计整改但用户要求推进，整体发布版本 V0.2.5.2 → **V0.2.5.3**（PL007 主题文件夹化一并纳入，commit `fix: V0.2.5.3` 已由用户执行）。

## N. 第19轮审计修复任务清单（依据 z.plan.md 附录 A019，2026-08-25 已实施，版本 V0.2.5.4）

> 来源：第 19 轮全量审计（A018 整改 M 批次完成后的连带复盘）；P 级 11 条（中 6 / 低 5，无高），观察项 14 条全部维持豁免
> 目标：逻辑边界防御（缓存兜底提示/解包守卫/文案外置/锁原子性），无功能性重构

正确性（N0）：_on_guide_done 载荷解包守卫——非二元组降级状态栏提示不抛 ValueError（消息外置 status_messages.guide_data_format_error）/ data_page _format_cell 三分支 isinstance 类型守卫防上游结构变更渲染崩溃。

去重与收敛（N1）：节流标注逻辑抽公共——新建 utils/cache_util.py 共享 mark_cached(obj, message, *, error_field, list_field)，opencode_data/go_quota 删本地 _mark_cached 改引共享并精简冗余导入；连带适配 verify_k1_accept/k3_accept/s10；probe_n0 9/9 + probe_n1 7/7 PASS。

配置化（N2）：opencode_data 三处面向用户文案外置 ui.json 新增 data_page_messages 组 / pricing UA 版本号改 utils.logger.VERSION 单点导出替换 _SC.base 直读。

清理与规范（N3）：main.py 缓存兜底超阈路径亦弹预警气泡（标注缓存来源保持去重语义）/ go_quota+opencode_data 缓存发布移入锁内与在途标志复位同段原子可见 / 删冗余 import urllib.error / main_window 说明区补两 handler 条目 / data_page 空结果单表占位反馈（落地为单表占位而非全表 _populate_placeholder 避免覆盖兄弟表）/ system_tray 注释路径残留修正；probe_n2/probe_n3 TDD 全 PASS，verify_l_accept/v1010_1 随实现演进适配。

验证与收尾（N4）：全量回归 63 脚本 0 失败 + IMPORT OK + offscreen 四主题冒烟 + 反向验收。**版本推进决策**：N 批次完成后用户要求继续推进，V0.2.5.3 → **V0.2.5.4**（commit `fix: V0.2.5.4` 已由用户执行）。

## O. 第20轮审计修复任务清单（依据 z.plan.md 附录 A020，2026-08-26 规划）

> 来源：第 20 轮全量审计（V0.2.5.4 提交 3c85e96 基线）；P 级 22 条（中 9 / 低 10 / 文档 3，无高），观察项合并 18 条全部维持豁免；核心发现集中于 N 整改连带效应

### O0 正确性与防御（类别①②）

- [x] O0.1 data_page.py:158 占位分支表头覆盖 —— 删除 `setColumnCount`/`setHorizontalHeaderLabels` 两行（列结构与中文表头 **init**:101/:111 已固定），仅保留 setRowCount(1)+占位 item；验证：probe 构造空 rows 调 `_populate_table` 后断言表头仍为中文首列名且 rowCount==1
- [x] O0.2 main_window.py:977 守卫分支不恢复引导态 —— 守卫命中后复用失败路径恢复序列（`_auto_guide_button/_manual_guide_button.setEnabled(True)` + `_guide_active=False` + `_set_guide_actions_enabled(True)` + `_refresh_timer.start(...)`）再 showMessage+return；验证：probe 断言守卫触发后 timer.isActive() 为 True 且按钮 enabled
- [x] O0.3 main.py:73/:104 format 兜底漏 AttributeError —— 两处 except 元组补 `AttributeError`（随 O1.1 helper 抽取单点化）；验证：probe 以 `{used.x}` 坏模板调 _danger_notify 断言走静态拼接 fallback 不抛
- [x] O0.4 main_window.py:192-211 契约缺新消费键 —— status_messages required 元组（:192-211）补 `"guide_data_format_error"`；验证：probe 临时删 ui.json 该键断言导入期 RuntimeError
- [x] O0.5 utils/logger.py:55 log_level 小写崩溃链 —— `getattr(logging, LOG_LEVEL, ...)` 改显式映射 `logging.getLevelNamesMapping().get(str(LOG_LEVEL).upper(), logging.INFO)`；验证：probe 以 "info" 配置断言 setLevel 后 root.level == logging.INFO 不抛
- [x] O0.6 static_config.py:75-77 数值白名单不查键缺失 —— 循环内补 `if _v is None: raise RuntimeError(f"base.json 缺少必需数值键：{_key}")`；验证：probe 隔离目录删 http_timeout 断言导入期 RuntimeError（不再后移 network 裸 KeyError）
- [x] O0.7 opencode_data.py:237 in-flight 无缓存裸快照 —— 返回前追加 `snapshot.errors.append(_SC.ui["data_page_messages"]["in_flight"])` 与 go_quota 占位口径对齐；验证：probe 在途无缓存断言返回快照 errors 含进行中文案

**O0 完成小结（2026-08-26）**：TDD 先行（`.temp/probe_o0.py` 12 断言修复前 FAIL——O0.2 初版探针无判别力已先置引导态修正，反向验收 `.temp/verify_o0_accept.py` 11 断言换载荷/换键/多重坏模板交叉触发全 PASS）；全量回归 64 脚本 0 失败 + IMPORT OK + offscreen 冒烟 OK。

### O1 去重与收敛（类别④）

- [x] O1.1 main.py:64-114 气泡逻辑两段复制 —— 提取模块级 `_danger_notify(tray, info, suffix)`（含模板 format+AttributeError 兜底+title 提取，成功路径传 suffix=""、缓存路径传配置后缀），两分支各一行调用；验证：probe 分别以成功/缓存超阈 GoQuotaInfo 断言气泡文案一致且仅差来源标注
- [x] O1.2 go_quota.py:26-29 ↔ opencode_data.py:36-39 CHROME_UA 双处维护 —— 收敛至 utils/network 定义并导出（如 `CHROME_UA`），两模块改 import；验证：grep 两模块无本地定义 + IMPORT OK

### O2 配置化与契约（类别③）

- [x] O2.1 opencode_data.py:256/:260 错误文案硬编码 —— data_page_messages 新增 `fetch_failed_template`/`release_failed_template` 两键（值含 `{error}` 占位符），两处 except 改 `.format(error=exc)`；验证：grep 无硬编码文案残留 + probe 断言 errors 消息来自配置
- [x] O2.2 main.py:109 "（缓存数据）"硬编码 —— 复用 `data_page_messages.cache_suffix` 或在 notify 组新增专用键统一措辞（随 O1.1 经 suffix 参数注入）；验证：probe 断言气泡消息尾部与配置键一致
- [x] O2.3 main_window.py:245-249 契约双缺口 —— go_quota_error_messages required 补 `"throttled_template"`；新增 data_page_messages 四键组入 `_UI_STRUCT_KEYS`（照 F0.1 式样）；验证：probe 分别删 throttled_template/data_page_messages.in_flight 断言导入期 RuntimeError

**O1/O2 完成小结（2026-08-26）**：TDD 先行（`.temp/probe_o1o2.py` 15 断言，修复前 11 FAIL——其中 O2.2 初版期望值用错实例数值、O2.1 行为段未考虑 release 链路内部自吞异常走 RSS 回退，均已修正探针后闭环）；实现要点：`_danger_notify(tray, info, suffix)` 单点承载阈值/去重/模板/兜底/标题全链（缓存路径 suffix 改读 `data_page_messages.cache_suffix`，"（缓存数据）"硬编码删除）、CHROME_UA 收敛 utils/network 单点导出、data_page_messages 组六键全部入 `_UI_STRUCT_KEYS` 契约；全量回归 64 脚本 0 失败 + IMPORT OK + offscreen 冒烟 OK。

### O3 清理与规范（类别⑤⑥⑨⑫⑬）

- [x] O3.1 opencode_data.py:258/:409 force 死参数 —— 删除 `fetch_github_releases` 的 force 形参与唯一调用实参（节流实际由快照层控制）；验证：grep 无 force 引用 + IMPORT OK
- [x] O3.2 main_window.py:1163-1179 QMenu 泄漏 —— `_show_columns_menu` 内 `menu.aboutToHide.connect(menu.deleteLater)`；验证：probe 连开两次菜单断言 children 中 QMenu 计数不累积（offscreen）
- [x] O3.3 ui.json usage_failed_template 死键 —— `_on_load_error` 改走该模板格式化（统一中文口径，推荐方案）保留键与契约行；验证：probe 断言状态栏消息为模板产物非原始异常串
- [x] O3.4 theme_loader.py:111-114 is_dir 死分支 —— 将目录存在性检查上移到 :100 注册循环之前恢复 M0.6 设计价值（缺失时中文诊断先于 iterdir）；验证：probe 隔离空资源目录断言导入期 RuntimeError 文案指向根目录
- [x] O3.5 theme_loader.py:24/:62 read_text 编码逃逸 —— 两处 read_text 包 try/except (OSError, UnicodeDecodeError, ValueError) 转 RuntimeError 中文诊断（消息含文件路径）；验证：probe 写入 GBK 字节主题文件断言导入期 RuntimeError 含路径
- [x] O3.6 data_page.py 表格属性重复设置 —— NoEditTriggers/alternatingRowColors 收敛至 **init** 单点一次，_populate_placeholder 与 _populate_table 两分支删除重复行；验证：probe 断言占位表格 editTriggers 为 NoEditTriggers 且填充路径行为不变
- [x] O3.7 services/service.py:95-122 sqlite3.Error 英文直显 —— get_usage/export_data 的 except 分支转 `ServiceError("usage_db_error", 中文消息)` 口径；验证：probe 传坏库路径断言收到中文 ServiceError 而非裸异常串
- [x] O3.8 services/service.py:64-84 登录等待 deadline 失真 —— deadline 检查下沉至每轮 dashboard 验证步骤之前；验证：probe mock 验证耗时断言总等待不超过 login_wait_seconds 上界（或注释声明取舍）
- [x] O3.9 browser_creds.py:232-234/:277 or 巧合写法 —— `_with_copied_db(...) or ([], False)` 改显式 `result = ...; if result is None:` 判空；验证：IMPORT OK + 全量回归 browser_creds 相关脚本通过
- [x] O3.10 pricing.py:291 变量遮蔽 —— 局部变量 `pricing` 改名 `cost_block`；验证：IMPORT OK
- [x] O3.11 说明区失实/缺漏批修（八处合并）—— main.py:149-152 补缓存气泡描述、utils/logger.py:97-99 _setup_handlers 条目平级化、go_quota.py:583 改"缓存由 fetch_go_quota 末尾原子发布"、opencode_usage.py:746 删 retry 两项/:722 去"10s"数值化、services/service.py:196-198 清残句、browser_creds.py:582/:674 改"内部使用"、ui/main_window.py 说明区补 _build_cards/_build_guide_card/_build_detail_section/_sorted_hidden_columns 四条目+_on_guide_done 条目附守卫一句、ui/task_runner.py 说明区补 _task_done/_FnTask.**init**/.run 三条目；验证：verify_s11 式 docstring/说明区检测脚本全 PASS

**O3 完成小结（2026-08-26）**：TDD 先行（`.temp/probe_o3.py` 24 断言，修复前 22 FAIL）；实施要点：O3.1 删 force 死参数（连带适配 verify_pl002_accept:87）、O3.2 QMenu aboutToHide→deleteLater 防滞留泄漏、O3.3 usage_failed_template 死键接入 _on_load_error 消费方（模板产物替代英文异常串直显）、O3.4 根目录缺失检查上移注册循环前恢复设计价值、O3.5 两处 read_text 编码/IO 失败转 RuntimeError 中文诊断（含路径，探针以 GBK 字节主题文件实证）、O3.6 表格静态属性收敛 init 单点（占位格不再可编辑）、O3.7 连接+查询统一 sqlite3.Error→ServiceError 中文口径（复用 usage/export_failed_template；OpenCodeDB 构造即连接故构造纳入 try，db 可空+finally 判空关闭）、O3.8 deadline 验证步骤前复查、O3.9 显式判 None 替代 or 巧合等价、O3.10 cost_block 改名、O3.11 八处说明区批修（含 O0-O2 新增函数补条目义务）。

### O4 验证与收尾

- [x] O4.1 全量回归 + 收尾 —— TDD 探针（probe_o*.py 修复前 FAIL）+ run_all_verify 0 异常 + IMPORT OK + offscreen 冒烟 + 反向验收（删键/坏模板/坏编码触发断言）；x.progress 勾选 + 版本推进决策 + commit 草稿

**O4 完成小结（2026-08-26）**：O 批次（第 20 轮审计整改）全部完成——probe_o0（12 断言）/verify_o0_accept（11 断言反向验收）/probe_o1o2（15 断言）/probe_o3（24 断言）全 PASS；全量回归 64 脚本 **0 失败** + IMPORT OK + offscreen 冒烟 OK。版本推进决策与 commit 草稿待用户确认后补充。

> **版本推进决策（O 批次）**：第 20 轮审计整改（O 系列）完成后用户确认推进，发布版本由 V0.2.5.4 提升至 **V0.2.5.5**（O 批次整改纳入本次提交；N 批次已随 `fix: V0.2.5.4` 提交 3c85e96，不在本次范围）。
> **commit 草稿（待用户执行，AI 不执行 git 写操作）**：
>
> ```
> fix: V0.2.5.5，审计整改（正确性防御/去重收敛/配置化契约/清理规范）
> - 正确性与防御：数据页空结果保持中文表头、引导载荷守卫恢复引导态与定时刷新、坏模板兜底补全属性异常捕获
> - 防御加固：日志级别非法值启动防护、数值配置键缺失导入期拦截、在途快照标注进行中文案
> - 防御再补：加载失败消息改模板产物、主题资源读取失败转含路径中文诊断、数据库坏库转业务错误统一提示
> - 去重收敛：超阈预警气泡逻辑单点化两路共用、浏览器标识字符串收敛网络工具单点导出
> - 配置化：数据页错误文案模板外置、缓存气泡尾部标注读配置、数据页文案组与节流模板键入契约校验
> - 清理：删除拉取死参数、菜单关闭即释放防泄漏、目录缺失检查上移、表格属性收敛单点、查询显式判空、变量改名避遮蔽
> - 规范：八处模块说明区失实修正与方法条目补全、登录等待验证前复查截止时间
> - 版本推进 V0.2.5.4 → V0.2.5.5（base.json/README 徽章/x.progress 三处一致）
> ```

## WTH001. 观察项可修正任务清单（依据 z.plan.md「Watch 系列」Watch001 批次，2026-08-26 规划）

> 来源：第 16-20 轮观察项三方分级——69 条中 33 条永久豁免 + 24 条条件豁免已并入 z.plan.md
> 「观察项豁免定案清单」①②两级；本清单为剩余 12 条可直接修正项。
> 编号规则：WTH001 为本批次代号，批内子项 .a-.l 与 z.plan.md Watch001.a-l 一一对应；
> .m 为批次收尾。后续新观察批次递增 WTH002…

### 修正组（对应 Watch001.a-l）

- [x] WTH001.a _quota_card dict frame/title 键零读取（死键） —— 删除两键及写入处（先确认全仓零消费）；验证：grep 零引用 + IMPORT OK
- [x] WTH001.b 时序解析数字正则收紧 —— `[\d.]+` 改 `\d+(?:\.\d+)?`；验证：probe 构造 "1.2.3" aria-label 断言跳过该条不丢整图
- [x] WTH001.c stack 扫描窗口魔数补注释 —— 6000 处补量纲注释（字符数窗口防超窗静默丢行）；验证：grep 注释在位
- [x] WTH001.d subprocess_timeout cast 统一 —— opencode_usage/browser_creds 两处统一 int()；验证：IMPORT OK + 全量回归
- [x] WTH001.e services 导入路径统一 —— 混用形式机械归一为 from services.service import X；验证：grep 零混用 + IMPORT OK
- [x] WTH001.f THEME_LABELS fallback 死分支处置 —— M3 改名后重新定位确认不可达后删分支；验证：IMPORT OK + 四主题冒烟
- [x] WTH001.g windows.py 顶层解包风格 —— 内联 get_static_config 改顶层 _SC 解包；验证：IMPORT OK
- [x] WTH001.h retry 计数口径注释澄清 —— retries 尝试总轮次语义注明；验证：注释与实现一致性核对
- [x] WTH001.i CLI --estimate help 补声明 —— help 文案补注生效范围；验证：--help 输出含说明
- [x] WTH001.j "≥80%" 注释符号化 —— 改"≥ QUOTA_DANGER_PERCENT"表述；验证：grep 全仓零残留
- [x] WTH001.k AGENTS verify 计数动态化 —— 写死计数改"全部 verify_*.py 脚本"；验证：AGENTS.md 无具体计数残留
- [x] WTH001.l zip 数量不齐补 warning —— releases 双源数量不一致记日志；验证：probe mock 不齐断言 warning

### 收尾组

- [x] WTH001.m 全量回归 + 收尾 —— run_all_verify 0 异常 + IMPORT OK + offscreen 四主题冒烟；x.progress 勾选 + commit 草稿（git 由用户执行）

**WTH001 完成小结（2026-08-26）**：TDD 先行（`.temp/probe_wth.py` 15 断言，修复前 15 FAIL）；实施要点——a 死键删除（card dict 仅留渲染消费键）、b 正则收紧 `\d+(?:\.\d+)?`、c 6000 补字符数窗口量纲注释、d 两模块统一 int()、e services 导入归并 from services.service 形式、f THEME_LABELS 直接下标访问（C0.6 契约保证可达，删不可达 fallback）、g windows.py 顶层 _SC 解包、h retries 总尝试轮次口径澄清、i --estimate help 注明仅总览生效、j 全仓 ≥80% 快照注释符号化为 QUOTA_DANGER_PERCENT 表述、k AGENTS 写死计数改"数量随批次增长"、l zip 双列表数量不齐 warning 告警；**教训记录**：f 条 edit 替换曾致 for 循环体缩进丢失（probe 仅文本断言未 import 未捕获，全量回归 IMPORT 阶段炸出）——已修复并确认 probe 后续批次应含至少一项 import 级冒烟断言；验证：全量回归 64 脚本 0 失败 + IMPORT OK + offscreen 四主题冒烟全 OK。本批随文档整理（A020 归档/豁免定案合并/双文件压缩）一并提交。

## PL008 QML 前端立项：双前端并存 + QtWidgets 迁入 ui/qt6（依据 z.plan.md PL008 方案，2026-08-26 规划）

> 目标：QML+FluentUI 前端（方案 A）并行孵化；现有 QtWidgets 前端迁入 ui/qt6/ 保持默认可用；共享语义经 services/contracts 单点
> 状态：📌 待实施
> **验收点：mock 数据源下 QML 前端可启动并查看全部页面效果（用量监控页两区 + 数据动态页 + 单基础主题 + 动效/光影/阴影/粒子能力展示）——粒子为必做；不接入真实业务；PL008 结束版本 V0.2.6.1（一次 commit 收口）**
> 硬约束：搬迁批纯重构行为零变化，独立 commit 可回滚；共享语义全走 contracts 单点无直读例外；QML 版稳定前旧前端不退役；QML 开发期间 qt6 全量回归保持 0 失败

### PL008.1 共享事实层（contracts.py）

- [x] PL008.1.a 新建 services/contracts.py —— 唯一解包点：QUOTA_WARN_PERCENT/QUOTA_DANGER_PERCENT（ui.json quota_warn_percent/quota_danger_percent）+ THEME_NAMES/DEFAULT_THEME_NAME（ui.json themes 数组）+ `get_ui_texts(group)` 泛型文案读取（含键存在性校验，对齐 H0.4 契约风格）；验证：IMPORT OK + 值与原 theme_loader 解包一致（probe 断言相等）✅ 2026-08-27（probe_contracts PASS）
- [x] PL008.1.b 新建 services/qt6_adapter.py —— qt6 前端适配桥（从 contracts 取数转发，qt6 特有整形留此处）；验证：IMPORT OK ✅ 2026-08-27（main.py 经它取阈值；probe 断言转发一致）⚠️ **PL008 收尾定案（2026-08-27）：此文件已删除**——纯转发零整形，唯一消费者 main.py 仅用 QUOTA_DANGER_PERCENT（业务阈值），绕道 UI 适配桥拿业务常量属分层错乱；main.py 改直连 services.contracts，QML 亦不建独立 adapter（launcher.py 承担数据桥）
- [x] PL008.1.c theme_loader.py 改造 —— 删两阈值与 THEME_NAMES 解包行，改 `from services.contracts import ...` 消费；验证：probe 断言 theme_loader 值 == contracts 值 ✅ 2026-08-27（probe_contracts PASS；main_window 保持经 theme_loader 转发，符合 z.plan 边界表）

### PL008.2 搬迁批（纯重构）

- [x] PL008.2.a git mv 五文件 + themes/ 至 ui/qt6/，新建 ui/qt6/**init**.py，ui/**init**.py 保留；验证：git mv 后文件在位 ✅ 2026-08-27（git status 全 R/RM 状态，历史保留）
- [x] PL008.2.b qt6 内部互引路径批量改 `from ui.qt6.xxx import ...`（main_window/data_page/theme_loader/task_runner/system_tray 互相引用全量排查）；验证：grep ui 内部零 `from ui.(main_window|data_page|theme_loader|task_runner|system_tray)` 残留 ✅ 2026-08-27（ZERO ✓；5 文件说明区标题同步 ui/qt6/*.py）
- [x] PL008.2.c main.py import 改 ui.qt6.* + 阈值/注册表改从 services.contracts 拿；验证：IMPORT OK ✅ 2026-08-27（main.py 经 ui.qt6.* + services.qt6_adapter）⚠️ PL008 收尾：阈值改为 main.py 直连 services.contracts（qt6_adapter 已删，见 PL008.1.b 注）
- [x] PL008.2.d .temp verify 脚本批量适配 ui.qt6.* import（全量 64 个排查）；AGENTS.md 验证命令 + x.progress 命令速查同步；验证：全量回归 64 脚本 0 失败（搬迁验收红线）✅ 2026-08-27（64/64 全绿；适配面含 import/sys.modules 清理/mock.patch 目标/源码路径/说明区标题/k 系列 probe_k0-k2）
- [x] PL008.2.e offscreen 四主题冒烟 + 新旧行为抽样对比（手动/探针各入口）；验证：冒烟全 OK ✅ 2026-08-27（probe_qt6_smoke PASS：四主题 QSS/调色板、阈值分级边界、窗口四主题切换、托盘创建四组抽样全 OK）

### PL008.3 QML PoC（环境验证）

- [x] PL008.3.a 安装 PySide6 + PySide6-FluentUI-QML（⚠️ 验证 Python 3.14 wheel 兼容性——不兼容则 QML 前端用独立 3.12 venv）；验证：`import PySide6, FluentUI` 成功 + `pyside6-qml` 可执行 ✅ 2026-08-27（PySide6 6.11.2 = cp310-abi3 wheel 兼容 3.14；FluentUI 1.6.7 纯 Python；装入 .venv 与 PyQt6 共存正常——PyQt6 Qt 6.11.1 + PySide6 Qt 6.11.2 双绑定各自独立；import 双成功 + pyside6-qml --help 可执行 + pyside6-* 全套工具就位）
- [x] PL008.3.b 最小 FluWindow + FluButton demo 跑通（offscreen + 窗口模式）；验证：demo 启动无异常 + QML 控制台零报错 ✅ 2026-08-27（probe_qml_demo PASS：offscreen 与 --windowed 双模式——① 根对象创建 ② FluButton 点击信号链路（click() 递增 window.clicks）③ QML 引擎 warnings 零收集；关键发现：**FluApp 为单例不可创建**（qmltypes isSingleton），1.6.7 入口用 FluWindow 作根）

### PL008.4 MockService 与数据桥

- [x] PL008.4.a 新建 services/mock_service.py —— 与 AppService 同签名（get_usage/get_quotas/get_data_page/export_data/save_account/add_account_via_cdp），返回构造的 UsageData/list[GoQuotaInfo]/ModelDataSnapshot，**含三态样例**（正常/错误占位/缓存标注，供 UI 各分支调试）；验证：MockService 各方法返回类型与真服务一致（probe isinstance） ✅ 2026-08-27（probe_mock_service PASS：① 六方法签名与 AppService inspect 一致 ② normal 态 isinstance（UsageData/UsageSummary/UsageRow/GoQuotaInfo/ModelDataSnapshot）+ export/save 返回 None + add_account 返回 (str,str) ③ error 态配额 error+error_stage=NETWORK/三窗口空、数据页 errors 非空、usage 抛 ServiceError（对齐真服务 db_path=None 口径）④ cached 态 is_cached=True+保留数据）
- [x] PL008.4.b QML 数据桥 —— 新建 ui/qml/launcher.py：QQmlApplicationEngine + setContextProperty("service", MockService) + QAbstractListModel 包装列表数据注入（usageModel/quotaModel/releasesModel，**role 名与 dataclass 字段一致**）+ 阈值/注册表经 contracts 注入 + 文案经 contracts.get_ui_texts 注入；资源路径用 get_project_root() 自定位；验证：探针断言 engine.rootContext() 各 property 非空 + QML 侧 Component.onCompleted 打印注入值 ✅ 2026-08-27（probe_qml_bridge PASS：build_context 十键齐备 + 三 model 行数 + role 名=字段名（点路径 tokens.total/five_hour.usage_percent，顶层平铺字段同名）+ QML report 打印注入值全对：warn=50;danger=80;themes=4;default=light;usageRows=2;quotaRows=2;releasesRows=3;sessions=12;total=301000;statusGroup=ok。ListModel 通用化：点路径取值 + @Property count（QAbstractListModel 无内置 count）+ prepare_engine 统一 FluentUI.init 与注入保活）

### PL008.5 QML 骨架

- [x] PL008.5.a ui/qml/main.qml —— FluApp 入口 + FluNavigationView 两页导航（用量监控/数据动态对齐现 UI）；验证：demo 启动显示两页 + 切换无异常 ✅ 2026-08-27（probe_qml_skeleton PASS：① 根对象创建 ② 导航两页标题=用量监控/数据与动态（对齐 qt6 usage_tab_title/data_page_tab_title）+ navCount=2 ③ QMetaObject.invokeMethod 调 switchToSecond→setCurrentIndex(1) 无异常 ④ QML 引擎零警告。注：**FluApp 在 1.6.7 为单例不可创建**（PL008.3.b 实测），入口实际用 FluWindow 根 + FluNavigationView；页面占位组件待 PL008.6/7 填充；图标用 FluentIcons 字符码 0xE9D2(Chart)/0xE81C(History)）
- [x] PL008.5.b ui/qml/theme/Theme.qml —— **单基础主题**单例：接收 context property 注入的 defaultTheme，初始化一套基础色板（chunk_ok/warn/danger/pie 等对齐语义），无主题切换 UI；能力体现在动效/光影/阴影/粒子而非主题数量；验证：探针断言 Theme 单例色板属性就位 + offscreen 启动无异常 ✅ 2026-08-27（probe_qml_skeleton ③ PASS：Theme 单例 pragma Singleton + theme/qmldir 注册，chunkOk=#47c18c/chunkWarn=#ffb020/chunkDanger=#ff4b4b + pie1-5 + bg/cardBg/text/accent 就位；themeName=light 证明 context 注入 defaultTheme 成功被单例接收；main.qml import "theme" 引用）

### PL008.6 用量监控页（卡片区 + 配额区 + 饼图）

- [x] PL008.6.a 卡片区 —— FluCard + FluProgressBar 绑定 usageModel（summary 字段），P17 顺序 + 缓存率标注；验证：探针断言卡片数值与 mock summary 一致 ✅ 2026-08-27（probe_qml_usage ① PASS：五卡按 P17 顺序 总tokens=301.0K/输入=125.0K/输出=98.0K/缓存率=15.9%（(cache_read+cache_write)/total）/总费用=$12.34，数值与 mock summary 一致；容器用 FluArea（**1.6.7 无 FluCard 组件**）替代；cardTitles/tokenAbbrUnits/costZeroEpsilon 经 contracts + launcher 注入（QML 侧格式化对齐 qt6 _format_tokens/_format_cost 口径））
- [x] PL008.6.b 配额区 —— FluComboBox（workspace_id，userData 同 qt6 语义）+ FluButton 添加账户 + 单卡三进度条（five_hour/weekly/monthly 绑定 quotaModel）+ 状态文案（错误/缓存态走 mock 三态样例）；验证：探针断言切换选择器渲染变化 + 三进度条 value 与 mock 一致 ✅ 2026-08-27（probe_qml_usage ② PASS：combo textRole=workspace_id 显示账户、切换后 bar 值 35/62/81→12/28/44 同步更新、normal 态状态文案空；④ PASS：error/cached 场景状态文案含模拟/缓存标注（mock 三态驱动）；QuotaBar 自绘进度条替代 FluProgressBar——**1.6.7 FluProgressBar 含 Infinite 循环动画，offscreen 下 0xC0000005 崩溃（库 bug）**；ListModel 补 getNumber/getString Slot（混合类型 Slot 返回 float 触发 Shiboken copy-convert 崩溃）+ count 属性）
- [x] PL008.6.c 饼图 —— QtCharts PieSeries（用量百分比），弧色分级 = contracts 共享阈值 + Theme.qml 自持三色（chunk_ok/warn/danger 色板键，不引用不复刻 qt6 的 quota_chunk_color），动态更新 clear-append；验证：探针断言扇区数与 mock infos 一致 + 分级色阈值边界（warn-1/warn/danger-1/danger 四值断言颜色） ✅ 2026-08-27（probe_qml_usage ③ PASS：扇区数=3（当前账户三窗口）、值 [35,62,81]、扇区色 [#47c18c,#ffb020,#ff4b4b]（分级 ok/warn/danger）、边界四值断言（warn-1→ok/warn→warn/danger-1→warn/danger→danger）；PieSeries 不在 QObject 树，探针经 UsagePage 暴露 pieCount/pieValues/pieColors 属性断言；**QtCharts QML 需 QApplication**（QGuiApplication 崩 0xC0000005）；onCountChanged→clear 递归死循环已移除；FluNavigationView 页面加载需 FluPaneItem onTap 显式 push（官方 demo 模式，FluNavigationView 不自动加载））

### PL008.7 数据与动态页

- [x] PL008.7.a TableView（QtQuick.TableView，列头对齐现有 COLUMN_IDS，行高列宽静态配置对齐 qt6 视觉）绑定 usageModel；验证：探针断言表格行数与 mock 一致 ✅ 2026-08-27（probe_qml_data_page ① PASS：列头 9 列与 ui.json table_columns 动态一致、表格行数=2（mock month rows）、首行格式化对齐 qt6 _render_table（label 直显/calls 原样/total=88.0K KMB/cache_rate=0.0%（缓存 0/总量）/cost=$3.40）；QtQuick.TableView + 列头 Row 固定行 + 表体空态覆盖（data_empty_text）；列 id 语义绑定 cellText 分支（P23），嵌套 role 经 model["tokens.total"] 访问；列宽/行高 QML 静态常量对齐 qt6 观感；列元数据经 contracts.TABLE_COLUMNS 注入（ui.json table_columns 权威 + TABLE_COLUMN_IDS 导入期契约校验）；DataPage 文案经 contracts.DATA_PAGE_TEXTS 注入）
- [x] PL008.7.b Releases 时间线 —— ListView + 自绘 delegate（版本号/日期/正文）+ 空态占位文案；验证：探针断言空数据 mock 显示占位 + 有数据渲染条数一致 ✅ 2026-08-27（probe_qml_data_page ②③ PASS：normal 3 条渲染（首条 tag=v1.6.7/日期=2026-08-01 取前 10 字符/正文）+ error 场景空态占位（data_releases_empty）；ListView + 自绘 delegate（版本号粗体/日期/正文卡片样式）+ StackLayout 空态切换（currentIndex 绑 count）；⚠️ delegate 用 model.role 而非 modelData——Qt6 多 role QAbstractListModel 下 modelData 为 undefined（实测警告））

### PL008.8 动效层（按需）

- [x] PL008.8.a MultiEffect 卡片阴影/光晕（shadowEnabled + blur 包裹 FluCard，blur 静态不动画）+ 页面过渡（FluNavigationView 自带 + 自定义 Transition opacity+位移）；验证：无头冒烟 + 手动目检清单（阴影可见/过渡流畅） ✅ 2026-08-27（probe_qml_effects ① PASS：MultiEffect 静态能力（shadowEnabled=true + blurEnabled/blur 静态数值）+ 两页入场过渡 opacity 0→1 归位 + 零警告；新建 ui/qml/effects/CardShadow.qml 封装（shadowEnabled + blur 静态不动画 + default property content），接入 UsagePage 五卡区与 DataPage releases 卡；页面过渡 = 各页根 opacity 淡入（NumberAnimation 300ms 有限动画，不阻塞）；⚠️ offscreen 下 Repeater/ListView 的 delegate 不实例化（Qt offscreen 环境限制，连基础 Text delegate 也 0）——卡片阴影 DOM 可见性无法无头断言，属手动目检清单（PL008.9.a 联调核对））
- [x] PL008.8.b 粒子系统（**必做**）—— QtQuick.Particles（ParticleSystem + Emitter + ImageParticle + ParticleGroup），启动画面或背景点缀二选一；验证：无头冒烟不崩 + 手动目检帧率流畅 ✅ 2026-08-27（probe_qml_effects ② PASS：粒子三件套就位（ParticleGroup spark + ImageParticle Fade/colorVariation + Emitter emitRate 8/AngleDirection 上浮）+ offscreen 冒烟不崩零警告；选**背景点缀**：UsagePage 底部上浮粒子，z 序低于内容区，粒子在卡片间隙可见；offscreen 冒烟不崩（fx_probe 预验证 MultiEffect/Particles offscreen 可创建））

### PL008.9 验收与版本推进（虚拟数据演示版）

- [x] PL008.9.a 全页面 mock 联调 —— launcher.py 启动完整 UI：用量监控页两区 + 数据动态页 + 单基础主题 + 动效/光影/阴影/粒子全可看可交互；验证：手动目检清单逐项核对（对照 qt6 版布局与字段）+ offscreen 冒烟 ✅ 2026-08-27（probe_qml_fullapp PASS：FluWindow 根 + 两页导航标题 + Theme 单例 + context 15 键齐备 + 三 model 行数 + 框架零警告；全页面 offscreen 冒烟 = usage/data_page/effects/fullapp 四探针全过；手动目检清单：五卡值/账户切换/三进度条/饼图/背景粒子/卡片阴影/导航切页/明细表格/Releases 卡，对照 qt6 布局与字段）
- [x] PL008.9.b 错误策略对齐核对 —— QML 版落实"不崩溃/不阻塞/有提示/能自愈"：FluInfoBar/Flyout 替代状态栏提示、缓存兜底标注、失败保留旧视图（mock 三态样例驱动）；验证：三态样例逐一目检 + 无头冒烟 ✅ 2026-08-27（FluInfoBar 接入 UsagePage：showError/showWarning 替代状态栏提示（onCompleted 绑 root + onStatusTextChanged 触发），⚠️ FluInfoBar 是 FluObject 非 Item——root 需 onCompleted 显式赋值，调用 API 是 showError/showWarning 非 create；缓存兜底标注 statusText="缓存数据"（cached 态）；保留旧视图：演示版无刷新操作标注 N/A（真实链路留 P27）；三态样例探针断言（probe_qml_usage ④）+ offscreen 冒烟零警告；手动目检：三态启动查看通知条）
- [x] PL008.9.c 收尾验证 —— qt6 全量回归 0 异常（QML 开发期间回归保持绿）+ IMPORT OK + 四主题冒烟 + 文档同步（README 结构/AGENTS 命令补 qml launcher）；验证：回归全绿 ✅ 2026-08-27（qt6 全量回归 64 脚本 0 失败 + IMPORT OK + probe_qt6_smoke 四主题冒烟 PASS；README 结构同步 ui/qt6 + ui/qml（含 launcher.py/main.qml/两页/theme/effects）+ services.mock_service + 主题路径 ui/qt6/themes + QML 演示版启动说明；AGENTS 命令已在 PL008.4 补 QML 独立验证，无需再加）
- [x] PL008.9.d 版本推进 V0.2.6.1 三处同步（base.json/README 徽章/x.progress 版本行）+ commit 草稿，一次 commit 收口（git 由用户执行）；验证：三处字面一致 + logger.VERSION ✅ 2026-08-27（三处字面一致 + logger.VERSION=V0.2.6.1；版本推进在批次收尾全量回归绿后执行，不污染回归集——A018 纪律；commit 草稿见汇报，git 由用户执行）
- [x] PL008.9.e 范围外标注 —— 接入真实业务（setContextProperty 换 get_service）与 main.py --frontend 分发 + qt6 文案直读改造（y.problem 已登记）列为后续批次（PL009 规划时立），不在本批验收；验证：x.progress 备注到位 + y.problem 条目在位 ✅ 2026-08-27（范围外三项落位：① 接入真实业务 + --frontend 分发 → y.problem **P27** 新增登记（2026-08-27）② qt6 文案直读改造 → y.problem **P26** 在位（2026-08-26）③ z.plan 决策 6/8 + 方案 Phase 6/7 已列范围外——本批 QML 保持虚拟数据演示版角色）

## P. 第21轮审计修复任务清单（依据 z.plan.md 附录 A021，2026-08-28 规划）

> 来源：第 21 轮 QML 前端 UI 设计审计（qt-ui-design skill 清单，V0.2.6.1 基线）；P 级 6 条（Critical 3 / Warning 3），参考级观察项 2 条维持豁免
> 范围：仅 ui/qml/ 前端设计合规整改，不涉及 qt6 与业务层；QML 版保持虚拟数据演示版角色，不接真实业务

### P0 正确性（Critical 3 条）

- [x] P0.1 字号体系整改 —— 新建 ui/qml/theme/TypeScale.qml 单例（modular scale：caption 12 / body 16 / title 21 / display 28 四档）+ theme/qmldir 注册；UsagePage/DataPage 全部 `font.pixelSize` 改 `font.pointSize` 并从 TypeScale 取档（卡片数值→title、卡片标题/配额账户/进度条标签→caption、正文/表格/动态→body 起步，对齐 16px 最小正文）；验证：探针断言两页所有 Text 无 pixelSize 直写 + 正文档 ≥16
- [x] P0.2 三色对比度校正 —— Theme.qml chunkWarn 由 #FFB020 调深至白底对比度 ≥3:1（候选 #E58E00），chunkOk/chunkDanger 同步白底核对 ≥3:1；验证：探针计算三色对比度断言 ≥3:1
- [x] P0.3 reduced-motion 路径 —— Theme 单例增 `reducedMotion` 属性（默认 false，QSettings 或代码开关）；粒子 Emitter 与根 opacity 过渡绑定之：开启时 emitRate=0、opacity 直达 1；验证：探针断言切 reducedMotion 后粒子停止/无过渡

### P1 规范与无障碍（Warning 3 条）

- [x] P1.1 颜色/圆角 token 化 —— Theme 单例补 `borderSubtle`（#E0E0E0）/`rowStripe`（#F4F4F4）色键 + `radius` 统一 8；UsagePage/DataPage 六处 #E0E0E0、斑马纹 #F4F4F4、radius 6/8 改引用单例；验证：grep 两页零硬编码色/圆角残留 + 探针断言卡片圆角一致
- [x] P1.2 Accessible 属性 —— 交互元素补 Accessible.name/role/description：添加账户按钮、导航两页（main.qml FluPaneItem）、三进度条、账户选择器；验证：探针断言关键交互元素 Accessible.name 非空
- [x] P1.3 饼图双编码 —— legend 开启或扇区外补百分比标签，分级色 + 数值文案并存（色弱可用）；验证：探针断言 pieSeries 每扇区有可见 label 或 legend 启用

### P4 验证与收尾

- [x] P4.1 全量验证收尾 —— QML 独立探针（usage/data_page/fullapp）+ 相关 verify 子集 + IMPORT 冒烟 + 手动目检（窗口模式核对字号/颜色/粒子可关）；x.progress 勾选 + commit 草稿（git 由用户执行）

**P 系列完成小结（2026-08-28）**：TDD 先行（`.temp/probe_qml_a021_p.py` offscreen 源码+运行时断言 21 项 + 窗口探针 `probe_qml_usage` 增补 P1.3 扇区 label 断言，修复前窗口探针因 Accessible 语法致 UsagePage 未实例化 FAIL——FluPaneItem 非 Item 派生禁挂 Accessible 附加属性（已移除导航项两处）、FluProgressBar 不支持 Accessible.value（已删三处））。实施要点——P0.1 新建 TypeScale 单例四档（caption 9/body 12/title 14/display 18 pointSize，随 OS DPI 缩放）两页 13 处 font.pixelSize 全改引用、P0.2 三色按 WCAG 白底 ≥3:1 校正（ok #47C18C→#3CA36F 3.15/warn #FFB020→#C77F00 3.25/danger #FF4B4B 3.3 不动）、P0.3 Theme.reducedMotion 开关绑粒子 emitRate 与两页入场过渡 Behavior.enabled、P1.1 两页六处 #E0E0E0 + 斑马纹 + radius 6/8 全改 Theme.borderSubtle/rowStripe/radius 引用、P1.2 按钮/选择器/三进度条补 Accessible.name/role（5 处）、P1.3 扇区 label=窗口名+百分比 + labelVisible 双编码；验证：全量回归 64 脚本 **0 失败** + IMPORT OK + QML 独立验证（import ui.qml.launcher）+ 四探针（a021_p/usage/effects/data_page/fullapp）全 PASS + 版本 V0.2.6.2 三处一致 + logger.VERSION。
