# Claw Code 源码分析博客系列

> whyj-style: 从问题出发，追溯设计决策，结合代码实现

---

## 系列定位

**目标读者**: 对 CLI 工具设计、Agent 系统架构感兴趣的开发者

**核心视角**:
- Python 版作为「架构学习样本」—— 理解设计思想
- Rust 版作为「生产实现参考」—— 看完整落地

**写作风格** (whyj-style):
- **Why**: 为什么要这样设计？解决什么问题？
- **How**: 代码层面的实现思路
- **Justification**: 为什么是这个方案？对比其他可能性
- **反思环节**: 「如果是我，我会怎么做」

---

## 文章清单

> 状态: `⬜ 待写` | `🟡 进行中` | `✅ 完成`

### Part 1: 入门与入口

| # | 文章 | 状态 | 核心素材 |
|---|------|------|---------|
| 00 | 《为什么我要拆解一个 CLI 工具》 | ⬜ | README.md 背景 |
| 01 | 《Python CLI 入口的五个细节》 | ⬜ | main.py, __init__.py |

### Part 2: 注册与发现

| # | 文章 | 状态 | 核心素材 |
|---|------|------|---------|
| 02 | 《元组即注册表》 | ⬜ | commands.py, tools.py |
| 03 | 《route_prompt 算法拆解》 | ⬜ | runtime.py:90-192 |

### Part 3: 运行时核心

| # | 文章 | 状态 | 核心素材 |
|---|------|------|---------|
| 04 | 《PortRuntime 会话启动》 | ⬜ | runtime.py:109-152 |
| 05 | 《QueryEnginePort 聚合层》 | ⬜ | query_engine.py |
| 06 | 《Turn Loop 状态机》 | ⬜ | runtime.py:154-167 |

### Part 4: 权限与模型

| # | 文章 | 状态 | 核心素材 |
|---|------|------|---------|
| 07 | 《ToolPermissionContext》 | ⬜ | permissions.py |
| 08 | 《frozen=True 的力量》 | ⬜ | models.py |

### Part 5: 数据驱动

| # | 文章 | 状态 | 核心素材 |
|---|------|------|---------|
| 09 | 《JSON 快照镜像哲学》 | ⬜ | reference_data/*.json |
| 10 | 《25 个空目录的野心》 | ⬜ | src/*/ 占位目录 |

### Part 6: Rust 实战

| # | 文章 | 状态 | 核心素材 |
|---|------|------|---------|
| 11 | 《TUI 的两种实现》 | ⬜ | rust/TUI-ENHANCEMENT-PLAN.md |
| 12 | 《render.rs 641 行艺术》 | ⬜ | rust/.../render.rs |

### Part 7: 收尾

| # | 文章 | 状态 | 核心素材 |
|---|------|------|---------|
| 13 | 《拆解后的收获》 | ⬜ | 全系列总结 |

---

## 目录结构

```
posts/
├── README.md           # 本文件（系列导航）
├── TEMPLATE.md         # 文章模板
│
├── 00-introduction/    # 开篇
├── 01-entrypoint/      # 入口篇
├── 02-registry/        # 注册表层
├── 03-routing/         # 意图路由
├── 04-runtime/         # 运行时核心
├── 05-query-engine/    # 查询引擎
├── 06-permissions/     # 权限系统
├── 07-data-models/     # 数据模型
├── 08-subsystems/      # 子系统分析
├── 09-json-snapshot/   # 数据驱动
├── 10-rust-tui/        # Rust TUI 分析
├── 11-rust-runtime/    # Rust 运行时
├── 12-comparison/      # Python vs Rust
├── 13-retrospect/      # 收尾
│
└── assets/             # 配图素材
    ├── diagrams/
    ├── snippets/
    └── comparisons/
```

---

## 写作优先级

**本周**: 00 → 01 → 02
**下周**: 03 → 04 → 11（Rust 素材已完整）

---

## 文章模板

每篇文章遵循 whyj-style 结构：

```
0. 遇到的问题    → 场景引入
1. Why          → 设计动机
2. How          → 代码拆解 + 流程图
3. Justification → 方案对比论证
4. 如果是我      → 反思环节
5. 关键代码引用   → 文件 + 行号
6. 延伸阅读      → 相关链接
```

详见 `TEMPLATE.md`

---

## 相关文档

- `../ARCHITECTURE.md` - Python 版架构总览
- `../COMMANDS.md` - 23 个命令参考手册
- `../../rust/README.md` - Rust 版完整文档
- `../../rust/TUI-ENHANCEMENT-PLAN.md` - TUI 增强计划