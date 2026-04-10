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

### 工具系统（P0）
- [x] ToolDef / ToolParam / ToolResult / ToolRegistry 框架
- [x] Bash — 跨平台 shell 检测（WSL / Git Bash / cmd.exe / native）
- [x] Read — cat -n 格式，offset/limit 分页
- [x] Write — 创建/覆写文件，自动创建父目录
- [x] Edit — 精确字符串替换，replace_all
- [x] Glob — pathlib.glob 文件模式匹配
- [x] Grep — re 正则搜索，glob 过滤，上下文行
- [x] `default_registry()` 工厂函数
- [x] 42 个单元测试覆盖全部工具

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

### 文档
- [x] CLAUDE.md 更新（与代码对齐）
- [x] ARCHITECTURE.md 更新（完整目录结构）
- [x] tool-design.md 更新（P0 工具实现记录）

---

## 进行中

- [ ] 无

---

## 待开始

### 工具系统（P1）
- [ ] `AskUserQuestion` — 交互式问答工具
- [ ] `Task*` — 任务管理工具组（Create/Get/List/Output/Stop/Update）
- [ ] `Agent` — 子 agent 生成工具

### 工具系统（P2-P3）
- [ ] `WebFetch` / `WebSearch` — 网络访问
- [ ] `MCPTool` / `McpAuth` — MCP 协议支持
- [ ] `LSP` — 语言服务协议
- [ ] `Skill` — 技能调用工具
- [ ] `NotebookEdit` — Jupyter notebook 编辑
- [ ] `EnterPlanMode` / `ExitPlanMode` — 计划模式

### 权限系统
- [ ] `PermissionGate` — 三级权限（auto-approve / context-aware / always-ask）
- [ ] 危险命令检测（rm -rf, git push --force, DROP TABLE）
- [ ] REPL 交互式审批（y/n 确认）

### CLI 增强
- [ ] `/help` 详细帮助
- [ ] `/history` 对话历史浏览

### Agent 增强
- [ ] Token 计数与预算控制
- [ ] 多模型切换（OpenAI, Gemini, etc.）

### 插件系统
- [ ] Skill 安装/加载机制（SKILL.md 发现 + 执行）
- [ ] 插件生命周期管理（install/enable/disable）
- [ ] 插件提供的 tool/command/MCP 扩展点

### 测试覆盖
- [ ] 单元测试覆盖率 > 80%
- [ ] 更多 E2E 场景
- [ ] Memory system 集成测试

### 文档
- [ ] API 文档
- [ ] 贡献指南

---

## 未来想法

- [ ] MCP Server 支持
- [ ] Web UI
- [ ] 语音输入/输出

---

## 优先级

```
P0 (核心)  → ✅ 已完成（CLI, Agent, 6 个工具, Memory, Session）
P1 (扩展)  → 更多工具, 权限系统, 插件系统
P2 (增强)  → 文档, 性能优化, 测试覆盖
P3 (探索)  → MCP, 多模型, Web UI
```
