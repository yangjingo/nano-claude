# Tool 实现设计

> 从 mirrored registry 到可执行 tool 系统

---

## 〇、参考实现：nanocode

[nanocode](https://github.com/1rgs/nanocode) — 271 行 Python，零依赖，完整 tool loop。

核心设计极其精简：

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

def make_schema():
    """三元组 → API tool definition，自动推断 required（后缀 ? 表示 optional）。"""
    ...

# agentic loop: 30 行
while True:
    response = call_api(messages, system_prompt)
    for block in content_blocks:
        if block["type"] == "text":    print(block["text"])
        if block["type"] == "tool_use": run_tool(name, args) → tool_result
    if not tool_results: break
    messages.append(tool_results)  # feed back → loop
```

**我们借鉴的设计**：
- `TOOLS` dict + `make_schema()` 模式 → 我们的 `ToolRegistry.make_schema()`
- `(desc, schema, handler)` 三元组 → 我们的 `ToolDef` dataclass
- agentic loop 结构 → 我们的 `AgentSession.run_turn()`

**我们的差异**：
- nanocode 用 `urllib.request` 直接调 REST API；我们用 `anthropic` SDK（async streaming）
- nanocode 同步；我们全异步（`asyncio.create_subprocess_exec`）
- nanocode 无类型；我们用 frozen dataclass + `ToolFunc` 类型别名
- nanocode 单文件；我们 `src/tools/` 模块化，每个工具一个文件

---

## 一、现状分析

### 当前状态：纯镜像注册表

工具系统目前是一个 **只读元数据层**，没有实际执行能力：

```
tools_snapshot.json (184 条 TS 文件路径)
    ↓ lru_cache 加载
registry/tools.py → tuple[PortingModule, ...]  # 只有 name/source_hint/responsibility
    ↓ execute_tool()
ToolExecution(handled=True, message="would handle payload...")  # 永远是模拟的
```

**关键问题**：
- `PortingModule` 只有三个字段（name, responsibility, source_hint），没有 input schema
- `execute_tool()` 返回固定字符串，不执行任何操作
- 没有工具与 anthropic SDK tool_use 的对接机制
- 权限系统（`ToolPermissionContext`）只有 deny list，没有运行时审批

### 已有基础

| 组件 | 文件 | 状态 |
|------|------|------|
| Agent SDK 调用 | `src/agent/agent.py` | 可用，已支持 tool_calls 解析 |
| 权限过滤 | `src/permissions.py` | 可用（deny_names / deny_prefixes） |
| 工具池组装 | `src/registry/tool_pool.py` | 可用（过滤 + markdown 渲染） |
| 路由匹配 | `src/engine/runtime.py` | 可用（token-based 模糊匹配） |

---

## 二、工具全景（从 snapshot 提取）

### 2.1 内置工具清单

按功能分类，共 **25 个顶层工具**：

| 分类 | 工具 | TS 文件数 | 优先级 |
|------|------|-----------|--------|
| **文件操作** | `FileReadTool`, `FileEditTool`, `FileWriteTool`, `GlobTool`, `GrepTool` | 18 | P0 |
| **Shell 执行** | `BashTool`, `PowerShellTool` | 24 | P0 |
| **Agent 系统** | `AgentTool`, `SendMessageTool` | 15 | P1 |
| **任务管理** | `TaskCreateTool`, `TaskGetTool`, `TaskListTool`, `TaskOutputTool`, `TaskStopTool`, `TaskUpdateTool` | 12 | P1 |
| **计划模式** | `EnterPlanModeTool`, `ExitPlanModeV2Tool` | 8 | P1 |
| **Worktree** | `EnterWorktreeTool`, `ExitWorktreeTool` | 8 | P2 |
| **定时任务** | `CronCreateTool`, `CronDeleteTool`, `CronListTool` | 5 | P2 |
| **Web** | `WebFetchTool`, `WebSearchTool` | 8 | P2 |
| **MCP** | `MCPTool`, `McpAuthTool`, `ListMcpResourcesTool`, `ReadMcpResourceTool` | 8 | P3 |
| **交互** | `AskUserQuestionTool`, `BriefTool` | 8 | P2 |
| **LSP** | `LSPTool` | 5 | P3 |
| **Notebook** | `NotebookEditTool` | 5 | P3 |
| **Skill** | `SkillTool` | 5 | P2 |
| **其他** | `ConfigTool`, `RemoteTriggerTool`, `SyntheticOutputTool`, `TeamCreateTool`, `TeamDeleteTool`, `TodoWriteTool`, `ToolSearchTool` | 18 | P2-P3 |

### 2.2 每个工具的内部结构（从 TS 推断）

TypeScript 中每个工具目录的典型结构：

```
tools/BashTool/
├── BashTool.tsx      # 主逻辑 + execute()
├── UI.tsx            # 渲染组件（CLI 下不需要）
├── prompt.ts         # system prompt 片段（工具描述 + 参数说明）
├── bashPermissions.ts  # 权限检查
├── bashSecurity.ts     # 安全校验
├── commandSemantics.ts # 命令语义分析
├── destructiveCommandWarning.ts  # 危险命令警告
├── pathValidation.ts  # 路径验证
├── readOnlyValidation.ts  # 只读模式验证
├── sedEditParser.ts   # sed 编辑解析
├── sedValidation.ts   # sed 校验
├── shouldUseSandbox.ts  # 沙箱判断
└── utils.ts           # 工具函数
```

**Python 端需要保留的核心**：`execute()` + `prompt` + 权限/安全逻辑。`UI.tsx` 可以完全丢弃。

---

## 三、核心架构设计（基于原版 Tool.ts 深度分析）

### 3.1 Tool 接口全景

原版 `Tool<Input, Output, P>` 是一个多维度接口，不仅仅是 "执行函数"：

```
Tool<Input, Output, P>
├── 生命周期方法（执行主流程）
│   ├── validateInput()      — 轻量级输入验证，早期失败
│   ├── checkPermissions()   — allow / deny / passthrough
│   ├── call()               — 核心执行逻辑
│   └── description()        — 动态生成工具描述
│
├── 元数据方法（系统调度决策）
│   ├── isEnabled()           — 运行时可用性（默认 true）
│   ├── isReadOnly(input)     — 只读判定 → 影响并发 + 权限
│   ├── isConcurrencySafe()   — 并发安全性（默认 false）
│   └── isDestructive(input)  — 破坏性标识 → 额外安全提示
│
└── UI 渲染方法（终端集成）
    ├── renderToolUseMessage()      — "Bash: npm test"
    ├── renderToolResultMessage()   — 压缩/详细模式
    ├── renderToolUseProgressMessage() — 长任务进度
    ├── getToolUseSummary()         — 单行摘要
    └── getActivityDescription()    — spinner 动词
```

### 3.2 Python Protocol 设计

```python
# src/tools/protocol.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Coroutine, Protocol


# ─── 结果类型 ─────────────────────────────────────────

@dataclass(frozen=True)
class ToolResult:
    output: str
    is_error: bool = False


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    error: str | None = None
    ask_message: str | None = None  # 需要用户确认时的提示


class PermissionBehavior(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"        # 对应原版 passthrough


@dataclass(frozen=True)
class PermissionResult:
    behavior: PermissionBehavior
    message: str = ""
    updated_input: dict[str, Any] | None = None


# ─── 进度报告 ─────────────────────────────────────────

@dataclass
class ToolProgress:
    """工具执行的实时进度。"""
    tool_use_id: str
    data: dict[str, Any]  # {type: "bash", stdout: "..."} 等


ProgressCallback = Callable[[ToolProgress], None]


# ─── Tool Protocol ────────────────────────────────────

class Tool(Protocol):
    """工具协议。Python 版的 Tool<Input, Output, P>。

    每个维度都有安全的默认值（对应原版 buildTool() 的 TOOL_DEFAULTS）。
    """

    # 必须实现
    name: str
    description: str
    async def call(self, **params: Any) -> ToolResult: ...

    # 可选覆盖（都有默认实现）
    def validate_input(self, **params: Any) -> ValidationResult: ...
    def check_permissions(self, **params: Any) -> PermissionResult: ...
    def is_enabled(self) -> bool: ...
    def is_read_only(self, **params: Any) -> bool: ...
    def is_concurrency_safe(self, **params: Any) -> bool: ...
    def is_destructive(self, **params: Any) -> bool: ...

    # UI（可选）
    def activity_description(self, **params: Any) -> str: ...
    def result_summary(self, result: ToolResult) -> str: ...
```

### 3.3 build_tool() 工厂函数

对应原版 `buildTool()` + `TOOL_DEFAULTS`，提供安全默认值：

```python
# src/tools/builder.py
from .protocol import (
    Tool, ToolResult, ValidationResult, PermissionResult, PermissionBehavior,
)

def build_tool(
    name: str,
    description: str,
    *,
    call: Callable,
    validate_input: Callable | None = None,
    check_permissions: Callable | None = None,
    is_enabled: Callable[[], bool] | None = None,
    is_read_only: Callable[..., bool] | None = None,
    is_concurrency_safe: Callable[..., bool] | None = None,
    is_destructive: Callable[..., bool] | None = None,
    activity_description: Callable[..., str] | None = None,
    result_summary: Callable[[ToolResult], str] | None = None,
    params: tuple | None = None,
) -> Tool:
    """创建工具实例，未覆盖的方法使用安全默认值。"""
    ...
```

### 3.4 渐进式工具组装（三级流水线）

对应原版 `getAllBaseTools()` → `getTools()` → `assembleToolPool()`：

```
Level 1: get_all_tools()
    所有内置工具（无条件加载 + 特性开关 + 平台检测）
    ↓
Level 2: filter_by_permissions(tools, permission_context)
    deny list 过滤 + simple mode 裁剪
    ↓
Level 3: assemble_tool_pool(tools, mcp_tools)
    合并 MCP 工具 + 按名称排序去重
    ↓
    make_schema() → API tool definitions
```

### 3.5 三层权限系统

```
Layer 1: 工具级 — check_permissions()
    FileReadTool → always allow
    FileWriteTool → ask (首次写路径)

Layer 2: 规则级 — PermissionContext
    always_allow: [Bash(git status), Bash(git diff)]
    always_deny:  [Bash(rm -rf /), Bash(git push --force)]
    always_ask:   [Bash(npm publish)]

Layer 3: 模式级 — 代理模式白名单
    子代理禁止: AgentTool, TaskOutputTool
    异步代理允许: 文件操作, Shell, 搜索
```

### 3.6 进度报告

```python
# 进度数据类型（对应原版 ToolProgressData union）
@dataclass
class BashProgress:
    type: str = "bash"
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None

@dataclass
class AgentProgress:
    type: str = "agent"
    agent_id: str = ""
    status: str = ""  # running, completed, error

# 进度回调由 call() 接收，工具在执行中推送
async def call(self, command: str, on_progress=None, **params) -> ToolResult:
    proc = await create_subprocess(...)
    while True:
        line = await proc.stdout.readline()
        if on_progress:
            on_progress(ToolProgress(
                tool_use_id=...,
                data=BashProgress(stdout=line),
            ))
    ...
```

### 3.7 当前实现 vs 目标架构

| 维度 | 当前 ToolDef | 目标 Tool Protocol |
|------|-------------|-------------------|
| 定义 | `(name, desc, params, handler)` | 完整 Protocol |
| 输入验证 | 无 | `validate_input()` |
| 权限 | 无 | `check_permissions()` → `PermissionResult` |
| 执行 | `handler(**args) -> str` | `call(**params, ctx, on_progress) -> ToolResult` |
| 元数据 | 无 | `is_read_only`, `is_destructive`, `is_concurrency_safe` |
| 进度 | 无 | `on_progress` 回调 |
| UI | 无 | `activity_description`, `result_summary` |
| 工厂 | 无 | `build_tool()` 安全默认值 |
| 组装 | 单层 `ToolRegistry` | 三级流水线 |

**演进策略**：当前 `ToolDef` 作为最小可用版本保留，新工具逐步迁移到 `Tool` Protocol。`ToolRegistry.make_schema()` 同时支持两种格式。

---

## 四、P0 工具实现方案

### 4.1 FileReadTool

**职责**：读取文件内容，支持 offset/limit 分页

```python
# src/tools/file_read.py
class FileReadTool(Tool):
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="FileRead",
            description="Read a file from the filesystem. Supports offset and limit for large files.",
            parameters=(
                ToolParameter("file_path", "string", description="Absolute path to the file"),
                ToolParameter("offset", "integer", required=False, description="Line offset (0-based)"),
                ToolParameter("limit", "integer", required=False, description="Max lines to read"),
            ),
        )

    async def execute(self, file_path: str, offset: int = 0, limit: int = 2000) -> ToolResult:
        path = Path(file_path)
        if not path.exists():
            return ToolResult(output="", error=f"File not found: {file_path}", is_error=True)
        if not path.is_file():
            return ToolResult(output="", error=f"Not a file: {file_path}", is_error=True)

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        sliced = lines[offset:offset + limit] if limit else lines[offset:]
        numbered = "\n".join(f"{i + 1}\t{line}" for i, line in enumerate(sliced, start=offset))
        return ToolResult(output=numbered)
```

**注意**：图片读取和 PDF 读取是 Claude Code 的特色功能，后续迭代加入。

### 4.2 FileEditTool

**职责**：精确字符串替换

```python
class FileEditTool(Tool):
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="FileEdit",
            description="Performs exact string replacements in files.",
            parameters=(
                ToolParameter("file_path", "string"),
                ToolParameter("old_string", "string", description="Text to replace"),
                ToolParameter("new_string", "string", description="Replacement text"),
                ToolParameter("replace_all", "boolean", required=False, default=False),
            ),
        )

    async def execute(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> ToolResult:
        path = Path(file_path)
        if not path.exists():
            return ToolResult(output="", error=f"File not found: {file_path}", is_error=True)

        content = path.read_text(encoding="utf-8")
        if old_string not in content:
            return ToolResult(output="", error="old_string not found in file", is_error=True)
        if not replace_all and content.count(old_string) > 1:
            return ToolResult(output="", error=f"old_string appears {content.count(old_string)} times, use replace_all or provide more context", is_error=True)

        replacement = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)
        path.write_text(replacement, encoding="utf-8")
        return ToolResult(output=f"Replaced in {file_path}")
```

### 4.3 FileWriteTool

**职责**：创建/覆写文件

```python
class FileWriteTool(Tool):
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="FileWrite",
            description="Writes content to a file. Creates new or overwrites existing.",
            parameters=(
                ToolParameter("file_path", "string"),
                ToolParameter("content", "string"),
            ),
        )

    async def execute(self, file_path: str, content: str) -> ToolResult:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(output=f"Wrote {len(content)} chars to {file_path}")
```

### 4.4 GlobTool

**职责**：基于 glob 模式搜索文件

```python
class GlobTool(Tool):
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="Glob",
            description="Fast file pattern matching using glob syntax.",
            parameters=(
                ToolParameter("pattern", "string", description="Glob pattern, e.g. '**/*.py'"),
                ToolParameter("path", "string", required=False, description="Root directory"),
            ),
        )

    async def execute(self, pattern: str, path: str | None = None) -> ToolResult:
        import glob as globmod
        root = Path(path) if path else Path.cwd()
        matches = sorted(globmod.glob(str(root / pattern), recursive=True))
        return ToolResult(output="\n".join(matches) if matches else "No matches found")
```

### 4.5 GrepTool

**职责**：基于正则表达式搜索文件内容

```python
class GrepTool(Tool):
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="Grep",
            description="Search file contents using regex patterns.",
            parameters=(
                ToolParameter("pattern", "string"),
                ToolParameter("path", "string", required=False),
                ToolParameter("glob", "string", required=False, description="File filter, e.g. '*.py'"),
                ToolParameter("output_mode", "string", required=False, default="files_with_matches",
                              enum=["content", "files_with_matches", "count"]),
            ),
        )

    async def execute(self, pattern: str, path: str | None = None, glob: str | None = None,
                      output_mode: str = "files_with_matches") -> ToolResult:
        import subprocess
        cmd = ["rg", "--json", pattern]
        if path:
            cmd.extend(["--", path])
        if glob:
            cmd.extend(["--glob", glob])
        if output_mode == "content":
            pass  # default rg behavior
        elif output_mode == "files_with_matches":
            cmd.insert(1, "--files-with-matches")
        elif output_mode == "count":
            cmd.insert(1, "--count")
        # ... subprocess 执行 ...
```

**注意**：Python 标准库的 `re` 模块在处理大型代码库时性能不足，建议依赖 `ripgrep`（rg）。如果不可用，fallback 到 `pathlib.rglob` + `re.search`。

### 4.6 BashTool

**职责**：执行 shell 命令

这是最复杂的工具，需要处理：
- 沙箱执行（subprocess isolation）
- 危险命令检测（`rm -rf`, `DROP TABLE`, `git push --force`）
- 超时控制
- 输出截断
- 权限审批流程

```python
class BashTool(Tool):
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="Bash",
            description="Execute a bash command and return its output.",
            parameters=(
                ToolParameter("command", "string"),
                ToolParameter("timeout", "integer", required=False, default=120000,
                              description="Timeout in milliseconds"),
                ToolParameter("description", "string", required=False,
                              description="Human-readable description of the command"),
                ToolParameter("run_in_background", "boolean", required=False, default=False),
            ),
        )

    def is_dangerous(self, **params: Any) -> bool:
        """检测危险命令，需要用户确认。"""
        command = params.get("command", "")
        dangerous_patterns = [
            r"\brm\s+(-[rfRF]+\s+)*/",  # rm -rf /
            r"\bgit\s+push\s+.*--force",  # force push
            r"\bDROP\s+TABLE",  # SQL destructive
            r"\bDELETE\s+FROM\s+\w+\s*;",  # SQL delete all
            r"\bgit\s+reset\s+--hard",  # git reset hard
        ]
        return any(re.search(p, command) for p in dangerous_patterns)

    async def execute(self, command: str, timeout: int = 120000,
                      description: str = "", run_in_background: bool = False) -> ToolResult:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout / 1000
            )
        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(output="", error=f"Command timed out after {timeout}ms", is_error=True)

        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")
        return ToolResult(
            output=output,
            error=error if error else None,
            is_error=proc.returncode != 0,
        )
```

---

## 五、权限系统设计

### 5.1 三级权限模型

```
Level 0: Auto-approve（无需确认）
  - FileRead, Glob, Grep（只读操作）
  - TaskCreate, TaskList, TaskGet（查询操作）

Level 1: Context-aware（条件审批）
  - FileEdit, FileWrite（首次写入需确认，同文件后续编辑自动通过）
  - Bash（安全命令自动通过，危险命令需确认）

Level 2: Always-ask（始终需要确认）
  - Bash（匹配危险模式时）
  - 任何 is_dangerous() 返回 True 的调用
```

### 5.2 Permission Gate 接口

```python
# src/permissions_v2.py
from enum import Enum
from src.tool_protocol import Tool, ToolResult


class PermissionDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionGate:
    """运行时权限决策。"""

    async def check(self, tool: Tool, params: dict) -> PermissionDecision:
        # 1. 检查全局 deny list（已有逻辑）
        # 2. 检查工具自带的 is_dangerous()
        # 3. 检查用户会话级的 allow list（已批准过的同类操作）
        # 4. 默认：只读工具 ALLOW，写入工具 ASK
        ...
```

---

## 六、目录结构

```
src/
├── tools/                    # 具体工具实现
│   ├── __init__.py           # ToolParam, ToolDef, ToolResult, ToolRegistry ✅
│   ├── bash.py               # BashTool（跨平台 shell 检测 + async execute）✅
│   ├── file_read.py          # P0（待实现）
│   ├── file_edit.py          # P0（待实现）
│   ├── file_write.py         # P0（待实现）
│   ├── glob_tool.py          # P0（待实现）
│   ├── grep_tool.py          # P0（待实现）
│   └── ...
├── registry/
│   ├── tools.py              # 保留：mirrored registry（向后兼容）
│   └── tool_pool.py          # 保留：权限过滤池
└── agent/
    └── agent.py              # ✅ 新增 run_turn() + TurnOutput + ToolInvocation
```

---

## 七、实现路线

### Phase 1: 基础设施 ✅

1. ~~创建 `tool_protocol.py` — 定义 `Tool`, `ToolResult`, `ToolSchema`~~ → `src/tools/__init__.py`
2. ~~创建 `src/tools/__init__.py`~~ — `ToolParam`, `ToolDef`, `ToolResult`, `ToolRegistry`
3. ~~重构 `ToolRegistry` — 注册、查找、schema 导出~~
4. ~~集成到 `AgentSession` — tool_use 循环~~ → `run_turn()` 方法

### Phase 2: P0 工具

5. ~~`BashTool` — shell 执行（跨平台：Git Bash / cmd.exe / /bin/bash）~~ ✅
6. `FileReadTool` — 文件读取（offset/limit）
7. `GlobTool` — 文件搜索
8. `GrepTool` — 内容搜索（依赖 rg 或 fallback）
9. `FileEditTool` — 字符串替换
10. `FileWriteTool` — 文件写入

### Phase 3: 权限系统（1 天）

11. `PermissionGate` — 三级权限
12. 与 REPL 交互 — 用户审批流程（y/n 确认）

### Phase 4: P1 工具（2 天）

13. `AskUserQuestionTool` — 交互式问答
14. `TaskTools` — 任务管理（6 合 1）
15. `PlanModeTools` — 计划模式切换
16. `AgentTool` — 子 agent 生成（基础版）

### Phase 5: P2-P3 工具（按需）

17. `WebFetchTool`, `WebSearchTool`
18. `NotebookEditTool`
19. `MCPTool`, `McpAuthTool`
20. `LSPTool`

---

## 八、关键设计决策

### 8.1 异步 vs 同步

**决策**：所有工具的 `execute()` 都是 `async`。

原因：
- `BashTool` 需要 `asyncio.create_subprocess_shell`
- `WebFetchTool` 需要 `aiohttp` 或 `httpx`
- 未来 MCP 工具需要网络 IO
- 即使是同步的文件操作，`async` 也不会有性能损失

### 8.2 单文件 vs 每工具一个目录

**决策**：P0 工具每工具一个文件，相关工具可合并。

TypeScript 用每个工具一个目录（含 UI 组件），Python 不需要 UI 层，一个文件足够。6 个 Task 工具放在一个文件中即可。

### 8.3 依赖 rg vs 纯 Python

**决策**：优先使用 `rg`（ripgrep），不可用时 fallback 到 `pathlib` + `re`。

原因：ripgrep 在大型代码库中快 10-100 倍，Claude Code 本身也依赖它。

### 8.4 保留 mirrored registry

**决策**：保留 `registry/tools.py` 的镜像注册表作为参考，新 registry 独立存在。

`tools_snapshot.json` 和 mirrored registry 仍然有价值——它们记录了 TS 源码结构，可以辅助 parity audit。

---

## 九、测试策略

```python
# tests/test_tools.py

class TestFileReadTool:
    async def test_read_existing_file(self, tmp_path):
        (tmp_path / "test.txt").write_text("hello")
        tool = FileReadTool()
        result = await tool.execute(file_path=str(tmp_path / "test.txt"))
        assert result.output == "1\thello"
        assert not result.is_error

    async def test_read_nonexistent_file(self):
        tool = FileReadTool()
        result = await tool.execute(file_path="/nonexistent")
        assert result.is_error

    async def test_read_with_offset_limit(self, tmp_path):
        lines = [f"line {i}" for i in range(100)]
        (tmp_path / "big.txt").write_text("\n".join(lines))
        tool = FileReadTool()
        result = await tool.execute(file_path=str(tmp_path / "big.txt"), offset=10, limit=5)
        assert "11\tline 10" in result.output
        assert "16\tline 15" in result.output
```

每个工具至少测试：
- 正常执行
- 错误输入（文件不存在、无效参数）
- 边界条件（空文件、超大文件、特殊字符）

---

## 十、与现有系统的对接点

| 现有组件 | 改动 | 状态 |
|---------|------|------|
| `agent/agent.py` | `AgentSession` 新增 `run_turn()` + `TurnOutput` + `ToolInvocation` | ✅ |
| `cli/repl.py` | `_run_connected()` 集成 `ToolRegistry`，`_display_tool_invocation()` UX | ✅ |
| `tools/__init__.py` | `ToolParam`, `ToolDef`, `ToolResult`, `ToolRegistry` | ✅ |
| `tools/bash.py` | 跨平台 shell 检测 + async `execute()` + `bash_tool` 定义 | ✅ |
| `engine/runtime.py` | `bootstrap_session` 用新 registry 替代 `PORTED_TOOLS` | 待做 |
| `registry/tool_pool.py` | 改为从 `ToolRegistry` 组装 | 待做 |
| `permissions.py` | 扩展为 `PermissionGate`，保留现有 deny 逻辑 | 待做 |
