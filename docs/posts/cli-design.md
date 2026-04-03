# CLI Design

> Nano-Claude 终端交互设计：极简 REPL + 富交互体验

---

## 技术栈选型

| 组件 | Claude Code (TS) | nano-claude (Python) |
|------|------------------|----------------------|
| 框架 | React + Ink | prompt-toolkit |
| 渲染 | Rich | Rich |
| 动画 | Ink 动画 | Status + Live |
| 测试 | Vitest | pytest + pexpect |
| 包管理 | npm/pnpm | uv |

---

## 核心特性

### 1. 交互式 REPL

使用 `prompt-toolkit` 实现丝滑输入体验：

- **命令自动补全** - 输入 `/` 显示命令菜单
- **选择菜单** - `ChoiceInput` 实现交互式选择
- **历史记录** - 上下键浏览历史
- **非交互模式** - 自动 fallback 到简单 `input()`

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts.choice_input import ChoiceInput

# 命令补全
session = PromptSession(completer=CommandCompleter())
raw = await session.prompt_async(">")

# 选择菜单
choice = ChoiceInput(message="Select:", options=[...])
selected = await choice.prompt_async()
```

### 2. 流式输出

Agent SDK 支持流式输出，包含 thinking 内容：

```python
async for chunk in agent.send_stream(prompt):
    if chunk.type == "thinking":
        console.print(chunk.content, style="dim")
    else:
        console.print(chunk.content)
```

**显示效果**：
```
∴ Thinking…
<model's internal reasoning...>

Hello! How can I help you today?
```

### 3. Buddy Pet System

终端宠物系统，增加情感连接：

```
┌─────────────────────────────────── Zelda ───────────────────────────────────┐
│                                                                             │
│       ___                                                                   │
│      /   \                                                                  │
│     |..|                                                                    │
│     |  __  |                                                                │
│      \    /                                                                 │
│     /|    |\                                                                │
│    (_|____|_)                                                               │
│                                                                             │
│ Health   +++++----- 56                                                      │
│ Stamina  ###::::::: 33                                                      │
│ Skill    #########: 93                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

- 10 种角色（Zelda Champions + Monsters）
- 5 种稀有度（Common → Legendary）
- 属性系统（Health, Stamina, Skill）
- Rich Panel 渲染

### 4. 状态动画

流式响应时的实时状态显示：

```
* Thinking... (2s)
* Grooving... (5s) · ↑ 1.2k tokens
```

---

## 文件结构

```
src/cli/
├── main.py          # CLI entrypoint
└── repl.py          # Interactive REPL

src/agent/
├── agent.py         # Streaming agent
└── settings.py      # Configuration

src/buddy/
├── models.py        # Buddy, Species, Rarity
├── generator.py     # Deterministic generation
└── species.py       # 10 Zelda characters
```

---

## 命令系统

| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助 |
| `/exit` | 退出 REPL |
| `/model` | 模型选择菜单 |
| `/config` | 显示配置 |
| `/buddy` | 抽取宠物 |

### 选择菜单风格

黑色背景 + 数字编号：

```
╭─────────────────────────────────────────────────────────────────────────────╮
│ Select command:                                                             │
│                                                                             │
│   1. Show available commands                                                │
│   2. Exit REPL                                                              │
│   3. Show or switch model                                                   │
│   4. Show configuration                                                     │
│   5. Roll a random buddy pet                                                │
│                                                                             │
╰─────────────────────────────────────────────────────────────────────────────╯
```

---

## 稀有度配色

| Rarity | Color | Chance |
|--------|-------|--------|
| Common | `#99a5b2` | 60% |
| Uncommon | `#a4bf8d` | 25% |
| Rare | `#86c0d0` | 10% |
| Epic | `#b78aaf` | 4% |
| Legendary | `#ebca89` | 1% |

---

## 错误处理

### Ctrl+C 友好退出

```python
try:
    async for chunk in agent.send_stream(prompt):
        ...
except asyncio.CancelledError:
    console.print("\n[dim]Interrupted[/]")
except KeyboardInterrupt:
    console.print("\n[dim]Goodbye![/]")
```

### 非交互模式

当检测到非 TTY 环境时，自动切换：

```python
if not sys.stdin.isatty():
    return None  # Fallback to simple input()
```

---

## E2E 测试

使用 `pexpect` + `pywinpty` 实现跨平台测试：

```python
from pexpect import popen_spawn

child = popen_spawn.PopenSpawn("uv run python -m src.cli.main")
child.expect("Nano-Claude")
child.sendline("/help")
child.expect("Commands:")
```

---

## 设计决策

| 决策 | 原因 |
|------|------|
| prompt-toolkit | 丝滑输入体验，自动补全，历史记录 |
| Rich Panel | 结构化显示，支持颜色和样式 |
| ChoiceInput | 交互式选择菜单，优于简单 input |
| pexpect + pywinpty | 跨平台 E2E 测试支持 |
| 黑色背景菜单 | 统一视觉风格，清晰对比 |

---

## 参考

- [prompt-toolkit Documentation](https://python-prompt-toolkit.readthedocs.io/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [pexpect Documentation](https://pexpect.readthedocs.io/)
- [Buddy Design](./buddy-design.md)