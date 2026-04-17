# Skill System Design

> Agent 技能系统 — Skill Creator, Evolve, Share, Evaluation

---

## 问题

Agent 的能力边界由它拥有的工具和技能决定。传统方式：

- 技能由开发者手动编写，发布后静态不变
- 用户积累的使用经验无法反馈到 Agent
- 跨 Agent 的技能无法复用（Claude Code 的 Skill 不能在 Cursor 用）
- 技能写了但不确定有没有用、触发准不准、质量稳不稳

核心矛盾：**Agent 用得越多，积累的经验越多，但能力不会增长**。

---

## 架构总览

技能系统围绕四个核心模块构建，覆盖技能的完整生命周期：

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Skill Creator ──→ Skill Evaluation ──→ Skill Share              │
│  （创建）           （评估）              （分享）                 │
│       ▲                  │                    │                  │
│       │                  ▼                    │                  │
│       └──── Skill Evolve ◄────────────────────┘                  │
│              （进化）                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

- **Skill Creator** — 从任务执行中自动提炼可复用技能
- **Skill Evaluation** — 评估技能的触发准确性和输出质量
- **Skill Evolve** — 基于反馈持续改进技能
- **Skill Share** — 跨 Agent 工具的技能可移植性

---

## Skill Creator（技能创建）

### Hermes Agent 的学习闭环

[Hermes Agent](https://hermes-agent.nousresearch.com) 是目前最成熟的自动技能创建实现。它独特的学习闭环设计：完成复杂任务后，会自动从中提炼出可复用的 Skills，保存为独立文档；在后续的使用中，这些 Skills 会被按需加载，并根据新的使用反馈不断自我改进。

> Hermes Agent 是一款强调持续学习与自我进化的开源 AI 智能体。
> — [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)

#### 触发条件

任务完成后，自动评估是否值得生成 Skill（满足任一即可）：

| 条件 | 含义 | 为什么值得记录 |
|------|------|---------------|
| **工具调用 > 5 次** | 走了非平凡路径 | 多步操作链本身就是一种"流程知识" |
| **中途出错后自行修复** | 失败 → 调试 → 成功 | 陷阱 + 解法，比纯成功路径更有价值 |
| **用户做过纠正** | Agent 原方案被否决 | 用户偏好信号，防止同类错误重犯 |
| **走了不明显但有效的路径** | 非直觉解法 | 创造性解法，手动编写 unlikely |

#### Skill 文件格式

```
~/.hermes/skills/
├── debug-race-condition.md
├── migrate-auth-middleware.md
└── setup-playwright-e2e.md
```

每个 Skill 文件遵循 [agentskills.io](https://agentskills.io) 开放标准：

```markdown
---
name: migrate-auth-middleware
description: >
  将 Session 认证迁移到 JWT 中间件。Use this skill when the user
  needs to migrate auth systems, replace session cookies with tokens,
  or set up JWT middleware — even if they don't explicitly mention "JWT."
tools: [Read, Edit, Bash, Grep]
triggers: [auth, middleware, migration, jwt, token, session]
created: 2026-04-10
updated: 2026-04-13
---

## Steps

1. 用 Grep 扫描现有 session 中间件的引用点
2. Read 当前中间件实现，理解依赖链
3. 创建 JWT 中间件骨架 (Write)
4. 逐文件替换 import 和调用 (Edit)
5. 运行测试验证 (Bash)

## Notes

- 注意 cookie-parser 的初始化顺序
- /health 端点不需要认证，保留白名单
```

### Anthropic Skill Creator 工具

Anthropic 提供了官方的 [Skill Creator](https://claude.com/plugins/skill-creator) 工具（`claude.com/plugins/skill-creator`），自动化技能创建的测试循环：

- 内置 eval loop 测试触发短语
- 遵循 agentskills.io 开放标准
- 自动检查 SKILL.md 格式合规性

参考：[The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)

### MiniMax M2.7 的模型自我进化

[MiniMax M2.7](https://www.minimaxi.com/news/minimax-m27-zh) 将技能自学习推到了更深层次 — 不只是 Agent 积累 Skill，而是模型优化自己的 Agent Harness。

M2.7 能自主执行超过 100 轮迭代循环：

```
分析失败轨迹 → 规划改动 → 修改脚手架代码 → 运行评测 → 对比结果 → 保留或回退
```

三模块架构：

```
┌─────────────────────────────────────────────────────┐
│  自优化 (Self-Optimization)                          │
│  基于所有历史轮次的记忆及自反馈链进行优化              │
├─────────────────────────────────────────────────────┤
│  自反馈 (Self-Feedback)                              │
│  对当前轮次结果自我评估，提供优化方向                  │
├─────────────────────────────────────────────────────┤
│  短时记忆 (Short-term Memory)                        │
│  每轮迭代后形成记忆文件，供后续轮次参考               │
└─────────────────────────────────────────────────────┘
```

| 指标 | 数值 |
|------|------|
| MLE Bench Lite 得牌率 | 66.6%（9 金 5 银 1 铜） |
| 40 个复杂 Skills 遵循率 | 97%（Skill > 2000 Token） |
| 自进化后内部评测提升 | 30% |

---

## Skill Evaluation（技能评估）

> 参考：[agentskills.io — Evaluating Skills](https://agentskills.io/skill-creation/evaluating-skills)

技能写了不代表有用。评估回答两个核心问题：

1. **触发准确性** — 该触发时触发，不该触发时不触发？
2. **输出质量** — 有 Skill 比没有 Skill，输出真的好？

### 评估一：触发准确性（Description Eval）

> 参考：[agentskills.io — Optimizing Descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)

`description` 字段是 Agent 决定是否加载技能的唯一依据。描述写不好，技能永远不会被激活。

#### 设计触发测试集

```json
// eval_queries.json — 约 20 条
[
  {
    "query": "I've got a spreadsheet in ~/data/q4_results.xlsx with revenue in col C and expenses in col D — can you add a profit margin column?",
    "should_trigger": true
  },
  {
    "query": "can you write a python script that reads a csv and uploads each row to postgres",
    "should_trigger": false
  }
]
```

分布建议：8-10 条 should-trigger + 8-10 条 should-not-trigger。

#### 编写原则

**should-trigger 查询**：覆盖多种表达方式
- 不同措辞（正式/随意/有错别字）
- 不同显式度（直接说"分析CSV" vs 间接说"老板想要个图表"）
- 不同复杂度（单步 vs 多步工作流）

**should-not-trigger 查询**：最有价值的是**近 misses**
- 分享关键词但需求不同（"更新 Excel 公式" vs "分析 CSV"）
- 涉及相关概念但任务本质不同（"CSV 转数据库" vs "CSV 分析"）

#### 评估方法

每条查询运行 3 次（模型行为不确定），计算 trigger rate：

```
should-trigger 查询：trigger rate > 0.5 → PASS
should-not-trigger 查询：trigger rate < 0.5 → PASS
```

#### 防止过拟合

将测试集分为 **train (60%)** 和 **validation (40%)**：
- 用 train set 指导修改
- 用 validation set 验证泛化性
- 选择 validation pass rate 最高的版本，而非最后一个版本

#### 描述优化循环

```
1. 在 train + validation 上评估当前描述
2. 分析 train set 中的失败案例
3. 修改描述（泛化，而非添加特定关键词）
4. 重复，直到 train set 全部通过
5. 选择 validation pass rate 最高的版本
```

5 轮迭代通常足够。

#### 编写有效描述的原则

- **祈使句** — "Use this skill when..." 而非 "This skill does..."
- **聚焦用户意图** — 描述用户想达成什么，而非技能内部实现
- **主动推送** — 明确列出适用场景，包括用户没直接提到的
- **保持简洁** — 几句话到一段，硬限 1024 字符

```markdown
<!-- Before -->
description: Process CSV files.

<!-- After -->
description: >
  Analyze CSV and tabular data files — compute summary statistics,
  add derived columns, generate charts, and clean messy data. Use this
  skill when the user has a CSV, TSV, or Excel file and wants to
  explore, transform, or visualize the data, even if they don't
  explicitly mention "CSV" or "analysis."
```

### 评估二：输出质量（Output Eval）

#### 设计测试用例

每个测试用例包含三部分：

```json
{
  "skill_name": "csv-analyzer",
  "evals": [
    {
      "id": 1,
      "prompt": "I have a CSV of monthly sales data in data/sales_2025.csv. Can you find the top 3 months by revenue and make a bar chart?",
      "expected_output": "A bar chart image showing the top 3 months by revenue, with labeled axes and values.",
      "files": ["evals/files/sales_2025.csv"],
      "assertions": [
        "The output includes a bar chart image file",
        "The chart shows exactly 3 months",
        "Both axes are labeled"
      ]
    }
  ]
}
```

#### 核心方法：A/B 对比

每个测试用例运行两次：**有 Skill** vs **无 Skill**（或旧版本）。

```
csv-analyzer-workspace/
└── iteration-1/
    ├── eval-top-months-chart/
    │   ├── with_skill/       # 有技能的输出
    │   │   ├── outputs/
    │   │   ├── timing.json   # Token 和耗时
    │   │   └── grading.json  # 断言结果
    │   └── without_skill/    # 基线对比
    │       ├── outputs/
    │       ├── timing.json
    │       └── grading.json
    └── benchmark.json        # 汇总统计
```

#### 编写断言

**好的断言**（可验证、具体）：
- "输出文件是合法的 JSON"
- "柱状图有坐标轴标签"
- "报告包含至少 3 条建议"

**弱的断言**（太模糊或太脆弱）：
- "输出很好" — 无法客观验证
- "输出必须精确包含 'Total Revenue: $X'" — 措辞变化就失败

#### 评分原则

- **PASS 需要具体证据** — 不给模糊的好处
- **同时审视断言本身** — 总是 PASS 的断言没有区分度，总是 FAIL 的断言可能有问题
- **关注 delta** — Skill 增加了多少 pass rate，花了多少额外 token

#### 汇总分析

```json
{
  "run_summary": {
    "with_skill": { "pass_rate": { "mean": 0.83 } },
    "without_skill": { "pass_rate": { "mean": 0.33 } },
    "delta": { "pass_rate": 0.50, "tokens": 1700 }
  }
}
```

delta 告诉你 Skill 的成本收益：提升 50% pass rate + 1700 额外 token → 值得；提升 2% + token 翻倍 → 不值得。

#### 迭代改进

```
1. 给 LLM 看 eval 信号 + 当前 SKILL.md，提议改进
2. 审阅并应用修改
3. 新 iteration 目录重跑全部测试
4. 评分 + 汇总
5. 人工审阅。重复
```

---

## Skill Evolve（技能进化）

### Hermes 的 Patch 补丁式更新

技能文件不是一次写死的。后续执行中发现更好的路径，直接修改。

```
旧方式（整体重写）:
  → 重新生成整个 Skill 文件
  → 可能丢失之前积累的上下文和注意事项

Hermes 方式（patch）:
  → 只传入 old_string 和 new_string
  → 精准替换，保留未变更内容
  → 每次改进都是增量式的
```

一个 Skill 可以经历数十次 patch，每次只改一个小点，最终形成高度精炼的操作手册。

### 按需加载（上下文经济）

系统提示中只加载技能的**名称 + 短描述**，全文按需调入：

```
系统提示（始终加载）:
  Skills: migrate-auth, debug-race, setup-e2e, ...

当任务匹配时:
  → 加载完整 Skill 文件到上下文
  → Agent 按步骤执行
```

```
40 个技能 → 200 个技能
上下文成本：几乎不变（只多了一行索引）
```

### Anthropic 的工具设计最佳实践

[Anthropic Engineering Blog: Writing Effective Tools for AI Agents](https://www.anthropic.com/engineering/writing-tools-for-agents) 的关键原则同样适用于技能进化：

- **只保留最重要的工具** — 过多工具反而降低 Agent 判断力
- **工具命名空间** — 让 Agent 清楚知道该调用哪个
- **返回有意义的上下文** — 工具结果要包含足够的决策信息
- **Token 效率优化** — 工具响应要精简，避免浪费上下文

参考：[Building Effective AI Agents](https://www.anthropic.com/research/building-effective-agents)

### 进化的三个信号源

基于 agentskills.io 的 eval 框架，技能改进的信号来自：

1. **失败断言** — 指向具体缺陷（缺少步骤、指令不清、边界情况未处理）
2. **人工反馈** — 指向更广泛的质量问题（方法错误、结构差、技术正确但没用）
3. **执行转录** — 揭示失败原因（Agent 忽略指令 → 指令有歧义；浪费时间 → 指令需精简）

最有效的改进方式：把三个信号源 + 当前 SKILL.md 一起给 LLM，让它提议修改。

---

## Skill Share（技能分享）

### agentskills.io 开放标准

[agentskills.io](https://agentskills.io) 是技能跨 Agent 兼容的基础。Skill 文件格式遵循统一标准：

| Agent 工具 | 兼容性 |
|-----------|--------|
| Claude Code | 支持 |
| OpenClaw | 支持 |
| Cursor | 支持 |
| Codex | 支持 |
| Hermes Agent | 支持 |
| 其他标准兼容工具 | 理论支持 |

这意味着用户在 Hermes 中沉淀的 Skill，可以直接迁移到 Claude Code、Cursor 等工具中使用。

### Anthropic 的 Skill 开放标准推动

> Anthropic didn't invent Skills. It made clear how to use the ones we have.
> — [Data Science Collective](https://medium.com/data-science-collective/anthropic-didnt-invent-skills-it-made-clear-how-to-use-the-ones-we-have-459e2823e5a5)

2025 年 12 月，Anthropic 将 Agent Skills 发布为开放标准，并提供：
- [Skill Creator 工具](https://claude.com/plugins/skill-creator) — 自动化创建和测试
- [The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) — 完整指南
- [Introduction to Agent Skills](https://anthropic.skilljar.com/introduction-to-agent-skills) — 训练课程

### 分享的层级

```
┌─────────────────────────────────────────────────────┐
│  L3  社区分享（Public Registry）     [未来]          │
│  公共 Skill 仓库，社区贡献和评分                      │
├─────────────────────────────────────────────────────┤
│  L2  团队分享（Team Skills）          [计划]          │
│  团队内共享 Skill，统一工作方式                        │
├─────────────────────────────────────────────────────┤
│  L1  跨工具移植（Cross-Agent）        [已实现]        │
│  agentskills.io 标准，同一 Skill 多工具使用           │
└─────────────────────────────────────────────────────┘
```

---

## 与 nano-claude 的整合

### 可借鉴方向

| 优先级 | 模块 | 借鉴内容 | 来源 |
|--------|------|---------|------|
| **P0** | Skill Creator | 任务后自动评估 + Skill 生成 | Hermes Agent |
| **P0** | Skill Evaluation | 触发准确性 eval + 输出质量 A/B 对比 | agentskills.io |
| **P1** | Skill Evolve | patch 补丁更新 + 按需加载 | Hermes Agent |
| **P1** | Skill Evolve | 工具设计最佳实践 | Anthropic |
| **P2** | Skill Share | agentskills.io 标准兼容 | Anthropic / agentskills.io |
| **P2** | Skill Creator | 模型自我进化脚手架 | MiniMax M2.7 |

### 与现有 /dream 的整合

nano-claude 已有 `/dream` 血月巩固引擎，可复用其信号提取机制：

```
/dream 血月巩固（已有）
    ↓ 提取信号 → 生成 memory 文件

扩展：信号分类
    ├── 偏好/反馈 → memory/*.md（现有）
    ├── 决策/截止 → memory/*.md（现有）
    └── 操作流程 → skills/*.md（新增 Skill Creator）
```

### 与 Hermes / M2.7 的互补

| 维度 | Hermes Agent | MiniMax M2.7 | nano-claude（目标） |
|------|-------------|--------------|-------------------|
| **进化对象** | Skill（操作流程） | Harness（脚手架） | 两者结合 |
| **进化粒度** | patch 补丁 | 完整代码修改 + 评测 | patch 优先 |
| **反馈来源** | 任务结果 + 用户纠正 | 自动评测 + 自反馈 | eval 框架 + 用户反馈 |
| **评估方法** | 无 formal eval | 内部评测集 | agentskills.io eval |

理想形态：Hermes 负责操作经验沉淀（Skill 层面），M2.7 的思路负责 Agent 自身进化（Harness 层面），agentskills.io 的 eval 框架保证质量可控。

---

## 参考

### 核心参考
- [agentskills.io — Evaluating Skills](https://agentskills.io/skill-creation/evaluating-skills)
- [agentskills.io — Optimizing Descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)
- [Hermes Agent 官网](https://hermes-agent.nousresearch.com)
- [Hermes Agent GitHub](https://github.com/NousResearch/hermes-agent)

### Anthropic
- [Building Effective AI Agents](https://www.anthropic.com/research/building-effective-agents)
- [Writing Effective Tools for AI Agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [The Complete Guide to Building Skills for Claude (PDF)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
- [Introduction to Agent Skills (Skilljar)](https://anthropic.skilljar.com/introduction-to-agent-skills)
- [Skill Creator Tool](https://claude.com/plugins/skill-creator)

### MiniMax
- [MiniMax M2.7 发布公告](https://www.minimaxi.com/news/minimax-m27-zh)
- [MiniMax M2.7 接入文档](https://platform.minimaxi.com/docs/token-plan/hermes-agent)

### 其他
- [graphify — 知识图谱 Skill](https://github.com/safishamsi/graphify/blob/v3/README.zh-CN.md)
- [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [Hermes Agent Design](./hermes-design.md)
- [Memory System Design](./memory-design.md)
