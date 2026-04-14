---
title: Nano Claude
subtitle: 从 Claude Code源码学习到复刻一个Nano Claude的一些碎碎念
version: 0.1
author: Why.J
date: 2026.04.13
watermark: whyj + nano banano + 2026/04/13
---

## 01 / Context
### 范式转移：复刻一个Nano 项目是最好的学习方式

- **旧范式**: 搭环境 -> 跑demo ->读源码 -> 陷细节 -> 陷入细节。
- **新范式**: 创Nano -> 跑demo -> 读文档-> 理解核心 -> 实现核心。
- **目标点**: 追求极致优雅的代码减法。

!visual: figures/fig1.png

@pulse: 端到端跑通最小的功能闭环，理解全部的逻辑更重要。

---

## 02 / Agenda
### OutLine
@layout: push-left
@no-bullet

- **Q1**: 如何进行项目的极致"减法复刻"？
- **Q2**: Vibe 时代的代码阅读流如何演进？
- **Q3**: Nano Claude 的具体设计与开发路径？
- **Q4**: 如何更加高效的进行 Vibe Coding？

---

## 03 / Mechanism
### 减法原则：从完整项目 进化到 Nano 麻雀

- **逻辑 Nano 化**: 剥离所有边缘依赖与交错， 简化一些复杂的边界管理。
- **效率 Nano 化**: 代码的运行效率是可以优先级放后的。
- **心态**: 为学习而拆解，理解核心功能，关注必要的细节即可，不必死磕所有细节。

!visual: figures/fig3.png

@pulse: 做减法，优雅的本质是删除到无可再删。

---

## 04 / Mechanism
### 阅读流重塑：架构理念学习优于源码实现细节

- **核心认知**: 与Agent交互重于具体代码实现， CC的单点代码能力一定比你强。
- **执行策略**: 喂给 Claude Code全量源码， 输出架构和工程细节的文档。
- **核心点**: 专注为你的Agent写好规范和需求，约束你的Agent的行动空间和边界。

!visual: figures/fig4.png

@pulse: Spec-Driven 规则/需求驱动的的Vibe Coding开发模式。

---

## 05 / Mechanism
### 逆向工具使用：快速获取源码的逻辑骨架

- **zread-cli**: zhipu的极速索引与全目录提取。
- **deepwiki**: 免费的自动化构建工程知识图谱。
- **claude /init**: Claude Code本身自带的功能。

!visual: figures/fig5.png

@pulse: 学习源码的文档和设计理念和细节，而不拘泥于源码细节。

---

## 06 / Mechanism
### 开发起点：以用户视角感受到的功能/UX进行入手

- **交互**: CLI 极简指令优于重度 WebUI， CLI可以让你更加专注和易于拓展
- **技术**: 收敛至相对可控的基础技术栈， 找自己熟悉的工具和框架。
- **锚点**: 从最惊艳的你自己的功能锚点开始切入，开始动手。

!visual: figures/fig6.png

@pulse: 用户感知到的功能是最好的入口，从你最喜欢的一个功能开始！

---

## 07 / Mechanism
### Spec-Driven：文档即代码的开发

- **文档架构**: Arch -> Module功能模块详设 -> Todo追踪管理进度。
- **文档管理**: Git 追踪一切文档的演进。
- **文档撰写**: 利用一些插件辅助深度的头脑风暴。

!visual: figures/fig7.png

@pulse: 写好你的文档，是最高效的指令，注意不断地迭代，以及做好版本控制。

---

## 08 / Mechanism
### Test-Driven：让 OpenClaw 负责最终测试

- **策略**: 让 （另外一个）Agent 接管全量测试流程。
- **测试**: 部署 OpenClaw 自己操作terminal/chrome 进行自动化的测试。
- **范式**: 告别手动 Debug，迈向 AI 的 "相爱相杀", 自主闭环。

!visual: figures/fig8.png

@pulse: 最好的测试员是另外一个Agent，但是在这之前请你自己确保你会。

---

## 09 / Mechanism
### 进展汇报： Nano Claude 一些开发的经验

- **/buddy**: 协同交互建议协议，在我的terminal装一个zelda宠物系统。
- **/dream**: 跨Session的记忆进化， 我以为的梦中进化，变成了血月来了。
- **/tools**: 核心工具链调用中枢，我也来践行一下bash is all you need 。

!visual: figures/fig9.png

@pulse: 找到你最感兴趣的点， 作为入口进行功能的拆解， 注意保留文档。

---

## 10 / Takeaways
### 行动指南: 立即启动你的Nano 项目
@no-bullet

- **行动 1**：启动一个 Nano 级的项目复刻。
- **行动 2**：固化 Spec-Driven 编程方法工作流。
- **行动 3**：跑通 Agent 开发-测试-验证闭环。

!visual: figures/fig10.png

@pulse: 停止仅限于理论的学习，开始构建一个Nano，干中学与分享！

---

## 11 / Reference
### Reference
@no-bullet
@ref-list

- 《重构 改善既有代码的设计第二版》- Martin Fowler - https://book-refactoring2.ifmicro.com/
- The Way of Code - Rick Rubin - https://www.thewayofcode.com/
- Nano Claude Artifacts - https://github.com/yangjingo/nano-claude/tree/main/docs
- Claude Code WIKI (Claude) - https://openedclaude.github.io/claude-reviews-claude
- Claude Code WIKI (Zread) - http://leow3lab.service.huawei.com:9681/
- Claude Code Src prompt - https://github.com/Piebald-AI/claude-code-system-prompts
- AIBot Halo Project - https://github.com/openkursar/hello-halo

!visual: figures/fig11.png

@pulse: 拒绝FOMO，不要焦虑，多读经典著作与优雅代码！
