# myboard 项目说明

单包 Python 桌面应用：Windows 上的 OpenCode 用量统计 + OpenCode Go 配额监控信息窗口（PyQt6，中文界面为主）。无测试套件、无 lint/格式脚本、无构建步骤。

## 运行与验证

- 入口 `main.py`：GUI 为默认模式；版本号 `VERSION` 单一来源在 `config/static/base.json` 的 `version` 字段，由 `utils/logger.py` 单点导出（main.py/main_window.py/system_tray.py 共引，D1/R4 模式）
- 没有测试/lint 命令。改动后验证：`.\.venv\Scripts\python.exe -c "import main, modules.opencode_usage, modules.go_quota, modules.pricing, modules.exporter, modules.browser_creds, modules.credential_store, config.settings, config.static.static_config, ui.main_window, ui.system_tray, ui.themes, utils.logger, utils.file_utils, utils.retry, utils.convert, utils.network, utils.windows, utils.sqlite_utils"`。不要直接跑 GUI 验证（会弹窗阻塞）；功能验证脚本在 `.temp/verify_*.py`（当前 43 个：s1-s14 基线 + v0808/v0809/v1010/3A/4A/5A/6A 各批次，全量回归 = 全部运行；分批次清单见 x.progress.md"阶段验证命令速查"，AGENTS.md 不再重复维护）
- GUI 无头初始化验证（不弹窗）：`$env:QT_QPA_PLATFORM="offscreen"; .\.venv\Scripts\python.exe -c "from PyQt6.QtWidgets import QApplication; from ui.main_window import MainWindow; app = QApplication([]); w = MainWindow(); print('GUI init OK')"`
- 依赖（`requirements.txt`）：PyQt6（其余按需添加，见 z.plan.md）

## 环境陷阱

- `.venv` 是机器绑定的：`pyvenv.cfg` 的 `home` 指向创建时机器的 Python 路径。换机器/换用户后解释器损坏，症状是 VSCode Python 扩展报 `write EPIPE / Shutting down server`（Jedi 语言服务器无法启动）。重建：`Remove-Item -Recurse -Force .venv; py -3.14 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt`，然后在 VSCode 重选解释器
- 数据源路径（Windows）：opencode.db 位于 `%USERPROFILE%\.local\share\opencode\`，路径探测必须兼容不同安装方式（见 reference/opencode-bar 的多路径探测）；auth.json 已不读取（P3：程序不接触任何 API key，仅使用 dashboard 会话凭据）

## 结构与约定

- 包结构按依赖单向分层（参考 AccelWorld）：`utils/` 通用工具（file_utils/retry/convert 无业务依赖；logger 允许依赖 `config.static` 读取日志路径，不依赖其他业务模块）→ `config/` 配置 → `modules/` 业务核心（opencode_usage 用量统计、go_quota Go 配额、pricing 定价、exporter 导出、browser_creds 浏览器凭据）→ `ui/` 界面（main_window 主窗口、system_tray 托盘、themes 主题 QSS）→ `data/` 静态数据 + 运行数据（凭据/日志/价格缓存）
- `config/` 配置分两类（S8 定案，对齐 AccelWorld）：
  - **静态配置**（`config/static/`，只读，json 驱动）：`static_config.py` 加载器 + `config.json` 引导映射表 + `base.json`（应用参数：版本/间隔/端口/上限等）+ `ui.json`（UI 参数：颜色/阈值/表头）；模块顶层 `_SC = get_static_config()` 一次性解包，运行时零 IO
  - **用户配置**（`config/settings.py`，可读写）：AppConfig dataclass，存项目内 `config/user_config.json`（路径由 base.json `user_config_path` 指定）
- **参数约定**：可调参数一律走 `config/static/*.json`，禁止代码硬编码；版本号唯一来源为 `base.json` 的 `version` 字段；所有配置与数据目录集中在项目内——凭据（opencode-go.json）、日志、价格缓存路径由 base.json 的 `credentials_dir` / `logs_dir` / `prices_dir` 指定（相对项目根，运行时生成、已 gitignore），**不使用用户目录**
- **契约层定案（P23，2026-08-13）**：结构键名（COLUMN_IDS/DIMENSIONS/_UI_STRUCT_KEYS/字段键集等）以**代码内显式声明 + 导入期校验**为健康标准，**不外置**——三重约束：①校验悖论（期望标准须独立于实际，外置后失去比对基准）②语义绑定（键名对应渲染/格式化分支，外置后分支仍在代码）③信息论（接口标识符必须双方声明）；AST 生成器方案为负收益（派生物非独立标准 + 引入构建链）不采用；其展示元数据（列宽/默认可见性等纯数据）随 P25 view 配置层外置。审计遇契约层问题直接引用本条，不再重开讨论
- `main.py` 收编 GUI 分发；模块间顶层 import，不要使用函数内延迟 import
- 提交信息按 Git 注意章节的 Commit 提交规范（V2）书写，如 `feat: V0.09，UI 改版与维护...`
- 项目规划与方案文档在 `z.plan.md`
- `reference/` 目录是外部项目的 git clone（浅克隆），**不纳入本仓库版本控制**；需要更新时重新 clone

## 工程原则（设计哲学，所有项目通用）

> 设计哲学总纲（18 条 / 5 大类，与用户级 instructions.md 同源）；下文"代码规范"为项目细则，两者冲突时以本项目边界为准。

### 核心思想

- 以第一性原理思考问题：理解需求背后的真实目标，而非直接套用已有模式或技术方案。
- 优先解决本质问题，避免为假设中的未来需求提前设计复杂系统。
- 在保证长期可维护性的前提下，选择当前最简单、可靠、清晰的实现方案。

### 简洁与设计

- 遵循 KISS：优先选择简单直接的实现，避免不必要的复杂度。
- 遵循 DRY：避免重复逻辑，但不要为了消除少量重复而创建过度抽象。
- 遵循 SOLID 思想：职责清晰、降低模块耦合，提高可维护性和扩展能力。

### 架构

- 不长期保留废弃方案：优先删除过时代码，而不是增加兼容层、fallback 或临时迁移逻辑。
- 不进行未经验证的架构设计：避免提前引入抽象、配置和间接层。
- 从最小可工作的版本开始逐步演进，每次修改建立在已有可运行系统之上。
- 永远不要用未来可能需要的复杂性，牺牲当前产品的可用性。

### 代码质量

- 保持模块职责明确，避免一个模块承担过多职责。
- 优先使用成熟、稳定、维护良好的第三方库，而不是重复造轮子。
- 使用项目已有依赖解决问题之前，不要随意新增依赖。
- 在引入新方案前，先检查已有代码、依赖、文档和能力。
- 避免为了"看起来更优雅"而增加实际复杂度。

### 工程决策

- 优先选择长期可维护的方案，而不是只能临时运行的解决方案。
- 代码应该服务于业务目标，而不是为了展示技术复杂度。
- 如果简单方案已经满足需求，不要主动升级为复杂方案。

### 本项目边界（消解原则与项目规范的表面张力）

- **参数外置 vs 避免过度配置化**：以 S8 定案为准——业务逻辑常量（SQL/正则/维度枚举）不抽，只抽"可调参数"；原则"避免提前引入配置和间接层"不覆盖既有外置体系
- **审计整改机制 vs 不升级复杂度**：原则约束编码决策；项目审计/文档/验证流程为用户既定工作流，不受"简单方案不升级"覆盖

## 代码规范

### 错误策略（z.plan.md 第四章，参考 opencode-bar / opencode-usage / OpenCode-Token）

常驻桌面应用的错误处理主线：**不崩溃、不阻塞、有提示、能自愈**。传统"抛异常就崩、出错就弹窗"对常驻应用不可接受。

- 统一错误类型：业务错误定义分类异常（如 `GoQuotaError` 的 auth/network/decoding/provider），携带中文消息；UI 只认分类不认细节
- 降级不中断：多数据源/多 provider 任一失败不影响整体；非核心子系统失败仅状态栏提示，不弹窗
- 缓存兜底：网络失败返回上次缓存数据 + 标注来源（`is_cached` + 错误原因），不显示空白
- 宽容解析：外部数据（opencode.db 结构、dashboard HTML、配置/价格文件）格式可能变更——数字字段可能是字符串（弹性转换）、坏 JSON 返回空不崩溃、None 语义区分"未记录"与 0
- 节流 + 去重：非官方接口（dashboard HTML）设 `minimumFetchInterval` 节流 + in-flight 去重，防频繁刷新打爆接口
- 保留旧数据：刷新失败保留旧 view，成功后视图才替换
- 只读防误写：opencode.db 一律只读连接（`mode=ro`），从源头杜绝误写
- 窗口缺失容忍：dashboard 单窗口解析失败仅警告，全部缺失才报错（markup 可能变更）

### 函数注释规则

- 每个函数定义下方紧跟 `#` 注释，说明该函数的用途和核心逻辑（1-3 行）
- **禁止使用 docstring（三引号字符串）替代 `#` 注释**——函数/类/模块文档统一走 `#` 注释体系，docstring 不承担注释职责；单行 docstring 当注释用属于违规（`.temp/verify_s11.py` 自动检测）
- 每个 `.py` 文件末尾必须有完整的函数逻辑说明区，用 `# =====` 分隔，涵盖文件中所有函数/模块级常量：
  - 输入、输出、逻辑步骤
  - 设计理由（为什么这样做）
  - 异常处理说明
  - 关联的配置或外部依赖

### 代码约定

- 注释必须用 `#`，禁止 `//` 或其他语言注释符号；所有注释使用中文
- 命名风格：函数/变量用 `snake_case`，类用 `CamelCase`，常量用 `UPPER_CASE`
- `_` 前缀：函数名前加 `_` 表示模块内部私用，如 `_format_tokens()`，外部模块不应直接调用
- `def main()`：每个可独立运行的脚本都有 `main()` + `if __name__ == "__main__": main()`
- 类型注解：优先使用 Python 类型注解，包括 `typing` 模块和 `| None` 语法
- dataclass：配置聚合优先用 `@dataclass`
- import 顺序：标准库 → 第三方库 → 本地模块，每组之间空行分隔
- f-string：字符串格式化优先用 f-string，避免 `.format()` 或 `%`
- 推导式：优先用列表/字典推导式而非手写 for 循环构建集合
- 布尔值判断：用 `if x:` / `if not x:` 而非 `if x == True:` / `if x is False:`
- 空值判断：用 `if x is None:` / `if x is not None:` 而非 `if x == None:`
- 异常捕获：避免裸 `except:`，至少用 `except Exception:`，指定具体异常类型更好；捕获多个异常类型可用 `except (Exc1, Exc2):`
- 行长度：每行尽量不超过 100 字符（超过时在运算符或逗号后换行）
- 空格约定：逗号后加空格、冒号前不加空格（切片冒号两侧不加）、赋值/比较运算符两侧加空格、函数定义前后各空两行、类定义前后各空两行、方法之间空一行
- 字符串引号：普通字符串用双引号，文档字符串用 `"""` 三引号；f-string 内含大量双引号时允许外层使用单引号
- 路径处理：强制使用 `pathlib` 代替 `os.path`
- 临时文件：所有临时生成的脚本/文件必须写入项目根目录下的 `.temp/` 文件夹（已 gitignore）

## Git 注意

- `.gitignore` 忽略 `.venv`、`reference/`、`archived/`、`.temp/`、`config/user_config.json`、`data/credentials/`、`data/logs/`、`data/prices/`、`opencode-go.json`（含配额凭据）—— 对这些文件的修改不会出现在 `git status` 中；`AGENTS.md` 已纳入版本控制
- 严禁将 API key、authCookie、workspaceId 等凭据提交到仓库
- 未经用户明确要求，不得擅自执行 `git add`、`git commit` 或任何其他 Git 写操作

### Commit 提交规范（V2，2026-08-10 定稿）

- **标题行**：`<type>: V<版本>，<摘要>`——版本号与 base.json `version` 字段一致；摘要一句话概括核心（可用括号列重点）
- **type 全集**（conventional 风格）：
  - `feat` 新功能 / `fix` 修复 / `refactor` 重构（行为不变）/ `perf` 性能
  - `docs` 文档 / `test` 测试 / `style` 格式 / `build` 构建依赖 / `ci` CI / `chore` 杂项 / `revert` 回滚
- **正文**（改动大时可选）：`- ` 列表，每个功能块一行自然中文描述，每行 ≤ 100 字符
- **禁止项**：内部编号（P2/S8/D1 等规划编号）、验证/回归数字（如"全量回归 506 项通过"）、英文混排描述
- **提交范围**：一个版本的所有连带改动一次提交（源码 + 配置 + 文档同步）
- **流程**：由 AI 根据 `git status`/`git diff` 核对清单并草拟 commit 内容（git add 清单 + message）→ 用户审阅后自行执行 `git add`/`git commit`/`git push`（AI 不执行 git 写操作）

## 操作注意

- **任务前强制 skill 搜索**：每轮新任务开始，先检查系统提示中 available_skills 列表，按触发词匹配（"推进任务/研究 progress.md 章节" → progress-task；"审计项目/全量审计/再次审计" → audit-project；"归档审计报告/写入 plan" → audit-report；"创建/编辑 opencode 自身配置" → customize-opencode），匹配即调用 skill 工具加载并严格按其指令执行（流程/TDD/验证/硬性约束逐条遵守，与记忆冲突时以 skill 为准）；无匹配才自行处理并说明。禁止仅凭上下文记忆执行 skill 流程（指令可能被上下文冲淡）
- **文件修改必须用 edit 工具**：修改任何既有文件（.py 代码、.md 文档、json 配置等）一律使用 edit 的精确 oldString/newString 替换，禁止用 Python 脚本（python -c / .temp/impl_*.py）或 PowerShell 命令执行内容替换（易踩引号/缩进/控制字符坑）；新建 .temp 探针/verify 脚本不受限（write 创建），但后续修改仍走 edit
- **修复验证独立化**（A010 教训：C0.1 字段名漏网因 probe 用与实现同源的手写 mock）：探针/verify 的结构性样例必须来自真实数据快照或独立证据（如现网 api.json 片段、官方 schema 字段名），禁止手写与实现一致的 mock 自证；手写 mock 仅用于"行为"（如 mock http_get 抛错）不用于"结构"
- **异步任务测试模板**（A017/PL006 教训：mock 上下文先于 worker 结束撤销，导致真实浏览器调用挂起 120s+）：涉及 QThreadPool/后台线程的场景，`with mock.patch(...)` 必须包住"提交 + 轮询等待 + 断言"全程——等待循环内持续 `app.processEvents()` 派发队列信号；禁止在 with 外做任何依赖 patch 生效的断言
- **挂起/崩溃立即抓线程栈**：测试进程挂起或 0xC0000409 秒杀时，第一动作是 faulthandler 线程栈转储**写文件**（stderr 会被 fail-fast 截断），按栈定位卡点；禁止在未定位前做逐个猜测性修补（PL006 实测：盲猜三轮 vs 栈转储一次定位）
- **QThreadPool + QRunnable 必须持引用**：QRunnable 子类提交池后若 Python wrapper 无引用，worker 运行期被 GC 触发 0xC0000409 崩溃——用 `_live_tasks` 集合 + 完成后转 `deque(maxlen=N)` 保引用；或 setAutoDelete(False) 由 Python 全权管理生命周期
- **版本号格式变更需全链路同步**：base.json / README 徽章 / x.progress 版本行三处一致外，还需排查历史 verify 脚本中 startswith("ver ") 式格式快照断言（V0.2.4.3 四段式切换实测漏 s1/s9/s12 三处）
- 执行命令前先检测当前 shell（Windows 下为 pwsh）：使用 PowerShell 兼容命令（`Select-String` 替代 `grep`，`Get-ChildItem` 替代 `ls` 等），避免 Linux-only 工具
- pwsh 会话带 `-NoProfile` 不加载 `$PROFILE`，输出中文前必须先设置编码：`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;`
- 未经用户明确要求，不得擅自执行 `git add`、`git commit` 或任何其他 Git 写操作
