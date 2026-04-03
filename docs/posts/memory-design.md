# Memory System

> 本地记忆持久化 + 梦境化呈现

---

## 问题

Claude Code 的 memory 系统需要：
1. 持久化用户的偏好和项目信息
2. 让用户愿意主动查看记忆内容

但记忆是冰冷的文件，没有情感，没有仪式感。

---

## 核心设计

### 双层架构

```
┌─────────────────────────────────────────────────────┐
│                    Dream Layer                       │
│  /dream command - 境境化呈现                         │
│  10 种主题 / 强度系统 / Buddy 陪伴                   │
├─────────────────────────────────────────────────────┤
│                   Storage Layer                      │
│  ~/.claude/projects/<hash>/memory/                  │
│  YAML frontmatter + Markdown body                   │
└─────────────────────────────────────────────────────┘
```

---

## 存储层 (Storage Layer)

### 文件结构

```
~/.claude/projects/<project-hash>/memory/
├── MEMORY.md           # 索引文件
├── user_role.md        # 用户记忆
├── feedback_testing.md # 反馈记忆
├── project_status.md   # 项目记忆
└── reference_links.md  # 引用记忆
```

### 项目路径哈希

```python
import hashlib

def project_hash(path: str) -> str:
    """Convert project path to unique hash."""
    normalized = os.path.abspath(path).replace("\\", "/")
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]

# C:\Users\yangjing\Project\nano-claude → "C--Users-yangj-Project-nano-claude"
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

## 梦境层 (Dream Layer)

### `/dream` 命令

将记忆转化为"梦境"体验：

```
/dream                    # 随机梦境：回顾一条记忆
/dream --all              # 梦境全景：所有记忆的融合
/dream --recent           # 近期梦境：最近 7 天的记忆
/dream --feedback         # 反馈梦境：只看 feedback 类型
/dream user               # 用户梦境：只看 user 类型
```

### 梦境主题

10 种 Zelda 风格的梦境主题：

| ID | 主题 | 渲染风格 |
|----|------|----------|
| `fountain` | 记忆之泉 | 流水动画 |
| `shrine` | 神殿回响 | 神秘光晕 |
| `forest` | 迷雾森林 | 渐隐渐现 |
| `mountain` | 山巅远眺 | 层叠视图 |
| `lake` | 镜湖倒影 | 对称渲染 |
| `volcano` | 火山熔岩 | 热烈色彩 |
| `desert` | 沙漠风沙 | 风蚀效果 |
| `ocean` | 深海沉眠 | 深色背景 |
| `sky` | 天空岛屿 | 悬浮效果 |
| `castle` | 城堡记忆 | 结构化 |

### 梦境强度

| 强度范围 | 效果 | 颜色 |
|----------|------|------|
| 0-30 | 微弱梦境 | `dim` 灰暗 |
| 31-60 | 清晰梦境 | 正常亮度 |
| 61-80 | 强烈梦境 | `bold` 加粗 |
| 81-99 | 预知梦境 | `bright_*` 高亮 |
| 100 | 神谕梦境 | 全特效 |

### 梦境渲染示例

```
==================================================
            Entering Memory Shrine...
==================================================

    ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
   ▐▌   Memory Shrine   ▐▌
    ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼

        ◆ ◇ ◆ ◇ ◆

┌─────────────────────────────────┐
│ Type: feedback                  │
│ Created: 2026-02-28             │
│ Intensity: 72 (Strong)          │
├─────────────────────────────────┤
│ 测试必须使用真实数据库            │
│                                 │
│ **Why:** 上季度 incident         │
│ mock/prod 分离掩盖了 migration   │
│ 失败                            │
│                                 │
│ **How to apply:**               │
│ integration tests 必须用真实 DB  │
└─────────────────────────────────┘

        ◎ ◎ ◎
        
   [Link nods in agreement]

==================================================
         The dream fades away...
==================================================
```

### 确定性生成

与 Buddy 系统类似，使用确定性 PRNG：

```python
seed = hash(user_id + memory_type + date)
rng = Mulberry32(seed)

theme = uniform_select(THEMES, rng)
duration = rng.next() % 5 + 3  # 3-8 秒
intensity = rng.next() % 100   # 梦境强度
```

---

## 文件结构

```
src/memory/
├── __init__.py        # Module exports
├── models.py          # MemoryEntry, MemoryType, DreamTheme
├── storage.py         # LocalStorage: 读写文件系统
├── index.py           # IndexManager: 维护 MEMORY.md
├── themes.py          # 10 Zelda-themed dream styles
├── dreamer.py         # Dream generation engine
└── renderer.py        # Rich rendering with animations

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

# 梦境操作
nano-claude dream                    # 随机梦境
nano-claude dream --all              # 梦境全景
nano-claude dream --recent           # 近期记忆
```

### REPL 命令

```
/memory              # 显示记忆索引
/memory show <name>  # 显示特定记忆内容
/memory add <type> <content>  # 添加记忆
/memory delete <name>  # 删除记忆
/dream               # 随机梦境
/dream --all         # 梦境全景
```

---

## 与 Buddy 系统的联动

Buddy 可以出现在梦境中：

```python
from src.buddy import get_current_buddy

buddy = get_current_buddy()

# Buddy 陪伴梦境
console.print(buddy.mini_render())
console.print(f"[{buddy.species.name}] whispers: {memory.content}")
```

---

## Python API

```python
from src.memory import (
    MemoryType, MemoryEntry, 
    LocalStorage, load_memories, save_memory, dream
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

# 梦境回顾
result = dream(memories)
print(result.render())
```

---

## 与 Claude Code 原版的对比

| 特性 | Claude Code (TS) | nano-claude (Python) |
|------|------------------|----------------------|
| 存储位置 | `~/.claude/projects/` | 相同 |
| 文件格式 | YAML frontmatter + MD | 相同 |
| 索引文件 | MEMORY.md | 相同 |
| 哈希算法 | SHA-256 truncated | SHA-256 12 chars |
| 自动更新 | 会话结束时 | 显式 save |
| 梦境功能 | 无 | `/dream` 命令 |
| Buddy 联动 | 无 | Buddy 陪伴梦境 |

---

## 设计决策

| 决策 | 原因 |
|------|------|
| 文件系统存储 | 无需数据库依赖，可读性强 |
| YAML frontmatter | 标准格式，易于解析和编辑 |
| MEMORY.md 索引 | 加载时无需扫描所有文件 |
| 项目路径哈希 | 避免路径冲突，跨平台一致 |
| 10 种梦境主题 | Zelda 风格统一，与 Buddy 系统呼应 |
| 确定性生成 | 同一天同一记忆 = 同一梦境，仪式感 |
| Rich 动画 | 无需外部依赖，终端原生支持 |

---

## 未来扩展

1. **记忆迁移** - 跨项目复制记忆
2. **记忆导入** - 从 JSON/Markdown 导入
3. **梦境收藏** - 用户可保存喜欢的梦境
4. **梦境分享** - 导出为图片或文本
5. **Buddy 互动** - Buddy 评论梦境内容

---

## 参考

- [Claude Memory System](https://docs.anthropic.com/claude-code/memory)
- [YAML Frontmatter](https://jekyllrb.com/docs/frontmatter/)
- [Rich Animation](https://rich.readthedocs.io/en/stable/live.html)
- [Buddy Design](./buddy-design.md)
- [Mulberry32 PRNG](https://gist.github.com/tommyettinger/46a874533a3876551e07)