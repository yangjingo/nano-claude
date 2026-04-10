# Tool 实现设计

> 从 mirrored registry 到可执行 tool 系统

---

## 一、参考实现：nanocode

[nanocode](https://github.com/1rgs/nanocode) — 271 行 Python，零依赖，完整 tool loop。

核心设计：

```python
# 工具 = (description, schema, handler) 三元组
TOOLS = {
    "read":  ("Read file with line numbers", {"path": "string", "offset": "number?"}, read),
    "write": ("Write content to file",       {"path": "string", "content": "string"}, write),
    "edit":  ("Replace old with new in file", {"path": "string", "old": "string", ...}, edit),
    "glob":  ("Find files by pattern",       {"pat": "string", "path": "string?"},   glob),
    "grep":  ("Search files for regex",      {"pat": "string", "path": "string?"},   grep),
    "bash":  ("Run shell command",           {"cmd": "string"},                      bash),
}
```

**我们的差异**：
- nanocode 用 `urllib.request` 直接调 REST API；我们用 `anthropic` SDK（async streaming）
- nanocode 同步；我们全异步（`asyncio.create_subprocess_exec`）
- nanocode 无类型；我们用 frozen dataclass + `ToolFunc` 类型别名
- nanocode 单文件；我们 `src/tools/` 模块化，每个工具一个文件

---

## 二、当前架构

### 工具框架

```
src/tools/
├── __init__.py       # ToolParam, ToolDef, ToolResult, ToolRegistry, default_registry()
├── bash.py           # BashTool — 跨平台 shell 检测 + async execute
├── read.py           # ReadTool — cat -n 格式，offset/limit 分页
├── write.py          # WriteTool — 创建/覆写文件，自动创建父目录
├── edit.py           # EditTool — 精确字符串替换，replace_all
├── glob_tool.py      # GlobTool — pathlib.glob 文件模式匹配
└── grep_tool.py      # GrepTool — re 正则搜索，glob 过滤，上下文行
```

### 核心数据流

```
REPL (cli/repl.py)
  → default_registry()  # 预装 6 个内置工具
  → registry.make_schema()  # 生成 Anthropic API tool definitions
  → AgentSession.chat(tools=schema)
    → model 返回 tool_use block
    → registry.run(name, args) → ToolResult
    → tool_result 反馈给 model
```

### 关键类型

```python
ToolFunc = Callable[..., Coroutine[Any, Any, str]]

@dataclass(frozen=True)
class ToolParam:
    name: str
    type: str          # "string", "integer", "boolean", "number"
    description: str = ""
    required: bool = True

@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str
    params: tuple[ToolParam, ...]
    handler: ToolFunc

@dataclass(frozen=True)
class ToolResult:
    output: str
    is_error: bool = False
```

### ToolRegistry API

```python
registry = ToolRegistry()
registry.register(bash_tool)         # 注册工具
registry.get("Bash")                 # → ToolDef | None
registry.list_names()                # → ["Bash", "Read", ...]
registry.make_schema()               # → [{name, description, input_schema}, ...]
result = await registry.run("Bash", {"command": "ls"})  # → ToolResult
```

`default_registry()` 工厂函数返回预装全部 6 个内置工具的 registry 实例。

---

## 三、内置工具清单

### 3.1 Bash — Shell 执行

**文件**：`src/tools/bash.py`

**跨平台检测优先级**：

| 平台 | 检测顺序 |
|------|---------|
| WSL 内部（Python 在 Linux） | `/bin/bash -c` |
| Windows 宿主 + WSL 可用 | `wsl bash -c` |
| Windows 宿主 + Git Bash | `<git-bash> --norc --noprofile -c` |
| Windows 宿主（无 bash） | `%COMSPEC% /c` |
| macOS / Linux | `/bin/bash -c` |

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `command` | string | 是 | Shell 命令 |
| `timeout` | number | 否 | 超时秒数（默认 120） |

### 3.2 Read — 文件读取

**文件**：`src/tools/read.py`

**功能**：读取文件内容，cat -n 格式（行号 + tab + 内容），支持 offset/limit 分页。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_path` | string | 是 | 文件路径 |
| `offset` | integer | 否 | 起始行（0-based，默认 0） |
| `limit` | integer | 否 | 最大行数（默认 2000） |

**输出格式**：
```
1\t第一行内容
2\t第二行内容
...
... 127 more lines not shown
```

### 3.3 Write — 文件写入

**文件**：`src/tools/write.py`

**功能**：创建或覆写文件，自动创建父目录。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_path` | string | 是 | 文件路径 |
| `content` | string | 是 | 写入内容 |

### 3.4 Edit — 字符串替换

**文件**：`src/tools/edit.py`

**功能**：精确字符串替换。`old_string` 必须在文件中唯一（或使用 `replace_all`）。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_path` | string | 是 | 文件路径 |
| `old_string` | string | 是 | 要查找的文本 |
| `new_string` | string | 是 | 替换文本 |
| `replace_all` | boolean | 否 | 替换全部（默认 false） |

**错误情况**：
- 文件不存在 → error
- `old_string == new_string` → error
- `old_string` 未找到 → error
- `old_string` 匹配多处且未设 `replace_all` → error（提示匹配数量）

### 3.5 Glob — 文件模式匹配

**文件**：`src/tools/glob_tool.py`

**功能**：使用 `pathlib.glob` 查找文件，返回排序后的相对路径。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pattern` | string | 是 | glob 模式（如 `**/*.py`） |
| `path` | string | 否 | 搜索目录（默认当前目录） |

**限制**：最多返回 250 个结果。

### 3.6 Grep — 内容搜索

**文件**：`src/tools/grep_tool.py`

**功能**：使用 Python `re` 模块搜索文件内容，支持 glob 过滤和上下文行。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pattern` | string | 是 | 正则表达式 |
| `path` | string | 否 | 文件或目录（默认当前目录） |
| `glob` | string | 否 | 文件过滤（如 `*.py`） |
| `case_insensitive` | boolean | 否 | 忽略大小写（默认 false） |
| `context` | integer | 否 | 上下文行数（默认 2） |

**输出格式**：`file:line>> 匹配行`，上下文用 `file:line:  ` 前缀。

**行为**：
- 路径是文件 → 只搜索该文件
- 路径是目录 → 递归搜索（跳过 `.` 和 `__pycache__`）
- 无效正则 → 返回 error

---

## 四、工具全景（从 TS snapshot 提取）

按功能分类，原版共 **25 个顶层工具**：

| 分类 | 工具 | 优先级 | 状态 |
|------|------|--------|------|
| **文件操作** | `Read`, `Write`, `Edit`, `Glob`, `Grep` | P0 | ✅ 已实现 |
| **Shell 执行** | `Bash` | P0 | ✅ 已实现 |
| **Shell 执行** | `PowerShell` | P2 | ⬜ |
| **Agent 系统** | `Agent`, `SendMessage` | P1 | ⬜ |
| **任务管理** | `TaskCreate`, `TaskGet`, `TaskList`, `TaskOutput`, `TaskStop`, `TaskUpdate` | P1 | ⬜ |
| **计划模式** | `EnterPlanMode`, `ExitPlanMode` | P1 | ⬜ |
| **Worktree** | `EnterWorktree`, `ExitWorktree` | P2 | ⬜ |
| **定时任务** | `CronCreate`, `CronDelete`, `CronList` | P2 | ⬜ |
| **Web** | `WebFetch`, `WebSearch` | P2 | ⬜ |
| **MCP** | `MCPTool`, `McpAuth`, `ListMcpResources`, `ReadMcpResource` | P3 | ⬜ |
| **交互** | `AskUserQuestion`, `Brief` | P2 | ⬜ |
| **LSP** | `LSP` | P3 | ⬜ |
| **Notebook** | `NotebookEdit` | P3 | ⬜ |
| **Skill** | `Skill` | P2 | ⬜ |
| **其他** | `Config`, `RemoteTrigger`, `TodoWrite`, `ToolSearch` | P2-P3 | ⬜ |

---

## 五、演进计划

### Phase 1: 基础设施 ✅

1. `ToolParam`, `ToolDef`, `ToolResult` dataclass
2. `ToolRegistry` — 注册、查找、schema 导出、执行
3. 集成到 `AgentSession` — tool_use 循环

### Phase 2: P0 工具 ✅

4. `BashTool` — 跨平台 shell 检测（WSL / Git Bash / cmd.exe / native）
5. `ReadTool` — cat -n 格式，offset/limit
6. `WriteTool` — 文件写入，自动创建目录
7. `EditTool` — 精确字符串替换
8. `GlobTool` — pathlib.glob 模式匹配
9. `GrepTool` — re 正则搜索 + glob 过滤

### Phase 3: 权限系统（待做）

10. `PermissionGate` — 三级权限（auto-approve / context-aware / always-ask）
11. 与 REPL 交互 — 用户审批流程

### Phase 4: P1 工具（待做）

12. `AskUserQuestion` — 交互式问答
13. `Task*` — 任务管理（6 合 1）
14. `Agent` — 子 agent 生成

### Phase 5: P2-P3 工具（按需）

15. `WebFetch`, `WebSearch`
16. `MCP*`
17. `LSP`
18. `Skill`

---

## 六、关键设计决策

### 6.1 全异步

所有工具的 `handler` 都是 `async`。BashTool 用 `asyncio.create_subprocess_exec`，未来 WebFetch/MCP 也需要 async IO。同步的文件操作通过 async wrapper 无性能损失。

### 6.2 每工具一个文件

TypeScript 每个工具一个目录（含 UI 组件），Python 不需要 UI 层，一个文件足够。相关工具（如 6 个 Task 工具）未来可合并到一个文件。

### 6.3 纯 Python grep（暂不依赖 rg）

当前 Grep 使用 `re` 模块，零外部依赖。性能对中小项目足够。未来可增加 ripgrep backend 作为加速。

### 6.4 保留 mirrored registry

`registry/tools.py` 的镜像注册表保留作为 parity audit 参考，不影响新的 `ToolRegistry` 系统。

### 6.5 `default_registry()` 工厂函数

提供预装所有内置工具的 registry 实例，REPL 和其他入口点只需一行调用。未来 MCP/插件工具也可通过这个入口注入。

---

## 七、测试覆盖

**文件**：`tests/test_tools.py`（42 个测试）

| 测试类 | 测试项 |
|--------|--------|
| `TestDataclasses` | ToolParam/ToolDef/ToolResult 冻结性和默认值 |
| `TestToolRegistry` | 注册、查找、覆盖、名称列表 |
| `TestMakeSchema` | schema 结构、类型保留、required 字段 |
| `TestToolRun` | 成功执行、未知工具、异常处理 |
| `TestBashShellDetection` | Linux、Windows WSL、Windows Git Bash、Windows cmd fallback |
| `TestBashExecute` | 正常输出、空输出、超时 |
| `TestDefaultRegistry` | 6 工具加载、schema 有效性 |
| `TestReadTool` | 存在文件、不存在文件、offset |
| `TestWriteEditTools` | 写入+读取、替换、歧义拒绝、replace_all |
| `TestGlobTool` | py 文件、递归、无匹配 |
| `TestGrepTool` | 模式匹配、大小写、无匹配、单文件、无效正则 |

---

## 八、与现有系统的对接

| 组件 | 改动 | 状态 |
|------|------|------|
| `tools/__init__.py` | `default_registry()` 工厂函数 | ✅ |
| `tools/bash.py` | 跨平台 WSL/Git Bash/cmd 检测 | ✅ |
| `tools/read.py` | cat -n 格式 + offset/limit | ✅ |
| `tools/write.py` | 写入 + 自动创建目录 | ✅ |
| `tools/edit.py` | 精确替换 + replace_all | ✅ |
| `tools/glob_tool.py` | pathlib.glob + 相对路径 | ✅ |
| `tools/grep_tool.py` | re 搜索 + glob 过滤 + 上下文 | ✅ |
| `cli/repl.py` | `default_registry()` 替代手动注册 | ✅ |
| `agent/agent.py` | `run_turn()` + tool_use 循环 | ✅ |
| `engine/runtime.py` | 用新 registry 替代 `PORTED_TOOLS` | 待做 |
| `registry/tool_pool.py` | 从 `ToolRegistry` 组装 | 待做 |
| `permissions.py` | 扩展为 `PermissionGate` | 待做 |
