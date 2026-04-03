# Nano Claude

<p align="center">
<strong>拆解 Claude Code，用 Python 从零构建 LLM Harness</strong>
</p>

<p align="center">
Claude Code 不只是个 CLI — 它是 LLM 与真实世界之间的桥梁。<br>
本项目把它拆开，一层一层用 Python 重新实现。
</p>

---

## Harness 四层

调用 LLM API 只需三行代码。但让 LLM **真正有用**，需要四层运行环境：

```
┌─────────────────────────────────────────┐
│  Memory     跨会话记忆，越用越懂你       │
├─────────────────────────────────────────┤
│  Tool       读写文件、执行命令、搜索代码  │
├─────────────────────────────────────────┤
│  Agent Loop 思考 → 行动 → 观察 → 再思考  │
├─────────────────────────────────────────┤
│  Context    你是谁、你在哪、你能做什么    │
├─────────────────────────────────────────┤
│              LLM API                    │
└─────────────────────────────────────────┘
```

参考 Claude Code 源码，逐层拆解，用纯 Python 实现。每一步记录设计决策和工程实践。

---

## 架构

```
src/
├── agent/           # Agent Loop — 流式会话、thinking、tool-use 迭代
├── registry/        # Tool & Command — 注册、权限过滤、执行
├── memory/          # Memory — 本地持久化、索引、会话注入
├── cli/             # REPL — 终端交互
└── system_init.py   # Context — system prompt 构建
```

---

## 快速开始

```bash
uv sync && uv run nano-claude
```

配置 `~/.nano-claude/settings.json`：

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

## 设计文档

- [CLI Design](docs/posts/cli-design.md) — 终端交互如何设计
- [Buddy Design](docs/posts/buddy-design.md) — 宠物系统的诞生
- [Memory Design](docs/posts/memory-design.md) — 让 AI 拥有记忆
- [TODO](docs/posts/TODO.md) — 接下来做什么

---

本项目仅用于学习目的，参考 Claude Code 的设计思路，借助 Claude Code 来实现。
