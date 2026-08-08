# 参考项目学习笔记（w.study.md）

> 学习日期：2026-08-08
> 目的：深度阅读 reference/ 下 3 个参考项目，总结其功能实现方法与代码规范，为 myboard 开发提供依据
> 阅读范围：
>
> - `reference/opencode-bar`（Swift，macOS 菜单栏，OpenCode Go 配额监控）
> - `reference/opencode-usage`（Python CLI，SQLite 用量统计）
> - `reference/OpenCode-Token`（Python GUI/CLI，token 分析 + 定价）

---

## 一、opencode-bar（Go 配额监控）

### 1.1 项目概览

macOS 菜单栏应用（LSUIElement），聚合监控 20 个 AI provider 的配额/用量，含 EOM 预测、订阅成本、Sparkle 自动更新。技术栈：Swift + AppKit（NSMenu/NSStatusItem），Swift Concurrency（async/await、actor、TaskGroup），SPM 管理依赖。

### 1.2 架构分层

```
App/      @main → AppDelegate → StatusBarController
Helpers/  MenuDesignToken（UI token 集中）、MenuResultBuilder（result builder DSL）、ProviderMenuBuilder
Models/   ProviderProtocol、ProviderUsage、ProviderResult、SubscriptionSettings、UsageHistory
Services/ TokenManager（auth.json 解析单例）、ProviderManager（actor）、UsagePredictor、BrowserCookieService
Providers/ 20 个 provider 各一文件，全部实现 ProviderProtocol
```

核心抽象：`ProviderProtocol`（identifier/type/fetchTimeout/minimumFetchInterval/`fetch() async throws -> ProviderResult`），payAsYouGo / quotaBased 两种类型。

### 1.3 OpenCode Go 配额完整实现（重点移植对象）

**API Key 凭据**：`auth.json` 的 `"opencode-go"` 条目 `{"type":"apiKey","key":"sk-..."}`。

**Key 校验 + 模型数**：`GET https://opencode.ai/zen/go/v1/models`，Header `Authorization: Bearer <key>`；响应依次尝试 `data[]` / `models[]` / 裸数组，取长度 = 模型数。

**Dashboard 用量（HTML 抓取，非 JSON API）**：

- URL：`https://opencode.ai/workspace/<workspaceID>/go`
- Header：`Cookie: auth=<authCookie>`（自动补 `auth=` 前缀）、Chrome UA
- 解析：① HTML 实体反转义（`&quot; &amp; &#34; \u0022` 等）→ ② 正则 `["']?field["']?\s*:\s*(?:\$R\[\d+\]\s*=\s*)?\{(?<body>[^{}]*)\}` 抓对象体（兼容 `"rollingUsage":$R[12]={...}` 赋值形式）→ ③ 抓 `usagePercent` 与 `resetInSec` 字段
- 三个窗口：`rollingUsage`（5h）、`weeklyUsage`（7d）、`monthlyUsage`；`resetDate = now + resetInSec`
- **窗口缺失容忍**：单窗口解析失败仅警告，全部失败才报错
- 结果：`overallUsed = max(各窗口百分比)`，`remaining = max(0, 100 - used)`
- 官方限制：5h $12 / 周 $30 / 月 $60

**Dashboard 凭据候选优先级**（逐个尝试，首成功即返回）：

1. 环境变量 `OPENCODE_GO_WORKSPACE_ID` + `OPENCODE_GO_AUTH_COOKIE`
2. 配置文件 opencode-go.json（key 兼容 `workspaceId/workspaceID/workspace_id` 与 `authCookie/auth_cookie/cookie`）：
   - `$OPENCODE_GO_CONFIG_FILE`、`$XDG_CONFIG_HOME/opencode-bar|opencode-quota/`、`~/.config/...`、`~/Library/Application Support/...`
3. 浏览器 cookie：`auth` cookie + 历史 URL 正则 `/workspace/(wrk_[A-Z0-9]+)` 提取 workspaceID

- 去重键：`workspaceID::authCookie`

**ProviderManager 并发与健壮性**（三层保护）：

- `withTaskGroup` 并行拉取所有 provider，错误与结果分离收集（部分失败不影响整体）
- in-flight 并发去重（同 identifier 复用同一 Task）
- `minimumFetchInterval` 节流（Go 用 60s）+ 失败用缓存兜底

**auth.json 解析健壮性**：

- 多路径：XDG_DATA_HOME → ~/.local/share → ~/Library/Application Support
- jsonc 注释剥离（状态机）、OAuth/APIKey 混合 schema 逐条 lossy 解码（单条异常不影响整文件）
- expires 相对/绝对启发式（<1e9 相对秒 / ≥1e9 时间戳）、13+ 位毫秒启发式
- APIKey 兼容 key/access/token/apiKey/value 多键 + 纯字符串裸值

**UsagePredictor 预测算法**：最近 7 天加权平均（权重 [1.5,1.5,1.2,1.2,1.2,1.0,1.0]）→ 周末系数 → UTC 日历算本月剩余工作日 → 预测月度总量 → 超量 × $0.04/请求 → 置信度（<3 天 low / <7 medium / 否则 high）。

### 1.4 代码规范

- 注释/日志/提交信息全部英文；日志用 `os.log` + emoji 状态前缀（🔵/🟡/🟢/🔴）
- `actor` 免锁、TaskGroup 并行、超时用 withThrowingTaskGroup + sleep 竞争
- 统一错误类型 `ProviderError`（authenticationFailed/networkError/decodingError/providerError/unsupported）
- 失败先落缓存再决定返回缓存或报错（graceful degradation）
- UI token 集中（MenuDesignToken，禁硬编码像素）；SF Symbols 图标禁 emoji
- `DependencyTests` 强制校验依赖方向
- 每 provider 一个测试文件 + 每 provider 一个 `scripts/query-xxx.sh` 双轨验证

### 1.5 对 myboard 的借鉴

| 可 1:1 移植                                                                         | 必须改造                                                                      |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Go 配额全套逻辑（models URL/Bearer、dashboard HTML 正则、窗口计算、max 取最紧窗口） | 浏览器 cookie：Swift Keychain → Windows DPAPI（v1 可只支持环境变量+配置文件） |
| 凭据多路径探测（env → json → cookie，首成功返回）                                   | actor/TaskGroup → QThread/QRunnable + QTimer + signal/slot                    |
| auth.json 多路径 + 弹性解析（String/Int 转换、毫秒启发式、lossy 解码）              | NSMenu → QSystemTrayIcon + QMenu；tag 999 重建 → menu.clear() 重建动态段      |
| ProviderManager 模式：并行 + 去重 + 节流 + 缓存兜底                                 | 订阅存储 → config/settings.py                                                 |

---

## 二、opencode-usage（SQLite 用量统计 CLI）

### 2.1 项目概览

Python ≥3.10 CLI（MIT），读本地 opencode.db 统计 token 与费用。运行时依赖仅 **rich**（渲染）；LLM 调用用 stdlib urllib 手写客户端；工具链：uv、ruff（line-length=100，select E W F I UP B SIM RUF）、hatchling、pytest。

### 2.2 数据模型（dataclass）

```python
@dataclass
class TokenStats:        # input/output/reasoning/cache_read/cache_write/total
@dataclass
class UsageRow:          # label/calls/tokens: TokenStats/cost/detail
```

### 2.3 SQLite 读取与聚合（核心可迁移 SQL）

- 连接：`sqlite3.connect(f"file:{path}?mode=ro", uri=True)` **只读模式** + `row_factory = sqlite3.Row`，每次查询独立连接 try/finally 关闭
- 只统计 `role='assistant'` 且 `tokens.total` 非空的消息
- 核心聚合模式：`json_extract(data, '$.tokens.input')` + `COALESCE(SUM(...),0)`；时间过滤参数化 `time.created >= ?`（毫秒 epoch，半开区间）
- 按天分组：`date(json_extract(data,'$.time.created') / 1000, 'unixepoch', 'localtime')`
- 分组维度：total / day / modelID / providerID / agent（双列 GROUP BY agent, model）/ session（JOIN session，`COALESCE(s.title, m.session_id)`）
- 周期对比：`prev_since = since - (now - since)`，delta 按 `label:detail` 复合 key 对齐
- **费用直接用数据库 `$.cost`，不自己估算**（估算作回退）

### 2.4 数据库路径三级探测

`OPENCODE_DB` 环境变量 → `opencode db path` 子进程（`shutil.which` + 10s 超时 + `@lru_cache`）→ XDG 回退 `~/.local/share/opencode/opencode.db`（Windows 同路径）。`opencode debug paths` 出 data/config 目录。二进制不可用 → 返回 None 走回退（不崩）。

### 2.5 CLI 设计

argparse 子命令 run（默认）/insights；run 参数 `--days/--since/--by {model,agent,provider,session,day}/--limit/--json/--compare`；时间解析 `re.fullmatch(r"(\d+)([dhwm])")` + ISO 双路。JSON 输出 `{"period", "total", "rows"}`，`json.dumps(indent=2, ensure_ascii=False)`。

### 2.6 错误处理

DB 不存在 → FileNotFoundError + 提示；JSON 坏行 continue 跳过；`project` 表缺失容错 `sqlite3.OperationalError`；LLM 子进程 127→FileNotFoundError、126→PermissionError；指数退避重试（min(2^n*2, 60)s）；单个失败 warnings 不中断整体。

### 2.7 代码规范

- 每模块首行 `from __future__ import annotations`；import 分组空行分隔；私有模块 `_opencode_cli.py`
- 全签名类型注解 + `| None` 联合语法；TYPE_CHECKING 条件导入
- 单行三引号 docstring；容器数据一律 dataclass + `field(default_factory=...)`
- 提交英文 conventional（feat(db): ...），release-please 自动发版

### 2.8 对 myboard 的借鉴

- 只读连接 + json_extract 聚合 SQL 原样迁移（modules/opencode_usage.py）
- 路径探测补 `opencode debug paths` 优先项
- 费用优先用库值，pricing 仅作回退
- GUI 常驻应用应改用长连接（CLI 每次重开连接的思路不适用）
- 避免同名 dataclass 两套定义（其 SessionMeta 在 db.py 与 insights/types.py 重复定义是反面教材）
- `_fmt_tokens`（K/M/B 缩写）可移植为 Qt 显示

---

## 三、OpenCode-Token（GUI 分析 + 定价）

### 3.1 项目概览

Python ≥3.11，Windows 桌面工具。GUI = **tkinter + ttk**（无第三方 GUI 依赖），图表 matplotlib；运行时依赖仅 matplotlib；PyInstaller 单文件 exe（spec + build.bat），`entry_path` 机制让 exe 旁的 prices.local.json 可被发现。双入口：GUI（opencode_token_gui.py）+ CLI 导出（export_opencode_tokens.py），共享同一数据管线。

### 3.2 架构：管道式分层

```
SQLite → data_loader.load_usage_from_db() → datasets（纯 dict）
       → pricing.price_loaded_usage()      → 加定价字段（返回新 dict 不改原结构）
       → viewmodels.build_application_viewmodels() → 追加 *_display 展示字段
       → gui.py（Notebook 5 页） / exporter.py（CSV）
```

关键设计：**viewmodel 层不改原始值，只追加 `xxx_display` 字段**，列名即字段名零映射；UI 文案用 `LABEL_TEXT` 常量 dict + `ui_text()` 查找。

### 3.3 SQLite 读取

- 表假设：`session (id, title)`、`message (id, session_id, time_created, data)`；data 为 JSON 字符串，SQL 只做四列投影
- `get_nested()` 逐层安全取数；`tokens.cache.read/write` 是嵌套层；`total_tokens <= 0` 丢弃行
- time_created 毫秒：`fromtimestamp(ts/1000)`；字符串归一化（strip + lower + 压缩空白），`canonical_model_key = "provider:model"`

### 3.4 定价机制（重点）

**prices.json 结构**（顶层 key = `provider:model`）：

```json
{
  "input_price_per_million": 0.4, "output_price_per_million": 1.6,
  "cache_read_price_per_million": 0.1, "currency": "USD",
  "pricing_status": "current", "source_urls": [...], "notes": [...]
}
```

**两种模式**：flat（直接字段）；session_tiered（`session_tiering: {scope/metric/threshold/comparison/trigger/default_tier/triggered_tier}` + `tiers`，任一行超阈值 → **整会话换档重定价**，any_row 语义）。

**优先级链**：内置 prices.json → 入口同目录 prices.local.json → 逐 key 合并，override 打标 `price_source="override"`。

**成本计算**：

```
estimated_cost = input/1e6*input_price + output/1e6*output_price
                 + cache_read/1e6*read_price + cache_write/1e6*write_price
```

reasoning_tokens 不计费；查不到价格 → `unpriced` 打标；无 cache 价格时 cache 成本为 None 而非 0。

**多币种**：按币种分桶 `estimated_cost_totals = {"USD": 1.0, "CNY": 2.0}`；**≥2 种币 → 总价置 None，禁止跨币种相加**，显示层渲染 `"¥2.00 CNY / $1.50 USD"`。

### 3.5 CSV 导出

UTF-8 BOM（`encoding="utf-8-sig"`）让 Excel 中文不乱码；5 个文件（summary/by_model/by_session/by_day/raw_messages）；DictWriter + 显式 fieldnames；dict 单元格 json.dumps 序列化。

### 3.6 GUI 与线程

- Notebook 5 页（总览/模型/按日/会话/明细）；总览 8 张汇总卡片 + 图表网格 + 每日小表；明细页分页（200 条/页）
- **启动线程化**：`after(10)` 延迟触发 daemon 线程 → 主线程轮询 `is_alive()` → 完成回主线程；手动加载时 `after_cancel` 取消调度防双加载
- 图表失败仅 warning 不阻塞（7 个图逐个 try/except）
- 中文字体：CJK 候选列表（Microsoft YaHei → SimHei...）+ `axes.unicode_minus = False`；matplotlib 缺失静默降级
- 加载失败弹窗但**保留旧 view**（viewmodels 只在成功后替换）

### 3.7 代码规范

- 模块级 `_` 前缀私有函数；公开 API 无前缀
- **几乎无注释，靠测试文件当规范文档**（3 个测试文件，test_gui_viewmodels.py 2116 行）
- 弱类型风格（dict 透传，少量注解）；`tests/conftest.py` 手动 sys.path.insert
- 无头测试 GUI 技巧：`__new__(OpenCodeTokenApp)` + monkeypatch ttk 组件

### 3.8 对 myboard 的借鉴

- 数据管线分层 + `*_display` 追加字段模式（GUI/CLI 共享同一 datasets）
- 宽容解析：get_nested / to_int / safe_json_loads 防御 OpenCode JSON 结构变化
- 价格表三层合并 + source_urls/notes 出处可审计
- 多币种禁止相加策略（Go 配额若涉及多币种照搬）
- 启动加载线程化 + 手动操作取消自动调度（PyQt6 用 QTimer.singleShot + QThread）
- 失败"警告不阻塞"而非弹窗；UTF-8 BOM CSV 范本

---

## 四、三项目对比与 myboard 结论

| 维度     | opencode-bar       | opencode-usage | OpenCode-Token   |
| -------- | ------------------ | -------------- | ---------------- |
| 语言     | Swift              | Python         | Python           |
| 形态     | 菜单栏常驻         | CLI            | GUI(tkinter)+CLI |
| 数据源   | 在线接口+auth.json | opencode.db    | opencode.db      |
| Go 配额  | ✅ 完整            | ❌             | ❌               |
| 用量统计 | ❌                 | ✅ SQL 聚合    | ✅ 四类聚合      |
| 定价估算 | 订阅 preset        | 库 cost 直用   | ✅ 三层价格表    |
| 错误策略 | 缓存兜底           | 降级回退       | 警告不阻塞       |

**综合结论（myboard 开发依据）**：

1. **Go 配额** → 移植 opencode-bar 全链路：env → opencode-go.json 多路径凭据探测（首成功返回）、`/zen/go/v1/models` Bearer 校验、dashboard HTML 正则抓 usagePercent/resetInSec、max 取最紧窗口、`min_fetch_interval = 60s` 节流
2. **用量统计** → opencode-usage 的只读连接 + `json_extract` 聚合 SQL + 库 cost 优先，pricing 仅回退
3. **GUI 架构** → OpenCode-Token 的管道分层 + `*_display` 追加字段 + 启动线程化 + 失败警告不阻塞
4. **通用健壮性** → auth.json 多路径 + 弹性解析（String/Int/毫秒启发式/lossy 解码）、数字字段可能是字符串、窗口缺失仅警告
5. **代码规范** → 本仓库 AGENTS.md 已对齐主流实践（line-length 100、dataclass、`_` 私有前缀、`from __future__` 可选）；OpenCode-Token 的"测试锁定行为"模式值得在 S7 测试阶段采纳
