# 开发进度追踪（x.progress.md）

> 依据：`z.plan.md`（myboard 初步方案报告）
> 当前版本：ver 0.0（开发起点，VERSION 单一来源在 main.py）
> 记录格式：状态 [⏳ 待开发, ✅ 已完成] / 优先级 [高, 中, 低]
> 执行原则：每阶段完成后运行验证命令确认无回归，再进入下一阶段

---

## S1 骨架搭建（对应 z.plan.md 第七章 S1）

> 目标：建立包结构、项目文档、git 仓库，安装依赖，空模块可导入

### S1.1 项目初始化

- [x] S1.1.1 创建 `modules/config/ui/utils/data` 包结构及各 `__init__.py`（对应 z.plan.md 第四章目录树）
- [x] S1.1.2 编写 `AGENTS.md`（参照 AccelWorld 规范：注释规则/代码约定/验证命令/环境陷阱）
- [x] S1.1.3 编写 `z.plan.md` 初步方案
- [x] S1.1.4 `reference/` 克隆 3 个参考项目（opencode-bar / opencode-usage / OpenCode-Token，浅克隆）
- [x] S1.1.5 `.gitignore`（合并 GitHub 模板 + 项目特有：reference/、.temp/、凭据文件）
- 状态：✅ 已完成｜优先级：高

### S1.2 git 仓库

- [x] S1.2.1 `git init`（main 分支）+ 项目本地 user 配置（pyapple12 / takechance_bao@188.com）
- [x] S1.2.2 绑定远程 `git@takechance:pyapple12/mrboard.git`（SSH 账号 B）
- [x] S1.2.3 整理干净单线历史（reset --soft 到网页 Initial commit 后重新提交）
- [x] S1.2.4 首次 push + 建立 tracking 关系
- 状态：✅ 已完成｜优先级：高

### S1.3 环境与入口

- [ ] S1.3.1 创建 `.venv` 并安装 `requirements.txt`（PyQt6）
- [ ] S1.3.2 编写 `main.py` 入口：GUI 分发 + `VERSION` 常量单一来源
- 状态：⏳ 待开发｜优先级：高

### S1.4 utils 基础骨架

- [ ] S1.4.1 `utils/logger.py`：统一日志（控制台+文件双 handler，`get_logger(name)`）
- [ ] S1.4.2 `utils/file_utils.py`：pathlib 封装 JSON 读写 + 缓存单例
- [ ] S1.4.3 `utils/retry.py`：泛型重试 `retry_call(func, *args, retries, exceptions, delay, **kwargs)`
- 状态：⏳ 待开发｜优先级：高

### S1.5 验证

- [ ] S1.5.1 导入验证：`.\.venv\Scripts\python.exe -c "import main, modules.opencode_usage, modules.go_quota, config.settings, ui.main_window, ui.system_tray, ui.themes, utils.logger, utils.file_utils, utils.retry"`
- [ ] S1.5.2 GUI 无头初始化：`$env:QT_QPA_PLATFORM="offscreen"; ... print('GUI init OK')`
- 状态：⏳ 待开发｜优先级：高

---

## S2 用量统计模块（对应 z.plan.md 3.1 与 S2）

> 目标：读取本地 opencode.db，统计 tokens/费用/会话，支持多维度聚合（参考 reference/opencode-usage）

### S2.1 数据源探测

- [ ] S2.1.1 多路径探测 opencode.db：`%USERPROFILE%\.local\share\opencode\`、`%USERPROFILE%\.config\opencode\` 等（参考 opencode-bar 多路径模式）
- [ ] S2.1.2 探测数据库结构（表/字段），确认 tokens/cost 字段来源
- 状态：⏳ 待开发｜优先级：高

### S2.2 统计核心

- [ ] S2.2.1 dataclass：`UsageSummary`/`UsageEntry`（时间/模型/provider/agent/tokens 明细）
- [ ] S2.2.2 时间过滤：全部 / 最近 7 天 / 最近 30 天
- [ ] S2.2.3 分组聚合：按 model、provider、agent（含子 agent）、日期
- [ ] S2.2.4 费用计算：优先数据库已记录 cost；缺失时走定价估算
- 状态：⏳ 待开发｜优先级：高

### S2.3 定价模块

- [ ] S2.3.1 `modules/pricing.py`：models.dev 定价表 + 本地缓存（参考 OpenCode-Token prices.json 机制）
- [ ] S2.3.2 cache read/write 折扣价处理
- 状态：⏳ 待开发｜优先级：中

### S2.4 验证

- [ ] S2.4.1 CLI 输出对照 `opencode stats` / `opencode stats --models` 数据一致
- 状态：⏳ 待开发｜优先级：高

---

## S3 Go 配额模块（对应 z.plan.md 3.2 与 S3）

> 目标：读取凭据并拉取 OpenCode Go 5h/周/月配额（移植 reference/opencode-bar 的 OpenCodeGoProvider.swift）

### S3.1 凭据探测

- [ ] S3.1.1 解析 `auth.json` 的 `opencode-go` 条目（API key）
- [ ] S3.1.2 workspaceId + authCookie 多路径探测：环境变量 `OPENCODE_GO_WORKSPACE_ID`/`OPENCODE_GO_AUTH_COOKIE` → `~/.config/myboard/opencode-go.json` → 其他路径
- [ ] S3.1.3 凭据仅在内存使用，严禁写入仓库/日志
- 状态：⏳ 待开发｜优先级：高

### S3.2 接口调用

- [ ] S3.2.1 key 校验：请求 `https://opencode.ai/zen/go/v1/models`（参考 OpenCodeGoProvider.swift:44）
- [ ] S3.2.2 配额拉取：5 小时 / 每周 / 每月三个窗口的已用量/剩余量/百分比
- [ ] S3.2.3 接入 `utils/retry.py` 重试 + 失败回退缓存数据
- 状态：⏳ 待开发｜优先级：高

### S3.3 降级策略

- [ ] S3.3.1 接口失效时：仅显示本地用量统计 + 明确提示配额不可用（对应 z.plan.md 待确认问题 1）
- [ ] S3.3.2 Cookie 过期/凭据变更时的提示与重新配置引导
- 状态：⏳ 待开发｜优先级：中

### S3.4 验证

- [ ] S3.4.1 打印 5h/周/月 数值与百分比，人工核对 dashboard
- 状态：⏳ 待开发｜优先级：高

---

## S4 GUI 界面（对应 z.plan.md 3.3 与 S4）

> 目标：主窗口 + 系统托盘 + 主题 + 定时刷新

### S4.1 主题

- [ ] S4.1.1 `ui/themes.py`：LIGHT/DARK 双主题 QSS（对齐 AccelWorld themes 模式）
- 状态：⏳ 待开发｜优先级：中

### S4.2 主窗口

- [ ] S4.2.1 `ui/main_window.py`：用量总览卡片（总 tokens/总费用/会话数）+ 分组表格
- [ ] S4.2.2 Go 配额进度条面板（5h/周/月 三窗口，颜色分级）
- [ ] S4.2.3 数据加载走后台线程（QThreadPool），不阻塞 UI
- [ ] S4.2.4 `QTimer` 定时刷新（约 5 分钟）+ 手动刷新按钮
- 状态：⏳ 待开发｜优先级：高

### S4.3 系统托盘

- [ ] S4.3.1 `ui/system_tray.py`：常驻图标 + 菜单（显示窗口/刷新/退出）
- [ ] S4.3.2 退出前保存配置（对齐 AccelWorld 修复 B2 的经验）
- 状态：⏳ 待开发｜优先级：中

### S4.4 验证

- [ ] S4.4.1 GUI 无头初始化 + 手动冒烟（切主题/刷新/托盘退出后配置保留）
- 状态：⏳ 待开发｜优先级：高

---

## S5 完善收尾（对应 z.plan.md 3.1 导出与 S5）

> 目标：配置持久化、数据导出、文档收尾

### S5.1 配置持久化

- [ ] S5.1.1 `config/settings.py`：`AppConfig` dataclass + JSON 存 `~/.config/myboard/config.json`（窗口位置/刷新间隔/主题）
- 状态：⏳ 待开发｜优先级：中

### S5.2 数据导出

- [ ] S5.2.1 CSV 导出（UTF-8 BOM，Excel 直接打开，参考 OpenCode-Token）
- [ ] S5.2.2 JSON 导出（供脚本处理）
- 状态：⏳ 待开发｜优先级：低

### S5.3 代码规范与文档

- [ ] S5.3.1 全部 .py 文件补齐函数下方 `#` 注释 + 文件末尾 `# =====` 说明区（AGENTS.md 规范）
- [ ] S5.3.2 更新 README（启动方式、功能说明、凭据配置说明）
- 状态：⏳ 待开发｜优先级：中

---

## 阶段验证命令速查（AGENTS.md 运行与验证）

```powershell
# 导入验证
.\.venv\Scripts\python.exe -c "import main, modules.opencode_usage, modules.go_quota, config.settings, ui.main_window, ui.system_tray, ui.themes, utils.logger, utils.file_utils, utils.retry"

# GUI 无头初始化验证（不弹窗）
$env:QT_QPA_PLATFORM="offscreen"; .\.venv\Scripts\python.exe -c "from PyQt6.QtWidgets import QApplication; from ui.main_window import MainWindow; app = QApplication([]); w = MainWindow(); print('GUI init OK')"
```
