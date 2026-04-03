# Nano Claude

> 极简 Claude Code 学习实现

---

## 是什么

从 Claude Code 源码学习，用极简 Python 重新实现核心功能。

```
理解 → 删除 → 理解更深
```

---

## 特性

| 功能 | 状态 | 说明 |
|------|------|------|
| 交互式 REPL | ✅ | prompt-toolkit，命令补全，选择菜单 |
| 流式输出 | ✅ | 支持 thinking 内容显示 |
| Buddy Pet | ✅ | 10 种角色，5 种稀有度，属性系统 |
| 配置管理 | ✅ | settings.json，模型切换 |
| Memory System | 🚧 | 本地存储，梦境呈现 |
| Tool Calling | 📋 | 待实现 |

---

## 运行

```bash
# 安装依赖
uv sync

# 启动 REPL
uv run nano-claude

# 或直接运行
uv run python -m src.cli.main
```

### REPL 命令

```
> hello              # 与 AI 对话
> /model             # 模型选择菜单
> /buddy             # 抽取宠物
> /config            # 显示配置
> /help              # 显示帮助
> /exit              # 退出
```

---

## 技术栈

| 组件 | 库 |
|------|-----|
| CLI 框架 | prompt-toolkit |
| 终端渲染 | Rich |
| LLM SDK | anthropic |
| 测试 | pytest + pexpect |
| 格式化 | black |
| 包管理 | uv |

---

## 项目结构

```
src/
├── cli/           # CLI 入口和 REPL
├── agent/         # LLM Agent 和流式输出
├── buddy/         # Buddy Pet System
├── memory/        # Memory System (WIP)
└── settings.py    # 配置管理

docs/posts/        # 设计文档
tests/             # 测试
```

---

## 文档

| 文档 | 说明 |
|------|------|
| [CLI Design](docs/posts/cli-design.md) | 终端交互设计 |
| [Buddy Design](docs/posts/buddy-design.md) | 宠物系统设计 |
| [Memory Design](docs/posts/memory-design.md) | 记忆系统设计 |
| [TODO](docs/posts/TODO.md) | 开发路线图 |

---

## 配置

编辑 `~/.nano-claude/settings.json`:

```json
{
  "env": {
    "NANO_CLAUDE_API_KEY": "your-api-key",
    "NANO_CLAUDE_BASE_URL": "https://api.anthropic.com",
    "NANO_CLAUDE_DEFAULT_SONNET_MODEL": "claude-sonnet-4-6"
  }
}
```

---

## 开发

```bash
# 运行测试
uv run pytest tests/ -v

# 格式化代码
uv run black src/ tests/

# 类型检查
uv run mypy src/
```

---

## 原则

1. **极简** - 只保留核心功能
2. **Pythonic** - 纯 Python，无外部依赖
3. **学习驱动** - 理解 Claude Code 的设计

详见 [AGENTS.md](AGENTS.md)

---

## 关系

```
Claude Code (功能完整)
    │
    └── Nano Claude (精简核心)
```

---

MIT License. 与 Anthropic 无关联。