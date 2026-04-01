# 当 Python 模仿遇到 Rust 实战：TUI 的两种实现

> whyj-style 源码分析 — Part 6: Rust 实战

---

## 0. 遇到的问题

同一个 CLI 工具，Python 版和 Rust 版的终端界面差距有多大？

- Python 版：纯命令行，无 TUI，输出 Markdown 文本
- Rust 版：完整终端界面，代码高亮，流式输出，进度条

这是「架构探索」与「生产实现」的差距。

---

## 1. Why：为什么 Rust 版更完整

### 设计定位差异

| 版本 | 目标 | 依赖 |
|------|------|------|
| Python | 理解架构，镜像结构 | 零第三方 |
| Rust | 生产可用，真实 API | crossterm, syntect, rustyline |

### 技术选型

| 库 | 版本 | 用途 |
|----|------|------|
| `crossterm` | 0.28 | 终端控制（光标、颜色、清屏）|
| `rustyline` | 15 | 行编辑 + Tab 补全 |
| `pulldown-cmark` | 0.13 | Markdown 解析 |
| `syntect` | 5 | 语法高亮 |
| `ratatui` | 计划中 | 全屏 TUI 框架 |

---

## 2. How：Rust TUI 实现拆解

### 文件结构

```
rust/crates/rusty-claude-cli/src/
├── main.rs     # 3,159 行 - REPL 核心（需拆分）
├── render.rs   # 641 行 - Markdown→终端渲染
├── input.rs    # 269 行 - 行编辑器
├── init.rs     # 433 行 - 仓库初始化
├── app.rs      # 398 行 - CLI 应用结构
└── args.rs     # 108 行 - 参数定义
```

### 核心组件

#### 2.1 输入层（input.rs）

```rust
// rustyline 行编辑器
// 支持：
// - Tab 补全（斜杠命令）
// - Shift+Enter 换行
// - 历史记录
```

#### 2.2 渲染层（render.rs）

```rust
// Markdown→终端渲染
// 支持：
// - 标题（H1-H6）
// - 列表（有序/无序）
// - 表格
// - 代码块（syntect 高亮）
// - 引用块
// - Spinner 动画
```

#### 2.3 REPL 循环（main.rs）

```rust
// LiveCli 结构体（3,159 行，需拆分）
// - 流式输出处理
// - 工具调用展示（╭─ tool ─╮）
// - 权限提示（Y/N）
// - 会话管理
```

---

## 3. TUI Enhancement 六阶段计划

### Phase 0: 结构清理（必要）

拆分 3,159 行的 main.rs：

```
main.rs (100行入口)
├── app.rs      # LiveCli + REPL 循环
├── format.rs   # 报告格式化
├── session_mgr.rs # 会话 CRUD
└── tui/
    ├── status_bar.rs
    ├── tool_panel.rs
    ├── diff_view.rs
    └── theme.rs
```

### Phase 1: 状态栏 & HUD

- 底部固定状态栏
- 显示：模型名、权限模式、Token 计数、预估成本
- 实时更新（随流式输出）

### Phase 2: 流式输出增强

- 增量 Markdown 渲染
- "思考中" 指示器 🧠
- 进度条（基于 max_tokens）

### Phase 3: 工具可视化

- 可折叠工具输出（>N 行折叠）
- 语法高亮工具结果
- Diff 高亮（edit_file）
- 工具调用时间线

### Phase 4: 斜杠命令增强

- `/diff` 彩色输出
- 长输出分页器
- `/search` / `/undo`
- 交互式会话选择器

### Phase 5: 主题系统

- 预设主题：dark, light, solarized, catppuccin
- ANSI-256/真彩色检测
- 可配置 Spinner

### Phase 6: 全屏 TUI（Stretch）

- `ratatui` 集成
- 分屏布局
- 鼠标支持

---

## 4. Python vs Rust 对比

| 特性 | Python 版 | Rust 版 |
|------|----------|---------|
| **API 调用** | 模拟输出 | 真实 Anthropic API |
| **流式输出** | 假延迟 8ms | 真实 SSE |
| **工具执行** | shim 返回消息 | 真实执行（Bash、文件）|
| **OAuth** | 无 | `login` 命令 |
| **TUI** | 无 | 完整终端界面 |
| **代码高亮** | 无 | syntect 语法高亮 |
| **会话恢复** | load_session | `--resume` |
| **自更新** | 无 | `self-update` |

### 架构关系图

```
┌─────────────────────────────────────────┐
│       原 Claude Code (TypeScript)        │
│              (闭源/已泄露)               │
└──────────────────┬──────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌─────────────────┐
│   Python 版     │  │    Rust 版      │
│   (架构探索)    │  │   (生产实现)    │
├─────────────────┤  ├─────────────────┤
│ • 元数据镜像    │  │ • 真实 API      │
│ • 模拟运行时    │  │ • 完整 TUI      │
│ • 零依赖        │  │ • 18 真实工具   │
│ • 学习样本      │  │ • 生产可用      │
└─────────────────┘  └─────────────────┘
```

---

## 5. 关键代码引用

| 文件 | 行数 | 功能 |
|------|------|------|
| `rust/.../main.rs` | 3,159 | REPL 核心，待拆分 |
| `rust/.../render.rs` | 641 | Markdown→终端 |
| `rust/.../input.rs` | 269 | rustyline 编辑器 |
| `rust/TUI-ENHANCEMENT-PLAN.md` | 222 | 六阶段计划 |

---

## 6. 延伸阅读

- `rust/README.md` - Rust 版完整文档
- `rust/TUI-ENHANCEMENT-PLAN.md` - TUI 增强详细计划
- `../ARCHITECTURE.md` - Python 版架构总览

---

## Buddy 子系统

Buddy 是 Claude Code 的「AI 伴侣」UI 子系统：

### 原始 TS 文件

| 文件 | 用途 |
|------|------|
| `CompanionSprite.tsx` | React 角色组件 |
| `companion.ts` | 核心逻辑 |
| `sprites.ts` | 精灵图资源 |
| `useBuddyNotification.tsx` | 通知钩子 |

### 功能推测

- 终端中显示动画化 AI 角色
- 用表情/动画反馈状态（思考中🤔、执行中⚡、空闲😊）
- 增加人机交互的情感化元素

---

*下一篇: 《render.rs 641 行艺术》*