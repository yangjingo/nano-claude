# Memory System

> 跨会话记忆持久化 + 血月巩固引擎

---

## 问题

Claude Code 的 memory 系统需要：
1. 持久化用户的偏好和项目信息
2. 让记忆在会话间保持连贯

但记忆是静态文件，用户不会主动维护。

- Session A 用户说"不要用 mock"，Session B 不知道，又用了 mock
- "周四之后合并冻结"没存进 memory，过期了也没人知道
- 连续编码几天，做了很多决策，但都没有沉淀

人类大脑在睡眠时巩固记忆 — 系统也需要一个"睡眠"机制来整理碎片。

---

## 架构总览

基于 Claude Code TS 源码逆向分析，记忆系统是 **7 层纵深防御**：

```
┌─────────────────────────────────────────────────────┐
│  L7  缓存对齐 (Cache Alignment)         [概念参考]   │
├─────────────────────────────────────────────────────┤
│  L6  血月巩固 (/dream Blood Moon)        [核心实现]   │
├─────────────────────────────────────────────────────┤
│  L5  持久化记忆 (Storage Layer)           [核心实现]   │
├─────────────────────────────────────────────────────┤
│  L4  全量摘要 + 熔断 (Summary Agent)     [概念参考]   │
├─────────────────────────────────────────────────────┤
│  L3  会话笔记 (Session Notes)             [计划实现]   │
├─────────────────────────────────────────────────────┤
│  L2  缓存微压缩 (cache_edits)            [API 依赖]   │
├─────────────────────────────────────────────────────┤
│  L1  大输出落盘 (Spill to Disk)           [计划实现]   │
└─────────────────────────────────────────────────────┘
```

每一层都在阻止下一层（更昂贵的）采样发生。

---

## 核心设计

### 双层架构

```
┌─────────────────────────────────────────────────────┐
│                   Blood Moon Layer                    │
│  /dream command - 血月巩固引擎                       │
│  Agent-loop keyword matching + Cron 定时             │
├─────────────────────────────────────────────────────┤
│                   Storage Layer                      │
│  ~/.nano_claude/memory/                             │
│  YAML frontmatter + Markdown body                   │
└─────────────────────────────────────────────────────┘
```

---

## L1: 大输出落盘

工具结果超过阈值时，强制写入磁盘，上下文仅保留预览。

```
工具输出 > 100KB
    │
    ▼
┌──────────────┐    ┌──────────────┐
│  磁盘存储     │    │  上下文预览   │
│  完整结果     │    │  ~2KB 摘要   │
└──────────────┘    └──────────────┘
```

**ContentReplacementState**:

```python
@dataclass
class ContentReplacementState:
    seen_ids: set[str]      # 已处理结果 ID
    replacements: dict[str, str]  # ID → 2KB 预览文本
```

- **阈值**: 100KB
- **预览**: 2KB（保持上下文可读性）
- **目的**: 用磁盘 I/O 规避昂贵的 API token 消耗

---

## L2: 缓存微压缩

> 依赖 API 层，nano-claude 标记为概念参考。

- 触发 `cache_edits` API，从服务端直接删除旧 token
- **冷启动**: 闲置 60 分钟后自动清理，防止缓存过期导致的高额分词成本

---

## L3: 会话笔记

> 计划实现。

边聊边记，避免窗口快满时才匆忙摘要。

### 9 模块模板

```markdown
### Workflow
- 当前任务的工作流状态

### Learnings
- 本次会话中学到的东西

### Errors & Corrections
- 踩过的坑，防止逻辑回滚

### Current State
- 当前正在处理的 Atomic Task

### Decisions
- 做出的关键决策及原因

### Blockers
- 遇到的阻碍

### Next Steps
- 后续待办

### Files Touched
- 修改过的文件列表

### User Preferences
- 捕获到的用户偏好信号
```

- **异步更新**: 通过 `runForkedAgent` 在后台静默维护，不干扰主进程
- **注入策略**: 压缩后重新注入最近 5 个文件和延迟调用的技能

---

## L4: 全量摘要 + 熔断

> 概念参考。

上下文缓冲区接近极限时的最后防线。

```
T_threshold = W_window - 20K_out - 13K_buffer
```

- **触发条件**: 缓冲区 < 13K 时，唤醒 Summary Agent
- **Scratchpad**: 模型先在思维草稿本中推理，最后剥离，仅保留纯净摘要
- **两阶段**: 推理 → 剥离 → 纯净摘要（避免推理过程污染后续上下文）

---

## L5: 持久化记忆 (Storage Layer)

### 文件结构

```
~/.nano_claude/memory/
├── MEMORY.md           # 索引文件
├── user_role.md        # 用户记忆
├── feedback_testing.md # 反馈记忆
├── project_status.md   # 项目记忆
└── reference_links.md  # 引用记忆
```

### 记忆文件格式

```markdown
---
name: user_role
description: 用户角色信息，用于定制交互风格
type: user
created: 2026-03-15
updated: 2026-04-03
---

你是数据科学家，专注于 observability 和日志分析。

**Why:** 项目需要构建日志管道，需要理解数据流

**How to apply:**
- 在解释代码时关联数据管道概念
- 使用数据处理相关类比
```

### MEMORY.md 索引

```markdown
# Memory Index

- [User Role](user_role.md) — 数据科学家，日志分析
- [Feedback: Testing](feedback_testing.md) — 测试必须用真实数据库
- [Project: Release](project_release.md) — 2026-03-05 合并冻结
- [Reference: Dashboard](reference_dashboard.md) — Grafana 监控面板
```

**约束**：
- 索引每行 < 150 字符
- 超过 200 行截断
- 按语义分组，不按时间

### MemoryType 枚举

```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class MemoryType(Enum):
    USER = "user"          # 用户角色、偏好
    FEEDBACK = "feedback"  # 行为指导
    PROJECT = "project"    # 项目状态
    REFERENCE = "reference"  # 外部资源指针

@dataclass
class MemoryEntry:
    name: str
    description: str
    type: MemoryType
    content: str
    created: datetime
    updated: datetime | None = None
    file_path: str | None = None
```

---

## L6: 血月巩固 (/dream)

### 血月隐喻

Zelda: Breath of the Wild 中，**血月** 是周期性事件：

- 午夜降临，天空变为血红色
- 海拉鲁大陆上所有被击败的敌人复活
- 格鲁德的怨念重新充斥世界
- 然后一切恢复正常，但世界已被"重置"

`/dream` 是记忆系统的血月：

- **天空变红** — Cron 触发前的预警信号
- **敌人复活** — 从旧转录中提取被遗忘的信号
- **怨念净化** — 清理过期、冲突的记忆
- **世界重置** — 索引重建，记忆归一化

### 问题

会话间的信号会丢失。用户不会主动说"请记住这个"。

### 核心机制

`/dream` 是**一个命令**，没有 flag，没有主题，没有强度。

它做的事：扫描历史 → 提取信号 → 巩固记忆。

```
/dream
  │
  ▼
┌─────────────────────────────────────────┐
│  Phase 1: Scan                          │
│  扫描会话转录文件 (.jsonl / session)     │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│  Phase 2: Extract                       │
│  Agent-loop 多轮 keyword matching       │
│  Round 1: 匹配关键词 → 候选信号         │
│  Round 2: 去重 + 对比已有 memory        │
│  Round 3: 日期归一化 + 分类             │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│  Phase 3: Consolidate                   │
│  写入新 memory / 更新已有 memory        │
│  合并重复 / 清理过期                     │
│  重建 MEMORY.md 索引                    │
└──────────────┬──────────────────────────┘
               ▼
         DreamResult summary
```

### Agent-Loop Keyword Matching

```python
KEYWORD_PATTERNS = {
    "preference": [
        "不要用", "别用", "prefer", "always use",
        "never use", "我喜欢", "我习惯", "总是",
    ],
    "error": [
        "bug", "错误", "失败", "broken", "fix",
        "incident", "regression",
    ],
    "decision": [
        "决定用", "我们选", "go with", "chose",
        "switch to", "migrate to",
    ],
    "deadline": [
        "截止", "deadline", "freeze", "due",
        "之前", "by friday", "release",
    ],
}
```

每一轮：
1. 用关键词模式扫描转录文本
2. 提取匹配段落的上下文（前后各 5 行）
3. 与已有 memory 做相似度对比
4. 决定：创建 / 更新 / 合并 / 跳过

### 日期归一化

转录中的相对时间必须转为绝对日期：

```
"昨天"    → "2026-04-06"
"下周一"  → "2026-04-13"
"周四之后" → "2026-04-09 之后"
```

### Cron 定时

血月不需要手动触发。

```python
# Cron: 每天凌晨 3 点
CRON_EXPRESSION = "0 3 * * *"

# 触发条件（双保险）
def should_trigger_dream() -> bool:
    return (
        accumulated_tokens() >= 5000  # 积累了足够的新内容
        and is_idle(minutes=30)        # 用户已闲置
    )
```

- **积累阈值**: 5000+ 新 token 才激活（避免空跑）
- **闲置检测**: 用户 30 分钟无操作
- **手动覆盖**: `/dream` 也可随时手动执行

### 血月预警

触发前给用户一个视觉信号（类似 Zelda 红色天空）：

```
==================================================
  🩸 Blood Moon Rising...
  Scanning 12 sessions for forgotten signals...
==================================================
```

### DreamResult

```python
@dataclass
class DreamResult:
    total: int
    created: int = 0
    updated: int = 0
    merged: int = 0
    pruned: int = 0

    def summary(self) -> str:
        parts = [f"{self.total} memories scanned"]
        changes = []
        if self.created: changes.append(f"{self.created} created")
        if self.updated: changes.append(f"{self.updated} updated")
        if self.merged: changes.append(f"{self.merged} merged")
        if self.pruned: changes.append(f"{self.pruned} pruned")
        parts.append("| " + ", ".join(changes) if changes else "| no changes")
        return "**Blood Moon complete:** " + " ".join(parts)
```

---

## L7: 缓存对齐

> 概念参考，运行时优化。

派生 Agent（L3/L5/L6 的后台任务）共享父进程的缓存：

```python
@dataclass
class CacheSafeParams:
    system_prompt: str       # 克隆父进程 system prompt
    fork_context_messages: list  # 克隆消息前缀
    tooluse_context: list    # 克隆工具上下文
```

- 字节级对齐 → 服务端缓存命中率接近 100%
- 目的：降低 API 成本，不是并发

---

## 文件结构

```
src/memory/
├── __init__.py        # Module exports
├── models.py          # MemoryEntry, MemoryType, MemoryIndex, DreamResult
├── storage.py         # LocalStorage: 文件系统读写
├── notes.py           # SessionNotes: L3 会话笔记（新增）
├── dreamer.py         # BloodMoon: L6 血月巩固引擎（重写）
├── keywords.py        # KeywordMatcher: 关键词匹配规则（新增）
└── scheduler.py       # CronScheduler: 血月定时触发（新增）

tests/
└── test_memory.py     # Unit tests
```

---

## CLI 命令

```bash
# 存储操作
nano-claude memory list              # 查看所有记忆
nano-claude memory show user_role    # 查看特定记忆
nano-claude memory add --type user "你是前端开发者"
nano-claude memory delete feedback_testing

# 血月巩固
nano-claude dream                    # 手动触发血月巩固
```

### REPL 命令

```
/memory              # 显示记忆索引
/memory show <name>  # 显示特定记忆内容
/memory add <type> <content>  # 添加记忆
/memory delete <name>  # 删除记忆
/dream               # 触发血月巩固
```

---

## 与 Buddy 系统的联动

Buddy 可以出现在血月场景中：

```python
from src.buddy import get_current_buddy

buddy = get_current_buddy()

# 血月中的 Buddy
console.print(buddy.mini_render())
console.print(f"[{buddy.species.name}] senses the Blood Moon...")
console.print(f"[{buddy.species.name}] whispers: {dream_result.summary()}")
```

---

## Python API

```python
from src.memory import (
    MemoryType, MemoryEntry,
    LocalStorage, load_memories, save_memory
)
from datetime import datetime

# 创建记忆
entry = MemoryEntry(
    name="user_role",
    description="用户是数据科学家",
    type=MemoryType.USER,
    content="你专注于 observability 和日志分析\n**Why:** 项目需要数据管道",
    created=datetime.now()
)

# 保存
storage = LocalStorage()
storage.save(entry)

# 加载所有
memories = storage.load_all()
for m in memories:
    print(f"[{m.type.value}] {m.name}: {m.description}")

# 触发血月
from src.memory.dreamer import BloodMoon
moon = BloodMoon(storage)
result = moon.consolidate()
print(result.summary())
```

---

## 与 Claude Code 原版的对比

| 层级 | 特性 | Claude Code (TS) | nano-claude (Python) |
|------|------|------------------|----------------------|
| L1 | 大输出落盘 | >100KB → 磁盘 + 2KB 预览 | 计划实现 |
| L2 | 缓存微压缩 | cache_edits API | API 依赖 |
| L3 | 会话笔记 | 9 模块模板 + 异步更新 | 计划实现 |
| L4 | 摘要熔断 | <13K 触发 + scratchpad | 概念参考 |
| L5 | 持久化 | ~/.claude/projects/memory/ | ~/.nano_claude/memory/ |
| L5 | 文件格式 | YAML frontmatter + MD | 相同 |
| L5 | 索引文件 | MEMORY.md (200 行硬限) | 相同 |
| L6 | 梦境巩固 | 闲置时扫描 .jsonl | /dream 血月 + Cron |
| L6 | 日期归一化 | 相对 → 绝对日期 | 相同 |
| L7 | 缓存对齐 | CacheSafe 克隆前缀 | 概念参考 |

---

## 设计决策

| 决策 | 原因 |
|------|------|
| 文件系统存储 | 无需数据库依赖，可读性强 |
| YAML frontmatter | 标准格式，易于解析和编辑 |
| MEMORY.md 索引 | 加载时无需扫描所有文件 |
| 血月隐喻 | Zelda 主题统一，周期性巩固直觉清晰 |
| /dream 单命令 | 简单即正确，无需 flag 变体 |
| Agent-loop matching | 多轮提取比单次扫描更精准 |
| Cron 定时 | 自动触发，用户无需记得 |
| 5000 token 阈值 | 避免空跑，有内容才巩固 |

---

## 未来扩展

1. **记忆迁移** - 跨项目复制记忆
2. **记忆导入** - 从 JSON/Markdown 导入
3. **血月日志** - 记录每次血月的巩固详情
4. **Buddy 互动** - Buddy 评论血月结果
5. **自定义关键词** - 用户扩展匹配规则

---

## 参考

- [Claude Memory System](https://docs.anthropic.com/claude-code/memory)
- [YAML Frontmatter](https://jekyllrb.com/docs/frontmatter/)
- [Buddy Design](./buddy-design.md)
- [Zelda: Blood Moon](https://zelda.fandom.com/wiki/Blood_Moon)
