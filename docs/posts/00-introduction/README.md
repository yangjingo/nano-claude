# 为什么要拆解 Claude Code

> Nano Claude 系列开篇

---

## 0. 遇到的问题

Claude Code 很强大，但也很复杂。

官方数据：
- 1,900+ TypeScript 文件
- 207 个命令
- 184 个工具

作为一个开发者，我想理解它是怎么工作的。

但面对这么多代码，从哪里开始？

---

## 1. Why：为什么要拆解

### 好奇心

我每天都在用 Claude Code：
- `git commit` 自动生成提交信息
- `review this PR` 代码审查
- `fix this bug` 自动修复

它是怎么做到的？

### 学习目的

Claude Code 是一个优秀的 CLI Agent 设计案例：

- 如何解析用户意图？
- 如何选择正确的工具？
- 如何管理会话状态？
- 如何处理权限控制？

这些都是可复用的设计知识。

### 减法哲学

我不想重建一个 Claude Code。

我想找到它的**核心**——然后用最少的代码重新实现。

```
理解 → 删减 → 重构 → 极简实现
```

---

## 2. How：我的方法

### 从用户视角出发

不是从代码结构出发，而是从**我常用的命令**出发：

```
我常用什么命令？
    ↓
这个命令做了什么？
    ↓
调用了哪些工具？
    ↓
数据怎么流转？
    ↓
核心代码在哪？
```

### 减法学习法

1. **看懂一个模块** — 先理解它在做什么
2. **自己重新实现** — 用极简的方式
3. **对比找差距** — 原版为什么这样设计？
4. **删除冗余** — 保留核心，抛弃非必要

### 输出过程

每拆解一个模块，写一篇文章：
- 我看到了什么
- 我理解了什么
- 我删除了什么
- 我学到了什么

---

## 3. 这个项目是什么

**Nano Claude** 是一个学习项目。

核心目的：
1. **做减法** — 只保留最核心的功能
2. **极简实现** — 用最少的代码实现
3. **输出过程** — 记录每次重构的思考
4. **学习意义** — 理解 Claude 的工程设计

这不是商业项目，不是 Claude Code 的替代品。

这是一个**学习笔记**，记录我如何一步步理解一个复杂的 CLI Agent 系统。

---

## 4. 如果是我，我会怎么做

假设让我设计一个 CLI Agent，我会：

### 4.1 命令系统

```python
# 用户输入 → 匹配命令 → 执行
commands = {
    "commit": handle_commit,
    "review": handle_review,
}
```

Claude Code 的方案更复杂：
- 从 JSON 快照加载命令元数据
- 用 Token 匹配算法计算相似度
- 支持 plugin/skill 扩展

### 4.2 工具系统

```python
# 简单版本
tools = [Read, Write, Bash, ...]
result = tool.execute(params)
```

Claude Code 的方案：
- 工具权限系统（deny_names, deny_prefixes）
- MCP 协议支持
- 工具结果折叠和格式化

### 4.3 会话管理

```python
# 简单版本
messages = []
messages.append(user_message)
response = llm.chat(messages)
```

Claude Code 的方案：
- 会话持久化
- Turn Loop 多轮控制
- Token 预算管理

---

## 5. 这一系列文章会讲什么

| # | 主题 | 从什么命令切入 |
|---|------|---------------|
| 01 | CLI 入口 | `nano-claude --help` |
| 02 | 命令注册表 | `nano-claude commands` |
| 03 | 意图路由 | `nano-claude route "commit"` |
| 04 | 运行时启动 | `nano-claude bootstrap` |
| 05 | 查询引擎 | 内部数据流 |
| 06 | 权限系统 | 工具过滤 |
| 07 | 数据模型 | frozen dataclass |
| 08 | 会话管理 | `load-session` |
| 09 | JSON 快照 | 元数据驱动 |
| 10 | 删除空目录 | 减法实践 |

每篇文章都遵循 **whyj-style**：
- 为什么这样设计
- 代码怎么实现
- 对比其他方案
- 我的反思

---

## 6. 延伸阅读

- [Claude Code 官方文档](https://docs.anthropic.com/claude-code)
- [Yufeng He 的源码分析](https://zhuanlan.zhihu.com/p/2022389695955346888)
- [Nano Claude 仓库](https://github.com/yangjingo/nano-claude)

---

*下一篇: [Python CLI 入口的五个细节](../01-entrypoint/)*