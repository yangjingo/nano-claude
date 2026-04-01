# Nano Claude

> 瘦身 Claude Code，一层层剥开

---

## 这个项目是什么

**Nano Claude** 是一个减法实验。

我们从一个功能完整的 Claude Code 镜像开始，通过不断删除代码来理解它。

```
理解 → 删除 → 理解更深 → 删除更多
```

这不是要重建 Claude Code，而是要**剥开它**，找到核心。

---

## 为什么要这样做

### 问题

Claude Code 有 1,900+ TypeScript 文件，207 个命令，184 个工具。

没有人能一次性理解这么多代码。

### 方法

**减法理解法**：

1. 删除不理解的代码
2. 观察什么坏了
3. 理解为什么坏了
4. 决定是否保留

### 目标

找到一个**最小可运行的核**—— 然后真正理解它。

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