# Nano Claude 博客系列

> 减法学习法：理解 → 删除 → 理解更深

---

## 已完成

| 文章 | 状态 |
|------|------|
| [introduction.md](introduction.md) | ✅ 为什么要拆解 + 删除 29 个空目录 |

---

## TODO

| 主题 | 状态 | 切入点 |
|------|------|--------|
| CLI 入口 | ⬜ | `nano-claude --help` |
| 命令注册表 | ⬜ | `nano-claude commands` |
| 意图路由 | ⬜ | `nano-claude route "commit"` |
| 运行时启动 | ⬜ | `nano-claude bootstrap` |
| 查询引擎 | ⬜ | 内部数据流 |
| 权限系统 | ⬜ | 工具过滤 |
| 数据模型 | ⬜ | frozen dataclass |

---

## 写作模板

whyj-style：

```
0. 遇到的问题    — 场景引入
1. Why          — 为什么这样设计
2. How          — 代码实现
3. Justification — 为什么是这个方案
4. 如果是我      — 反思
5. 关键代码      — 文件:行号
```

详见 [TEMPLATE.md](TEMPLATE.md)