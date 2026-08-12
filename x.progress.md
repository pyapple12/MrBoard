# 开发进度追踪（x.progress.md）

> 依据：`z.plan.md`（myboard 方案报告）
> 当前版本：ver 0.13（VERSION 单一来源在 config/static/base.json 的 version 字段）
> 记录格式：状态 [⏳ 待开发, ✅ 已完成] / 优先级 [高, 中, 低]
> 执行原则：每阶段完成后运行验证命令确认无回归，再进入下一阶段
> 错误策略：各模块开发时落实 z.plan.md 第四章约定（统一错误类型/降级不中断/缓存兜底/宽容解析/节流去重/保留旧数据/只读防误写）

---

## S1-S6 完成记录（简化）

> 结果：S1-S6 全量回归 195 项断言通过（verify_s1:17 / s2:30 / s3:39 / s4:29 / s5:29 / s6:33 / s7:18）

包结构（modules/config/ui/utils/data）+ AGENTS.md + z.plan.md + git 干净单线历史 + `.venv`（Python 3.14）+ `main.py` 入口；utils 层 logger（双 handler）/file_utils（原子写+缓存单例）/retry（指数退避）。`opencode_usage.py`：三级路径探测、只读连接、json_extract 聚合（兼容新旧格式）、分组、cost 优先 + estimate 回退；`pricing.py`：三级来源（缓存→models.dev→内置）+ 本地覆盖 + 多币种；真实库对照 `opencode stats` 一致。`go_quota.py`：凭据链（env→配置→浏览器）去重首成功、HTML 解析三窗口 + max 最紧、节流 + 缓存兜底 + 四分类错误（注：当时含 auth.json 链路，V0.08 P3 已删）。
GUI：themes 双主题 QSS + 三色分级；main_window 卡片/进度条/表格/后台加载/防双加载/保留旧 view/定时刷新/主题切换；system_tray 状态色图标 + 菜单 + 信号解耦。settings 持久化（宽容解析）；exporter 5 CSV + usage.json（现 6 个）+ GUI 导出；AGENTS.md 错误策略落地；README；closeEvent 托盘常驻。`browser_creds.py`：v10 DPAPI+AES-GCM 离线解密（实测确认 History/Local State 可读、Cookies 独占锁定）；v20 CDP 方案（临时 profile + getAllCookies，Chrome 自行解密跨版本稳定）；凭据引导（卡片 + 一键 CDP 后台全流程 + 手动填写，P4 后改对话框加密）；S6.3 多 provider 评估关闭。

---

## S7 审计整改（依据 z.plan.md 第九章审计结果）

> 目标：修复 4 个真实 bug + 8 个中危 + 消重抽取 + 注释规范定案；全量回归 279 项通过

4 个真实 bug：retry 重试失效（分类错误原样抛交 retry，401/403 不重试）、托盘预警未接线（quota_updated 信号 + main.py 接线）、估算混入范围外消息（_time_clause 复用）、日志目录崩溃（FileHandler 保护）。8 个中危：VERSION 循环依赖（constants.py 持值）、数字强转（新建 utils/convert.py 弹性转换）、QSS 不重算（unpolish/polish）、引导卡片误导（error_stage 分类，CDP 可解决才显示）、浏览器探测冒泡（逐浏览器 try）、CDP 端口抢占检测、死代码接入（v10 预检 + is_chrome_running 日志）。
消重抽取 14 项（flatten_tokens/_TOKEN_SUM_SELECT/write_json 复用/_rate_from_raw/_with_copied_db/fetch_go_quota 与 _build_ui 拆分/_wait_for_login_cookie/themes 模板化/_mark_cached/_local_appdata/阈值常量等）。注释规则定案：函数下 `#` 注释 + 文件尾 `# =====` 说明区，**禁止 docstring 顶替**（verify_s11 AST 检测 + 155 函数整改零残留）。

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

高价值：H1 审计误判证伪保留（`except GoQuotaError: raise` 必要——401/403 分类错误会被外层包装破坏，传播测试证实）；OpenAuth 死条件收敛、不可达 2xx 检查删除；login_wait_seconds 默认 None 走 base.json；refresh 远程失败回退旧缓存；UA 去硬编码；临时目录清理补全；阈值单一来源。中价值：8 处死代码删除；M11 `_status_bar` 结构性整改（状态栏在信号连接区提前创建、导出信号直连、转发方法删除——消除初始化顺序依赖）；一行转发内联；抽取复用（_read_local_state_json/PRAGMA 缓存）；说明区补齐。
低价值：行宽/魔法数字/冗余清理；THEMES 单一来源；映射缺键抛 RuntimeError；base.json +8 参数（table_limit_group/day、cdp_fetch/wait_timeout、http_timeout、app_name、log_level）+ ui.json 饼图参数；托盘图标几何按比例。版本 ver 0.10。

---

## 第三轮审计整改（依据 z.plan.md 第十三章，2026-08-11 规划）

> 目标：57 条发现按三批整改（复用 15 → 小错误/边界 9 → 死代码/硬编码约 25）；全量回归 690 项通过

跨模块复用：新建 utils/network.py（http_get 统一，go_quota 保留 401/403 分类）；read_json/round_cost ×5/常量（SUBPROCESS_TIMEOUT/RETRY_NETWORK_ERRORS/OAUTH_REDIRECT_MARKER/凭据键/APP_NAME）收敛；公开入口去下划线；CSV 列名推导；_by_field 抽取。小错误/边界：bool 语义对齐、min_ts=0 纪元边界、cost_source 修正、CLI 坏库中文提示、映射值类型校验。清理：死代码删除、_load_rate_items 合并、过期缓存回退旧缓存、参数/文案外置（db_default_path/notify/布局/色值）；BUNDLED_PRICES 评估**保留**（离线兜底有意设计）；3A.4 收尾（版本 ver 0.11 与第四轮一并实施）。

---

## 第四轮审计整改（2026-08-12 规划）

> 目标：47 条发现按三批整改（错漏 11 → 重复实现 5 → 清理/规范约 20）；全量回归 788 项通过；版本 ver 0.11

错漏：exporter CSV 计数修正、缓存毒化修复（解析失败不写缓存）+ unlink 竞态、sqlite URI 转义两处、parse_time_arg strip 统一、show_guide 永真精简、v20 提示每会话一次、CDP 响应结构校验、to_optional_float bool 排除。重复实现：APP_NAME 单一来源（utils.logger 导出）、新建 utils/windows.py（win32crypt 降级 + WIN32CRYPT_AVAILABLE + DPAPI 三处收敛）、凭据去重键共享、文案与 24 色调色板外置 ui.json（S8.3 颜色外置补齐）。
清理/规范：rows 伪维度删除、闭包参数化提取（3 查询函数 + *query_args 透传，AST 确认无嵌套 def）、limit 常量收敛、THEMES 外置、hidden_columns strip、防御补强（mapping 非 dict/retry assert）、说明区补齐、审计报告入 z.plan 第十四章。

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

### 6A.1 第一批：错漏（7 条）

- [x] E1 themes {chunk_ok} 占位符残留：QSS 模板注入无效值——移除模板占位或调色板补键（行为验证：apply 后无无效规则）
- [x] E2 convert.to_int 补 OverflowError 捕获（"inf"/"1e999" 崩溃逃逸，行为验证）
- [x] E3 browser_creds CDP 探测族走 base.json：CDP_HTTP_TIMEOUT/CDP_WAIT 复用 cdp_fetch_timeout/cdp_wait_timeout，说明区修正
- [x] E4 launch_chrome_debug 提前 return 前清理临时 profile（mkdtemp 后失败路径 rmtree）
- [x] E5 parse_time_arg 注释/help 与正则一致（支持 m 或注明）
- [x] E6 find_db_path CLI 分支失败补 warning（与 env 分支一致）
- [x] E7 network.py 说明区与 timeout 默认值一致（注明 15.0 兜底语义）
- 状态：✅ 完成（2026-08-13，验证：verify_6a1 27 项 + 全回归 verify_5a1/5a2/5a3/s11 + GUI offscreen；同步 verify_5a3 常量名断言）｜优先级：高

### 6A.2 第二批：防御性（6 条）

- [x] D1 by_session _has_session_columns 补 id 列校验（缺列时降级 session_id 不 JOIN）
- [x] D2 system_tray QMenu 防 GC：QSystemTrayIcon 非 QWidget 不能挂父——菜单存实例属性 `self._menu`（setContextMenu 不接管所有权）
- [x] D3 settings refresh_interval_ms 加最小下限（如 >= 1000ms，防手改 1ms 疯狂刷新）
- [x] D4 logger _configured 竞态防护（锁或幂等重入检查）
- [x] D5 retry retries<0/delay<0 参数校验（clamp 或 ValueError）
- [x] D6 credential_store 缺文件 WARNING 降级 DEBUG（无凭据用户常态噪音）
- 状态：✅ 完成（2026-08-13，验证：verify_6a2 18 项 + 全回归 verify_6a1 27/s5a3 26/s11 4 + GUI offscreen）｜优先级：高

### 6A.3 第三批：硬编码/清理（13 条）

- [x] H1 pricing round(cost, 10) 魔法 10 命名常量（如 COST_COMPARE_DIGITS，说明用途）
- [x] H2 UNKNOWN_LABEL = "未知" 外置 ui.json
- [x] H3 go_quota 凭据缺失提示文案外置 ui.json
- [x] H4 windows DPAPI_DESCRIPTION 改从 base.json app_name 派生（消除双源）
- [x] H5 main_window 0.00005 容差命名常量或外置
- [x] H6 "亿"/1e8 与 %H:%M:%S 格式收敛（RESET_TIME_FORMAT 同源）
- [x] H7 main_window 任务错误文案 4 处评估外置（上轮争议项，决策后执行）
- [x] U1-U5 未用 import 删除：settings Path、opencode_usage to_float、pricing Path、logger Path、network Any
- 状态：✅ 完成（2026-08-13，验证：verify_6a3 32 项 + 全回归 verify_6a1 27/6a2 18/5a3 26/s11 4 + GUI offscreen）｜优先级：中

### 6A.4 第四批：重复/优化（10 条）

- [x] R1 sqlite 只读 URI 连接构造提 utils 公共函数（opencode_usage/browser_creds 两处收敛）
- [x] R2 main_window 配额窗口键引用 go_quota.QUOTA_WINDOW_KEYS（507/749-751）
- [x] R3 主题名双源决策：DARK_THEME_NAME/LIGHT_THEME_NAME 单一来源（settings 校验引用或反向）
- [x] R4 窗口标题/tooltip 拼接统一（VERSION 段一致性决策）
- [x] O1 opencode_usage _base_sql 与 totals 共用 time_clause 生成
- [x] O2 pricing estimate_cost 四段重复抽取公共小函数
- [x] O3 main_window 缓存率复合函数（_format_cache_rate(_cache_rate_percent) 3 处）
- [x] O4 main.py 配额预警去重（已通知标志，持续超限不重复弹）
- [x] O5 logger 文件日志轮转（RotatingFileHandler）
- [x] O6 to_float/to_optional_float 合并评估（动调用方，收益存疑——评估后决策）
- 状态：✅ 完成（2026-08-13，验证：verify_6a4 30 项 + 全回归 verify_6a1-3/s12/s5a2/s5a3/s11 + GUI offscreen；同步 verify_5a2 tooltip 断言）｜优先级：低

### 确认保留

> go_quota add 闭包（第五轮确认项）；network RETRY_NETWORK_ERRORS 含 URLError 为有意设计（5xx/429 重试，401/403 已分类）——不整改

## 阶段验证命令速查（AGENTS.md 运行与验证）

```powershell
# 导入验证（全量 18 个模块）
.\.venv\Scripts\python.exe -c "import main, modules.opencode_usage, modules.go_quota, modules.pricing, modules.exporter, modules.browser_creds, modules.credential_store, config.settings, config.static.static_config, ui.main_window, ui.system_tray, ui.themes, utils.logger, utils.file_utils, utils.retry, utils.convert, utils.network, utils.windows"

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
```
