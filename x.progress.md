# 开发进度追踪（x.progress.md）

> 依据：`z.plan.md`（myboard 方案报告）
> 当前版本：ver 0.15（VERSION 单一来源在 config/static/base.json 的 version 字段）
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
