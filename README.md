# Nano Claude

> O(1) 减法学习：删除代码，理解本质

---

## 是什么

学习项目。从 Claude Code 源码学习，用极简 Python 重新实现。

```
理解 → 删除 → 理解更深
```

---

## 方法

从常用命令出发，不从代码结构出发：

```
命令做了什么？
    ↓
调用了哪些工具？
    ↓
数据怎么流转？
    ↓
核心代码在哪？
```

---

## 减法记录

| 操作 | 结果 |
|------|------|
| 起始 | 66 文件, 32 目录 |
| 删 Rust | -74 文件, -21 目录 |
| 删空目录 | -29 目录 |
| **当前** | **37 文件, 3 目录** |

---

## 运行

```bash
uv sync
uv run nano-claude summary
uv run nano-claude commands --limit 10
uv run nano-claude route "commit changes"
```

---

## 后续

| 主题 | 状态 |
|------|------|
| CLI 入口 | ⬜ |
| 命令注册 | ⬜ |
| 意图路由 | ⬜ |
| 运行时 | ⬜ |
| 权限 | ⬜ |

详见 [docs/posts/](docs/posts/)

---

## 原则

1. 只做减法
2. 全程使用 Claude Code
3. 纯 Python 实现

详见 [AGENTS.md](AGENTS.md)

---

## 关系

```
Claw Code (功能完整)
    │
    └── Nano Claude (精简核心)
```

---

MIT License. 与 Anthropic 无关联。