# Session Storage

> 会话持久化：保存对话历史，支持 `--resume` 恢复

---

## 问题

CLI 会话是脆弱的。关掉终端，一切归零。

```
用户：帮我重构 auth 模块
AI：  好的，先看看现有代码...（调了 5 个工具，聊了 20 轮）
      [Ctrl+C]

# 重开终端
用户：继续刚才的 auth 重构
AI：  什么 auth？我不记得了。
```

上下文丢了。工具调用历史丢了。SessionNotes 丢了。
`/dream` 扫描 transcript，但 transcript 本身也没可靠地落盘。

---

## 发现：Claude Code 的会话持久化

基于 Claude Code TS 源码分析，会话持久化是核心基础设施：

### 存储格式：JSONL 增量追加

每个会话一个 `.jsonl` 文件，每行一个 JSON 对象（Entry）：

```
~/.claude/projects/<project-hash>/<session-id>.jsonl
```

为什么是 JSONL 而不是单个大 JSON？

- **增量追加**：每条消息 `appendFile` 一次，不需要重写整个文件
- **流式友好**：消息还在生成时就可以落盘
- **崩溃安全**：即使进程被 kill，已写入的行不会丢
- **可截断**：消息删除只需 `ftruncate` 到目标行

### Entry 类型系统

```
Entry (联合类型)
├── TranscriptMessage          ← 参与 API 对话链
│   ├── user                   ← 用户消息
│   ├── assistant              ← 助手消息 (含 tool_use)
│   ├── attachment             ← 附件 (图片/文件)
│   └── system                 ← 系统消息
├── MetadataEntry              ← 会话级元数据
│   ├── custom-title / ai-title
│   ├── tag                    ← 搜索/过滤
│   ├── agent-name / agent-color
│   ├── mode                   ← coordinator / normal
│   └── worktree-state
└── SnapshotEntry              ← 状态快照
    ├── file-history-snapshot
    ├── content-replacement    ← 压缩替换记录
    └── context-collapse-*
```

### parentUuid 链式结构

这不是简单的列表，是**对话树**：

```
                root (uuid: a1, parentUuid: null)
                 │
            user (uuid: b2, parentUuid: a1)
                 │
         assistant (uuid: c3, parentUuid: b2)
                ╱ ╲
    tool_use(d1)  tool_use(d2)     ← 并行工具调用 = DAG
           │            │
    tool_result(e1) tool_result(e2)
           │            │
            assistant (uuid: f3)   ← 合并后继续
                 │
            user (uuid: g4)
                 │
            ... (新分支从这里继续)
```

每个消息有 `uuid` + `parentUuid`，从叶子向根遍历得到对话链。
并行 `tool_use` 产生 DAG 拓扑，`recoverOrphanedParallelToolResults()` 恢复遗漏的兄弟节点。

### 写入流程：异步队列

```
用户消息 → appendEntry() → writeQueue (内存缓冲)
                                │
                           100ms 定时器
                                │
                        drainWriteQueue()
                                │
                          appendFile (磁盘)
```

两阶段策略：
1. **延迟创建**：第一条消息到达前，缓存在 `pendingEntries`，不创建文件
2. **异步刷新**：100ms 批量写入，不阻塞主线程
3. **退出重追加**：进程退出时 `reAppendSessionMetadata()`，确保元数据在文件尾部 64KB 窗口内

### 恢复流程

```mermaid
flowchart LR
    A[--resume] --> B[loadTranscriptFile]
    B --> C[构建 UUID 索引]
    C --> D[识别叶子节点]
    D --> E[buildConversationChain]
    E --> F[过滤]
    F --> G[中断检测]
    G --> H[状态重建]
```

关键步骤：
1. 读取 JSONL → 构建 `Map<UUID, Message>` 索引
2. 找到最新叶子节点 → 沿 parentUuid 链回溯到根
3. 过滤：删除孤立 tool_use、空白 assistant、未完成的 thinking
4. 中断检测：判断是正常结束 / 用户中断 / 工具中断
5. 状态重建：文件历史、归属、压缩状态、Todo、代理设置

### 轻量级元数据读取

`readLiteMetadata()` 只读文件**头尾各 64KB**：
- 头部：提取第一条用户提示作为默认标题
- 尾部：提取 customTitle、tag、agentName 等元数据

会话文件可能达到 GB 级别，不需要全部解析就能列出会话列表。

### 安全边界

| 配置项 | 默认值 | 作用 |
|-------|-------|------|
| `MAX_TRANSCRIPT_READ_BYTES` | 50 MB | 完整读取上限，防 OOM |
| `MAX_TOMBSTONE_REWRITE_BYTES` | 50 MB | 删除重写上限 |
| `LITE_READ_BUF_SIZE` | 64 KB | 轻量读取缓冲 |

---

## nano-claude 方案：简化但够用

Claude Code 的设计是为了**生产级** CLI：分支对话、并行工具、远程同步、子代理、GB 级会话。

nano-claude 是**学习项目**。我们需要的是：

1. 关掉终端不丢对话
2. `--resume` 能接着聊
3. `/dream` 能扫到 transcript

### 简化决策

| 原版特性 | nano-claude | 原因 |
|---------|-------------|------|
| JSONL 增量追加 | JSON 单文件 | 我们不需要流式中间态恢复，每次 save 写完整文件 |
| parentUuid 链式结构 | 线性 list | 不支持分支对话/编辑 |
| 异步写入队列 | 同步写入 | 会话规模小，不会阻塞 |
| Entry 联合类型 | 单一消息结构 | 不需要 metadata/snapshot 条目 |
| 中断状态检测 | 不实现 | 恢复后直接继续，不做特殊注入 |
| 并行工具恢复 | 不实现 | tool loop 是同步的 |
| 远程同步 | 不实现 | 本地 CLI |
| 轻量级元数据读取 | 不需要 | JSON 文件头部有元数据，整体解析 |
| 延迟文件创建 | 实现 | 避免空会话文件 |

### 存储格式

```
.nano_claude/sessions/
└── {session_id}.json
```

JSON 文件结构：

```json
{
  "session_id": "a1b2c3d4",
  "created": "2026-04-08T14:30:00",
  "updated": "2026-04-08T15:45:00",
  "model": "claude-sonnet-4-20250514",
  "system_prompt": "You are nano-claude...",
  "messages": [
    {"role": "user", "content": "帮我重构 auth"},
    {"role": "assistant", "content": [...blocks...]},
    {"role": "user", "content": [
      {"type": "tool_result", "tool_use_id": "...", "content": "..."}
    ]}
  ],
  "notes": {
    "decisions": ["决定用 JWT 而非 session"],
    "files_touched": ["src/auth.py", "src/middleware.py"]
  },
  "token_usage": {"input": 1234, "output": 567}
}
```

关键点：
- `messages` 保留完整的 API 格式（含 tool_use blocks、tool_result blocks）
- `notes` 保存 SessionNotes 的 9 模块数据
- `system_prompt` 保存时包含已注入的 memory context

### 写入流程

```
run_turn() 结束
  │
  ├─ _capture_turn_signals()  → 更新 SessionNotes
  │
  └─ save()                   → 序列化到 .nano_claude/sessions/{id}.json

stop() 退出
  │
  ├─ save()                   → 最终保存
  │
  └─ _flush_transcript()      → 写纯文本给 /dream 扫描
```

延迟创建：第一条 `run_turn()` 才触发第一次 save，避免空会话。

### 恢复流程

```
--resume        → 找 .nano_claude/sessions/ 下最新修改的 JSON
--resume <id>   → 加载指定 session_id 的 JSON

AgentSession.load(session_id)
  │
  ├─ 读取 JSON 文件
  ├─ 恢复 messages (完整 API 格式，直接可用)
  ├─ 恢复 SessionNotes
  ├─ start()   → 只创建 API client，不重载 memory
  │
  └─ 用户继续对话 → messages 追加 → model 看到完整上下文
```

### CLI 接口

```bash
# 新建会话（默认）
python -m src.cli.main repl

# 恢复最近会话
python -m src.cli.main repl --resume

# 恢复指定会话
python -m src.cli.main repl --resume a1b2c3d4

# 列出所有会话
python -m src.cli.main sessions list
```

REPL 内：

```
> /sessions          # 列出可恢复的会话
> /resume            # 恢复最近会话
> /resume a1b2c3d4   # 恢复指定会话
```

---

## 与 Memory 的关系

Session 是 Memory 的**上游**：

```
Session (会话)
  │
  ├─ save() ──→ .nano_claude/sessions/{id}.json    ← 结构化，给 --resume 用
  │
  ├─ _flush_transcript() ──→ .nano_claude/transcripts/  ← 纯文本，给 /dream 用
  │
  └─ notes ──→ SessionNotes (内存)                  ← 边聊边记

                        │
                   /dream 扫描
                        │
                  keywords.py 匹配信号
                        │
                  .nano_claude/memory/*.md          ← 永久记忆
                        │
                  MEMORY.md 索引
                        │
                  下次 start() → 注入 system prompt
```

两份数据，两个用途：
- `sessions/*.json` → **机器读**：恢复完整对话状态
- `transcripts/*.md` → **dream 读**：关键词匹配提取信号

---

## 代码结构

```
src/
├── agent/
│   └── agent.py           # AgentSession.save() / .load() / .list_sessions()
├── cli/
│   ├── main.py            # --resume 参数
│   └── repl.py            # /resume (picker), /save, /clear, /dream
└── memory/
    ├── notes.py           # SessionNotes
    ├── dreamer.py         # BloodMoon (读 transcripts)
    ├── keywords.py        # KeywordMatcher (信号匹配)
    ├── scheduler.py       # CronScheduler (自动 dream)
    └── models.py          # DreamResult (含 files, updated_names)
```

---

## 实现记录

### 2026-04-08 Session 机制补全

**问题**: `/sessions` 显示 "No saved sessions."，`/resume` 无法恢复会话。

**根因**: 代码骨架已存在但存在断点——`/resume` 丢弃参数、connected 模式未接入完整命令集。

**改动**:

1. **`/resume` 内联切换会话** — 不再退出 REPL 重启，直接在循环内 `stop` 旧 session → `load` 新 session → `start`
   - 无参数时弹出 ChoiceInput 选择框（最近 20 个 session，显示 preview + 消息数）
   - 有参数时直接恢复指定 session_id 或 "latest"

2. **`/sessions` 合并为 `/resume` 的别名** — 两者行为一致

3. **`list_sessions()` 增加 preview 字段** — 提取第一条 user 消息作为预览，自动跳过 `[context]...` 前缀

4. **恢复后显示对话历史** — `_show_session_history()` 展示最近 3 轮 user/assistant 摘要

5. **新增 `/save`** — 手动触发 save()，显示文件路径

6. **新增 `/clear`** — 清空当前 session 的 messages 和 token_usage

7. **`/dream` 增强** — 运行后用 Rich Panel/Table 展示结果；自动记录 dream_log.jsonl；显示历史和下次自动触发时间；update 前自动备份 `.bak`

8. **`DreamResult` 扩展** — 新增 `files` (被更新的 memory 文件路径) 和 `updated_names` (信号名称)

**文件变更**:

| 文件 | 改动 |
|------|------|
| `src/cli/repl.py` | `/resume` picker + 内联切换；`/save`、`/clear`；`/dream` Rich Panel；`_show_session_history` |
| `src/agent/agent.py` | `list_sessions()` 增加 preview 字段（过滤 context block） |
| `src/memory/models.py` | `DreamResult` 增加 `files`、`updated_names` 字段 |
| `src/memory/dreamer.py` | `_apply_consolidation()` 返回 files_touched；update 前备份 `.bak` |
| `tests/test_session_mechanism.py` | 6 个测试覆盖 save/list/load/resume/clear/empty |

---

## 对比

| 特性 | Claude Code | nano-claude |
|------|------------|-------------|
| 格式 | JSONL 增量追加 | JSON 单文件 |
| 对话拓扑 | DAG (parentUuid 链) | 线性 list |
| 写入 | 异步队列 + 100ms 批量 | 同步写入 |
| 存储 | `~/.claude/projects/<hash>/` | `.nano_claude/sessions/` |
| 恢复 | 链构建 + 过滤 + 中断检测 | 直接反序列化 |
| 元数据 | 尾部 64KB 窗口读取 | JSON 头部字段 |
| 延迟创建 | pendingEntries 缓冲 | 第一次 run_turn 才 save |
| 空会话保护 | materializeSessionFile | 同上 |
| 并行工具恢复 | recoverOrphanedParallelToolResults | 不需要 |
| 子代理会话 | subagents/ 子目录 | 不支持 |
| 远程同步 | CCR hydrate | 不支持 |
