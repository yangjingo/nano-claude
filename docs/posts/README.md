# Nano Claude 源码分析博客系列

> 减法理解法：理解 → 删除 → 理解更深

---

## 系列定位

**核心理念**：通过删除代码来理解代码。

每篇文章对应一次减法操作，记录"为什么可以删"。

---

## 博客进度

| # | 文章 | 状态 | 对应减法 |
|---|------|------|---------|
| 00 | 为什么要拆解 Claude Code | ✅ 完成 | 系列开篇 |
| 00.5 | Python 项目配置与 PyPI 发布 | ✅ 完成 | 打包发布流程 |
| 01 | Python CLI 入口的五个细节 | ⬜ 待写 | main.py 分析 |
| 02 | 元组即注册表 | ⬜ 待写 | commands.py |
| 03 | route_prompt 算法拆解 | ⬜ 待写 | runtime.py |
| 04 | PortRuntime 会话启动 | ⬜ 待写 | runtime.py |
| 05 | QueryEnginePort 聚合层 | ⬜ 待写 | query_engine.py |
| 06 | Turn Loop 状态机 | ⬜ 待写 | runtime.py |
| 07 | ToolPermissionContext | ⬜ 待写 | permissions.py |
| 08 | frozen=True 的力量 | ⬜ 待写 | models.py |
| 09 | JSON 快照镜像哲学 | ⬜ 待写 | reference_data/ |
| 10 | 删除 29 个空目录 | ⬜ 待写 | subsystems 删除 |
| 11 | 拆解后的收获 | ⬜ 待写 | 系列收尾 |

---

## 写作模板 (whyj-style)

```markdown
# [标题]

## 0. 遇到的问题
（场景引入）

## 1. Why：为什么这样设计
（设计动机）

## 2. How：代码实现
（关键代码 + 流程图）

## 3. Justification：为什么是这个方案
（对比其他可能）

## 4. 如果是我
（反思环节）

## 5. 关键代码引用
（文件:行号）

## 6. 延伸阅读
```

---

## 写作优先级

**本周**:
- 00 → 01 → 02

**下周**:
- 03 → 04 → 10（已有素材）

---

## 相关文档

- [../README.md](../README.md) - 项目总览
- [../AGENTS.md](../AGENTS.md) - 减法原则
- [../NANO.md](../NANO.md) - 减法记录
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - 架构文档
- [../COMMANDS.md](../COMMANDS.md) - 命令手册