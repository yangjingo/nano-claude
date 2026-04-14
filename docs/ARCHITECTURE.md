# Claw Code 架构总览

> Nano CC — 精简 Python 实现

---

## 一、项目定位

**Nano CC** 是 Claude Code 的精简 Python 重写，通过理解代码来精简它。

---

## 二、技术栈

| 层面 | 技术 |
|------|------|
| **语言** | Python 3.12+ |
| **依赖** | `anthropic` (官方 SDK), `rich` (UI), `prompt-toolkit` (REPL), `questionary` (交互选择) |
| **核心库** | `dataclasses`, `argparse`, `pathlib`, `json`, `asyncio` |

### API 调用

基于 [anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)，**异步流式输出**：

```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic()

async with client.messages.stream(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": "Hello"}],
) as stream:
    async for text in stream.text_stream:
        print(text, end="", flush=True)
```

配置文件 `~/.nano-claude/settings.json`：

```json
{
  "env": {
    "NANO_CLAUDE_API_KEY": "your-key",
    "NANO_CLAUDE_BASE_URL": "https://api.anthropic.com",
    "NANO_CLAUDE_MODEL": "claude-sonnet-4-6"
  }
}
```

### 配置回退链

当 nano-claude 自身配置为空时，自动从 Claude Code 的 `~/.claude/settings.json` 回退读取，优先级：

1. **nano-claude** `~/.nano-claude/settings.json` env
2. **OS 环境变量**
3. **Claude Code** `~/.claude/settings.json` env（自动映射变量名）
4. **硬编码默认值**

环境变量名映射（nano-claude ↔ Claude Code）：

| nano-claude | Claude Code |
|-------------|-------------|
| `NANO_CLAUDE_API_KEY` | `ANTHROPIC_AUTH_TOKEN` |
| `NANO_CLAUDE_BASE_URL` | `ANTHROPIC_BASE_URL` |
| `NANO_CLAUDE_DEFAULT_SONNET_MODEL` | `ANTHROPIC_DEFAULT_SONNET_MODEL` |
| `NANO_CLAUDE_DEFAULT_OPUS_MODEL` | `ANTHROPIC_DEFAULT_OPUS_MODEL` |
| `NANO_CLAUDE_DEFAULT_HAIKU_MODEL` | `ANTHROPIC_DEFAULT_HAIKU_MODEL` |

---

## 三、代码规模

| 指标 | 数值 |
|------|------|
| Python 文件 | **57** |
| 目录（src/） | **7**（agent, buddy, cli, engine, memory, registry, tools） |
| 总行数 | **~6,800** |
| 内置工具 | **6**（Bash, Read, Write, Edit, Glob, Grep） |
| 测试行数 | **~1,700** |

---

## 四、目录结构

```
src/
├── cli/                    # CLI 入口 + REPL
│   ├── main.py             # argparse 子命令
│   └── repl.py             # 交互式 REPL（prompt-toolkit）
├── agent/                  # Agent 核心
│   ├── agent.py            # AsyncAnthropic 流式 + tool calling
│   └── settings.py         # API key/model/base_url 配置
├── tools/                  # 工具系统
│   ├── __init__.py         # ToolDef, ToolParam, ToolResult, ToolRegistry
│   ├── bash.py             # 跨平台 shell（WSL / Git Bash / cmd / native）
│   ├── read.py             # cat -n 格式文件读取
│   ├── write.py            # 文件写入
│   ├── edit.py             # 精确字符串替换
│   ├── glob_tool.py        # pathlib.glob 文件搜索
│   └── grep_tool.py        # re 正则内容搜索
├── memory/                 # 记忆系统
│   ├── __init__.py         # 子系统门面
│   ├── storage.py          # .nano_claude/memory/*.md 文件 I/O
│   ├── index.py            # MEMORY.md 索引管理
│   ├── models.py           # MemoryEntry, MemoryType
│   ├── dreamer.py          # /dream 巩固引擎
│   ├── keywords.py         # 关键词提取 + 信号匹配
│   ├── scheduler.py        # 自动 dream 调度
│   └── notes.py            # SessionNotes（决策、文件、偏好、错误）
├── engine/                 # 查询引擎 + 运行时
│   ├── query_engine.py     # QueryEnginePort（submit/persist/summarize）
│   └── runtime.py          # PortRuntime（route/bootstrap/turn-loop）
├── registry/               # 命令/工具注册表（mirrored）
│   ├── commands.py         # PORTED_COMMANDS
│   ├── tools.py            # PORTED_TOOLS
│   ├── command_graph.py    # 命令依赖图
│   ├── tool_pool.py        # 工具池组装 + 权限过滤
│   └── execution_registry.py # 执行分发 shim
├── buddy/                  # 宠物系统（彩蛋）
│   ├── __init__.py         # roll_buddy() 入口
│   ├── species.py          # 10 种角色
│   ├── rarities.py         # 5 种稀有度
│   ├── models.py           # Buddy, BuddyStats
│   ├── generator.py        # Mulberry32 PRNG 生成
│   ├── prng.py             # PRNG 实现
│   ├── hats.py             # 帽子分配
│   └── eyes.py             # 眼色分配
├── models.py               # 共享 dataclass
├── context.py              # system prompt 上下文
├── session_store.py        # JSON 会话持久化
├── transcript.py           # 纯文本 transcript
├── history.py              # 对话历史管理
├── permissions.py          # 权限过滤
├── cost_tracker.py         # Token 用量追踪
├── port_manifest.py        # 工作空间内省
├── parity_audit.py         # TS vs Python 一致性审计
└── ...                     # 其他辅助模块
```

---

## 五、核心循环

```
用户输入
  ↓
REPL (cli/repl.py)
  → /command 处理（内置命令）
  → 或 AgentSession.chat(input)
      ↓
  AsyncAnthropic API（流式）
      ↓
  响应解析
  → text block → rich 输出
  → tool_use block → ToolRegistry.run()
      ↓
  工具执行（Bash/Read/Write/Edit/Glob/Grep）
      ↓
  tool_result 反馈 → 继续循环
      ↓
  记忆捕获（session notes + token 计数）
      ↓
  会话自动保存
```

---

## 六、架构分层

```
REPL 层 (cli/repl.py)
    ↓ 用户交互 /help /exit /model
Agent 层 (agent/agent.py)
    ↓ anthropic SDK 流式 + tool calling
工具层 (tools/)
    ↓ Bash, Read, Write, Edit, Glob, Grep
记忆层 (memory/)
    ↓ /dream 巩固 + session notes
会话层 (session_store.py + transcript.py)
    ↓ JSON 持久化 + /resume
查询引擎层 (engine/query_engine.py + runtime.py)
    ↓ submit / persist / route / bootstrap
注册表层 (registry/)
    ↓ mirrored 命令/工具 + 权限过滤
配置层 (agent/settings.py)
    ↓ ~/.nano-claude/settings.json
```

---

## 七、快速命令

```bash
# 启动 REPL（默认）
uv run nano-claude

# CLI 子命令
uv run nano-claude summary
uv run nano-claude bootstrap "review this"
uv run nano-claude route "commit changes"

# 测试
uv run python -m pytest tests/ -v
```

---

## 八、Agent 框架对比

### nano-claude / OpenClaw / Hermes Agent

| 维度 | OpenClaw | Hermes Agent | nano-claude |
|------|----------|--------------|-------------|
| **架构** | 多 Agent 联合 | 单 Agent 自学习 | 单 Agent 精简实现 |
| **扩展方式** | 修改配置文件联合多 Agent | 运行时自学习 Skill | 手动编码工具/命令 |
| **记忆系统** | 外部配置 | 4 层（常驻提示 + SQLite 归档 + Skill + Honcho） | 7 层纵深防御（文件系统 + 血月巩固） |
| **技能管理** | 手动编写 | 自动生成 + patch 进化 | 无内置 |
| **定位** | 编排工具 | 自进化搭档 | Claude Code 最小复刻 |

### nano-claude 的独特定位

nano-claude 选择**精简复刻 Claude Code** 路线，通过理解代码来精简它（减法哲学）。记忆系统采用 7 层纵深防御架构，核心特色是血月巩固引擎（`/dream`）。

可从 Hermes Agent 借鉴的方向：
- **自学习循环** — 任务后自动沉淀 Skill
- **SQLite FTS5** — 替代文件扫描的历史检索
- **按需加载** — 控制上下文成本

### Karpathy LLM Wiki + graphify

[Karpathy 的 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 提出了知识持久化的另一条路径：用 LLM 把原始文件编织成带反向链接的持久化 Wiki。[graphify](https://github.com/safishamsi/graphify) 将其工程化 — 两轮提取（AST + Claude 子代理）构建知识图谱，Leiden 社区发现聚类，SHA256 缓存增量更新，watch 模式实时同步。52 个混合文件语料可降低 71.5x 查询 token 消耗。

三者定位：**LLM Wiki** 是知识输入端（收集 → 组织 → 导航），**Hermes** 是知识输出端（执行 → 学习 → 进化），**graphify** 是两者的桥梁（文件 → 可查询图谱）。

详见 [Hermes Agent Design](./posts/hermes-design.md) / [Skill System Design](./posts/skill-design.md) / [官网](https://hermes-agent.nousresearch.com) / [GitHub](https://github.com/NousResearch/hermes-agent)。

---

## 相关文档

- `CLAUDE.md` — 项目说明（给 Claude Code 的指引）
- `NANO.md` — 减法记录
- `COMMANDS.md` — 命令手册
- `docs/posts/tool-design.md` — 工具系统设计
- `docs/posts/memory-design.md` — 记忆系统设计
- `docs/posts/hermes-design.md` — Hermes Agent 对比与参考
- `docs/posts/skill-design.md` — 技能系统设计（自学习闭环 + 开放标准）
- `docs/posts/TODO.md` — 开发路线图
- [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — LLM 编织知识 Wiki 的原始思路
- [graphify](https://github.com/safishamsi/graphify/blob/v3/README.zh-CN.md) — 知识图谱 Skill（Claude Code / Codex / OpenClaw）
