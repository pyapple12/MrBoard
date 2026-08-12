# 开发进度追踪（x.progress.md）

> 依据：`z.plan.md`（myboard 方案报告）
> 当前版本：ver 0.10（VERSION 单一来源在 config/static/base.json 的 version 字段）
> 记录格式：状态 [⏳ 待开发, ✅ 已完成] / 优先级 [高, 中, 低]
> 执行原则：每阶段完成后运行验证命令确认无回归，再进入下一阶段
> 错误策略：各模块开发时落实 z.plan.md 第四章约定（统一错误类型/降级不中断/缓存兜底/宽容解析/节流去重/保留旧数据/只读防误写）

---

## S1-S6 完成记录（简化）

### S1 骨架搭建 ✅

包结构（modules/config/ui/utils/data）+ AGENTS.md + z.plan.md + git 仓库（干净单线历史）+ `.venv`（Python 3.14）+ `main.py` 入口 + `utils/logger.py`（双 handler）/`file_utils.py`（原子写+缓存单例）/`retry.py`（指数退避重试）。验证：17 项断言通过。

### S2 用量统计模块 ✅

`modules/opencode_usage.py`：三级路径探测、只读连接（mode=ro）、`json_extract` + `COALESCE(SUM)` 聚合（兼容新旧格式混合）、按天/模型/provider/agent 分组、库 cost 优先 + estimate 估算回退、CLI 自测。`modules/pricing.py`：三级来源合并（缓存 TTL → models.dev → 内置表）+ 本地覆盖打标 + 多币种分桶。真实库对照 `opencode stats` 全口径一致。验证：30 项断言通过。

### S3 Go 配额模块 ✅

`modules/go_quota.py`：dashboard 凭据链（env → 配置文件 → 浏览器）去重首成功返回；dashboard HTML 抓取（实体反转义 + `$R[NN]=` 兼容正则）→ 5h/周/月三窗口 + max 取最紧；60s 节流 + 缓存兜底 + `GoQuotaError` 四分类；窗口缺失容忍。（注：当时含 auth.json/key 校验链路，V0.08 P3 已删除）验证：39 项断言通过。

### S4 GUI 界面 ✅

`ui/themes.py`（LIGHT/DARK QSS + 三色分级）、`ui/main_window.py`（5 卡片 + 配额进度条 + 分组表格 + QThreadPool 后台加载 + 防双加载 + 保留旧 view + 5 分钟定时刷新 + 主题切换）、`ui/system_tray.py`（状态色图标 + 菜单 + 信号解耦）。验证：29 项断言通过 + offscreen GUI init OK。

### S5 完善收尾 ✅

`config/settings.py`（AppConfig 持久化，宽容解析）；`modules/exporter.py`（5 CSV UTF-8 BOM + usage.json，现 6 个——V0.08 增 by_month）+ GUI 导出按钮；AGENTS.md 错误策略章节落地；README；closeEvent 隐藏到托盘常驻。验证：29 项断言通过。

### S6 增强 ✅

`modules/browser_creds.py`：v10 DPAPI+AES-GCM 离线解密（实测确认 History/Local State 可读、Cookies 独占锁定、CDP 流程无需关闭用户浏览器）；v20 走 CDP 方案（独立临时 profile + `Network.getAllCookies`，Chrome 自行解密跨版本稳定）。凭据配置引导：引导卡片 + 一键 CDP 获取（后台线程全流程）+ 手动填写（当时为模板文件方式，V0.08 P4 改为对话框 + 加密写入）。S6.3 多 provider 已评估关闭。验证：verify_s6 33 项 + verify_s7 18 项通过。

### 验证总览

S1-S6 全量回归 **195 项断言全部通过**（verify_s1:17 / verify_s2:30 / verify_s3:39 / verify_s4:29 / verify_s5:29 / verify_s6:33 / verify_s7:18）。

---

## S7 审计整改（依据 z.plan.md 第九章审计结果）

> 目标：修复 4 个真实 bug + 8 个中危问题 + 消重抽取 + 注释规范定案；完成后全量回归

### S7.1 真实 Bug 修复 ✅

B1 retry 重试失效（网络异常转分类导致 retry 匹配不到 → 原样抛出交 retry 重试，401/403 仍分类不可重试）；B2 托盘配额预警未接线（quota_updated 信号 + main.py 接线）；B3 估算混入范围外消息（_time_clause 复用）；B4 日志目录异常崩溃（FileHandler 异常保护 + 删 import 副作用）。验证：verify_s8 通过。

### S7.2 中危问题修复 ✅

M1/M2 VERSION 循环依赖（constants.py 持 VERSION + 顶层 import）；M3 数字强转违反宽容解析（新建 utils/convert.py 弹性转换）；M4 QSS 不重算（unpolish/polish）；M5 引导卡片误导（GoQuotaInfo.error_stage 阶段分类，CDP 可解决才显示）；M6 浏览器探测冒泡（逐浏览器 try）；M7 CDP 端口抢占（启动前占用检测）；M8 死代码接入（v10 预检提示 + is_chrome_running 日志）。验证：verify_s9 通过。

### S7.3 消重与函数抽取 ✅

D1 flatten_tokens / D2 _TOKEN_SUM_SELECT / D3 复用 write_json / D4 _rate_from_raw / D6 _with_copied_db / D7 fetch_go_quota 拆分（_throttled_cache/_fetch_usage_with_fallback/_build_info）/ D8 _build_ui 拆分 / D9 _wait_for_login_cookie / D10 themes 模板化 / D11 _mark_cached / D12 _local_appdata / D13-D14 阈值常量与 system_tray 解包。验证：verify_s10 通过。

### S7.4 规范口径与验证 ✅

注释规则定案：函数下方 `#` 注释（1-3 行）+ 文件尾 `# =====` 说明区，**禁止 docstring 顶替 `#` 注释**（AGENTS.md 修订 + verify_s11 AST 检测 + 全量 155 函数整改零残留）。全量回归 279 项全部通过。

---

## S8 配置层对齐 AccelWorld（json 驱动静态配置）

> 目标：静态配置 json 文件驱动、代码零硬编码；用户配置 dataclass + json 持久化，两类严格分离
> 边界：业务逻辑常量（SQL/正则/维度枚举）不抽，只抽"可调参数"
> 路径决策（用户审核确认，注：凭据/日志位置已被 V0.08 P2 反转——现集中项目内 data/ 下）：当时定用户配置移项目内 `config/user_config.json`；凭据保留 `~/.config/myboard/`；日志保留 `~/.local/share/myboard/`
> 版本决策（用户审核确认）：constants.py 删除，VERSION 移入 base.json（单一来源）；`get_project_root()` 置于 `utils/file_utils.py`

### S8.1-S8.2 静态配置基础设施与应用参数外置 ✅

新建 `config/static/`（config.json 映射表 + static_config.py 加载器 + 缓存单例 + 失败抛 RuntimeError，修复 use_cache 缓存不生效 bug）；base.json 外置窗口/刷新/节流/重试/CDP/导出/定价等 17 处硬编码参数（verify_s12 防回归）。验证：verify_s12 通过。

### S8.3-S8.4 UI 参数外置与用户配置改造 ✅

ui.json 外置配额颜色阈值/托盘图标/表格表头；settings.py 默认值从静态配置现取，用户配置路径移项目内 `config/user_config.json`。验证：verify_s13 通过。

### S8.5 各模块引用改造（顶层一次性解包，运行时零 IO）✅

main_window/go_quota/browser_creds/exporter/pricing/themes/system_tray 全部 `_SC` 解包；**constants.py 删除与 VERSION 迁移**：VERSION 移入 base.json `version` 字段（main.py 与 ui 改从 static_config 读取，连带同步 README/verify_s9/s11/导入命令）。验证：verify_s14 通过。

### S8.6-S8.7 验证与文档同步 ✅

verify_s12 17 项（加载正确性/解包一致/VERSION 单一来源）；全量回归 verify_s1-s14 共 **328 项全部通过** + GUI offscreen OK；AGENTS.md 结构与约定章节重写；README 结构树与配置参数表更新；z.plan.md 第五章结构树同步。

---

## V0.08 P2-P8 整体改造（依据 z.plan.md 第十章）

> 目标：P2-P8 七个问题一次整体改造（凭据/路径治理 + 展示修正 + 月度统计）；决策见 z.plan.md 10.4（D1-D5）；2026-08-10 全部完成

### V0.08.1 P6 移除跨项目凭据路径探测 ✅

`_dashboard_config_paths` 收敛为仅本程序路径（env + 项目内），消除 opencode-bar/opencode-quota 刷新 WARNING 噪音。验证：verify_v0808_p6 9 项 + verify_s3 24 项。

### V0.08.2 P2 配置与数据目录集中到项目内 ✅

凭据/日志/价格缓存移至 `data/` 下（base.json 三 dir 字段驱动），logger 顶层引用静态配置（AGENTS.md 分层放宽）；探测链同步收敛为 env + 项目内（保存→读取闭环）；.gitignore 增加运行数据忽略并清理冲突残留；旧用户目录残留已删除、真实凭据已复制迁移。验证：verify_v0808_p2 14 项 + verify_s12 20 项。

### V0.08.3 P3 删除 API key 链路 ✅

models 接口与 auth.json 读取链（五函数/两常量/两字段/no_key 分支）全部移除，主流程简化为"节流 → 凭据 → 三窗口"（顺带清理死代码）；UI 元信息只留 dashboard 凭据来源；全源码 grep 零残留。验证：verify_v0808_p3 21 项。

### V0.08.4 P4 凭据 DPAPI 加密存储 ✅

新增 `modules/credential_store.py`（`encrypted_v1` 格式 + 明文旧格式兼容读取）；保存路径统一加密写入，win32crypt 缺失拒绝明文落盘；手动填写改 QInputDialog 对话框；真实验证发现并适配 pywin32 两个返回结构怪癖（CryptProtectData 直接返回 bytes、CryptUnprotectData 数据在第二元素）；现有真实凭据已加密迁移。验证：verify_v0808_p4 15 项 + verify_s7 21 项。

### V0.08.5 P5 配额重置时间显示 ✅

`_render_quota` 改为 `%m-%d %H:%M`（"重置于 08-12 06:30"）。验证：verify_v0808_p5 6 项。

### V0.08.6 P7 按日期统计由近到远 ✅

`by_day()` 排序 `label DESC`，GUI/CLI/导出同步。验证：verify_v0808_p7 7 项 + verify_s2 33 项。

### V0.08.7 P8 月度用量统计 ✅

新增 `by_month()`（`%Y-%m` 本地时区分组降序）；GUI 下拉"按月份" / CLI `--by month` / 导出 by_month.csv（6 个 CSV）；真实库验证月份与日期聚合总 token 一致。验证：verify_v0808_p8 17 项。

### V0.08.8 验证与文档收尾 ✅

全量回归 **409 项断言全部通过**（s1-s14 + v0808_p2-p8）+ import/GUI offscreen OK；README/AGENTS.md/z.plan.md/y.problem.md 同步；版本 ver 0.08（`--version` 验证）；凭据迁移与加密完成；提交由用户执行。

---

## V0.08 验证总览（P2-P8 整体改造）

> V0.08 全量回归 **409 项断言全部通过**（verify_s1-s14 基线 328 项含删改后 + verify_v0808_p2-p8 新增 103 项）——2026-08-10 实施完毕
> P2-P8 全部完成：P6 删跨项目探测 → P2 目录集中项目内 → P3 删 API key 链路 → P4 凭据 DPAPI 加密 → P5 重置时间 → P7 日期倒序 → P8 月度统计
> 遗留：P1（多账户区分）、P9（workspace 区分）、P10（二次审计）、P11（明文兼容去留）待评估，见 y.problem.md

---

## V0.09 UI 改版与维护（P12-P19 + P21，2026-08-10 规划）

> 目标：V0.08 人工审核后的一轮 UI 改版——基础修复（时区/元信息/自动更新）+ 卡片区与总览重构 + 明细表格列开关 + 配额饼图 + 会话维度
> 依据：y.problem.md P12-P19、P21（P20 属 V0.11，不在本版本）
> 执行原则：每项完成后运行对应验证；全部完成后全量回归

### V0.09.1 基础修复（P21 时区 / P12 元信息 / P14 自动更新）

- [x] 21.1 `ui/main_window.py` `_render_quota`：reset_date 显示前 `astimezone()` 转本地时区（实测修复前 UTC+8 差 8 小时）
- [x] 21.2 `modules/go_quota.py` CLI `main()`：重置时间同样转本地
- [x] 21.3 `.temp/verify_v0808_p5.py` 断言同步（构造值改 astimezone 动态预期 + 源码防回归检查带 astimezone）
- [x] 21.4 真实验证：UI 显示本地时间 08-10 23:57（reset_date.astimezone()），为未来时间点（修复前 UTC 直出比当前还早 8 小时）
- [x] 12.1 `ui/main_window.py` `_build_quota_section`/`_render_quota`：删除 `_quota_meta` 元信息行（"dashboard 凭据：..."）及创建代码
- [x] 12.2 `.temp/verify_s4.py` "配额元信息含 dashboard 凭据来源"断言删除；`credential_source` 字段保留（日志/排查用）
- [x] 14.1 排查结论：链路正常无 bug——`_refresh_timer`（5 分钟，用户配置 300000ms 已核实）→ `refresh()` → `_UsageTask` → 信号 → 渲染 + 状态栏"用量已更新（时间）"；用户观察"不更新"源于 5 分钟间隔内数据无变化时表格内容不变（状态栏时间戳会变，不易察觉）
- [x] 14.2 链路验证：`.temp/verify_v0809_1.py` 模拟定时触发（refresh 两次），用量渲染 + 状态栏提示正常、表格有数据；定时器间隔断言 300000ms
- 状态：✅ 已完成（2026-08-10）｜优先级：高

### V0.09.2 卡片区与总览改造（P17 + P15）

- [x] 17.1 `_build_cards`：删除"会话"卡片；顺序 总 tokens → 输入 → 输出 → 缓存率 → 总费用（P17）
- [x] 17.2 新增 `_cache_rate_percent`（(缓存读+缓存写)/总 token 百分比）+ `_format_cache_rate`（一位小数百分比，卡片与 P18 表格共用）+ `_format_total_tokens`（千分位 + 亿单位）
- [x] 17.3 `_render_cards` 更新（缓存率百分比格式；费用格式保留）
- [x] 17.4 `.temp/verify_s4.py` 卡片断言重写（新键集合/值/无 sessions/总览按钮）
- [x] 15.1 总览独立显示移至明细旁：`_total_button`（"总 token：12,775（千分位）"，亿单位 `123,456,789（1.23 亿）`）
- [x] 15.2 点击总览弹出总量明细（`_show_total_detail` → QMessageBox：会话/消息/天数/tokens 分解/缓存率/费用）
- [x] 15.3 维度下拉移除 "total"（DIMENSIONS/DIMENSION_LABELS；_UsageTask 的 total 数据保留，弹窗用 summary）
- [x] 15.4 `.temp/verify_s4.py` 维度断言同步（默认维度按月份 + 表格 1 行；失败保留旧卡片改 tokens）
- [x] 检验：`.temp/verify_v0809_2.py` 21 项（缓存率函数/边界、总 token 格式化、卡片键集合、渲染+总览按钮+弹窗内容、维度下拉无总览）
- 状态：✅ 已完成（2026-08-10）｜优先级：高

### V0.09.3 明细表格重构（P13 列顺序+开关 + P18 缓存率列）

- [x] 13.1 `config/static/ui.json` `table_headers` 重构：标签/总 token/调用数/输入/输出/推理/缓存（读+写合并）/缓存率/费用（9 列，P13+P18）
- [x] 13.2 `ui/main_window.py`：新增 `COLUMN_IDS` 列模型（与 TABLE_HEADERS 索引对齐）；`_render_table` 按新列渲染（缓存合并列 = 缓存读+缓存写；缓存率复用 `_cache_rate_percent`）
- [x] 13.3 明细区"设置"按钮 + QMenu 列开关（`_show_columns_menu`/`_on_column_toggle`，勾选=显示/取消=隐藏，`setColumnHidden`）
- [x] 13.4 `config/settings.py` `AppConfig` 增加 `hidden_columns`（tuple，宽容解析）+ to_dict/from_dict；`save_state` 持久化；`__init__` 恢复隐藏列
- [x] 13.5 `.temp/verify_s4.py` 表格断言兼容（列值变化无需改）；`.temp/verify_v0809_3.py` 23 项：列模型对齐、渲染列值（缓存合并 725/缓存率 34.1%）、开关隐藏+持久化+恢复显示、启动恢复隐藏列、设置菜单弹出；**发现并修复测试污染**：窗口 close 触发 save_state 写真实配置——mock 需覆盖窗口全生命周期（真实 user_config.json 已清理）
- [x] 回归：verify_s4 33 项 + s5 29 项 + s13 20 项 + s12 20 项 + s11 4 项 + v0809_1 11 项 + v0809_2 21 项 + 全量 import 全部通过
- 状态：✅ 已完成（2026-08-10）｜优先级：中

### V0.09.4 配额展示改饼图（P16）

> 方案（2026-08-10 与用户讨论定稿）：
>
> - **三个配额进度条（5 小时/每周/每月）与重置时间保持现状不动**
> - **改动点只有一处**：原"最紧窗口 X% / 剩余 Y%"文字位置（配额区标题行右侧）改为小饼图，展示剩余量
> - 饼图 = 已用/剩余双色圆弧 + 中心"剩余 Y%"标注（绿/黄/红分级色，固定小尺寸约 56x56，QPainter 自绘无新依赖）
> - 异常处理：正常 → 饼图显示；缓存/错误 → 饼图隐藏，"让位"给警告文字（原提示逻辑保留）
> - overall 内部计算保留（托盘预警继续用）

- [x] 16.1 新建 `_RemainingPieChart` 控件（QPainter 自绘：浅色底[剩余] + 分级色圆弧[已用] + 中心"剩余 Y%"文字；set_used_percent 0-100 截断，56x56）
- [x] 16.2 `_build_quota_section`：标题行右侧接入饼图（状态标签旁；正常时饼图显示、缓存/错误时饼图隐藏、警告文字在相同区域显示）
- [x] 16.3 `_render_quota`：删除"最紧窗口 X% / 剩余 Y%"文字；正常分支 → `饼图.set_used_percent(overall)` + 状态标签清空；缓存/错误分支 → 饼图隐藏 + 警告文字（is_cached/error 逻辑保留）
- [x] 16.4 三个进度条与重置时间零改动（verify_v0809_4 断言 5h 12%/每周 26%/每月 80% + 重置时间保留确认）
- [x] 16.5 `.temp/verify_s4.py` 配额断言改饼图（可见性/used 80%/状态空）；`.temp/verify_v0809_4.py` 20 项：控件边界截断、正常渲染（进度条零改动）、缓存/错误三态切换（饼图隐藏/恢复）、源码无最紧窗口渲染文案（overall 保留）；`.temp/verify_v0809_1.py` 同步（状态行断言改饼图，P12 遗留冲突）
- 状态：✅ 已完成（2026-08-10）｜优先级：中

### V0.09.5 会话维度统计（P19）

- [x] 19.1 `modules/opencode_usage.py` 新增 `by_session()`（LEFT JOIN session 取 title/directory，label = "标题｜项目目录"，按总 token 降序）；**真实库研究确认**：新版 session 表为结构化列（title/directory 覆盖率 100%，message 全关联）；**容错**：session 表缺 title/directory 列时降级仅显示 session_id（`_has_session_columns` PRAGMA 检测）
- [x] 19.2 CLI：`--by` choices 加 `session`；methods 映射加 `db.by_session`
- [x] 19.3 GUI：DIMENSIONS 加 `"session"`（"按会话"）、_UsageTask rows 加 `db.by_session(limit=50)`
- [x] 19.4 `modules/exporter.py`：datasets 加 `by_session`（`by_session.csv` + usage.json 字段），7 → 8 个 CSV
- [x] 19.5 `.temp/verify_s2.py` 建库 session 表加 directory 列 + by_session 断言（标题｜目录 + 消息数）；`.temp/verify_s5.py` 导出断言同步（8 文件 + usage.json by_session + GUI 线程 8）
- [x] 19.6 `.temp/verify_v0809_5.py` 13 项：跨会话聚合/空 title 降级 session_id/无 session 表容错/CLI `--by session`/GUI 维度/**真实库验证**（标签含｜分隔 + 会话聚合与日期聚合总 token 一致）；修复两处：by_session SQL 拼接语法错误、`_has_session_table` → `_has_session_columns`（旧库 session 表可能缺列）
- [x] 回归：verify_s2 35 项 + s4 35 项 + s5 29 项 + s13 20 项 + s11 4 项 + v0809_1 12 项 + v0809_2 21 项 + v0809_3 23 项 + v0809_4 20 项 + v0808_p8 17 项 + 全量 import 全部通过
- 状态：✅ 已完成（2026-08-10）｜优先级：中

### V0.09.6 验证与文档收尾

- [x] V.1 全量回归：verify_s1-s14 + verify_v0808_p2-p8 + verify_v0809_1-5 共 **506 项断言全部通过**（s1:17 / s2:35 / s3:24 / s4:35 / s5:29 / s6:33 / s7:21 / s8:14 / s9:30 / s10:38 / s11:4 / s12:20 / s13:20 / s14:8 / v0808_p2-p8:89 / v0809_1-5:89）
- [x] V.2 导入验证 + GUI offscreen 初始化 OK + `--version` 输出 ver 0.09
- [x] V.3 README 同步：badge ver 0.09、项目展示表（新卡片 + 剩余量饼图）、特性（会话维度 + 8 CSV）、CLI `--by session`、GUI 操作说明（总量总览按钮/列开关设置/饼图/按会话）、配置参数表版本
- [x] V.4 y.problem.md：P12-P19、P21 移入"✅ 已完成"区（V0.09 小节压缩描述）；待评估区保留 P1/P9/P10/P11/P20
- [x] V.5 z.plan.md：新增第十一章 V0.09 记录 + 头部实施状态更新
- [x] V.6 `config/static/base.json` `version` → `ver 0.09`（`--version` 验证）
- [x] V.7 x.progress.md 完成记录回填（本节 + 验证总览 + 头部版本）
- 状态：✅ 已完成（2026-08-10）｜优先级：高

---

## V0.09 验证总览（P12-P19 + P21 UI 改版）

> V0.09 全量回归 **506 项断言全部通过**（s1-s14 基线 + v0808_p2-p8 89 项 + v0809_1-5 新增 89 项）——2026-08-10 实施完毕
> P12-P19、P21 全部完成：时区修复 → 元信息移除 → 自动更新排查 → 卡片栏重排 → 总览独立 → 列开关 → 饼图 → 会话维度
> 遗留：P1/P9（多账户区分）、P11（明文兼容去留）待评估，P20（模型数据页+社交跟踪）V0.11 实施，见 y.problem.md

---

## V0.10 二次审计整改（依据 z.plan.md 第十二章）

> 目标：P10 二次审计的 59 条发现按三批整改（高价值 10 → 中价值 20 → 低价值 22）；基线回归 506 项
> 执行原则：每项完成后运行对应验证；全部完成后全量回归 + 版本 V0.10

### V0.10.1 第一批：高价值（行为相关）

- [x] H1 go_quota.py:183-184：**审计误判已纠正**——`except GoQuotaError: raise` 并非死代码（`_http_get` 的 401/403 分类错误经 retry_call 传播后会被外层 `except Exception` 包装成 network，破坏 auth 分类）；保留并补充必要性注释（verify_v1010_1 的 auth 传播测试证实）
- [x] H2 go_quota.py:195：OpenAuth 死条件收敛为 `"OpenAuth" in html`（`<title>` 蕴含于前者）
- [x] H3 go_quota.py:254-258：`_add_seconds` 删 if/else 直接返回（naive/aware 语义不变）
- [x] H4 go_quota.py:287-288：`_http_get` 删除不可达的 2xx 检查（urlopen 非 2xx 必抛 HTTPError）
- [x] H5 main_window.py:289-299：`_CdpGuideTask.login_wait_seconds` 默认改 `int | None = None`，统一从 base.json 读（改 json 生效）
- [x] H6 pricing.py:96-109：`load_price_map(refresh=True)` 远程失败回退 TTL 内旧缓存（不再降级内置表）
- [x] H7 pricing.py:282：UA 从 `_SC.base["version"]` 构造（消除 myboard/0.1 硬编码）
- [x] H8 browser_creds.py:231-257：`_safe_copy_db` 失败路径补临时目录清理（success 标志 + finally rmtree）
- [x] H9 main.py:42：预警阈值改用 `QUOTA_DANGER_PERCENT`（ui.json 单一来源）
- [x] H10 settings.py:72：说明区凭据路径更新为项目内 data/credentials/
- [x] 检验：`.temp/verify_v1010_1.py` 24 项（源码核验/行为保持断言：auth 传播、OpenAuth 识别、加秒语义、HTTP 200、默认参数、refresh 缓存兜底、UA、临时目录清理、阈值、说明区）+ 回归 verify_s3 24 项/s8 14 项/s9 30 项/s7 21 项/s5 29 项/s12 20 项/s11 4 项/s2 35 项 + 全量 import 全部通过
- 状态：✅ 已完成（2026-08-10）｜优先级：高

### V0.10.2 第二批：中价值（死代码/冗余/抽取/规范）

- [x] M1 file_utils.py `clear_cache()` 无调用 → 删除（verify_s1 改用 use_cache=False 验证等价能力）
- [x] M2 settings.py `CONFIG_DIR` 无引用 → 删除（verify_s13 同步移除断言）
- [x] M3 retry.py 不可达 raise → 删除（留注释说明不可达）
- [x] M4 main_window.py `REFRESH_INTERVAL_MS` 未使用 → 删除（verify_s12 同步移除）
- [x] M5 main_window.py `_quota_info` 只写不读 → 删除（verify_s4 等待条件改用饼图可见性）
- [x] M6 `_RemainingPieChart.used_percent()` 保留（控件读取接口，verify 脚本使用，标注理由）
- [x] M7 system_tray.py `_quota_status` 只写不读 → 删除（verify_s4/s8 改用 setIcon mock 断言）
- [x] M8 go_quota.py `_throttled_cache` 未用参数 `now` → 删除
- [x] M9 go_quota.py `_read_credentials_json` 一行转发 → 内联 credential_store.read_credentials_file
- [x] M10 pricing.py `json_loads` 一行 → 内联 json.loads(body.decode)
- [x] M11 `_status_bar_show`：**结构性整改完成**——根因是初始化顺序依赖；方案：`_status_bar` 作为窗口基础设施在信号连接区**提前创建**（setStatusBar），导出信号直连 `showMessage`、转发方法删除、`_build_ui` 不再创建状态栏——所有信号连接统一前部，彻底消除"连接必须发生在 _build_ui 之后"的隐式约定（verify_v1010_2 断言同步，回归全绿）
- [x] M12 browser_creds.py：抽 `_read_local_state_json` 收敛 `_load_aes_key`/`has_v20_cookies` 重复（顺带补 UnicodeDecodeError 容错）
- [x] M13 opencode_usage.py `totals()` 的 `_time_clause` 6 次调用 → 开头算一次复用
- [x] M14 `_has_session_columns` PRAGMA 结果实例属性缓存（Mock(wraps) 验证只执行一次）
- [x] M15 exporter.py 维度名用 `datasets.items()` 收敛（CSV 循环 + usage.json 组装）
- [x] M16 browser_creds.py 删 `--restore-last-session`（空 profile 无效）+ 说明区"保留登录态"/9222 修正
- [x] M17 browser_creds.py / credential_store.py：第三方 try-import 移到本地 import 前；`T = TypeVar` 后移
- [x] M18 说明区补齐：opencode_usage（7 聚合入口 + _EPOCH_MS/_TOKEN_SUM_SELECT 等）、go_quota（9 函数 + CREDENTIALS_FILE）、main_window（_RemainingPieChart/COLUMN_IDS/列开关等）、system_tray（常量）
- [x] M19 main_window.py 4 处"调试："注释删除
- [x] M20 browser_creds.py 2 处截断注释补全（has_v20_cookies/launch_chrome_debug）
- [x] 检验：`.temp/verify_v1010_2.py` 32 项（源码核验 + 行为断言 + PRAGMA 缓存计数 + 导出收敛）+ 全量回归（s1-s14 + v1010_1 共 15 脚本全绿）+ import OK
- 状态：✅ 已完成（2026-08-10）｜优先级：中

### V0.10.3 第三批：低价值（行宽/魔法数字/冗余包装）

- [x] L1 行宽 3 处拆分：go_quota `_capture_object_body` 正则拼接、opencode_usage CLI 打印、main_window 重置时间三元（全项目扫描无超 100 行）
- [x] L2 `Path(str(...))` 3 处去冗余：logger / settings / go_quota（`Path / str` 直接拼接）
- [x] L3 file_utils `read_json` 注解改 `Path | str`；L4 说明区补 `_PROJECT_ROOT`；L5 缓存写入收敛为单处（read_json 先算值统一写缓存）
- [x] L6 主题枚举单一来源：settings 定义 `THEMES = ("light", "dark")`，themes.get_theme 引用（消除两处定义不同步）
- [x] L7 static_config 映射缺 base/ui 键抛 RuntimeError（对齐文件缺失的失败策略，不再静默兜底）
- [x] L8 base.json 新增 `table_limit_group`(50)/`table_limit_day`(200)，_UsageTask 接入
- [x] L9 ui.json 新增饼图参数（pie_size/pie_font_size/colors.quota_pie_bg/quota_pie_text），_RemainingPieChart 接入
- [x] L10 base.json 新增 `cdp_fetch_timeout`(10)/`cdp_wait_timeout`(30)，CDP 调用接入
- [x] L11 system_tray `_build_icon` 几何按 ICON_SIZE 比例（margin=//16、圆点=//8，改尺寸不畸变）
- [x] L12 opencode_usage 新增 `_DAY_MS` 常量 + SQL 复用 `_EPOCH_MS`（消除字面 86400_000/1000）
- [x] L13 base.json 新增 `http_timeout`(15)，三模块统一（go_quota._http_get/pricing._http_get/opencode_usage 子进程）
- [x] L14 exporter 删除 `Path(out_dir)` 重复构造
- [x] L15 `row[1]` → `row["name"]`（M14 时顺带完成）
- [x] L16 base.json 新增 `app_name`/`log_level`：main.py 应用名、logger 日志文件名与级别驱动
- [x] 检验：`.temp/verify_v1010_3.py` 36 项（行宽扫描/冗余核验/缓存收敛/主题单一来源/缺键抛错/配置常量一致/饼图托盘源码/常量）+ 全量回归 17 脚本全绿（verify_s10 同步 _throttled_cache 新签名）+ import OK
- 状态：✅ 已完成（2026-08-10）｜优先级：低

### V0.10.4 验证与收尾

- [x] V.1 全量回归：verify_s1-s14 + v0808_p2-p8 + v0809_1-5 + v1010_1-3 共 **596 项断言全部通过**（v1010_3 后重新全量计数；同步了 verify_s10/_throttled_cache 新签名、v0808_p6/read_credentials_file 内联、v0808_p8/TABLE_LIMIT_GROUP 常量）
- [x] V.2 导入验证 + GUI offscreen 初始化 OK + `--version` 输出 ver 0.10
- [x] V.3 README 配置表同步：base.json 新增 8 参数（cdp_fetch/wait_timeout、http_timeout、table_limit_group/day、app_name、log_level）+ ui.json 饼图参数（pie_size/pie_font_size/色值）
- [x] V.4 y.problem.md：P10 移入"✅ 已完成"区（压缩记录 + 标注 H1/M11 审计证伪项）；z.plan.md 第十二章标注"全部完成（V0.10）"
- [x] V.5 `config/static/base.json` `version` → `ver 0.10`（`--version` 验证）；verify_s12 required 补 8 个新字段
- [x] V.6 x.progress.md 完成记录回填（本节 + 验证总览 + 头部版本）
- 状态：✅ 已完成（2026-08-10）｜优先级：高

---

## V0.10 验证总览（P10 二次审计整改）

> V0.10 全量回归 **596 项断言全部通过**（s1-s14 基线 + v0808_p2-p8 + v0809_1-5 + v1010_1-3 新增 92 项）——2026-08-10 实施完毕
> 三批整改全部完成：H1-H10 高价值（行为相关，H1 审计证伪保留）→ M1-M20 中价值（8 处死代码/内联/抽取/说明区，M11 结构性整改）→ L1-L16 低价值（行宽/魔法数字/冗余，base.json 新增 8 参数）
> 遗留：P1/P9（多账户区分）、P11（明文兼容去留）待评估，P20（模型数据页+社交跟踪）V0.11 实施，见 y.problem.md

---

## 阶段验证命令速查（AGENTS.md 运行与验证）

```powershell
# 导入验证
.\.venv\Scripts\python.exe -c "import main, modules.opencode_usage, modules.go_quota, modules.pricing, modules.exporter, modules.browser_creds, config.settings, config.static.static_config, ui.main_window, ui.system_tray, ui.themes, utils.logger, utils.file_utils, utils.retry, utils.convert"

# GUI 无头初始化验证（不弹窗）
$env:QT_QPA_PLATFORM="offscreen"; .\.venv\Scripts\python.exe -c "from PyQt6.QtWidgets import QApplication; from ui.main_window import MainWindow; app = QApplication([]); w = MainWindow(); print('GUI init OK')"

# 阶段验证脚本（各自模块开发完成后运行）
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
```
