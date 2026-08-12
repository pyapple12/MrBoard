# 已知问题与增强备忘（y.problem.md）

> 目的：记录已发现但不属于当前阶段范围的问题/增强项，供未来评估
> 记录格式：状态 [✅ 已完成 / 📌 待评估] / 来源（讨论日期/场景）

---

## ✅ 已完成（V0.08，2026-08-10 实施完毕）

### P2. 用户目录路径硬编码 → 集中项目内 ✅

- 完成：2026-08-10（V0.08）
- 落地：base.json 新增 `credentials_dir`/`logs_dir`/`prices_dir`，凭据/日志/价格缓存移至 `data/` 下；logger 顶层 `get_static_config()` 引用（AGENTS.md 分层放宽）；用户目录残留已清理

### P3. 删除 API key 链路（程序不接触任何 key）✅

- 完成：2026-08-10（V0.08）
- 落地：models 接口与 auth.json 读取链（五函数 + 两常量 + model_count/auth_source 字段）全部移除，主流程简化为"节流 → 凭据 → 三窗口"；全源码 grep 零残留

### P4. 凭据加密存储（DPAPI）✅

- 完成：2026-08-10（V0.08）
- 落地：新增 `modules/credential_store.py`——`{"encrypted_v1": base64(DPAPI blob)}` 格式绑定当前 Windows 用户；明文旧格式兼容读取；手动填写改 GUI 对话框；win32crypt 缺失拒绝明文落盘；现有真实凭据已迁移加密

### P5. 配额重置时间显示改为"月-日 时:分" ✅

- 完成：2026-08-10（V0.08）
- 落地：`_render_quota` 改为 `strftime('%m-%d %H:%M')`（"重置于 08-12 06:30"）

### P6. 移除跨项目凭据路径探测（opencode-bar / opencode-quota）✅

- 完成：2026-08-10（V0.08）
- 落地：`_dashboard_config_paths` 收敛为 env + 项目内路径，刷新 WARNING 噪音消除

### P7. 按日期统计显示改为由近到远 ✅

- 完成：2026-08-10（V0.08）
- 落地：`by_day()` 排序 `label ASC` → `DESC`，GUI/CLI/导出同步

### P8. 新增月度用量统计功能 ✅

- 完成：2026-08-10（V0.08）
- 落地：`OpenCodeDB.by_month()`（`%Y-%m` 本地时区分组，降序）；GUI 下拉"按月份"、CLI `--by month`、导出 `by_month.csv`；真实库验证月份与日期聚合总 token 一致

### P12. UI 元信息行"dashboard 凭据来源"移除 ✅

- 完成：2026-08-10（V0.09）
- 落地：删除 `_quota_meta` 元信息行（创建 + 渲染）；`credential_source` 字段保留（内部排查/日志用）

### P13. 用量明细列顺序调整 + 列显示开关 ✅

- 完成：2026-08-10（V0.09）
- 落地：列顺序 标签/总 token/调用数/输入/输出/推理/缓存（读+写合并）/缓存率/费用（ui.json `table_headers` + `COLUMN_IDS` 列模型）；"设置"按钮 QMenu 列开关（勾选=显示/取消=隐藏，`setColumnHidden`），状态持久化 `config/user_config.json` 的 `hidden_columns`

### P14. 用量明细 5 分钟自动更新（排查结论：链路正常）✅

- 完成：2026-08-10（V0.09）
- 结论：定时器（5 分钟）→ refresh → 后台任务 → 渲染链路正常无 bug；"观察未更新"源于间隔内数据无变化时表格内容不变（状态栏时间戳会变）；链路已用模拟触发验证

### P15. 总览卡片改造：独立显示 + 点击弹出总量明细 ✅

- 完成：2026-08-10（V0.09）
- 落地：维度下拉移除"总览"；明细旁"总 token"按钮（千分位 + 亿单位）；点击弹出总量明细（QMessageBox：会话/消息/天数/tokens 分解/缓存率/费用）

### P16. 配额展示改饼图 + 剩余量，删除"最紧窗口" ✅

- 完成：2026-08-10（V0.09）
- 落地：三个进度条与重置时间不动；原"最紧窗口 X% / 剩余 Y%"位置改为剩余量饼图（`_RemainingPieChart`：双色圆弧 + 中心"剩余 Y%" + 分级色）；缓存/错误时饼图隐藏、警告文字让位；overall 内部保留（托盘预警继续用）

### P17. 顶部卡片栏调整：删除会话数，重排为 总 tokens → 输入 → 输出 → 缓存率 → 总费用 ✅

- 完成：2026-08-10（V0.09）
- 落地：卡片键集合 `tokens/input/output/cache_rate/cost`；缓存率 = (缓存读+缓存写)/总 token 百分比（`_cache_rate_percent`，卡片与表格共用）

### P18. 用量明细表格增加"缓存率"列 ✅

- 完成：2026-08-10（V0.09）
- 落地：表格"缓存率"列（每行 (缓存读+缓存写)/总 token，与 P17 同定义），随 P13 列重构一并实施

### P19. 新增按会话统计维度（tokens 精确到每个会话）✅

- 完成：2026-08-10（V0.09）
- 落地：`by_session()`——LEFT JOIN session 表，label = "会话标题｜项目目录"（真实库 title/directory 覆盖率 100%）；旧库缺列降级 session_id；GUI"按会话"/CLI `--by session`/导出 by_session.csv（8 个 CSV）

### P21. 配额重置时间时区 bug 修复 ✅

- 完成：2026-08-10（V0.09）
- 落地：`_render_quota` 与 CLI `main()` 的 reset_date 显示前 `astimezone()` 转本地时区（修复前 UTC 直出差 8 小时）；真实验证显示与本地一致

### P10. 项目二次全面审计（硬编码/规范错误/代码优化/架构完善）✅

- 完成：2026-08-10（V0.10）
- 落地：全量 16 文件审计发现 59 条（高 10/中 20/低 22）按三批整改完毕——死分支/死条件清理、配置失效修复（CDP 等待时长/pricing 缓存兜底/UA 版本/预警阈值）、8 处死代码删除、过简函数内联、重复逻辑抽取（Local State/JSON/time_clause/PRAGMA 缓存/导出收敛）、import 分组修正、4 文件说明区补齐、行宽/魔法数字/冗余包装清理（base.json 新增 8 参数）
- 注：审计中 2 项建议经实测证伪（H1 except GoQuotaError 非死代码、M11 直连信号受初始化顺序限制）——均以行为验证为准

---

## 待评估 / 待实施

### P1. 用量统计不区分 API key/账户（增强候选）

- **状态**：📌 待评估
- **来源**：2026-08-09 用户提问（更换 OpenCode Go 账户后希望区分 key 用量）
- **现状**：
  - 用量统计（opencode.db）：message 数据只有 `providerID`/`modelID`，**无 key 维度**——新旧账户消息混在一起，无法区分
  - Go 配额监控：dashboard 按 `workspaceId` 拉取，换账户后仅显示**当前账户**配额，旧账户配额不保留
- **约束**：opencode.db 无 key 字段，无法精确回溯历史
- **可行方案（近似）**：换 key 时在本地记录时间点（如 config/user_config.json 增加 key 变更日志），按时间切片统计各账户用量
- **触发条件**：用户明确需要多账户统计时再评估

### P9. 按 workspace/账户区分使用量的方案讨论

- **状态**：📌 讨论中（2026-08-09 用户提出）
- **背景**：用户换过 OpenCode Go 账户（换 key 换 workspace），希望区分各账户的使用量（关联 P1）
- **候选方案**：
  - **方案 A：以 workspace ID 区分**——用量数据（opencode.db message）无 workspace 字段，需确认 db 中能否关联（message.session_id → session.workspace_id 字段存在，但历史数据可能为空），或按时间切片推断
  - **方案 B：程序记录 key/账户切换时间点**——用户换 API key 时，myboard 提供"替换 API 并记录时间"功能（替换 auth.json 的 opencode-go key + 写入切换时间日志），按时间切片统计各账户用量
  - **方案 C：凭据变更检测**——检测 auth.json 的 key 变化（指纹比对）自动记录切换时间，免手动操作
- **待讨论点**：方案 A 的数据可行性（session.workspace_id 覆盖情况）；方案 B/C 的时间切片统计粒度（月/日）；是否需要 GUI 展示"按账户用量"
- **触发条件**：讨论确定方案后实施（注：P3 已删 auth.json 读取，方案 B/C 若依赖 key 读取需重新设计）

### P11. 明文旧格式凭据兼容读取的去留（增强候选）

- **状态**：📌 待评估（2026-08-10 P4 实施后记录）
- **来源**：2026-08-10 用户提问"现在的凭证是不是没加密，兼容是什么意思"→ 迁移现有凭据为加密格式后提出
- **现状**：`credential_store.read_credentials_file` 读取路径同时支持加密格式（`encrypted_v1` 解密）与明文旧格式（原样返回）；现有真实凭据已迁移为加密格式
- **考虑点**：
  - 彻底删除明文分支：读取强制加密格式，旧明文文件不再可读（需重新获取凭据）——代码更简单、安全口径统一
  - 保留兼容：手动放置明文文件/旧文件仍可用；明文读取分支是历史代码（安全弱口，但明文内容来自用户自己）
  - 写入路径已无条件加密（win32crypt 缺失拒绝写入），明文只会来自"用户手动放置"或"旧版本遗留"
- **触发条件**：P10 二次审计时评估（若删除，连带更新 verify_v0808_p4 明文兼容断言与 verify_s7 相关断言）

### P20. 模型数据页 + 官方社交消息跟踪（V0.11 规划，2026-08-10 可行性研究定稿）

- **状态**：📌 已确认方向，待实施（V0.11；用户决策：V0.09 不做）
- **来源**：2026-08-10 用户要求研究 https://opencode.ai/zh/data/ 与 opencode 社交账号跟踪可行性后提出
- **可行性研究结论（2026-08-10）**：
  - **数据页可获取性：高**——数据以 `$R[N]={...}` 内嵌在 HTML script 中（Next.js streaming），与现有 dashboard 解析技术同构（`_capture_object_body` 已兼容）；数据块：tokenCost（每百万 token 价格）/sessionCost（每次会话成本）/cacheRatio（缓存比例）+ 热门模型/独立用户/地理分布；公开页面无凭据
  - **社交渠道**：
    - **GitHub（可行，推荐）**：`releases.atom` RSS 免费无认证，或 `api.github.com/repos/anomalyco/opencode/releases` JSON（匿名限速 60 次/小时够用）——最新版本发布公告
    - **X/Twitter @opencode：不可行**——官方 API 需付费认证（免费层无读取权限）；无 API 抓取被登录墙 + 反爬拦截
    - **小红书：不可行**——未发现 opencode 官方账号；平台反爬极强（x-s 签名）+ 无公开 API
- **目标**：
  - **模型数据页**：GUI **新页签**（用户确认方案）展示数据页内容；展示哪些数据块**做的时候再定**（用户未考虑完全）
  - **社交消息**：GitHub Releases 拉取最新版本消息（版本号 + 更新摘要）展示
  - 获取策略复用现有模式：60s 节流 + TTL 缓存 + 解析失败降级（$R 兼容 + 缺失容忍）
- **连带**：新模块（如 modules/opencode_data.py）+ UI 页签（QTabWidget 改造或独立窗口）；verify 脚本新增；README 同步
- **触发条件**：V0.11 启动时实施

---

## 开发日志摘录（2026-08-09 CDP 真实闭环修复）

> 记录：真实环境验证中定位并修复的 4 个问题，供后续参考

1. **CDP WebSocket 403**：Chrome 137+ 校验 WebSocket Origin，`fetch_auth_cookie_via_cdp` 连接被拒（403）。修复：`launch_chrome_debug` 增加 `--remote-allow-origins=*` 启动参数
2. **占位 cookie 误判登录**：临时窗口打开 opencode.ai 登录页时页面自动种匿名 auth cookie，程序误判"已登录"→ 提前关闭窗口。修复：端到端验证——拿到 cookie 后实测 dashboard 可解析才算登录完成（`_wait_for_login_cookie` 改造）
3. **多账户 workspace 保存错误**：History 有多个 workspaceId（换过账户），验证时第二个通过，但 `save_dashboard_credentials` 固定保存第一个（旧账户）→ dashboard 仍 OpenAuth。修复：`_wait_for_login_cookie` 返回验证通过的 workspace_id，保存时使用
4. **OpenAuth 登录页误报 decoding**：凭据失效时 dashboard 返回 OpenAuth 登录页，被解析为"页面结构变更"（decoding），引导卡片不显示。修复：检测 `OpenAuth` 标记 → 分类为 auth 错误（引导卡片重新出现）
5. **API key 失效阻断配额**：`fetch_go_quota` 先校验 models 接口 key，403 直接中断未走 dashboard（配额走浏览器会话，与 key 独立）。修复：key 校验失败降级继续（模型数未知），配额照常拉取

---

## 增强候选

（暂无其他记录）
