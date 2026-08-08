# 开发进度追踪（x.progress.md）

> 依据：`z.plan.md`（myboard 方案报告）
> 当前版本：ver 0.05（VERSION 单一来源在 config/constants.py）
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
