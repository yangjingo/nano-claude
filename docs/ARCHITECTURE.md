# Claw Code 架构总览

> Nano CC — 精简 Python 实现

---

## 一、项目定位

**Nano CC** 是 Claude Code 的精简 Python 重写，通过理解代码来精简它。

---

## 二、技术栈

| 层面 | 技术 |
|------|------|
| **语言** | Python 3.12+ |
| **依赖** | `anthropic` (官方 SDK), `rich` (UI) |
| **核心库** | `dataclasses`, `argparse`, `pathlib`, `json`, `asyncio` |

### API 调用

基于 [anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)，**异步流式输出**：

```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic()

async with client.messages.stream(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": "Hello"}],
) as stream:
    async for text in stream.text_stream:
        print(text, end="", flush=True)
```

配置文件 `~/.nano-claude/settings.json`：

```json
{
  "env": {
    "NANO_CLAUDE_API_KEY": "your-key",
    "NANO_CLAUDE_BASE_URL": "https://api.anthropic.com",
    "NANO_CLAUDE_MODEL": "claude-sonnet-4-6"
  }
}
```

---

## 三、代码规模

| 指标 | 数值 |
|------|------|
| Python 文件 | **37** (已删空目录) |
| CLI 命令 | **24** (含 repl) |
| 命令镜像 | 207 条（JSON）|
| 工具镜像 | 184 条（JSON）|

---

## 四、目录结构

```
src/
├── 核心模块
│   ├── main.py          # CLI 入口
│   ├── repl.py          # REPL 交互
│   ├── agent.py         # API 调用 (anthropic SDK)
│   ├── settings.py      # 配置管理
│   ├── runtime.py       # 运行时核心
│   ├── query_engine.py  # 查询引擎
│   ├── commands.py      # 命令注册表
│   ├── tools.py         # 工具注册表
│   ├── permissions.py   # 权限控制
│   ├── models.py        # 领域模型
│   └── ...
│
├── reference_data/
│   ├── commands_snapshot.json
│   ├── tools_snapshot.json
│   └── subsystems/
│
└── 用户配置
    ~/.nano-claude/
    ├── settings.json     # API 配置
    ├── projects/         # 项目数据
    └── sessions/         # 会话历史
```

---

## 五、架构分层

```
REPL 层 (repl.py)
    ↓ 用户交互 /help /exit
Agent 层 (agent.py)
    ↓ anthropic SDK 调用
CLI 层 (main.py)
    ↓ 24 子命令
运行时层 (runtime.py)
    ↓ route / bootstrap / turn_loop
查询引擎层 (query_engine.py)
    ↓ submit / persist
注册表层 (commands.py, tools.py)
    ↓ JSON 快照
配置层 (settings.py)
    ↓ ~/.nano-claude/settings.json
```

---

## 六、核心模型

### 不可变 (frozen=True)

```python
@dataclass(frozen=True)
class PortingModule:
    name: str
    responsibility: str
    source_hint: str
    status: str

@dataclass(frozen=True)
class RoutedMatch:
    kind: str      # 'command' | 'tool'
    name: str
    score: int
```

### 可变状态

```python
@dataclass
class QueryEnginePort:
    mutable_messages: list[str]
    transcript_store: TranscriptStore
```

---

## 七、24 个命令

| 类别 | 命令 |
|------|------|
| 交互 | `repl` (默认) |
| 信息 | `summary`, `manifest`, `parity-audit` |
| 查询 | `commands`, `tools`, `show-*` |
| 运行时 | `route`, `bootstrap`, `turn-loop` |
| 会话 | `flush-transcript`, `load-session` |
| 远程 | `remote-mode`, `ssh-mode`, ... (待删) |
| 执行 | `exec-*` (待删) |

详见 `COMMANDS.md`

---

## 八、快速命令

```bash
# 启动 REPL（默认）
uv run nano-claude

# CLI 子命令
uv run nano-claude summary
uv run nano-claude bootstrap "review this"
uv run nano-claude route "commit changes"

# 测试
uv run unittest discover -s tests -v
```

---

## 相关文档

- `AGENTS.md` — 开发原则
- `NANO.md` — 减法记录
- `COMMANDS.md` — 命令手册
- `docs/posts/` — 博客文章