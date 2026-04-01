# Nano Claude

> O(1) 减法学习：删除代码，理解本质

---

## 问题

Claude Code 有 1,900+ TypeScript 文件。207 个命令。184 个工具。

没人能一次性理解。

---

## 方法

**减法学习法**：

```
理解 → 删除 → 理解更深
```

不是从代码结构出发，从**常用命令**出发：

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

## 项目定位

学习项目。不是 Claude Code 替代品。

核心目的：
1. 做减法
2. 极简实现
3. 输出过程
4. 理解工程设计

---

## 实践：删除 29 个空目录

### 发现

`src/` 有 29 个子目录，每个只有 `__init__.py`。

占位符。原始 TS 有这些子系统，Python 移植保留了结构，没实现内容。

### 验证

```bash
grep -r "from .assistant" src/  # 无依赖
uv run nano-claude summary      # 运行正常
```

### 删除

```bash
rm -rf src/assistant src/bootstrap src/bridge src/buddy ...
```

### 结果

- 文件：66 → 37
- 目录：32 → 3

### 收获

删除的前提是理解。知道是什么、知道没被用、知道删了不坏。

---

## 设计反思

如果让我设计 CLI Agent：

| 模块 | 简单版 | Claude Code |
|------|--------|-------------|
| 命令 | dict 映射 | JSON 快照 + Token 匹配 |
| 工具 | 数组 + execute | 权限 + MCP + 折叠 |
| 会话 | messages 数组 | 持久化 + Turn Loop |

Claude Code 每个模块都更复杂。为什么？值得吗？

---

## 后续

| 主题 | 切入点 |
|------|--------|
| CLI 入口 | `--help` |
| 命令注册 | `commands` |
| 意图路由 | `route` |
| 运行时 | `bootstrap` |
| 查询引擎 | 内部流 |
| 权限 | 工具过滤 |
| 数据模型 | frozen |

---

## 参考

- [Claude Code 文档](https://docs.anthropic.com/claude-code)
- [Yufeng He 分析](https://zhuanlan.zhihu.com/p/2022389695955346888)
- [GitHub](https://github.com/yangjingo/nano-claude)