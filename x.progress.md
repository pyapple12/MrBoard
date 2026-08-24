# 开发进度追踪（x.progress.md）

> 依据：`z.plan.md`（myboard 方案报告）
> 当前版本：V0.2.5.2（VERSION 单一来源在 config/static/base.json 的 version 字段；**2026-08-24 起启用四段式版本号规则 V0.2.4.3 形式**，此前为 ver 0.NNN 两段式）
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

## PL004 用量纯净视图回归：切换日志移除 + 配额单卡选择器（依据 z.plan.md PL004 方案，2026-08-23 规划，版本 ver 0.240）

> 目标：用量统计删除账户概念回归纯净单视图；Go 配额改"单卡 + 账号选择器 + 选择记忆"；凭据管理入口与托盘预警原样保留
> 根因：opencode.db 消息 JSON 无账号维度字段且多账号混写同库——时间窗近似对并行使用物理不可分、对串行切换有采样漏检，实用价值有限
> 已拍板（2026-08-23）：删 A+B 全量/配额单卡选择器选谁显示谁/凭据数组格式与追加式保存保留/残留物物理删除/托盘零改动/版本 ver 0.240
> 硬限制：since/until 形参是 --since 时间过滤与账户无关严禁误删；时间窗近似方案退役后不再以任何形式重新引入
> 完成情况：✅ 全部实施完成（2026-08-23）——removal 探针 26→0 失败、quota 行为探针 5/5、legacy 兼容实证 6/6、verify_pl004_accept 验收 18/18、全量回归 0 异常

### PL004.1 删 A：切换日志体系（时间点记录）

- [x] PL004.1.a credential_store.py：删 `SWITCH_LOG_FILENAME` 常量（:23）+ `load_switch_log`/`save_switch_log`/`detect_credential_switch` 三函数（:111-182）+ 说明区对应条目（:214-235 相关行）
- [x] PL004.1.b 连带删指纹链：credential_store.py `credential_fingerprint`（:103）+ go_quota.py `GoQuotaInfo.fingerprint` 字段定义（:140）与两处赋值（:396-408/:478）——无 UI 消费者，账户标识统一改用 workspace_id
- [x] PL004.1.c go_quota.py：删 `SWITCH_LOG_FILE` 常量（:50）+ `record_credential_switch` 钩子（:103-112）+ fetch 循环内调用点（:458-459 含 PL001.3 注释）+ 说明区条目（:560/:570）
- [x] PL004.1.d main.py：删 import（:15）与启动时调用（:38）；ui/main_window.py：删 `SWITCH_LOG_FILE`/`load_switch_log` import（:50/:65）
- [x] PL004.1.e 验证：IMPORT OK + offscreen init + 定向探针（访问被删符号 AttributeError 即 PASS）

### PL004.2 删 B：时段截取链（intervals 参数 + 账户下拉 + 导出标注列）

- [x] PL004.2.a opencode*usage.py：删 intervals 形参全链——totals（:230/:235/:272）/各 by*\* 约 8 处签名与透传（:297-443）/\_time_clause 区间分支仅 intervals 部分（:460-489）/其余查询（:510/:554）；**严禁动 since/until**（--since 时间过滤）
- [x] PL004.2.b opencode_usage.py：删 CLI `--account` 参数（:650-654）与切换日志解析块（:659-683）+ import L18-19；CLI 调用点 intervals=intervals 清理（:715/:740）
- [x] PL004.2.c exporter.py：删 `account_intervals`/`account_label` 形参（:34-35）+ 六处查询传参（:40-65）+ 标注列写入块（:69-77 row["account"] 与 CSV_COLUMNS + ("account",)）+ 说明区条目（:132/:135）
- [x] PL004.2.d ui/main*window.py：删账户下拉三常量（:98-100）+ `_UsageTask.intervals` 字段与传参（:363/:380/:386）+ `\_ExportTask.account*\*`（:474-475/:487-488）+ `self.\_account_intervals` 初始化（:737）
- [x] PL004.2.e ui/main_window.py：删下拉构建与装配（:898-901/:930）+ 三方法整体 `_rebuild_account_combo`/`_sync_account_intervals`/`_on_account_changed`（:948-1019）+ 任务赋值点（:1042/:1274-1277）
- [x] PL004.2.f config/settings.py：删 `account_filter` 字段（:40）+ to_dict 输出（:49）+ from_raw 解析块（:77-79）
- [x] PL004.2.g config/static/ui.json：删 `account_filter_all_label`/`account_combo_template`/`account_label_date_format` 三键
- [x] PL004.2.h 验证：IMPORT OK + offscreen init + 全量回归（pl001 系列预期 FAIL 属涟漪，PL004.5 清理）

### PL004.3 配额区改造：单卡 + 账号选择器 + 选择记忆

- [x] PL004.3.a `_build_quota_section` 回归单卡：删 `_quota_cards` 动态列表容器与 `_build_quota_card(primary=True)` 兼容主卡模式（PL001.9 结构），恢复单个 `_quota_card` dict
- [x] PL004.3.b `_render_quota` 单卡渲染：按选中 workspace_id 从 infos 取项渲染；失配（已删凭据/尚未刷出）回落首个有效项；全无效渲染 infos[0] 错误态
- [x] PL004.3.c 配额区顶部新增选择器行：QLabel + QComboBox（userData = workspace_id 自然 ID 与凭据判重同源）；标签文案外置 ui.json 新键 `quota_account_label`
- [x] PL004.3.d 选项以每次刷新的 infos 为准重建（blockSignals 防回环）；错误占位项照常入列（选中显示该账号错误文字，不拖垮其他账号）
- [x] PL004.3.e settings.py 新增 `quota_account: str = ""` 字段三件套（dataclass 字段/to_dict/from_raw strip 宽容）；切换回调立即 save_config（失败仅 warning 降级与 E0.3 同式）；启动恢复 blockSignals 包裹
- [x] PL004.3.f 托盘零改动确认：main.py `_on_quota_updated` 取最紧有效账户驱动图标/预警的逻辑不动（只依赖 infos 列表不依赖卡片形态）
- [x] PL004.3.g 数据层零改动确认：fetch_go_quota 全量轮询返回 list 不动（60s 节流/in-flight 去重/缓存兜底/占位错误项原样）——切换选择零延迟的数据基础
- [x] PL004.3.h 探针验证：切换下拉 → 渲染项变化 + quota_account 落盘 + 重启恢复 + 失配回落路径断言

### PL004.4 清理与兼容性（残留物物理删除）

- [x] PL004.4.a config/user_config.json：物理删除 `"account_filter": "..."` 行（不留死键等运行时无视）
- [x] PL004.4.b data/credentials/switch_log.json：文件直接删除（gitignore 内纯死数据，无代码再读写）
- [x] PL004.4.c 凭据文件数组格式与追加式保存确认保留不动（go_quota.save_dashboard_credentials 同 workspaceId 覆盖/异账号追加——选择器的数据基础，已拍板第 3 条）
- [x] PL004.4.d 兼容实证：带旧残留键的临时 user_config 跑一次 offscreen init（from_raw 逐键 raw.get() 天然容忍未知键，启动无错且其余配置正常生效）

### PL004.5 回归脚本清理与新验收

- [x] PL004.5.a 必删：`.temp/verify_pl001_accept.py` + `.temp/probe_pl001_*` 系列（锚定被删代码必 FAIL）
- [x] PL004.5.b 逐一排查清理其他引用 intervals/account_filter/switch_log 的探针与验收脚本
- [x] PL004.5.c `.temp/verify_5a3.py` 白名单移除失效条目（"保存账户过滤配置失败"等锚定点）；`.temp/run_all_verify.py` 清单同步移除已删脚本
- [x] PL004.5.d 新建 `.temp/verify_pl004_accept.py` 反向断言：credential_store 无 switch_log 四函数/opencode_usage 各查询无 intervals 参数/exporter 无 account 标注/main_window 无 `_account_combo`/quota_account 切换持久化回环/单卡按选中 workspace_id 渲染/user_config 残留键已物理清除
- [x] PL004.5.e 验证：run_all_verify.py 全量回归 0 异常 + IMPORT OK + offscreen 冒烟

### PL004.6 文档同步与版本推进

- [x] PL004.6.a README 分账号用量章节改写为"配额账户切换"说明（选谁看谁 + 凭据引导入口指引）
- [x] PL004.6.b z.plan.md 本章节状态更新为已实施；y.problem.md 如有 PL001 关联条目同步标注退役
- [x] PL004.6.c x.progress.md 本清单逐项勾选附日期与验证结果
- [x] PL004.6.d 版本推进 ver 0.240 三处同步：base.json version 字段 + README 徽章 + x.progress 当前版本行
- [x] PL004.6.e commit 草稿按 V2 规范给出（git add 清单 + message），由用户审阅执行

## PL005 配额区"添加账户"常驻入口（依据 z.plan.md PL005 方案，2026-08-23 规划）

> 目标：已有有效凭据时提供随时可点的"添加账户"入口（现状引导卡仅在凭据全失效时显示，引入新账户无 UI 途径）
> 已拍板：入口放配额区选择器旁常驻按钮 + QMenu 两路径复用既有引导流程；托盘零改动；添加后自动选中新账户
> 硬限制：引导流程三件套（CDP 任务/手动对话框/并发防护）全部复用不建平行流程；\_on_guide_failed 显示条件修正必须与 show_guide 同源逻辑防双路径漂移
> 版本归属：独立 **ver 0.241**（2026-08-23 用户定版，不并入 ver 0.240）
> 完成情况：✅ 全部实施完成（2026-08-23）——probe_pl005_entry 10/10 PASS（幂等自清理）、全量回归 0 异常、IMPORT OK、凭据文件测后还原

### PL005.1 入口按钮与菜单

- [x] PL005.1.a config/static/ui.json 新键 `quota_add_account_button`（"添加账户"）；ui/main_window.py 常量解包（QUOTA_ADD_ACCOUNT_BUTTON）（2026-08-23 完成）
- [x] PL005.1.b `_build_quota_section` 选择器行尾加 QPushButton；点击弹 QMenu 两项（文案复用 GUIDE_AUTO_BUTTON/GUIDE_MANUAL_BUTTON 不新增重复键）；动作分别路由 `_start_cdp_guide`/`_manual_guide`（2026-08-23 完成）
- [x] PL005.1.c 复用确认：A0.6/A0.7 引导并发防护标志与按钮禁用逻辑对配额区入口同样生效（同一 `_guide_active` 状态）（2026-08-23 完成）

### PL005.2 复用适配与添加后闭环

- [x] PL005.2.a **关键修复**：`_on_guide_failed` 无条件 `self._guide_frame.show()`——已有有效凭据时从配额区触发失败会把引导卡弹出（语义混乱）；提取 `_should_show_guide()` 私有方法（与 `_on_quota_ready.show_guide` 同源单点维护），failed 回调改按条件显示（2026-08-23 完成）
- [x] PL005.2.b `_start_cdp_guide` 从非引导卡上下文触发适配确认（`_guide_frame.hide()` 幂等无害；定时刷新暂停/恢复不变）（2026-08-23 完成）
- [x] PL005.2.c 手动填写路径确认保存后已调 refresh（现实现 L1149 ✅ 原样复用）（2026-08-23 完成）
- [x] PL005.2.d 添加后自动选中：一次性 pending 标志 `_pending_quota_account`；手动路径直接携带 workspace_id；CDP 路径改 `_CdpGuideSignals.success` 信号签名携带 workspace_id（带默认值向后兼容）；`_render_quota` 重建选项后优先匹配 pending 选中并清除（失配静默丢弃回落既有逻辑）（2026-08-23 完成）

### PL005.3 验证与收尾

- [x] PL005.3.a 探针 probe_pl005_entry.py：按钮存在 + QMenu 两动作路由正确（offscreen 触发不崩）；手动路径 mock QInputDialog → 凭据数组追加（真实 save_dashboard_credentials 落盘验证）+ refresh 触发 + pending 自动选中生效（2026-08-23 完成：10/10 PASS，唯一 ID 幂等 + 测后自清理还原凭据文件）
- [x] PL005.3.b 全量回归 run_all_verify 0 异常 + IMPORT OK + offscreen 冒烟 + --version 单一来源（2026-08-23 完成）
- [x] PL005.3.c README 配额账户章节补"添加账户入口"说明；x.progress.md 本清单勾选附验证结果（2026-08-23 完成）
- [x] PL005.3.d 版本归属定案 ver 0.241 三处同步（base.json/README 徽章/x.progress 版本行）+ V2 规范 commit 草稿给出（2026-08-23 完成）

## K. 第16轮审计修复任务清单（依据 z.plan.md 附录 A016，2026-08-23 规划）

> 范围：P 级 19 条（高 3/中 8/低 8）；观察项 26 条经用户复核全部维持豁免
> 硬限制：只修 A016 清单条目；高严重度三条先行；每批完成后跑反向验收再全量回归

### K0 P0 正确性（高严重度 3 条）

- [x] K0.1 main_window.py:1310-1312 `_render_quota_card` 的 `quota_chunk_color(percent)` 补第二参 `self._theme_name`（2026-08-23 完成：探针 console 主题断言样式随主题）
- [x] K0.2 main_window.py:807-813 添加账户菜单重入防护——`_start_cdp_guide` 与 `_manual_guide` 入口均加 `if self._guide_active: return` 早退（2026-08-23 完成：假池断言零任务提交+定时器不停）
- [x] K0.3 main_window.py:1264 `_rebuild_quota_account_combo` 改为当前选中在 infos 则保持不动、失配才回落持久化值/首项；连带修正 clear 前读 currentData 顺序（2026-08-23 完成：模拟"持久化 A→会话内切 B→重建"断言不被打回）

### K1 P1 数据与防御一致性（中 5 条）

- [x] K1.1 opencode_data.py:249-250 失败快照不覆盖成功缓存——has_data 实质数据守卫（model_blocks/daily_usage/releases 任一非空才写缓存），失败且有旧缓存时返回 `_mark_cached` 标注副本；同步修正 :226 注释（2026-08-23 完成：探针断言旧快照保留+is_cached）
- [x] K1.2 go_quota.py:408-418 in-flight 分支返回全集——遍历 `_last_quotas` 逐条 `_mark_cached` 标注副本（空列表维持单占位），与节流分支行为对齐（2026-08-23 完成：预置两条缓存断言返回 2 条均 is_cached）
- [x] K1.3 browser_creds.py:509,518 CDP 响应 isinstance 校验——cookie_response/url_response 非 dict 时 warning+宽容返回 (None, None)，校验先于 .get() 消费（2026-08-23 完成：mock list 响应断言不抛 AttributeError）
- [x] K1.4 opencode_data.py:361 RSS `published_at` 补 `or ""` 兜底（对齐 title/content 同函数内写法）（2026-08-23 完成：空 updated 元素探针断言为空串）
- [x] K1.5 选择器 userData 错位修复：渲染目标改按 combo 当前索引取（_render_quota 用 infos[idx]、切换回调用 cached[index]，combo 顺序==infos 顺序），同 workspace 双 cookie 按索引区分不再恒匹配首项；持久化语义不变（2026-08-23 完成：双 cookie 探针断言切到失效项渲染其错误态且选择保持 index1）

### K2 P2 配置化（中 3 条）

- [x] K2.1 static_config.py `_NUMERIC_BASE_KEYS` 补 `data_fetch_interval_sec`（data_cache_ttl_sec 随 K2.3 删键不入白名单）；说明区计数 25→26 键——验证：verify 反向断言 base.json 数值键集与白名单差集为空 + bool 伪装导入抛 RuntimeError（2026-08-23 完成）
- [x] K2.2 opencode_data.py 三处删 `timeout=15` 实参走 network 层 http_timeout 配置回退——验证：grep timeout=数字零残留 + mock 断言 http_get 实收 timeout=None 走默认（2026-08-23 完成）
- [x] K2.3 CACHE_TTL 死键采纳删除路线：删 opencode_data 常量 + base.json `data_cache_ttl_sec` 键 + 说明区两处条目（当前无陈旧度需求，KISS）——验证：定义零残留 + 配置加载正常无副作用（2026-08-23 完成）

### K3 P3 清理与文档（低 8 条）

- [x] K3.1 main_window.py 删 `_quota_frame`/`_quota_status`/`_quota_reset` 三孤儿属性；注释改如实描述；`_build_quota_card` 去返回值——验证：grep 零引用 + IMPORT OK；连带更新 .temp 五个历史 verify 脚本的属性访问为 dict 式（2026-08-23 完成）
- [x] K3.2 opencode_data.py 删 DataPageError 死类——验证：AST 类名零残留 + IMPORT OK（2026-08-23 完成）
- [x] K3.3 opencode_data.py 两处函数内 import（json/xml.etree）提到模块顶部——验证：AST 扫描 FunctionDef 子节点零 Import（2026-08-23 完成）
- [x] K3.4 PL004 死注释清理：go_quota "附指纹"→"附账户标注"；opencode_usage 删"，含账户时段过滤 PL001.4"——验证：grep 两短语零残留（2026-08-23 完成）
- [x] K3.5 说明区四处同步：opencode_data 重写（函数名修正+九缺列函数补齐+DataPageError 条目移除+悬空括号修复）；go_quota `_last_quotas` 复数+fetch 多账户描述；pricing 补 PRICE_KEY_MAP 条目；main.py `_on_quota_updated` 多账户口径——验证：verify_k3_accept 说明区符号名真实性断言（2026-08-23 完成）
- [x] K3.6 main_window.py 说明区重写：PIE_COLOR_*_DEFAULT 改名同步；_build_ui 页签装配现状；单卡渲染/选择器/添加账户/guide 条件五处失实更新；补 13 个缺失函数条目（2026-08-23 完成）
- [x] K3.7 x.progress.md:4 版本行 ver 0.240 → ver 0.241——验证：三处字面值一致断言 PASS（2026-08-23 完成）
- [x] K3.8 MW-6 连带确认：K1.5 索引化渲染已覆盖错位场景；ui.json/base.json 键集契约由 _UI_STRUCT_KEYS 与 K2.1 白名单机械比对兜底（2026-08-23 完成）

### K4 验证与收尾

- [x] K4.1 新建 .temp/verify_k_accept.py 汇总反向验收：串联 K0-K3 七个子脚本（探针+验收成对）统一出口——验证：7/7 PASS（2026-08-23 完成）
- [x] K4.2 全量回归 run_all_verify 0 异常 + IMPORT OK + offscreen 冒烟 + --version 单一来源 ver 0.242（2026-08-23 完成）
- [x] K4.3 版本推进 ver 0.242 三处同步（base.json/README 徽章/x.progress 版本行，按审计修复第三位数字惯例）+ V2 规范 commit 草稿给出（2026-08-23 完成）

## L. 第17轮审计修复任务清单（依据 z.plan.md 附录 A017，2026-08-23 规划）

> 范围：P 级 16 条（中 1 / 低 15，无高）；观察项 18 条经用户复核全部维持豁免
> 重点：中级别饼图弧色需用户先裁定意图方向；多条为 A016/K 系列修复的边界补全
> 硬限制：只修 A017 清单条目；每批完成后跑反向验收再全量回归

### L0 展示语义裁定与修复（中 1 条，已裁定方案 A）

- [x] L0.1 饼图弧色分级色改造（**已裁定方案 A，2026-08-23 用户确认**）：_RemainingPieChart 增加 theme 名持有（构造/set_colors 联动更新）+ set_used_percent 内按 `quota_chunk_color(percent, theme)` 联动重算弧色（<60% 绿/60-80% 黄/≥80% 红三档与进度条一致）；两处矛盾注释统一为"分级色圆弧"——验证：探针断言 panel 主题下 usage=90 时弧色==quota_chunk_color(90,"panel")=#a03030 且 ≠ quota_chunk_color(90)（2026-08-24 完成）

### L1 数据与交互一致性（低 8 条）

- [x] L1.1 K0.2 补全：main_window.py `_start_cdp_guide` 早退分支补状态栏提示（复用 ui.json in_flight 文案）+ 新增 `_set_guide_actions_enabled` 随引导态启停菜单动作（_start_cdp_guide 禁用 / _on_guide_success+failed 恢复）（2026-08-24 完成：假池断言动作禁用+提示出现+零重复提交）
- [x] L1.2 K0.3 回落换源：main_window.py `_rebuild_quota_account_combo` 回落分支 `self._config.quota_account` → `load_config().quota_account`（与切换回调同源）——验证：结构断言；行为层面两实现等价（磁盘值恒跟随会话选择），探针以合法落定项断言（2026-08-24 完成）
- [x] L1.3 G1 失败占位入缓存：go_quota.py fetch 循环 except 分支将占位错误项同步 append 进 `_last_quotas`（成功项照旧）——in-flight/节流期全集不再丢失败项——验证：探针一好一坏 mock 断言缓存含 2 条且坏项带 error（2026-08-24 完成）
- [x] L1.4 K1.1 粒度声明：opencode_data.py 守卫注释补"单源失败空覆盖属已知取舍（per-source 合并待后续评估）"（2026-08-24 完成）
- [x] L1.5 B1 深度校验：browser_creds.py 取值改 `(resp.get("result") or {})` 式 + cookie 循环 isinstance(cookie, dict) 过滤——验证：探针 result=null 响应断言不抛 AttributeError 返回 (None, None)（2026-08-24 完成）
- [x] L1.6 O2 JSON null 兜底：opencode_data.py releases JSON 路径 tag_name/published_at/body 改 `(x or "")` 兜底显式 null（对齐 RSS 口径）——验证：探针 null 字段断言空串非 "None"（2026-08-24 完成）
- [x] L1.7 G2 并发收敛：go_quota.py 新增 `_FETCH_STATE_LOCK = threading.Lock()` 护 in-flight check-set 与 finally 复位路径（网络 IO 不持锁保持即时返回语义）——验证：源码结构断言 + 行为 smoke（2026-08-24 完成）
- [x] L1.8 error_stage 对齐：go_quota.py in-flight 全集副本删 error_stage 赋值行（对齐节流分支不设语义；ui 引导判断依赖 is_cached 已排除不受影响）——验证：结构断言 in-flight 段零 error_stage（2026-08-24 完成）

### L2 配置卫生（低 1 条）

- [x] L2.1 theme 死键双侧删除：ui.json button_labels 删 `"theme": "主题"` 行 + main_window.py _UI_STRUCT_KEYS 的 button_labels 元组同步删 `"theme"`——验证：verify 断言 ui.json 无该键且 IMPORT OK 契约通过（2026-08-24 完成）

### L3 清理与文档（低 6 条）

- [x] L3.1 注释失实修正：main_window.py `_render_quota` 函数头注释按 K0.3 现状重写（"失配回落持久化值，仍失配保持首项（不保证有效性）"）（2026-08-24 完成）
- [x] L3.2 说明区补条目：main_window.py 类型清单补 _DataSignals/_DataPageTask 两行；常量清单补 USAGE_TAB_TITLE/DATA_PAGE_ERROR_TEMPLATE/THEME_LABELS/QUOTA_ACCOUNT_LABEL/QUOTA_ACCOUNT_UNKNOWN/QUOTA_ADD_ACCOUNT_BUTTON 六键——验证：说明区提及符号 grep 全存在（2026-08-24 完成）
- [x] L3.3 pending 冗余补发：main_window.py _on_load_error seq 匹配分支追加 self._consume_pending()——验证：结构断言 error 路径消费 pending（2026-08-24 完成）
- [x] L3.4 README 配置表同步：ver 快照删除/table_headers→data_table_headers/删 notify_message_fallback 行/palettes 描述更新为四主题/base.json 表补列 data_fetch_interval_sec/data_url/gh_releases_api_url/gh_releases_rss_url 四键（2026-08-24 完成）
- [x] L3.5 符号名修正：opencode_data.py 说明区 _R_BLOCK_PATTERN → _R_OBJECT_PATTERN（2026-08-24 完成）
- [x] L3.6 关联配置补列：opencode_usage.py 说明区补 base.json（db_default_path/table_limit_group/table_limit_day/subprocess_timeout/retry_count/retry_delay）与 ui.json（unknown_label）键列（2026-08-24 完成）

### L4 验证与收尾

- [x] L4.1 新建 .temp/verify_l_accept.py 反向验收 20 断言（L0.1 分级色/L1 组七项结构+行为/L2.1 双侧删除/L3 组五项）（2026-08-24 完成：20/20 PASS）
- [x] L4.2 全量回归 run_all_verify 0 异常 + IMPORT OK + offscreen 冒烟 + --version 单一来源；连带更新 verify_k0_accept/verify_k1_accept/verify_5a3 三处过时断言适配 L 系列新结构（2026-08-24 完成）
- [x] L4.3 版本推进三处同步（base.json/README 徽章/x.progress 版本行）+ **2026-08-24 起启用四段式版本号规则 V0.2.4.3 形式（用户指定）** + V2 规范 commit 草稿给出（2026-08-24 完成）

## PL006 前后端接口层：AppService 门面 + 统一任务运行器（依据 z.plan.md PL006 方案，2026-08-24 规划）

> 目标：建立 services/service.py 门面与 ui/task_runner.py 异步设施，main_window 与 modules 解耦——UI 只 import services 不再直接触碰任何 modules 符号；前端可整体替换而后端不动
> 现状诊断：点对点直连——直接 import 五个 modules 的 8 类符号 + 自建 5 个 QRunnable 任务类 + 4 组 Signals 承载编排
> 三条纪律：Service 纯 Python 零 Qt / DTO 第一版直接透传 modules dataclass（独立 DTO 留待 QML 迁移）/ UI 只 import services
> 归属判定规则：替换前端时必然重写 = 归 ui/（TaskRunner）；可原样带走 = 归 services/（AppService）。多前端并存（ui/qt6 与 ui/qml 并列+main.py --frontend 分发）为远期形态，启用第二前端那天才搬迁
> 版本归属：**V0.2.5.1**（2026-08-24 用户定版；四段式第三位=功能批次、第四位=批次内序号）

### PL006.1 services/service.py 门面

- [x] PL006.1.a 新建 services/**init**.py（get_service 单例入口 re-export）与 services/service.py：ServiceError(Exception) 业务错误基类（message 中文）；AppService 类（2026-08-24 完成）
- [x] PL006.1.b resolve_db_path() -> Path | None（find_db_path 包装）与 get_usage(db_path) -> UsageData：内聚 OpenCodeDB 打开/totals/by_* 循环/DIMENSIONS 推导/TABLE_LIMIT 分档/close 全套（原 _UsageTask.run 主体迁入；db_path None 抛 ServiceError）；UsageData dataclass 随迁 services（2026-08-24 完成：探针 ② 真实库等价 PASS）
- [x] PL006.1.c get_quotas() -> list[GoQuotaInfo]（fetch_go_quota 直通）；get_data_page() -> ModelDataSnapshot（refresh_data_page 直通）（2026-08-24 完成）
- [x] PL006.1.d export_data(db_path, out_dir) -> None（OpenCodeDB + export_all + close，原 _ExportTask.run:473-479 主体迁入；db_path None 抛 ServiceError）（2026-08-24 完成：探针 ③ ServiceError 断言）
- [x] PL006.1.e save_account(ws, cookie)（save_dashboard_credentials 包装）；add_account_via_cdp(login_wait_seconds=None) -> tuple[str, str]：CDP 五步编排 + _wait_for_login_cookie 整体迁入，失败抛 ServiceError(中文消息)（2026-08-24 完成：s7/s9 场景全过）
- [x] PL006.1.f 验证：Service 各方法行为等价断言 + 全程零 PyQt6 import 断言（AST 扫描 services/ 目录）（2026-08-25 完成：probe_pl006 ① 零 Qt []）

### PL006.2 ui/task_runner.py Qt 异步设施

- [x] PL006.2.a TaskRunner(QObject)：finished = pyqtSignal(int, object)/failed = pyqtSignal(int, str)；构造注入 QThreadPool——归属 ui/（随前端生灭，内部零业务逻辑）（2026-08-24 完成）
- [x] PL006.2.b run(fn, *, seq)：fn 提交线程池，成功发 finished、异常发 failed(seq, str(exc))；ui.json 文案格式化留在 UI 层 handler（2026-08-24 完成）
- [x] PL006.2.c **实测教训落地**：QRunnable wrapper 在 worker 运行期被 GC 触发 0xC0000409 崩溃——_live_tasks 持执行中引用 + _done_tasks deque(maxlen=16) 保完成引用防悬空；setAutoDelete(False) 由 Python 全权管理生命周期——验证：最小 TaskRunner 用例 + s4/s7/s9 全链路零崩溃（2026-08-25 完成）

### PL006.3 main_window 切换调用

- [x] PL006.3.a 删四个数据任务类（_UsageTask/_QuotaTask/_DataPageTask/_ExportTask）与对应 Signals，改 TaskRunner.run(service...)：usage_ready/quota_ready/data_ready 由 finished(object) 载荷区分，handler 逻辑不变；error/failed 由 failed 承载（2026-08-24 完成）
- [x] PL006.3.b _CdpGuideTask 删除改 TaskRunner.run(lambda: service.add_account_via_cdp(...))：success/failed 双语义由 on_done(结果元组)/on_error 回调承载（workspace_id 经结果携带，pending 逻辑不变）（2026-08-24 完成）
- [x] PL006.3.c import 区收敛：删全部 from modules... 编排行仅保留 DTO 类型注解用途 import 与 from services / from ui.task_runner；CDP 四常量随编排迁 services；MainWindow 可注入性保留（2026-08-24 完成：probe_pl006 ⑤ 八个编排符号零残留）
- [x] L3.3 同步核对：_on_load_error 的 _consume_pending 在新信号体系下语义保持（2026-08-24 完成：verify_f_accept 补发断言适配 PASS）
- [x] PL006.3.d 验证：offscreen GUI 冒烟全流程 + 全量回归 usage/export 相关历史脚本全部适配通过（s4/s7/s9/v0809/v1010/5a2/f/g/h）（2026-08-25 完成）

### PL006.4 验证与收尾

- [x] PL006.4.a 新建 .temp/verify_pl006_accept.py 反向验收：services/ 目录零 Qt 断言（AST 扫描）/行为等价/runner 双路径/UI 零 modules import（2026-08-24 完成）
- [x] PL006.4.b 全量回归 0 异常 + IMPORT OK + offscreen 冒烟 + --version；run_all_verify 超时放宽 120→300 秒（批量环境 CDP mock 场景偶超旧阈值）（2026-08-25 完成）
- [x] PL006.4.c README 项目结构段补 services/ 与 ui/task_runner 说明（L141/L151）+ x.progress 勾选 + commit 草稿 V0.2.5.1 已给出（2026-08-24 完成；仅本条自身勾选拖延至确认时补记）ss 勾选 + commit 草稿

## PL007 主题资源文件夹化：theme 与代码彻底解耦（依据 z.plan.md PL007 方案，2026-08-24 规划）

> 目标：主题作为纯声明式资源管理于 ui/themes/ 文件夹（theme.json 纯数据 + base.qss 共享模板），不含任何 Python；新增主题 = 新建文件夹不改任何 .py
> 现状诊断：颜色已外置 ui.json palettes 但两处耦合残留——QSS 模板是 themes.py 的 Python 字符串常量；主题资产分散三处（themes.py 模板/ui.json palettes/ui.json theme_labels）
> 硬限制：themes.py 与 themes/ 不能同名共存（Python 硬约束）→ 加载器改 theme_loader.py + themes/ 纯资源文件夹（零 .py）；消费方 import 一次性替换 from ui.theme_loader
> 版本归属：**V0.2.5.2**（2026-08-24 用户定版；与 PL006 的 V0.2.5.1 同属 V0.2.5.x 功能批次）

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
