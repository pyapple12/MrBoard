# 开发进度追踪（x.progress.md）

> 依据：`z.plan.md`（myboard 方案报告）
> 当前版本：ver 0.08（VERSION 单一来源在 config/static/base.json 的 version 字段）
> 记录格式：状态 [⏳ 待开发, ✅ 已完成] / 优先级 [高, 中, 低]
> 执行原则：每阶段完成后运行验证命令确认无回归，再进入下一阶段
> 错误策略：各模块开发时落实 z.plan.md 第四章约定（统一错误类型/降级不中断/缓存兜底/宽容解析/节流去重/保留旧数据/只读防误写）

---

## S1-S6 完成记录（简化）

### S1 骨架搭建 ✅

包结构（modules/config/ui/utils/data）+ AGENTS.md + z.plan.md + git 仓库（干净单线历史）+ `.venv`（Python 3.14）+ `main.py` 入口（VERSION 单一来源）+ `utils/logger.py`（双 handler）/`file_utils.py`（原子写+缓存单例）/`retry.py`（指数退避重试）。验证：17 项断言通过。

### S2 用量统计模块 ✅

`modules/opencode_usage.py`：三级路径探测（env → `opencode db path` → XDG）、只读连接（mode=ro）、`json_extract` + `COALESCE(SUM)` 聚合（不依赖 `tokens.total`，兼容新旧格式混合）、按天/模型/provider/agent 分组、库 cost 优先 + estimate 估算回退、CLI 自测。`modules/pricing.py`：三级来源合并（缓存 TTL → models.dev → 内置表）+ 本地覆盖打标 + 多币种分桶禁止相加。真实库对照 `opencode stats` 全口径一致（Sessions 111/Days 214/Cost $63.19 等）。验证：30 项断言通过。

### S3 Go 配额模块 ✅

`modules/go_quota.py`：auth.json 多路径 + jsonc 剥离 + key 多键兼容；dashboard 凭据链（env → 配置文件 key 兼容集合 → 浏览器）去重首成功返回；models Bearer 校验；dashboard HTML 抓取（实体反转义 + `$R[NN]=` 兼容正则）→ 5h/周/月三窗口 + max 取最紧；60s 节流 + 缓存兜底 + `GoQuotaError` 四分类；窗口缺失容忍。验证：39 项断言通过。

### S4 GUI 界面 ✅

`ui/themes.py`（LIGHT/DARK QSS + 三色分级）、`ui/main_window.py`（5 卡片 + 配额进度条 + 分组表格 + QThreadPool 后台加载 + 启动延迟防双加载 + 保留旧 view + 5 分钟定时刷新 + 主题切换）、`ui/system_tray.py`（状态色图标 + 菜单 + 信号解耦）、`main.py` run_gui + _quit_app（VERSION 循环依赖函数内打破，对齐 AccelWorld）。验证：29 项断言通过 + offscreen GUI init OK。

### S5 完善收尾 ✅

`config/settings.py`（AppConfig 持久化：几何/主题/刷新间隔，宽容解析）；`modules/exporter.py`（5 CSV UTF-8 BOM + usage.json）+ GUI 导出按钮（后台线程）；AGENTS.md 错误策略章节落地；README（启动/凭据/配置表）；closeEvent 隐藏到托盘常驻。验证：29 项断言通过。

### S6 增强 ✅

S6.1 `modules/browser_creds.py`：v10 DPAPI+AES-GCM 离线解密；**实测**确认 History/Local State 运行时共享可读、Cookies 独占锁定、Chrome 136+ 调试端口仅非默认 profile 开放、完整 CDP 流程无需关闭用户浏览器；v20 检测改查 Local State `app_bound_encrypted_key`；CDP 方案（独立临时 profile + `Network.getAllCookies`，Chrome 自行解密跨版本稳定）。S6.2 凭据配置引导：引导卡片（凭据缺失显示）+ 一键 CDP 获取（后台线程：快照 workspaceID → 临时调试 Chrome → 轮询登录 → 写凭据 → 清理 → 自动刷新）+ 手动填写（模板 + 示例 + 打开文件夹）。S6.3 多 provider 已评估关闭。验证：verify_s6 33 项 + verify_s7 18 项通过。

### 验证总览

S1-S6 全量回归 **195 项断言全部通过**（verify_s1:17 / verify_s2:30 / verify_s3:39 / verify_s4:29 / verify_s5:29 / verify_s6:33 / verify_s7:18）。

---

## S7 审计整改（依据 z.plan.md 第九章审计结果）

> 目标：修复 4 个真实 bug + 8 个中危问题 + 消重抽取；完成后全量回归
> 依据：z.plan.md 九、代码审计结果（2026-08-08 全量 13 文件审计）

### S7.1 真实 Bug 修复（优先级：高）

- [x] S7.1.1 B1：`go_quota.py` retry_call 重试失效修复——`_http_get` 网络类异常（URLError/TimeoutError/5xx）原样抛出交 retry_call 重试（401/403 仍转 auth 分类不可重试）；`fetch_dashboard_usage` 的 HTTPError 兜底分支从死代码变活代码；重试耗时 mock 验证（第 1/2、2/2 次重试真实发生）
- [x] S7.1.2 B2：托盘配额预警接线——MainWindow 新增 `quota_updated` 信号（_on_quota_ready 发射），main.py `_on_quota_updated`：错误置灰 / 正常更新状态色 / ≥80% 气泡预警
- [x] S7.1.3 B3：`_estimate_missing_costs` 增加 since/until 时间过滤（`_time_clause` 复用），估算范围与 totals 一致（验证：范围外 cost=0 消息不计入）
- [x] S7.1.4 B4：logger.py FileHandler 异常保护（try/except OSError 降级仅控制台，修正说明区）；删除 settings.py 未使用的 `logger` 变量（消除 import 副作用）
- 状态：✅ 已完成｜优先级：高

### S7.2 中危问题修复（优先级：中）

- [x] S7.2.1+M7.2.2 M1/M2：VERSION 循环依赖根治——新建 `config/constants.py` 持 VERSION，main.py 与 ui 均从该模块引用；main.py 改顶层 import（删除函数内延迟 import），`_quit_app` 注解引用顶层名字（Python ≤3.13 兼容）
- [x] S7.2.3 M3：新建 `utils/convert.py`（to_int/to_float/to_optional_float 弹性转换），替换 opencode_usage 全部 12 处 `int(row[...])` 强转 + 2 处 float 强转；pricing 私有转换迁移复用（删除本地重复定义）
- [x] S7.2.4 M4：`_set_status_style` 方法（setObjectName + unpolish/polish 强制 QSS 重算），替换 _render_quota 三处样式设置
- [x] S7.2.5 M5：`GoQuotaInfo.error_stage` 字段（no_key/no_dashboard_creds/auth/network/...），_fallback 携带阶段；引导卡片仅对 CDP 可解决的阶段（no_dashboard_creds/auth）显示，no_key/network 不误导
- [x] S7.2.6 M6：浏览器探测降级闭环——`find_browser_credentials` 逐浏览器 try + `_profile_dirs` iterdir 异常捕获，不再冒泡打断 go_quota 凭据链
- [x] S7.2.7 M7：CDP 端口占用检测——`launch_chrome_debug` 启动前 wait_cdp_ready(timeout=1)，占用则拒绝启动（防误连他人调试实例）
- [x] S7.2.8 M8：死代码接入——`_CdpGuideTask.run` 预检：v10 环境（has_v20_cookies False）跳过 CDP 提示自动探测；is_chrome_running 记录日志（独立 profile 不冲突）
- 状态：✅ 已完成｜优先级：中

### S7.3 消重与函数抽取（优先级：中）

- [x] S7.3.1 D1：`flatten_tokens(tokens, prefix)`（opencode_usage 模块函数）——CLI 嵌套结构（空前缀）与 exporter 平铺（tokens_ 前缀）4 处统一复用
- [x] S7.3.2 D2：`_TOKEN_SUM_SELECT` 模块常量——`_base_sql` 与 `_query_grouped` 聚合列模板 2 处复用（加字段只改一处）
- [x] S7.3.3 D3：exporter 删除私有 `_write_json`，复用 file_utils.write_json（原子写 + 缓存）
- [x] S7.3.4 D4：pricing `_rate_from_raw(item, default_source)`——内置/缓存/本地覆盖三处弹性构建统一（宽容回默认）
- [x] S7.3.5 D6：browser_creds `_with_copied_db(db_path, query)`——三个复制库查询骨架统一（自动连接/关闭/清理，修复异常路径临时文件残留）
- [x] S7.3.6 D7：go_quota 拆分 `_throttled_cache` / `_fetch_usage_with_fallback` / `_build_info`（修复拆分时丢失 global 声明的回归：缓存更新失效已修）
- [x] S7.3.7 D8：main_window `_build_ui` 拆分 `_build_cards` / `_build_quota_section` / `_build_guide_card` / `_build_detail_section`
- [x] S7.3.8 D9：`_wait_for_login_cookie(deadline)` 抽取（轮询循环独立）
- [x] S7.3.9 D10：themes `_build_theme(palette)` 模板化——两套 QSS 60 行重复消除（改样式只改模板/调色板）
- [x] S7.3.10 D11：go_quota `_mark_cached(info, message)`——dataclasses.replace 浅拷贝标注，不再污染共享缓存对象
- [x] S7.3.11 D12：browser_creds `_local_appdata()` 收敛三处 LOCALAPPDATA 推导
- [x] S7.3.12 D13：themes 阈值常量 `QUOTA_WARN_PERCENT=50` / `QUOTA_DANGER_PERCENT=80`（quota_chunk_color 与 system_tray 共用）
- [x] S7.3.13 D14：system_tray 阈值改用 themes 常量 + `NOTIFY_DURATION_MS` 常量（消除硬编码 80/50/5000）
- 状态：✅ 已完成｜优先级：中

### S7.4 规范口径与验证（优先级：中）

- [x] S7.4.1 注释规则决策（用户审批通过）：**回归 AGENTS.md 原规则**——函数下方只允许 `#` 注释（1-3 行），详细信息全部在文件末尾 `# =====` 说明区；**禁止 docstring 顶替 `#` 注释**
- [x] S7.4.2 AGENTS.md 修订：函数注释规则新增"禁止 docstring 替代 # 注释（verify_s11 自动检测）"条款
- [x] S7.4.3 全量整改：147 个函数 docstring → 函数下 `#` 注释 + 15 个模块 docstring + 23 个类 docstring 全部转 `#` 注释（155 函数/15 模块/23 类零残留，py_compile 全过）
- [x] S7.4.4 `.temp/verify_s11.py`：AST 全量检测（函数下必须有 # 注释、禁止任何 docstring 节点残留）+ 检测器反向验证（能抓无注释函数/残留 docstring）
- [x] S7.4.5 全量回归：verify_s1-s10 共 279 项全部通过（注释转换零逻辑变更）
- 状态：✅ 已完成｜优先级：中

---

## S8 配置层对齐 AccelWorld（json 驱动静态配置）

> 目标：对齐 AccelWorld config 模式——静态配置（开发期参数）json 文件驱动、代码零硬编码；用户配置（运行时设置）保持 dataclass + json 持久化，两类严格分离
> 参考：AccelWorld `config/static/`（static_config.py + config.json 引导映射表 + base.json 应用参数 + ui.json UI 参数）+ `config/settings.py`（UserConfig，默认值从静态配置现取）
> 边界：业务逻辑常量（SQL 表达式、正则、ASSISTANT_ROLE、维度枚举）**不抽**，保持代码内；只抽"可调参数"
> 路径决策（用户审核确认）：**用户配置移到项目内**（对齐 AccelWorld S9.5 定案：`get_project_root() / base["user_config_path"]` = config/user_config.json）；**凭据 opencode-go.json 保留 `~/.config/myboard/`**（敏感，防误提交 + 打包安全）；**日志保留 `~/.local/share/myboard/`**（打包分发到只读目录时项目内日志会写失败）
> 版本决策（用户审核确认）：**S8 完成后 constants.py 删除**——VERSION 移入 base.json（版本号外置为静态配置，单一来源跟随 json）；`get_project_root()` 放置于 `utils/file_utils.py`（对齐 AccelWorld）

### S8.1 静态配置基础设施（config/static/）

- [x] S8.1.1 新建 `config/static/` 包 + 引导映射表 `config.json`（`{"base": "base.json", "ui": "ui.json"}`）
- [x] S8.1.2 `config/static/static_config.py`：`StaticConfig` dataclass（base/ui 只读）+ `_load_static_config()`（映射表 → 遍历聚合）+ `get_static_config()` 缓存单例（懒加载，`__file__` 自定位）
- [x] S8.1.3 失败策略：映射/文件缺失或损坏抛 `RuntimeError`（开发期快速暴露）；**修复真实 bug**：`_load_static_config` 用 `use_cache=False`（file_utils 缓存导致"改 json 不生效"，static_config 单例为唯一缓存层）
- 状态：✅ 已完成｜优先级：高

### S8.2 应用参数外置（config/static/base.json）

- [x] S8.2.1 窗口与刷新：默认窗口尺寸（760x640）、`REFRESH_INTERVAL_MS`（5 分钟）、`AUTO_LOAD_DELAY_MS`（10ms）——ui/main_window.py 已解包
- [x] S8.2.2 配额节流：`MIN_FETCH_INTERVAL`（60s）、`RETRY_COUNT`（2）/`RETRY_DELAY`（1.0s）——modules/go_quota.py 已解包
- [x] S8.2.3 浏览器/CDP：`CDP_PORT`（9222）、`HISTORY_LIMIT`（200）、`ESENTUTL_TIMEOUT`（30s）、`cdp_login_wait_seconds`（180s）、`cdp_poll_interval`（5s）——modules/browser_creds.py + ui/main_window.py 已解包
- [x] S8.2.4 导出与定价：`EXPORT_LIMIT`（100000）、`PRICE_CACHE_TTL`（86400）、`MODELS_DEV_URL`——exporter/pricing 已解包
- [x] S8.2.5 路径与默认值：`utils/file_utils.py` 新增 `get_project_root()`（校验 main.py）；base.json 增加 `user_config_path`/`default_theme`/`version`；凭据与日志路径不进 base.json（决策保留）
- [x] S8.2.6 硬编码常量删除：6 个文件 17 处硬编码全部清除（verify_s12 防回归检查），解包值与原值一致
- 状态：✅ 已完成｜优先级：高

### S8.3 UI 参数外置（config/static/ui.json）

- [x] S8.3.1 配额颜色与阈值：`QUOTA_COLOR_OK/WARN/DANGER`、`QUOTA_WARN_PERCENT`/`QUOTA_DANGER_PERCENT`、托盘灰 `quota_gray`——ui/themes.py + ui/system_tray.py 已解包（分级函数行为不变）
- [x] S8.3.2 托盘与通知：`ICON_SIZE`（128）、`NOTIFY_DURATION_MS`（5000）——ui/system_tray.py 已解包
- [x] S8.3.3 表格列文案 `TABLE_HEADERS`（9 列中文表头）→ ui.json list——ui/main_window.py 已解包（维度枚举 DIMENSIONS 保留代码内）
- 状态：✅ 已完成｜优先级：中

### S8.4 用户配置改造（config/settings.py）

- [x] S8.4.1 `AppConfig` 默认值从 `get_static_config()` 现取（`theme` → default_theme、`refresh_interval_ms` → base.json），代码内默认值硬编码清除
- [x] S8.4.2 用户配置路径对齐 AccelWorld：`get_project_root() / base["user_config_path"]` = 项目内 `config/user_config.json`（与 AccelWorld 一致随项目走、被 git 跟踪）；**凭据路径 go_quota.CREDENTIALS_FILE 保持 `~/.config/myboard/opencode-go.json` 不变**
- 状态：✅ 已完成｜优先级：中

### S8.5 各模块引用改造（顶层一次性解包，运行时零 IO）

- [x] S8.5.1 `ui/main_window.py`：窗口尺寸/刷新间隔/启动延迟 → `_SC` 解包（S8.2 提前完成）
- [x] S8.5.2 `modules/go_quota.py`：节流/重试 → 静态配置（S8.2 提前完成，URL 属接口常量保留代码内）
- [x] S8.5.3 `modules/browser_creds.py`：CDP 端口/超时/上限 → 静态配置（S8.2 提前完成）
- [x] S8.5.4 `modules/exporter.py`：EXPORT_LIMIT → 静态配置（S8.2 提前完成）
- [x] S8.5.5 `modules/pricing.py`：TTL/URL → 静态配置（S8.2 提前完成）
- [x] S8.5.6 `ui/themes.py` + `ui/system_tray.py`：调色板阈值/图标参数 → ui.json（S8.3 提前完成）
- [x] S8.5.7 **constants.py 删除与 VERSION 迁移**：VERSION 移入 base.json `version` 字段——main.py 与 ui/main_window.py 改为 `get_static_config().base["version"]` 读取；`config/constants.py` 已删除；连带同步：README 结构/badge 链接、verify_s9 断言改 base.json、verify_s11 文件清单、AGENTS.md 与 x.progress 导入命令移除 config.constants
- 状态：✅ 已完成｜优先级：中

### S8.6 验证

- [x] S8.6.1 `.temp/verify_s12.py` 17 项：静态配置加载正确性（映射/缺失抛错/缓存单例单次 IO/改 json 后生效）+ 各模块解包值一致 + **VERSION 单一来源断言**（base.json `version` == main.VERSION）
- [x] S8.6.2 全量回归：verify_s1-s14 共 **328 项全部通过** + GUI offscreen 初始化 OK
- [x] S8.6.3 AGENTS.md 更新：结构与约定章节重写——config 两类配置说明（static 只读 json 驱动 / settings 用户配置项目内）+ 新约定"可调参数一律走 config/static/*.json，禁止代码硬编码；版本号唯一来源为 base.json version 字段；凭据与日志保持在用户目录"
- 状态：✅ 已完成｜优先级：高

### S8.7 文档同步

- [x] S8.7.1 README：项目结构树含 config/static/（S8.5 已更新）+ 新增"配置参数（json 驱动）"小节（base.json/ui.json 全参数清单 + 生效说明）+ Q5 答案修正（用户配置移项目内 config/user_config.json，凭据仍在 ~/.config）
- [x] S8.7.2 z.plan.md 第五章结构树更新：config/ 展开为 settings.py + static/ 四文件（映射表/base/ui/加载器），VERSION 来源、utils 清单同步
- 状态：✅ 已完成｜优先级：低

---

## V0.08 P2-P8 整体改造（依据 z.plan.md 第十章）

> 目标：P2-P8 七个问题一次整体改造——凭据/路径治理（P2 目录集中项目内 + P3 删 API key 链路 + P4 凭据加密 + P6 删跨项目探测）+ 展示修正（P5 重置时间 + P7 日期倒序）+ 月度统计（P8）
> 决策（2026-08-10 已定案，见 z.plan.md 10.4）：D1 目录集中项目内 + utils 层引用配置（方案 C）/ D2 手动填写改 GUI 对话框 / D3 win32crypt 缺失拒绝写入 / D4 连带导出 by_month / D5 提交由用户执行
> 已定稿的文档层改动（不再重复）：z.plan.md 第十章 ✅、AGENTS.md 分层放宽 + 参数约定 ✅、.gitignore 清理冲突残留 + 增加 data/ 忽略 ✅、base.json 新增 credentials_dir/logs_dir/prices_dir ✅
> 执行原则：每项完成后运行对应验证；全部完成后全量回归

### V0.08.1 P6 移除跨项目凭据路径探测（最小改动，先做）

- [x] P6.1 `modules/go_quota.py` `_dashboard_config_paths`：sub 循环 `("myboard", "opencode-bar", "opencode-quota")` → 仅 `("myboard",)`（XDG 系列与 `~/.config` 系列两处）
- [x] P6.2 `_dashboard_config_paths` 函数注释与模块说明区同步（`~/.config/{myboard,opencode-bar,opencode-quota}/` 描述更新）
- [x] P6.3 验证：verify_s3 凭据探测测试通过（mock 注入路径不受影响）+ 刷新日志不再出现 opencode-bar/opencode-quota 的 WARNING 噪音
- 状态：✅ 已完成（2026-08-10）｜优先级：中

### V0.08.2 P2 配置与数据目录集中到项目内

- [x] P2.0 文档/配置层（2026-08-10 已定稿）：base.json 三字段 ✅、AGENTS.md 分层放宽与参数约定 ✅、.gitignore 增加 `data/credentials/` `data/logs/` `data/prices/` + 清理 `>>>>>>>` 残留 ✅、z.plan.md 第十章 D1 定案 ✅
- [x] P2.1 `utils/logger.py`：顶层 `_SC = get_static_config()` + `get_project_root()` 拼接 LOG_DIR/LOG_FILE（`logs_dir` 字段）；模块说明区更新（依赖关系、关联配置）
- [x] P2.2 `modules/pricing.py`：PRICE_CACHE_DIR 改 `get_project_root() / Path(_SC.base["prices_dir"])`；import 补 `get_project_root`；说明区更新
- [x] P2.3 `modules/go_quota.py`：CREDENTIALS_FILE 改 `get_project_root() / Path(_SC.base["credentials_dir"]) / "opencode-go.json"`；import 补 `get_project_root`；说明区更新；**关键联动**：`_dashboard_config_paths` 探测链同步收敛为 [$OPENCODE_GO_CONFIG_FILE, CREDENTIALS_FILE]（原 ~/.config/myboard 与 XDG 变体移除，否则保存的凭据探测不到——保存→读取闭环）
- [x] P2.4 循环依赖验证：全量 import 通过（确认 file_utils/static_config 不依赖 logger，logger 依赖 config.static 无环）
- [x] P2.5 `.temp/verify_s12.py` 同步：required 字段加 `credentials_dir`/`logs_dir`/`prices_dir`；解包一致性加 LOG_DIR/PRICE_CACHE_DIR/CREDENTIALS_FILE 与 base.json 拼接比对（Path 单独断言，不走 int 比较）；`test_no_hardcoded_params` 加 `Path.home()` 残留检查（logger/go_quota/pricing 三处）
- [x] P2.6 验证：verify_v0808_p2 13 项 + verify_v0808_p6 复验 9 项 + verify_s12 20 项 + verify_s3 39 项 + verify_s4 29 项 + verify_s7 18 项 + 全量 import + 日志落盘 `data/logs/myboard.log` 全部通过
- [x] P2.7 凭据迁移提醒（已告知用户 2026-08-10）：旧凭据 `~/.config/myboard/opencode-go.json` 需重新"一键自动获取"或手动复制到 `data/credentials/`
- 状态：✅ 已完成（2026-08-10）｜优先级：高

### V0.08.3 P3 删除 API key 链路（程序不接触任何 key）

- [x] P3.1 `modules/go_quota.py` 删除常量：`MODELS_URL`、`AUTH_KEY_FIELDS`；文件头说明同步
- [x] P3.2 `modules/go_quota.py` 删除函数：`find_auth_file` / `read_auth_json` / `strip_json_comments` / `get_opencode_go_key` / `fetch_model_count`
- [x] P3.3 `GoQuotaInfo` 删除字段：`model_count` / `auth_source`；`error_stage` 注释更新（移除 no_key）
- [x] P3.4 `fetch_go_quota` 主流程简化：删除 key 校验段（节流 → 凭据 → 三窗口），顺带清理死代码（`_last_quota = info` 未定义变量两行）
- [x] P3.5 `_build_info` / `_fallback` 签名简化：删 model_count/auth_path 参数
- [x] P3.6 `main()` CLI 自测：删"API key 来源""模型数"打印
- [x] P3.7 模块说明区同步（函数清单、常量说明、设计理由补充 P3 原则）
- [x] P3.8 `ui/main_window.py`：`_render_quota` 元信息删"模型数：未知"；`_on_quota_ready` 注释 no_key 引用更新
- [x] P3.9 `.temp/verify_s3.py`：删 `test_auth_parsing` 整组；`test_http_and_models` → `test_http_layer`（删 fetch_model_count 断言与 models 分支）；`test_flow_and_cache` 删 auth mock、"模型数 2"、"无 key 降级提示"测试
- [x] P3.10 verify 同步：verify_s4（构造删 model_count/auth_source + "含模型数"断言改"含凭据来源"）、verify_s5（`GoQuotaInfo(model_count=1)` → 空构造）、verify_s7（构造删 model_count）、verify_s8（删 fetch_model_count 重试测试，保留 auth 不重试）、verify_s9（no_key 引导测试删除）
- [x] P3.11 残留核验：全源码 grep 无 `fetch_model_count`/`MODELS_URL`/`AUTH_KEY_FIELDS`/`find_auth_file`/`read_auth_json`/`strip_json_comments`/`get_opencode_go_key`/`no_key`/`model_count`/`auth_source`/`auth.json`/`Bearer`/`api key` 任何残留
- [x] P3.12 文档同步：README FAQ（"不读取 API key，仅使用 dashboard 会话凭据"）、AGENTS.md 数据源说明删 auth.json（"auth.json 已不读取（P3）"）
- [x] P3.13 检验：verify_v0808_p3 21 项（key 符号不存在/主流程无 key 步骤/无凭据阶段 no_dashboard_creds/失败提示无 key 文案/CLI 输出无 key）+ 回归 verify_s3 24 项 + verify_s4 29 项 + verify_s5 29 项 + verify_s7 18 项 + verify_s8 14 项 + verify_s9 30 项 + verify_v0808_p2 13 项 + verify_s11 4 项 + 全量 import 全部通过
- 状态：✅ 已完成（2026-08-10）｜优先级：高

### V0.08.4 P4 凭据加密存储（DPAPI，新增 modules/credential_store.py）

- [x] P4.1 新建 `modules/credential_store.py`：`encrypt_credentials` / `decrypt_credentials` / `read_credentials_file`（CryptProtectData/CryptUnprotectData + base64 + 格式标记 `encrypted_v1`）+ 明文旧格式兼容读取 + win32crypt 可选导入 + CredentialEncryptionError + 文件尾说明区
- [x] P4.2 `modules/go_quota.py` `save_dashboard_credentials`：改为经 credential_store 加密写入（写入 `{"encrypted_v1": ...}`）；win32crypt 缺失拒绝写入并抛错（D3=A 安全优先）
- [x] P4.3 `modules/go_quota.py` `_read_credentials_json`：改为经 `credential_store.read_credentials_file` 读取（识别加密标记解密 / 明文兼容）；顺带删除 go_quota 中已无用的 `json` import
- [x] P4.4 `ui/main_window.py` `_manual_guide`：改 QInputDialog 对话框（workspaceId + authCookie 两字段）→ 加密写入 → 自动刷新；删除模板/example 文件生成与"打开文件夹"逻辑；顺带删除无用的 json/os/write_json/CREDENTIALS_FILE import
- [x] P4.5 核验：日志不打印明文凭据（credential_store 仅打印错误消息，无凭据值；verify_v0808_p4 断言日志不含凭据字样）
- [x] P4.6 `.temp/verify_s7.py` 同步：test_save_credentials 改加密格式断言（含解密回读）；test_cdp_guide_success 改加密格式断言；test_manual_guide 重写为对话框流程（输入→加密写入→自动刷新；取消路径不写文件）；`.temp/verify_v0808_p2.py` roundtrip 断言改加密格式
- [x] P4.7 `.temp/verify_v0808_p4.py` 15 项：真实 DPAPI 往返、明文旧格式兼容、go_quota 集成闭环、win32crypt 缺失拒绝写入/宽容读取、日志无明文、现有真实凭据兼容读取
- [x] P4.8 真实验证：真实本机 DPAPI 往返通过（发现并修复 pywin32 两个怪癖——CryptProtectData 直接返回 bytes 非元组、CryptUnprotectData 解密数据在第二个元素）；现有明文凭据 `data/credentials/opencode-go.json` 兼容读取（结构正确）
- [x] P4.9 回归：verify_s3 24 项 + s4 29 项 + s5 29 项 + s7 21 项 + s9 30 项 + s12 20 项 + s11 4 项 + v0808_p2 14 项 + v0808_p3 21 项 + v0808_p6 9 项 + 全量 import 全部通过
- 状态：✅ 已完成（2026-08-10）｜优先级：高

### V0.08.5 P5 配额重置时间显示

- [x] P5.1 `ui/main_window.py` `_render_quota`：`reset_date.strftime('%H:%M')` → `strftime('%m-%d %H:%M')`（"重置于 08-12 06:30"）
- [x] P5.2 验证：`.temp/verify_v0808_p5.py` 6 项（渲染文本含月-日时分、窗口缺失显示"未获取到"、非纯时分、源码防回归）+ verify_s4 29 项回归通过
- 状态：✅ 已完成（2026-08-10）｜优先级：低

### V0.08.6 P7 按日期统计由近到远

- [x] P7.1 `modules/opencode_usage.py` `by_day()`：`order="label ASC"` → `"label DESC"`；函数注释与说明区同步
- [x] P7.2 验证：`.temp/verify_v0808_p7.py` 7 项（3 天数据 by_day 由近到远 + 与升序相反 + 时间过滤后仍倒序 + CLI `--by day` 首行为最新日期）+ verify_s2 30 项回归通过
- 状态：✅ 已完成（2026-08-10）｜优先级：低

### V0.08.7 P8 月度用量统计

- [x] P8.1 `modules/opencode_usage.py` 新增 `by_month()` + `_month_expr()`：`strftime('%Y-%m', datetime(ts/1000,'unixepoch','localtime'))` 分组，`order="label DESC"`（%Y-%m 字符串排序 = 时间排序）
- [x] P8.2 CLI：`--by` choices 加 `month`；methods 映射加 `db.by_month`
- [x] P8.3 `ui/main_window.py`：DIMENSIONS 加 `"month"`（总览后第二位）、DIMENSION_LABELS 加 `"按月份"`、_UsageTask rows 加 `db.by_month(limit=50)`
- [x] P8.4 `modules/exporter.py`：datasets 加 `by_month`（`by_month.csv` + usage.json 字段），导出计数 5 → 6 个 CSV（D4=A）
- [x] P8.5 `.temp/verify_s2.py` 加 by_month 断言（跨月数据：msg_4 在 2025-12、其余 2026-01 → 分组 `["2026-01","2025-12"]` + 消息数 + tokens）
- [x] P8.6 `.temp/verify_s5.py` 导出断言同步（文件列表 6 → 7 个含 by_month.csv；usage.json 结构加 by_month；GUI 导出线程 6 → 7 文件）；`.temp/verify_s4.py` 维度选择改 findText（DIMENSIONS 插入 month 后索引偏移，改用文本查找防回归）
- [x] P8.7 `.temp/verify_v0808_p8.py` 17 项：跨月库 by_month 分组排序/CLI `--by month`/GUI 维度与导出/**真实 opencode.db 验证**（月份行非空、降序、%Y-%m 格式、月份聚合总 token 与日期聚合一致）
- [x] P8.8 回归：verify_s2 33 项 + s3 24 项 + s4 29 项 + s5 29 项 + s7 21 项 + s8 14 项 + s9 30 项 + s12 20 项 + s11 4 项 + v0808_p2-p7 共 72 项 + 全量 import + GUI offscreen 全部通过
- 状态：✅ 已完成（2026-08-10）｜优先级：中

### V0.08.8 验证与文档收尾

- [x] V.1 全量回归：verify_s1-s14 + verify_v0808_p2-p8 共 **409 项断言全部通过**（verify_s1:17 / s2:33 / s3:24 / s4:29 / s5:29 / s6:33 / s7:21 / s8:14 / s9:30 / s10:38 / s11:4 / s12:20 / s13:20 / s14:8 / p2:14 / p3:21 / p4:15 / p5:6 / p6:9 / p7:7 / p8:17）
- [x] V.2 导入验证 + GUI offscreen 初始化 OK
- [x] V.3 README 同步：badge ver 0.08、特性（按月份分组 + 6 CSV）、CLI `--by month`、GUI 维度列表、凭据配置（对话框方式 + DPAPI 加密说明 + data/credentials/ 路径）、结构树（credential_store.py + data/ 运行数据 + logger 路径）、配置参数表（version ver 0.08 + 三个 dir 字段）、依赖表（pywin32 加密）、FAQ Q1/Q5
- [x] V.4 AGENTS.md 残留核验：无过时表述（唯一匹配为正确正文本）
- [x] V.5 z.plan.md：头部实施状态更新（V0.08 完成）+ 第十章实施标记
- [x] V.6 `config/static/base.json` `version` 更新为 `ver 0.08`（`main.py --version` 验证输出 ver 0.08）
- [x] V.7 x.progress.md 完成记录回填（本节 + 验证总览）
- [x] V.8 交付说明：凭据迁移已完成（旧用户目录 → data/credentials/，P4 后 DPAPI 加密迁移）；提交由用户执行
- 状态：✅ 已完成（2026-08-10）｜优先级：高

---

## V0.08 验证总览（P2-P8 整体改造）

> V0.08 全量回归 **409 项断言全部通过**（verify_s1-s14 基线 328 项含删改后 + verify_v0808_p2-p8 新增 103 项）——2026-08-10 实施完毕
> P2-P8 全部完成：P6 删跨项目探测 → P2 目录集中项目内 → P3 删 API key 链路 → P4 凭据 DPAPI 加密 → P5 重置时间 → P7 日期倒序 → P8 月度统计
> 遗留：P1（多账户区分）、P9（workspace 区分）、P10（二次审计）、P11（明文兼容去留）待评估，见 y.problem.md

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
