# Nano Claude

> 极简 Python 实现，学习 Claude Code 的工程设计哲学

---

## 这个项目是什么

**Nano Claude** 是一个**学习项目**。

我们从学习 Claude Code 源码开始，然后用极简的 Python 重新实现。

```
学习源码 → 理解设计 → 自己实现 → 输出过程
```

这不是要重建 Claude Code，而是要**学习它的设计哲学**。

---

## 核心目的

1. **做减法** — 只保留最核心的功能
2. **极简实现** — 用最少的代码实现
3. **输出过程** — 记录每次重构的思考
4. **学习意义** — 理解 Claude 的工程设计

---

## 方法

### 从用户视角出发

从最常见的命令入手，逐步深入：

```
用户常用命令
    ↓
这个命令做了什么？
    ↓
用了哪些工具？
    ↓
数据怎么流转？
    ↓
核心代码在哪？
```

### 减法学习法

1. 看懂一个模块
2. 自己重新实现（极简版）
3. 对比原版找差距
4. 删除冗余，保留核心

---

## 减法记录

| 日期 | 操作 | 结果 |
|------|------|------|
| 起始 | 完整镜像 | 66 Python 文件, 32 目录 |
| Day 1 | 删除 Rust 实现 | -74 文件, -21 目录 |
| Day 1 | 删除空子系统 | -29 目录 |
| **当前** | | **37 文件, 3 目录** |

---

## 当前状态

```
src/
├── main.py          # CLI 入口
├── runtime.py       # 运行时核心
├── commands.py      # 命令注册
├── tools.py         # 工具注册
├── models.py        # 数据模型
├── query_engine.py  # 查询引擎
└── ...              # 其他核心模块
```

**已删除**：
- ✅ Rust 实现 (74 文件)
- ✅ 29 个空子系统目录
- ✅ TypeScript 归档引用

**待删除**：
- ⏳ 5 个 remote-mode 命令
- ⏳ 2 个 exec-* shim 命令
- ⏳ 更多冗余模块

---

## 快速开始

```bash
# 安装
uv sync

# 运行
uv run nano-claude summary

# 命令列表
uv run nano-claude commands --limit 10

# 工具列表
uv run nano-claude tools --limit 10

# 意图路由
uv run nano-claude route "commit changes"
```

---

## 博客进度

我们在写一系列博客，记录每次减法的思考过程。

| # | 文章 | 状态 |
|---|------|------|
| 00 | 为什么要拆解一个 CLI 工具 | ⬜ |
| 01 | Python CLI 入口的五个细节 | ⬜ |
| 02 | 元组即注册表 | ⬜ |
| 03 | route_prompt 算法拆解 | ⬜ |
| 04 | PortRuntime 会话启动 | ⬜ |
| 05 | QueryEnginePort 聚合层 | ⬜ |
| 06 | Turn Loop 状态机 | ⬜ |
| 07 | ToolPermissionContext | ⬜ |
| 08 | frozen=True 的力量 | ⬜ |
| 09 | JSON 快照镜像哲学 | ⬜ |
| 10 | 删除 29 个空目录 | ⬜ |
| 11 | 拆解后的收获 | ⬜ |

详见 [docs/posts/](docs/posts/)

---

## 减法原则

详见 [AGENTS.md](AGENTS.md)

1. **只做减法** — 禁止新增代码
2. **全程使用 Claude Code** — Claude 理解后才能删除
3. **纯 Python 实现** — 删除 Rust 和 TypeScript 归档

---

## 与 Claw Code 的关系

**Claw Code** 是原始的 Python 移植项目，功能完整。

**Nano Claude** 是 Claw Code 的减法分支，追求极简理解。

```
Claw Code (功能完整)
    │
    └── Nano Claude (精简核心)
          │
          └── 每次删除都是一次理解
```

---

## License

MIT

---

## 免责声明

- 本项目不拥有 Claude Code 的原始源码
- 本项目与 Anthropic 无关联
- 这是一个独立的学习/研究项目