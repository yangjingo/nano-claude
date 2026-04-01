# Nano CC Python — 减法分支

> 理解即删除：每拆解一个模块，就精简一份代码

---

## 分支理念

```
原项目: 功能完整的 Claude Code 镜像
   ↓
Nano CC: 精简核心，理解本质
```

**目标**：通过深度理解代码来精简它，而不是添加功能。

---

## 基准数据（2026-04-01）

| 指标 | 起始值 | 当前值 |
|------|--------|--------|
| Python 文件 | 66 | **37** |
| 目录 | 32 | 3 |
| 总行数 | 2,138 | ~2,138 |
| 子系统占位目录 | 25 | **0** |

---

## 减法原则

详见 `AGENTS.md`

1. **只做减法** — 禁止新增代码
2. **全程使用 Claude Code** — Claude 理解后才能删除
3. **纯 Python 实现** — 删除 Rust 和 TypeScript 归档

---

## 减法记录

| 日期 | 操作 | 删除 | 剩余行数 |
|------|------|------|---------|
| 2026-04-01 | 初始状态 | - | 2,138 |
| 2026-04-01 | 删除 `rust/` 目录 | 74 文件, 21 目录 | 2,138 |
| 2026-04-01 | 删除 Rust 相关博客 | 3 目录 | 2,138 |
| 2026-04-01 | 删除 29 个空子系统目录 | 29 文件, 30 目录 | 2,138 |
| 2026-04-01 | 删除 subsystems JSON | 29 JSON 文件 | ~2,100 |

---

## 待办清单

### Phase 1: 删除占位符（理解结构）

| 目录 | 状态 | 理由 |
|------|------|------|
| `src/assistant/` | ⬜ 待删 | 空占位 |
| `src/bootstrap/` | ⬜ 待删 | 空占位 |
| `src/bridge/` | ⬜ 待删 | 空占位 |
| `src/buddy/` | ⬜ 待删 | 空占位 |
| ... (25个) | | |

### Phase 2: 精简命令（理解功能）

| 命令 | 状态 | 理由 |
|------|------|------|
| `remote-mode` 系列 (5个) | ⬜ 待删 | 远程功能非核心 |
| `show-command/show-tool` | ⬜ 待删 | 可合并到 `commands/tools` |
| `exec-command/exec-tool` | ⬜ 待删 | shim 非必要 |

### Phase 3: 合并模块（理解架构）

| 操作 | 状态 | 理由 |
|------|------|------|
| `tool_pool.py` → `tools.py` | ⬜ 待合并 | 功能重叠 |
| `execution_registry.py` → `commands.py` | ⬜ 待合并 | shim 可内联 |
| `transcript.py` → `session_store.py` | ⬜ 待合并 | 会话相关 |

### Phase 4: 精简数据

| 操作 | 状态 | 理由 |
|------|------|------|
| `reference_data/subsystems/*.json` (25个) | ⬜ 待删 | 占位元数据 |

---

## 目标结构

```
src/
├── main.py          # CLI 入口
├── runtime.py       # 运行时核心
├── router.py        # 意图路由
├── commands.py      # 命令注册
├── tools.py         # 工具注册
├── models.py        # 数据模型
├── session.py       # 会话管理
└── reference_data/
    ├── commands.json
    └── tools.json
```

---

## 相关文档

- `AGENTS.md` — 开发原则
- `docs/ARCHITECTURE.md` — 架构总览
- `docs/COMMANDS.md` — 命令手册
- `docs/posts/` — 博客文章