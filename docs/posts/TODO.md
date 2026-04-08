# TODO

> Nano-Claude 开发路线图

---

## 已完成

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
- [x] Tool Calling（Bash tool + ToolRegistry）
- [x] 多轮对话上下文管理
- [x] System Prompt 支持 + context 注入（per-turn 刷新）

### Memory System
- [x] 本地存储（`.nano_claude/memory/*.md`）
- [x] 记忆索引（MEMORY.md）
- [x] 记忆类型（user/feedback/project/reference）
- [x] `/memory` 命令
- [x] `/dream` 血月巩固引擎（keywords 信号匹配 + dreamer 整合）
- [x] 自动 dream 调度（scheduler）
- [x] SessionNotes（会话笔记：决策、文件、偏好、错误）

### Session 持久化
- [x] JSON 会话存储（`.nano_claude/sessions/*.json`）
- [x] `/resume` 内联切换 + ChoiceInput 选择框
- [x] `/save` 手动保存
- [x] `/clear` 清空会话
- [x] 会话列表（preview + 消息数）
- [x] 恢复后显示对话历史（最近 3 轮）
- [x] `--resume` CLI 参数 + `/resume` REPL 命令
- [x] transcript 纯文本落盘（给 /dream 扫描）

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

## 进行中

- [ ] 无

---

## 待开始

### CLI 增强
- [ ] `/help` 详细帮助
- [ ] `/history` 对话历史浏览

### Agent 增强
- [ ] 更多工具（Read, Write, Edit, Glob, Grep）
- [ ] Token 计数与预算控制
- [ ] 多模型切换（OpenAI, Gemini, etc.）

### 测试覆盖
- [ ] 单元测试覆盖率 > 80%
- [ ] 更多 E2E 场景
- [ ] Memory system 集成测试

### 文档
- [ ] API 文档
- [ ] 架构图
- [ ] 贡献指南

---

## 未来想法

- [ ] MCP Server 支持
- [ ] 插件系统
- [ ] Web UI
- [ ] 语音输入/输出

---

## 优先级

```
P0 (核心)  → 已完成
P1 (扩展)  → 更多工具, 测试覆盖
P2 (增强)  → 文档, 性能优化
P3 (探索)  → MCP, 多模型, Web UI
```