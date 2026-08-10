# 已知问题与增强备忘（y.problem.md）

> 目的：记录已发现但不属于当前阶段范围的问题/增强项，供未来评估
> 记录格式：状态 [📌 待评估] / 来源（讨论日期/场景）

---

## 已知问题

### P1. 用量统计不区分 API key/账户（增强候选）

- **状态**：📌 待评估
- **来源**：2026-08-09 用户提问（更换 OpenCode Go 账户后希望区分 key 用量）
- **现状**：
  - 用量统计（opencode.db）：message 数据只有 `providerID`/`modelID`，**无 key 维度**——新旧账户消息混在一起，无法区分
  - Go 配额监控：dashboard 按 `workspaceId` 拉取，换账户后仅显示**当前账户**配额，旧账户配额不保留
  - 根因：auth.json 的 `opencode-go` 条目是单 key 结构（`{"type": "api", "key": "..."}`），凭据链按单账户设计
- **约束**：opencode.db 无 key 字段，无法精确回溯历史
- **可行方案（近似）**：换 key 时在本地记录时间点（如 config/user_config.json 增加 key 变更日志），按时间切片统计各账户用量
- **触发条件**：用户明确需要多账户统计时再评估

### P2. 用户目录路径硬编码，应统一收录为静态配置参数

- **状态**：📌 待评估（2026-08-09 用户决策：当日不修改）
- **来源**：2026-08-09 用户提问"这些配置由哪个参数决定还是硬编码"
- **现状**：5 处用户目录路径全部硬编码在代码中：
  - `modules/go_quota.py`：`CREDENTIALS_FILE = ~/.config/myboard/opencode-go.json`
  - `modules/pricing.py`：`PRICE_CACHE_DIR = ~/.config/myboard/`（prices.json / prices.local.json）
  - `ui/main_window.py`：`opencode-go.example.json`（从 CREDENTIALS_FILE.parent 派生）
  - `utils/logger.py`：`LOG_DIR = ~/.local/share/myboard/`
- **背景**：S8 对齐 AccelWorld 时，凭据与日志路径**有意不进 json**（S8 头部路径决策：凭据防误提交/打包安全、日志防只读目录）；但 `PRICE_CACHE_DIR` 属于 S8 外置时的**遗漏**（同为可调参数性质）
- **目标方案**：base.json 增加 `credentials_dir`、`logs_dir`、`prices_dir` 等字段，代码统一从静态配置读取（保持"参数零硬编码"原则）
- **约束**：路径值仍须指向用户目录（凭据/日志不进项目，打包安全）；`.gitignore` 已忽略相关文件
- **触发条件**：下次配置层调整时一并处理

---

### P3. 删除 API key 链路（models 接口 + auth.json 读取），程序不接触任何 key

- **状态**：📌 已确认方向，待实施（2026-08-09 用户决策）
- **来源**：2026-08-09 用户提出"models 接口没必要存在，获取 key 易泄露；程序不应有任何获取 key 的可能"
- **原则**：程序从任何路径（本地读取或网络外发）都不应接触用户的 API key
- **删除范围**（整条链路）：
  - `fetch_model_count`（key 经 Bearer 外发 models 接口）
  - `get_opencode_go_key` / `read_auth_json` / `find_auth_file` / `strip_json_comments`（auth.json 读取链——auth.json 含所有 provider 的 key，不只是 opencode-go）
  - 常量 `MODELS_URL` / `AUTH_KEY_FIELDS`
  - `GoQuotaInfo.model_count` 字段、"模型数：未知"展示、`auth_source`（API key 来源）字段、`error_stage="no_key"` 分支
- **保留**：`find_dashboard_credentials`（workspaceId + authCookie 链路，与 key 无关）；authCookie 为登录会话凭据（不能直接调用 API 消费额度，但可冒充网页操作，仍属敏感）
- **连带**：verify_s3 相关测试项删除；配额面板元信息只显示 dashboard 凭据来源
- **验证口径**：删除后全源码 grep 无 key 相关读取/外发逻辑；配额/用量功能不受影响

### P4. 凭据加密存储（防文件泄露后他人使用）

- **状态**：📌 讨论中（2026-08-09 用户提问"能否加密获取的凭证，即使泄露也无法供他人使用"）
- **目标**：`~/.config/myboard/opencode-go.json`（authCookie + workspaceId）即使文件泄露（分享/转移），他人无法解密使用
- **候选方案**：
  - **DPAPI（CryptProtectData）**（首选）：绑定当前 Windows 用户（SID），他人换机/换用户无法解密；技术栈已有 pywin32；Chrome v10 同款思路；常驻应用当前用户自动解密，无需交互
  - 主密钥 + DPAPI 包裹（随机 AES key，DPAPI 保护 key）：Chrome 同构，可加 entropy
  - 用户口令 PBKDF2：不现实（常驻应用自动刷新无法交互）
  - TPM 绑定：复杂，收益不成比例
- **局限**：同 Windows 用户下运行的恶意软件仍可解密（DPAPI 不防同会话进程）；换机迁移需重新 CDP 获取（本机获取语义，可接受）
- **待讨论点**：
  - 程序写入为加密格式（加格式标记，如前缀），向后兼容明文旧格式读取
  - "手动填写"路径（用户编辑明文 opencode-go.json）与加密格式的冲突——是否改由 GUI 填写（程序加密写入）而非直接编辑文件
  - 日志/调试输出不打印明文凭据（现有约定保持）
- **触发条件**：P3 实施后一并评估

### P5. 配额重置时间显示改为"月-日 时:分"

- **状态**：📌 已确认方向，待实施（2026-08-09 用户决策）
- **来源**：2026-08-09 用户提问"重置于显示的时间是小时和分钟吗"→ 倾向显示完整日期时间
- **现状**：`ui/main_window.py` `_render_quota` 中 `reset_date.strftime('%H:%M')`——仅显示 24 小时制时分；对每周/每月窗口不直观（用户看不出重置是哪天）
- **目标**：改为 `%m-%d %H:%M`（如"重置于 08-12 06:30"），明确告知用户重置的月日时分
- **连带**：无（纯展示层改动）；verify_s4 无相关断言
- **触发条件**：下次 UI 调整时一并处理

### P6. 移除跨项目凭据路径探测（opencode-bar / opencode-quota）

- **状态**：📌 已确认方向，待实施（2026-08-09 用户决策）
- **来源**：2026-08-09 用户看到刷新日志中"读取凭据配置失败 ...opencode-bar\opencode-go.json / opencode-quota\opencode-go.json"警告（No such file）
- **现状**：`find_dashboard_credentials` 的多路径探测链包含**其他项目的配置习惯路径**（`~/.config/opencode-bar/`、`~/.config/opencode-quota/`，源自 opencode-bar 的多路径兼容设计）——这些路径无文件时每次刷新都打 WARNING 噪音
- **决策**：**不读取其他项目的配置文件**——myboard 凭据只从自身路径读取（`~/.config/myboard/opencode-go.json`）+ 环境变量；移除 `_dashboard_config_paths` 中的 opencode-bar / opencode-quota 路径（保留 `$OPENCODE_GO_CONFIG_FILE` 与 myboard 路径）
- **连带**：`_read_credentials_json` 探测噪音消除；verify_s3 凭据探测相关测试若引用这些路径需同步
- **触发条件**：P3/P4 实施时一并处理

### P7. 按日期统计显示改为由近到远

- **状态**：📌 已确认方向，待实施（2026-08-09 用户决策）
- **来源**：2026-08-09 用户提出"按日期统计 tokens 是由近到远，和当前的方式反过来"
- **现状**：`modules/opencode_usage.py` `by_day()` 用 `order="label ASC"`（日期升序，最旧在前）——GUI 表格最新日期在底部
- **目标**：改为由近到远（最新日期在最上方）：`by_day` 排序改 `label DESC`
- **连带**：CLI `--by day` 输出顺序同步反转；verify_s2 若有 by_day 顺序断言需同步
- **触发条件**：小改动，可随下次 UI 调整一并处理

### P8. 新增月度用量统计功能

- **状态**：📌 已确认方向，待实施（2026-08-09 用户决策）
- **来源**：2026-08-09 用户提出"添加一个统计月度用量的功能"
- **需求**：按自然月聚合用量（tokens/费用/会话），展示每月汇总（如 2026-07 / 2026-08），供月度账单核对
- **方案方向**：
  - 数据层：`opencode_usage.py` 新增 `by_month()`（`strftime('%Y-%m')` 分组，复用 `_query_grouped`）
  - 展示层：GUI 维度下拉新增"按月份"选项（DIMENSIONS/DIMENSION_LABELS 扩展）；CLI `--by month`
  - base.json 无需新增参数（沿用现有聚合模式）
- **触发条件**：待实施

### P9. 按 workspace/账户区分使用量的方案讨论

- **状态**：📌 讨论中（2026-08-09 用户提出）
- **背景**：用户换过 OpenCode Go 账户（换 key 换 workspace），希望区分各账户的使用量（关联 P1）
- **候选方案**：
  - **方案 A：以 workspace ID 区分**——用量数据（opencode.db message）无 workspace 字段，需确认 db 中能否关联（message.session_id → session.workspace_id 字段存在，但历史数据可能为空），或按时间切片推断
  - **方案 B：程序记录 key/账户切换时间点**——用户换 API key 时，myboard 提供"替换 API 并记录时间"功能（替换 auth.json 的 opencode-go key + 写入切换时间日志），按时间切片统计各账户用量
  - **方案 C：凭据变更检测**——检测 auth.json 的 key 变化（指纹比对）自动记录切换时间，免手动操作
- **待讨论点**：方案 A 的数据可行性（session.workspace_id 覆盖情况）；方案 B/C 的时间切片统计粒度（月/日）；是否需要 GUI 展示"按账户用量"
- **触发条件**：讨论确定方案后实施

### P10. 项目二次全面审计（硬编码/规范错误/代码优化/架构完善）

- **状态**：📌 待实施（2026-08-09 用户决策：明日执行）
- **来源**：2026-08-09 用户要求"再次对项目进行审计，找出硬编码、代码规范错误、优化代码，让代码目录架构更为完善"
- **背景**：首轮审计（S7 前置，基于 S6 时代码）后经历 S8 大改（config/static/ 建立、参数外置、VERSION 迁移）与 CDP 真实闭环修复，代码已大幅变化，需二次全量审计
- **审计范围**：
  1. **硬编码排查**：S8 后残留硬编码（已知：P2 用户目录路径；待查：中文文案/表头/维度标签、错误消息、魔法数字等是否应外置或常量化）
  2. **代码规范错误**：对照 AGENTS.md（函数 `#` 注释、文件尾说明区、命名、import 顺序、行宽、类型注解、异常处理）；verify_s11 已覆盖注释部分，其余人工/工具核查
  3. **代码优化**：重复逻辑、过长函数、性能（SQL/网络/UI 渲染）、死代码、调试日志清理（本次 CDP 修复遗留的 INFO 调试日志）
  4. **目录架构完善**：data/ 空置是否需填充或移除；modules 是否需子包拆分（如 modules/go/、modules/browser/）；P3-P9 实施后的架构影响
- **交付物**：审计报告 + 问题清单（按严重度）+ 优化建议，写入 z.plan.md 或独立记录
- **触发条件**：次日开始，与 P3-P8 实施合并排期

### P11. 明文旧格式凭据兼容读取的去留（增强候选）

- **状态**：📌 待评估（2026-08-10 P4 实施后记录）
- **来源**：2026-08-10 用户提问"现在的凭证是不是没加密，兼容是什么意思"→ 迁移现有凭据为加密格式后提出
- **背景**：P4 凭据加密后，`credential_store.read_credentials_file` 保留**明文旧格式兼容读取**（文件 dict 无 `encrypted_v1` 标记时原样返回）——向后兼容 P4 前的老文件；2026-08-10 现有真实凭据已迁移为加密格式（`{"encrypted_v1": ...}`，解密回读验证通过）
- **现状**：读取路径同时支持两种格式：
  - 加密格式（`encrypted_v1` 键）→ DPAPI 解密（主路径）
  - 明文旧格式（无标记）→ 原样返回（兼容分支）
- **考虑点**：
  - 彻底删除明文分支：读取强制加密格式，旧明文文件不再可读（需重新获取凭据）——代码更简单、安全口径统一（磁盘上只存在加密凭据）
  - 保留兼容：手动放置明文文件/旧文件仍可用；但明文读取分支是历史代码（安全弱口：攻击者可替换为明文文件让程序读取，不过读取明文本身不增加泄露，明文内容来自用户自己）
  - 写入路径已无条件加密（win32crypt 缺失拒绝写入），明文只会来自"用户手动放置"或"旧版本遗留"
- **触发条件**：P10 二次审计时与 P3-P9 遗留项一并评估（若评估删除，连带更新 verify_v0808_p4 的明文兼容断言与 verify_s7 相关断言）

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
