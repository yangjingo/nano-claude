# Context 设计

> 运行时上下文管理：动态获取、注入、压缩

---

## 一、上下文窗口预算

### 1.1 模型上下文配置

```python
# 默认配置（可通过 settings.json 覆盖）
CONTEXT_CONFIG = {
    "model_context_window": 128_000,   # 默认 128K，按模型调整
    "output_reservation": 16_384,      # 预留输出 ~16K (≈12.8%)
    "compact_threshold_pct": 75,       # 上下文占用 75% 时触发自动压缩
    "warn_threshold_pct": 60,          # 上下文占用 60% 时发出警告
}
```

常见模型上下文窗口：

| 模型 | 上下文窗口 |
|------|-----------|
| Claude Sonnet 4 | 200K |
| Claude Opus 4 | 200K |
| Claude Haiku 4.5 | 200K |
| GPT-4o | 128K |
| GPT-4o-mini | 128K |
| Gemini 2.5 Pro | 1M |

### 1.2 Token 预算公式

```python
有效上下文窗口 = model_context_window - output_reservation

# 示例：128K 模型
有效窗口:   111,616 tokens (128k - 16k 预留)

# 按百分比触发
自动压缩:   83,712 tokens (有效窗口 × 75%)
警告阈值:   66,970 tokens (有效窗口 × 60%)
```

### 1.3 Token 计数来源

**基于 `response.usage` 回传值：**

```python
@dataclass
class TokenCounter:
    """基于 API response.usage 跟踪 token 消耗。"""

    total_input_tokens: int = 0    # 累计 input tokens
    total_output_tokens: int = 0   # 累计 output tokens
    cache_read_tokens: int = 0     # prompt cache 命中

    def update(self, usage: dict) -> None:
        """每次 API 响应后更新计数。"""
        self.total_input_tokens = usage.get("input_tokens", 0)
        self.total_output_tokens = usage.get("output_tokens", 0)
        self.cache_read_tokens = usage.get("cache_read_input_tokens", 0)

    @property
    def context_usage_pct(self) -> float:
        """当前上下文占用百分比。"""
        effective = CONTEXT_CONFIG["model_context_window"] - CONTEXT_CONFIG["output_reservation"]
        if effective == 0:
            return 0.0
        return (self.total_input_tokens / effective) * 100
```

> **注意：** `response.usage` 中的 `input_tokens` 包含 system prompt + tool definitions + conversation history 的总和，可直接用于判断上下文占用。

### 1.4 上下文构成

```
┌──────────────────────────────────────────┐
│ System Prompt                             │ 固定 ~500 tokens
│   - 人设定义                             │
│   - Skill prompts (活跃的)               │
├──────────────────────────────────────────┤
│ Tool Definitions                         │ ~2k-10k tokens
│   - 内置工具 (6-10 个)                   │
│   - MCP 工具 (可变)                      │
├──────────────────────────────────────────┤
│ Runtime Context                          │ ~50 tokens
│   - platform, shell, cwd, git status     │
├──────────────────────────────────────────┤
│ Conversation History                      │ 变量 (最大)
│   - user / assistant messages             │
│   - tool_use blocks                      │
│   - tool_result blocks                   │ ← 最大变量
├──────────────────────────────────────────┤
│ Current Turn                            │
│   - user prompt + tool results          │
│   - model response (streaming)          │
└──────────────────────────────────────────┘
```

**Token 消耗排序：** Tool Definitions > Conversation History > System Prompt > Runtime Context

---

## 二、压缩命令

### 2.1 `/compact` — 手动压缩

用户随时执行，立即触发渐进式压缩（见第三节）。

```
用户: /compact
→ 执行 Step 1 (microcompact) → Step 2 (截断) → 按需 Step 3 (摘要)
→ 输出压缩报告：
  Compacted: 142k → 87k tokens (-39%)
  - 8 tool results microcompacted
  - 2 tool results truncated
  - Conversation history summarized (kept recent 6 turns)
```

### 2.2 `/auto-compact` — 自动压缩开关

```
/auto-compact          → 显示当前状态
/auto-compact on       → 开启自动压缩（默认关闭）
/auto-compact off      → 关闭自动压缩
```

开启后，每次 API 响应检查 `context_usage_pct`：
- **≥ 60%** — 输出警告（黄色提示）
- **≥ 75%** — 自动触发压缩

```python
async def check_auto_compact(self) -> None:
    """API 响应后检查是否需要自动压缩。"""
    if not self.auto_compact_enabled:
        return

    pct = self.token_counter.context_usage_pct
    warn = CONTEXT_CONFIG["warn_threshold_pct"]
    compact = CONTEXT_CONFIG["compact_threshold_pct"]

    if pct >= compact:
        self.console.print(f"[yellow]Auto-compact triggered ({pct:.0f}% context used)[/]")
        await self.run_compact()
    elif pct >= warn:
        self.console.print(
            f"[dim]Context usage: {pct:.0f}% — approaching limit. "
            f"Use /compact to free space.[/]"
        )
```

---

## 三、渐进式压缩策略

核心原则：**从最小侵入开始，只在必要时执行完整摘要。**

```
Step 1: Microcompact (轻量)
  ↓  空间仍不足
Step 2: 工具结果截断
  ↓  空间仍不足
Step 3: 完整对话摘要
```

### 3.1 Step 1 — Microcompact

**不生成摘要，只清理冗余工具结果。**

可压缩工具类型：

```python
COMPACTABLE_TOOLS = {
    "Read",       # 文件读取 — 保留文件路径，清理内容
    "Bash",       # Shell 命令 — 保留命令，清理输出
    "Grep",       # 搜索 — 保留匹配数，清理具体行
    "Glob",       # 文件匹配 — 保留文件列表，清理路径细节
    "WebSearch",  # 网络搜索 — 保留摘要，清理详情
    "WebFetch",   # 网页获取 — 保留 URL + 摘要
    "Edit",       # 文件编辑 — 保留 diff 摘要
    "Write",      # 文件写入 — 保留路径
}
```

时间基础清理策略：

```python
def microcompact_tool_result(tool_name: str, content: str, age_minutes: int) -> str:
    """根据消息年龄动态压缩工具结果。"""
    if age_minutes < 5:   # 最近 5 分钟：完整保留
        return content

    if tool_name in COMPACTABLE_TOOLS:
        if age_minutes < 20:  # 5-20 分钟：保留关键信息
            return _summarize_tool_result(tool_name, content)
        else:                 # 20+ 分钟：清理
            return f"[Old tool result content cleared]"

    return content  # 不可压缩工具：保持原样
```

清理标记 `[Old tool result content cleared]` 让模型知道这里曾有内容但被压缩了。

### 3.2 Step 2 — 工具结果截断

对于无法 microcompact 的大结果：

```python
MAX_TOOL_RESULT_LINES = 500  # 单次工具结果最大行数

def truncate_tool_result(content: str) -> str:
    lines = content.split("\n")
    if len(lines) > MAX_TOOL_RESULT_LINES:
        kept = lines[:MAX_TOOL_RESULT_LINES]
        truncated = len(lines) - MAX_TOOL_RESULT_LINES
        return "\n".join(kept) + f"\n... ({truncated} {truncated} more lines)"
    return content
```

### 3.3 Step 3 — 完整对话摘要

当 microcompact + 截断仍不够时，对整个对话历史执行摘要：

```python
async def full_compact(messages: list[dict]) -> list[dict]:
    """将旧消息压缩为摘要，保留最近 N 轮。"""
    KEEP_RECENT_TURNS = 6  # 保留最近 6 轮完整对话

    old_messages = messages[:-KEEP_RECENT_TURNS]
    recent_messages = messages[-KEEP_RECENT_TURNS:]

    if not old_messages:
        return messages

    # 调用模型生成摘要
    summary = await generate_summary(old_messages)

    return [
        {"role": "user", "content": f"[Conversation history compacted]\n{summary}"},
        {"role": "assistant", "content": "Understood, I'll continue from this context."},
        *recent_messages,
    ]
```

**信息保留优先级：**
1. 用户消息（完整保留）
2. 关键决策和结论
3. 代码片段（不截断）
4. 技术细节和错误信息
5. 工具调用结果的路径信息（清理具体内容）

---

## 四、动态上下文注入

### 4.1 SessionContext — 运行时上下文管理器

```python
@dataclass
class SessionContext:
    """Mutable runtime context, refreshed before each API call."""

    # 静态（初始化时设置）
    platform: str
    shell: str
    shell_hint: str
    python_version: str
    git_branch: str
    project_root: Path

    # 动态（每次刷新）
    cwd: Path
    git_status: str

    def refresh(self) -> None:
        """刷新动态字段。每次 API 调用前调用。"""
        self.cwd = Path.cwd()
        try:
            r = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, timeout=3,
            )
            self.git_status = r.stdout.strip()
        except Exception:
            self.git_status = ""

    def render(self) -> str:
        """渲染为消息前缀。"""
        parts = [
            f"Platform: {self.platform}",
            f"Shell: {self.shell_hint}",
            f"Python: {self.python_version}",
            f"Git: {self.git_branch} | CWD: {self.cwd}",
        ]
        if self.git_status:
            parts.append(f"Changed:\n{self.git_status}")
        return "\n".join(parts)
```

### 4.2 注入策略

**system prompt = 固定人设（永不变）**
**context block = 渲染到每条 user message 前缀（动态刷新）**

```python
async def run_turn(self, prompt, tools, tool_runner):
    self.context.refresh()

    # 注入到 user message 前缀
    enriched = f"{self.context.render()}\n\n{prompt}"
    self.messages.append({"role": "user", "content": enriched})
    ...
```

---

## 五、Skill/MCP 的上下文管理

### 5.1 Skill Prompt 注入

Skill 本质是 prompt 模板，激活时注入 system prompt：

```
System Prompt (固定部分)
├── 人设定义
├── 通用规则
└── 活跃 Skill Prompt（动态部分）
    ├── /commit → commit 流程指南
    ├── /review → review 检查清单
    └── /qa → QA 测试策略
```

**策略：**
- 只注入当前活跃 skill 的 prompt
- Skill prompt 缓存在本地，避免重复传输
- Skill prompt 过大时触发 compact 评估

### 5.2 MCP Tool Definition 管理

MCP 服务器可以暴露大量工具，每个工具定义占用 ~100-500 tokens：

```
Tool Definitions
├── 内置工具 (~3k tokens)
│   ├── Bash, Read, Edit, Write, Glob, Grep
│   └── ...
└── MCP 工具 (可变，可能 5k-50k)
    ├── mcp__github__* (5 个工具)
    ├── mcp__postgres__* (8 个工具)
    └── ...
```

**策略：**
- 内置工具始终包含
- MCP 工具按需加载（首次使用时注入）
- MCP 工具过多时执行 tool definition compact（只保留 name + description，去掉完整 schema）
- 用户可通过 `--simple-mode` 或 deny prefix 排除不需要的 MCP 工具

### 5.3 Compact 与 Skill/MCP 的交互

```
compact 触发时：
1. 先 microcompact 工具结果（最大收益）
2. 评估 MCP tool definitions 占用
3. 如果 MCP tools 占用 > 30% 有效窗口 → 压缩为 name-only
4. 如果仍不够 → 完整对话摘要
5. Skill prompt 不压缩（通常很小）
```

---

## 六、透明性

压缩后的摘要对用户可见：

```
* Auto-compacted conversation (147k → 89k tokens)
  - 12 tool results compressed
  - 3 MCP tool definitions compacted
  - Conversation history summarized
```

用户可通过展开操作查看被压缩的原始内容（如果本地有缓存）。

---

## 七、实现路线

### Phase 1: 基础设施
1. `SessionContext` + `build_session_context()`
2. 上下文注入到 user message 前缀
3. `run_turn()` 每次调用前 refresh()

### Phase 2: Token 计数 + 压缩命令
4. `TokenCounter` — 基于 `response.usage` 累计 token
5. `CONTEXT_CONFIG` — 模型上下文窗口 + 百分比阈值（settings.json 可配）
6. `/compact` 命令 — 手动触发渐进式压缩
7. `/auto-compact` 命令 — 开关 + 自动检查逻辑

### Phase 3: Microcompact
8. `microcompact_tool_result()` — 时间基础清理
9. 工具结果截断
10. `_summarize_tool_result()` — 按工具类型生成摘要

### Phase 4: 完整压缩（摘要策略待定）
11. 自动压缩阈值检测（基于百分比）
12. `full_compact()` — 对话摘要 + 最近 N 轮保留
13. **摘要 prompt 设计**（后续讨论）

### Phase 5: Skill/MCP 集成
14. Skill prompt 动态注入
15. MCP tool definition 按需加载
16. MCP tool definition 压缩

### Phase 6: 透明性
17. Compact 事件通知用户
18. 压缩统计（节省了多少 tokens）
19. 展开查看原始内容
