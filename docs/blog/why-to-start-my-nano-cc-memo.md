# 拆解是最好的学习：用 Claude Code 复刻 一个Nano Claude Code

> whyj-style — 我的 nano-claude 项目之路

---

## 0. 遇到的问题

2026 年初，Claude Code 已经成为我日常开发的核心工具。但越用越觉得——

**我只是在用，并不理解它。**

我知道 `/help` 能列出命令，知道它能调 Bash、读文件、写代码，但不知道：
- 消息发出去之后，Agent Loop 到底怎么转的？
- Tool Calling 的结果怎么喂回给模型？
- `/memory` 写进去的东西，下次会话怎么加载回来？
- 为什么有时候它自己会总结上下文？

以前，学习一个项目最好的办法是搭建环境跑一跑。现在，应该是**复刻一个 nano 跑一跑**。

所以我决定：用 Claude Code 本身，来复刻一个 Claude Code。

抱着做减法的原则和学习的目的，打造一个极简、代码优雅简洁的 nano project。

---

## 1. 为什么要复刻而不是阅读源码？

### 阅读代码的困境

Claude Code 是 TypeScript 写的，50 万+ 行。直接读代码的问题：

- 依赖链太深，一个 `QueryEngine` 牵出十几个模块
- 设计模式密集，不看上下文根本不知道为什么这样写
- 缺少依赖和文档，跑不起来，静态阅读缺乏"手感"

### 复刻的减法哲学

```
理解 → 删除 → 理解更深
```

复刻不是抄，是**做减法**：

- Claude Code 有 20+ 个工具 → nano-claude 先做 1 个（Bash）
- Claude Code 有复杂的权限系统 → nano-claude 先不做
- Claude Code 有 MCP 协议 → nano-claude 先不做

每一层删除都是一次理解：**删掉之后系统还能跑吗？跑不了说明什么？**

### 如何用 Claude Code 作为开发工具进行开发

> 现在这个时间点，没有什么比学习 Agent 的使用这件事情更重要。

用 Claude Code 来开发 nano-claude，本身就是最好的学习：
- 你在造工具的过程中理解工具的一些实现
- 让 Claude Code 帮你处理繁琐的实现细节，你专注理解架构
- 遇到设计决策时，直接问 Claude Code："你是怎么做的？"

---

## 2. 从零开始的Nano Claude的路径

### 第一步：找到一个 REPL

```
一切从一个能对话的循环开始。
```

不需要想架构，不需要画 UML。先让模型能说话：

```python
# 文件: src/agent/agent.py
# 行号: 1-10

from anthropic import AsyncAnthropic

client = AsyncAnthropic()
async with client.messages.stream(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": "Hello"}],
) as stream:
    async for text in stream.text_stream:
        print(text, end="", flush=True)
```

一个 REPL 能跑起来，你就有了起点。

### 第二步：从功能入口倒推

不要从架构顶层开始设计。从一个你**每天在用的功能，或者最有趣的功能开始**开始：

| 入口 | 对应模块 | 学到什么 |
|------|---------|---------|
| `/buddy` | Buddy 宠物系统 | 随机数生成、数据模型、Rich 渲染 |
| `/tools` | 工具注册表 | ToolDef/ToolResult、注册/查找/执行 |
| `/dream` | 血月巩固引擎 | 关键词匹配、信号提取、记忆整合 |
| `/memory` | 记忆系统 | 文件 I/O、索引管理、YAML frontmatter |

**以用户视角来开发**：你觉得最好用的功能是什么？从那里开始。

### 第三步：文档驱动开发

不是先写代码再补文档。是**先写文档，再让 Claude Code 写代码**。

文档的组织：

```
docs/
├── ARCHITECTURE.md       # 架构总览 — 代码结构一目了然
├── posts/
│   ├── cli-design.md     # CLI 入口设计
│   ├── tool-design.md    # 工具系统设计
│   ├── memory-design.md  # 记忆系统设计
│   ├── session-design.md # 会话持久化设计
│   └── TODO.md           # 路线图 — 驱动开发方向
└── CLAUDE.md             # 给 Claude Code 的项目指引
```

文档的完成方式：

- **借助逆向工具**：deepwiki、zread、openedclaude 等，先理解原版设计
- **头脑风暴插件**：brainstorm、superpowers 等，帮助发散思路
- **git 管理一切**：是最好的方式，没有之一

### 让OpenClaw 帮你测试

> 最好的测试方式，是让 另外一个 Agent (OpenClaw) 来带你测试。

- 使用 Agent 来测试，推荐用 OpenClaw，尽量隔离开来
- 让另一个 Agent 实例扮演用户，按照你的文档操作
- 它会告诉你哪里不好用、哪里文档和代码对不上

---

## 3. Nano Claude 为什么是这个方案 ？ 

### 为什么选 Python 而不是 TypeScript

| 方案 | 优点 | 缺点 | 选择理由 |
|------|------|------|---------|
| TypeScript (原版复刻) | 1:1 对照 | 依赖链太重，学习成本高 | |
| Python (减法复刻) | 语法简洁、生态轻量、`anthropic` SDK 成熟 | 与原版语言不同 | ✓ 做减法，不追求 1:1 |
| Go / Rust | 性能好 | SDK 生态不如 Python | |

**选择 Python 的核心理由**：目标是理解，不是搬运， Python是我最熟悉的开发工具。

### 为什么不用 Claude Code 直接生成整个项目？

| 方案 | 优点 | 缺点 | 选择理由 |
|------|------|------|---------|
| 一句话生成整个项目 | 快 | 不理解、无法维护、没有学习价值 | |
| 逐步复刻 + 理解每一步 | 慢 | 耗时 | ✓ 目标是学习 |
| 文档先行 + Agent 辅助实现 | 平衡速度和理解 | 需要写文档 | ✓ 当前选择 |


### 为什么优先文档驱动而不是测试驱动？

- TDD 需要你先理解"正确行为"是什么
- 但你正在学习这个项目，还不知道"正确行为"
- 文档驱动：先把理解写下来，再验证理解对不对

---

## 4. 如果是我，我下一次如何改进？

### 如果重新开始，刷新几个认知

1. **先写 CLAUDE.md** — 这是给 Agent 的地图，也是给自己的大纲
2. **从一个 REPL 开始** — 不要想太多，先让模型说话
3. **每完成一个模块，写一篇 whyj-style 博客** — 强迫自己理解
4. **用另一个 Agent 来测试** — 发现盲点最快的方式
5. **不要追求完整** — 做减法，删到不能再删
6.  **"现在不需要阅读代码，而是直接阅读文档，然后交给 CC"** — 逆向工具抽取文档 + Claude Code 是这个时代最高效的学习方式
7.  **"觉得好玩、觉得有趣就可以开始"** — 不需要完美计划，不需要完整架构， 动起来比设计完成更重要
8.   **"git 管理一切"** — 每一次提交都是一次理解的记录，回顾每一次重大的改变

---

## 5. Nano Claude 关键代码费分享


### 相关界面

抽象的buddy


能用的tool

糟糕的血月

### 相关源码

项目地址：https://github.com/yangjingo/nano-claude
文档地址: https://github.com/yangjingo/nano-claude/tree/main/docs
项目分享：https://github.com/yangjingo/nano-claude/tree/main/docs/blog


| 文件 | 行号 | 功能 |
|------|------|------|
| `src/agent/agent.py` | 1-10 | AsyncAnthropic 流式对话 — 一切的起点 |
| `src/cli/repl.py` | — | REPL 循环 — 用户交互的入口 |
| `src/tools/bash.py` | — | 第一个工具 — 跨平台 Shell |
| `src/memory/dreamer.py` | — | 血月巩固 — 信号提取 + 记忆整合 |
| `docs/CLAUDE.md` | — | 项目指引 — Agent 的地图 |
| `docs/posts/TODO.md` | — | 路线图 — 开发方向 |

---

## 6. 延伸阅读


### 书籍推荐 

- 《重构 改善既有代码的设计第二版》- Martin Fowler - https://book-refactoring2.ifmicro.com/
- The Way of Code - Rick Rubin - https://www.thewayofcode.com

### 项目相关

- Claude Code 逆向文档（Claude 分析源码） - https://openedclaude.github.io/claude-reviews-claude
- Claude Code 逆向文档（Zread 分析源码） - http://leow3lab.service.huawei.com:9681/
- Claude Code （源码之中的 Prompt ） - https://github.com/Piebald-AI/claude-code-system-prompts
- Nano Claude Toy -https://github.com/yangjingo/nanoclaude/tree/main/docs