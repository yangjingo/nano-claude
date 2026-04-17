# Tool 实现设计

> 从 mirrored registry 到可执行 tool 系统

---
## 当前整体架构

```

● 读完所有文件了。以下是架构图：

  src/tools/ 架构图
  ═══════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────┐
  │  __init__.py — 框架层                                    │
  │                                                         │
  │  ToolParam(name, type, desc, required)    ← frozen DC  │
  │  ToolDef(name, desc, params, handler)     ← frozen DC  │
  │  ToolResult(output, is_error)             ← frozen DC  │
  │                                                         │
  │  ToolRegistry(security?)                                │
  │    .register(tool)   .get(name)   .list_names()         │
  │    .make_schema()    → Anthropic API tools[]            │
  │    .run(name, args)  → ToolResult                       │
  │       │                                                 │
  │       ├─ 1. SecurityGate.check(name, args)  ← 可选      │
  │       ├─ 2. tool.handler(**args)                       │
  │       └─ 3. ToolResult(output, warning)                 │
  │                                                         │
  │  default_registry(security?)                            │
  │    5 文件工具 + 1 Shell 工具（平台自动选择）              │
  └───────────┬─────────────────────────────────────────────┘
              │
      ┌───────┼───────────────────────────────────────┐
      │       │                                       │
      ▼       ▼                                       ▼
  ┌──────────────────────┐            ┌──────────────────────────┐
  │  文件工具（5 个）      │            │  Shell 工具（平台选择）    │
  │                       │            │                          │
  │  read.py    ← 68 行  │            │  bash.py      ← 111 行  │
  │  write.py   ← 43 行  │            │  powershell.py ← 107 行  │
  │  edit.py    ← 74 行  │            │                          │
  │  glob_tool.py ← 68 行│            │  每个文件结构相同：        │
  │  grep_tool.py ← 129 行│            │    _detect_xxx() 缓存    │
  │                       │            │    execute(cmd, timeout) │
  │  每个文件结构相同：      │            │    xxx_tool = ToolDef   │
  │    execute() 异步处理   │            └──────────────────────────┘
  │    xxx_tool = ToolDef  │
  └──────────────────────┘

  ┌─────────────────────────────────────────────────────────┐
  │  security.py — 安全层（~230 行）                          │
  │                                                         │
  │  命令安全指导通过 system prompt 提供（非正则白名单）      │
  │                                                         │
  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │
  │  │ PathSandbox  │  │CoreDangerDet.│  │SensitiveFileChk│ │
  │  │              │  │              │  │                │ │
  │  │ allowed_root │  │ ~20 致命模式  │  │ .env, .ssh/,   │ │
  │  │ blocked_path │  │ sudo, rm -rf│  │ credentials    │ │
  │  │              │  │ pipe to bash│  │ *.pem, *.key   │ │
  │  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘ │
  │         │                 │                   │          │
  │         └─────────────────┼───────────────────┘          │
  │                           ▼                              │
  │                  ┌──────────────────┐                     │
  │                  │   SecurityGate   │                     │
  │                  │                  │                     │
  │                  │ PermissionLevel  │                     │
  │                  │  AUTO_APPROVE    │ → 直接放行          │
  │                  │  CONTEXT_AWARE   │ → 三层检查          │
  │                  │  ALWAYS_ASK      │ → 始终确认          │
  │                  │                  │                     │
  │                  │ confirm_callback │ → ChoiceInput 弹窗  │
  │                  └──────────────────┘                     │
  └─────────────────────────────────────────────────────────┘

  安全检查流程（三层）
  ═══════════════════

    registry.run("Bash", {"command": "cat /etc/passwd"})
         │
         ▼
    SecurityGate.check("Bash", args)
         │
         ├─ 权限级别？
         │   ├─ AUTO_APPROVE → ✅ 放行（Glob, Grep）
         │   ├─ ALWAYS_ASK   → 📋 确认弹窗
         │   └─ CONTEXT_AWARE ↓
         │
         ├─ Bash/PowerShell？
         │   ├─ ① 致命模式？(sudo, rm -rf /, | bash)
         │   │   └─ 命中 → 📋 确认弹窗
         │   ├─ ② 参数路径检查（cat/head/tail/diff 等文件命令）
         │   │   ├─ 敏感文件？(.env, credentials) → 📋 确认
         │   │   └─ 保护路径？(/etc/, ~/.ssh/)    → 📋 确认
         │   └─ 都安全 → ✅ 放行（无白名单，prompt 约束）
         │
         └─ 文件工具？(Read/Write/Edit)
             ├─ 敏感文件？ → 📋 确认弹窗
             ├─ 保护路径？ → 📋 确认弹窗
             └─ 都安全     → ✅ 放行

    📋 确认弹窗（ChoiceInput）:
         ├─ 有 callback → [Allow once] [Deny]
         └─ 无 callback → ⚠️ Warning + soft-allow


```

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
├── security.py       # SecurityGate, PathSandbox, CoreDangerDetector, SensitiveFileChecker
├── bash.py           # BashTool — Unix-only shell 执行
├── powershell.py     # PowerShellTool — pwsh (PowerShell 7+) 执行
├── read.py           # ReadTool — cat -n 格式，offset/limit 分页
├── write.py          # WriteTool — 创建/覆写文件，自动创建父目录
├── edit.py           # EditTool — 精确字符串替换，replace_all
├── glob_tool.py      # GlobTool — pathlib.glob 文件模式匹配
└── grep_tool.py      # GrepTool — re 正则搜索，glob 过滤，上下文行
```

### 核心数据流

```
REPL (cli/repl.py)
  → build_security_gate(confirm_callback)  # 创建安全网关
  → default_registry(security=gate)        # 预装 5 文件工具 + 1 Shell 工具（平台自动选择）
  → registry.make_schema()                  # 生成 Anthropic API tool definitions
  → AgentSession.run_turn(tools=schema, tool_runner=registry.run)
    → model 返回 tool_use block
    → registry.run(name, args)
      → SecurityGate.check(name, args)     # 三层安全检查（致命模式 + 路径 + 敏感文件）
      → tool.handler(**args) → ToolResult
    → tool_result 反馈给 model
```

命令安全由 system prompt 指导（非正则白名单）：
- 安全命令类别：文件查看、Git、Python/uv/pip、系统信息等
- 禁止命令：sudo, rm -rf, git push --force, pipe to bash/sh 等
- 非白名单命令由 prompt 引导模型使用专用工具替代

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
registry = ToolRegistry(security=security_gate)  # 可选安全网关
registry.register(bash_tool)         # 注册工具
registry.get("Bash")                 # → ToolDef | None
registry.list_names()                # → ["Bash", "Read", ...]
registry.set_security(gate)          # 延迟设置安全网关
registry.make_schema()               # → [{name, description, input_schema}, ...]
result = await registry.run("Bash", {"command": "ls"})  # → ToolResult
```

`default_registry()` 工厂函数根据平台返回预装工具的 registry 实例：
- **Linux / macOS / WSL**：Bash + 5 文件工具
- **Windows + pwsh**：PowerShell + 5 文件工具
- **Windows 无 pwsh**：Bash（fallback）+ 5 文件工具

### Shell 工具平台自动选择

| 平台 | 注册的 Shell 工具 | 检测逻辑 |
|------|-------------------|----------|
| Linux / macOS | `Bash` | `/bin/bash -c` |
| WSL 内部 | `Bash` | Python 报告 `linux` 平台，使用 `/bin/bash -c` |
| Windows + pwsh | `PowerShell` | `shutil.which("pwsh")` → `pwsh -NoProfile -Command` |
| Windows 无 pwsh | `Bash` | 回退到 Git Bash / WSL 中的 bash |

---

## 三、内置工具清单

### 3.1 Bash — Unix Shell 执行

**文件**：`src/tools/bash.py`

**平台支持**：Linux、macOS、WSL。Windows 原生环境不注册此工具。

**检测逻辑**：
- `sys.platform != "win32"` → `/bin/bash -c`
- `sys.platform == "win32"` → `None`（不可用）

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `command` | string | 是 | Shell 命令 |
| `timeout` | number | 否 | 超时秒数（默认 120） |

### 3.2 PowerShell — PowerShell 7+ 执行

**文件**：`src/tools/powershell.py`

**平台支持**：跨平台（需安装 pwsh / PowerShell 7+）。

**检测逻辑**：`shutil.which("pwsh")` → `pwsh -NoProfile -Command`

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `command` | string | 是 | PowerShell 命令 |
| `timeout` | number | 否 | 超时秒数（默认 120） |

### 3.3 Read — 文件读取

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

### 3.4 Write — 文件写入

**文件**：`src/tools/write.py`

**功能**：创建或覆写文件，自动创建父目录。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_path` | string | 是 | 文件路径 |
| `content` | string | 是 | 写入内容 |

### 3.5 Edit — 字符串替换

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

### 3.6 Glob — 文件模式匹配

**文件**：`src/tools/glob_tool.py`

**功能**：使用 `pathlib.glob` 查找文件，返回排序后的相对路径。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pattern` | string | 是 | glob 模式（如 `**/*.py`） |
| `path` | string | 否 | 搜索目录（默认当前目录） |

**限制**：最多返回 250 个结果。

### 3.7 Grep — 内容搜索

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
| **Shell 执行** | `Bash` | P0 | ✅ 已实现（Unix-only） |
| **Shell 执行** | `PowerShell` | P0 | ✅ 已实现（pwsh 7+） |
| **安全系统** | `SecurityGate` | P0 | ✅ 已实现 |
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

4. `BashTool` — Unix-only shell 执行（Linux / macOS / WSL）
5. `PowerShellTool` — pwsh（PowerShell 7+）跨平台执行
6. `ReadTool` — cat -n 格式，offset/limit
7. `WriteTool` — 文件写入，自动创建目录
8. `EditTool` — 精确字符串替换
9. `GlobTool` — pathlib.glob 模式匹配
10. `GrepTool` — re 正则搜索 + glob 过滤

### Phase 3: 安全系统 ✅

11. `SecurityConfig` — 安全配置（allowed_roots, blocked_paths, 核心危险模式, 敏感文件模式）
12. `SecurityGate` — 统一安全检查入口
13. `PathSandbox` — 路径沙箱（allowed_roots + blocked_paths）
14. `CoreDangerDetector` — 致命命令检测（sudo, rm -rf /, pipe to bash 等）
15. `SensitiveFileChecker` — 敏感文件检测（.env, .ssh/, credentials）
16. 三级权限（auto-approve / context-aware / always-ask）+ ConfirmCallback
17. REPL 集成 — 交互式用户确认（ChoiceInput 弹窗 + spinner 暂停）

### Phase 4: P1 工具（待做）

18. `AskUserQuestion` — 交互式问答
19. `Task*` — 任务管理（6 合 1）
20. `Agent` — 子 agent 生成

### Phase 5: P2-P3 工具（按需）

21. `WebFetch`, `WebSearch`
22. `MCP*`
23. `LSP`
24. `Skill`

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

### 6.5 `default_registry()` 平台自动选择

根据平台自动选择 Shell 工具：Linux/Mac 注册 Bash，Windows 优先 PowerShell（pwsh 7+）。`security` 参数可选，向后兼容。

### 6.6 安全系统（SecurityGate — 三层架构）

安全系统作为独立模块 `security.py`（~230 行），通过依赖注入集成到 `ToolRegistry`。

**设计原则**：命令安全知识通过 system prompt 提供给模型（而非正则白名单）。`security.py` 只负责硬性保护。

#### 三层安全检查

| 层 | 组件 | 职责 | 触发场景 |
|----|------|------|---------|
| ① 致命命令 | `CoreDangerDetector` | ~20 条致命模式（sudo, rm -rf /, pipe to bash） | Bash/PowerShell |
| ② 敏感文件 | `SensitiveFileChecker` | .env, credentials, *.pem, id_rsa 等 | 文件工具 + Shell 文件参数 |
| ③ 路径沙箱 | `PathSandbox` | /etc/, ~/.ssh/, ~/.aws/, /proc/ 等 | 文件工具 + Shell 文件参数 |

#### 默认工具权限

| 工具 | 权限级别 | 说明 |
|------|---------|------|
| `Glob` | AUTO_APPROVE | 只列文件名，无内容泄露风险 |
| `Grep` | AUTO_APPROVE | 搜索需匹配 pattern，风险可控 |
| `Read` | CONTEXT_AWARE | 三层检查 |
| `Write` | CONTEXT_AWARE | 三层检查 |
| `Edit` | CONTEXT_AWARE | 三层检查 |
| `Bash` | CONTEXT_AWARE | 致命命令 + 文件路径检查 |
| `PowerShell` | CONTEXT_AWARE | 致命命令 + 文件路径检查 |

#### Shell 文件路径检查

文件类命令（`cat`, `head`, `tail`, `less`, `more`, `diff`, `grep`, `find`, `file`, `stat`, `wc`, `sort`, `tree`）会提取参数中的文件路径做敏感文件 + 路径沙箱检查。`ls`, `echo`, `pwd` 等不做路径检查。

#### 交互式确认

REPL 中使用 `ChoiceInput` 框式选择菜单，确认时自动暂停 spinner：

```
⚠  Path is in a protected directory: /etc/

┌─ Security: Read ─────────────┐
│  Allow once                   │
│  Deny                         │
└───────────────────────────────┘
```

#### 命令安全 Prompt（system prompt 替代正则白名单）

安全命令通过 `SYSTEM_PROMPT` 指导模型，包括安全命令类别和禁止命令列表。详见 `src/agent/agent.py` 的 `SYSTEM_PROMPT`。

---

## 七、测试覆盖

**文件**：`tests/test_tools.py` + `tests/test_security.py` + `tests/test_powershell.py`（约 170 个测试）

### test_tools.py

| 测试类 | 测试项 |
|--------|--------|
| `TestDataclasses` | ToolParam/ToolDef/ToolResult 冻结性和默认值 |
| `TestToolRegistry` | 注册、查找、覆盖、名称列表 |
| `TestMakeSchema` | schema 结构、类型保留、required 字段 |
| `TestToolRun` | 成功执行、未知工具、异常处理 |
| `TestBashShellDetection` | Linux/macOS 返回 bash，Windows 返回 None |
| `TestBashExecute` | 正常输出、空输出、超时、无 shell |
| `TestDefaultRegistry` | 平台工具选择、schema 有效性、security 集成 |
| `TestReadTool` | 存在文件、不存在文件、offset |
| `TestWriteEditTools` | 写入+读取、替换、歧义拒绝、replace_all |
| `TestGlobTool` | py 文件、递归、无匹配 |
| `TestGrepTool` | 模式匹配、大小写、无匹配、单文件、无效正则 |

### test_security.py

| 测试类 | 测试项 |
|--------|--------|
| `TestSecurityConfig` | 默认值、冻结性、自定义配置 |
| `TestPathSandbox` | CWD 放行、敏感目录拦截（ssh/aws/gnupg/etc）、自定义 allowed_root |
| `TestCoreDangerDetector` | 致命模式拦截（sudo/rm/dd/chmod/shutdown/pipe）、安全命令放行 |
| `TestExtractPaths` | 文件类命令路径提取（cat/head/diff/grep）、非文件命令返回空 |
| `TestSensitiveFileChecker` | .env/.ssh/credentials/pem/aws 检测 |
| `TestSecurityGate` | AUTO_APPROVE 放行、CONTEXT_AWARE 致命拦截+路径检查、敏感文件拦截、ALWAYS_ASK 确认、deny 覆盖、confirm 回调 |
| `TestSecurityDecision` | 默认值、冻结性 |

### test_powershell.py

| 测试类 | 测试项 |
|--------|--------|
| `TestPwshDetection` | pwsh 检测（Linux/Windows）、不存在、可用性查询、诊断信息 |
| `TestPowerShellExecute` | 正常执行、空输出、超时、无 pwsh |
| `TestPowerShellToolDef` | 工具名、参数、required 属性 |

---

## 八、与现有系统的对接

| 组件 | 改动 | 状态 |
|------|------|------|
| `tools/__init__.py` | `ToolRegistry` 安全集成 + `default_registry()` 平台选择 | ✅ |
| `tools/security.py` | SecurityGate + PathSandbox + CoreDangerDetector + SensitiveFileChecker | ✅ |
| `tools/bash.py` | Unix-only，移除 Windows 回退逻辑 | ✅ |
| `tools/powershell.py` | pwsh（PowerShell 7+）跨平台执行 | ✅ |
| `tools/read.py` | cat -n 格式 + offset/limit | ✅ |
| `tools/write.py` | 写入 + 自动创建目录 | ✅ |
| `tools/edit.py` | 精确替换 + replace_all | ✅ |
| `tools/glob_tool.py` | pathlib.glob + 相对路径 | ✅ |
| `tools/grep_tool.py` | re 搜索 + glob 过滤 + 上下文 | ✅ |
| `cli/repl.py` | SecurityGate 注入 + ChoiceInput 确认弹窗 + spinner 暂停/恢复 | ✅ |
| `agent/agent.py` | SYSTEM_PROMPT 命令安全指导 + `_build_context_block()` 区分 Shell | ✅ |
| `permissions.py` | `build_security_gate()` 桥接函数（简化 profile） | ✅ |
| `engine/runtime.py` | 用新 registry 替代 `PORTED_TOOLS` | 待做 |
| `registry/tool_pool.py` | 从 `ToolRegistry` 组装 | 待做 |
