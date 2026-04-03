# TODO

> Nano-Claude 开发路线图

---

## ✅ 已完成

### CLI 核心
- [x] REPL 交互式终端
- [x] prompt-toolkit 集成（命令补全、选择菜单）
- [x] 流式输出（支持 thinking 内容）
- [x] Ctrl+C 友好退出
- [x] E2E 测试（pexpect + pywinpty）

### Agent
- [x] Anthropic SDK 集成
- [x] 流式响应
- [x] Thinking 内容提取

### Buddy Pet System
- [x] 10 种角色（Zelda Champions + Monsters）
- [x] 5 种稀有度
- [x] 属性系统（Health, Stamina, Skill）
- [x] 确定性生成（Mulberry32 PRNG）
- [x] Rich Panel 渲染

### 配置管理
- [x] settings.json 读写
- [x] 环境变量支持
- [x] 模型切换

---

## 🚧 进行中

### Memory System
- [ ] 本地存储（LocalStorage）
- [ ] 记忆索引（MEMORY.md）
- [ ] 记忆类型（user/feedback/project/reference）
- [ ] `/memory` 命令
- [ ] `/dream` 梦境系统

---

## 📋 待开始

### CLI 命令
- [ ] `/help` 详细帮助
- [ ] `/history` 对话历史
- [ ] `/clear` 清屏
- [ ] `/save` / `/load` 会话持久化

### Agent 增强
- [ ] Tool Calling
- [ ] 多轮对话上下文管理
- [ ] System Prompt 支持
- [ ] Token 计数

### 测试覆盖
- [ ] 单元测试覆盖率 > 80%
- [ ] 更多 E2E 场景
- [ ] 性能基准测试

### 文档
- [ ] API 文档
- [ ] 架构图
- [ ] 贡献指南

---

## 💡 未来想法

- [ ] MCP Server 支持
- [ ] 多模型切换（OpenAI, Gemini, etc.）
- [ ] 插件系统
- [ ] Web UI
- [ ] 语音输入/输出

---

## 优先级

```
P0 (核心)  → Memory System
P1 (重要)  → Tool Calling, 多轮对话
P2 (增强)  → 更多 CLI 命令, 测试覆盖
P3 (优化)  → 文档, 性能优化
```