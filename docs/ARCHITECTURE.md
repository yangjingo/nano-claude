# Claw Code 架构总览

> Python 版架构文档 | Rust 版详见 `posts/10-rust-tui/`

---

## 一、项目定位

**Claw Code** 是 Claude Code 的 Clean-room Python 重写项目。

### 两个版本

| 版本 | 目录 | 定位 |
|------|------|------|
| **Python** | `src/` | 架构探索、结构学习、零依赖 |
| **Rust** | `rust/` | 生产实现、真实 API、完整 TUI |

### 原始 TS 归档

```
archive/claude_code_ts_snapshot/
├── 1,902 个 TypeScript 文件
├── 207 个命令条目
├── 184 个工具条目
└── 36 个子系统目录
```

---

## 二、技术栈

| 层面 | 技术 |
|------|------|
| **语言** | Python 3.12+ |
| **依赖** | 零第三方（纯标准库）|
| **核心库** | `dataclasses`, `argparse`, `functools.lru_cache`, `pathlib`, `json` |

---

## 三、代码规模

| 指标 | 数值 |
|------|------|
| Python 文件 | **66** |
| 子系统目录 | **25**（占位符）|
| CLI 命令 | **23** |
| 命令镜像 | 207 条（JSON）|
| 工具镜像 | 184 条（JSON）|

---

## 四、目录结构

```
src/
├── 核心模块
│   ├── main.py          # CLI 入口 (213行)
│   ├── runtime.py       # PortRuntime (193行)
│   ├── query_engine.py  # QueryEnginePort
│   ├── commands.py      # 命令注册表 (207条)
│   ├── tools.py         # 工具注册表 (184条)
│   ├── permissions.py   # 权限控制
│   ├── models.py        # 领域模型
│   ├── context.py       # 环境检测
│   ├── session_store.py # 会话持久化
│   ├── parity_audit.py  # TS 对比审计
│   └── ...
│
├── reference_data/
│   ├── commands_snapshot.json
│   ├── tools_snapshot.json
│   └── subsystems/       # 25个子系统元数据
│
└── 子系统占位 (25个目录)
    ├── assistant/
    ├── buddy/
    ├── bootstrap/
    ├── hooks/
    ├── plugins/
    ├── remote/
    ├── skills/
    └── ...
```

---

## 五、架构分层

```
CLI 层 (main.py)
    ↓ 23+ 子命令路由
运行时层 (runtime.py)
    ↓ route_prompt / bootstrap_session / turn_loop
查询引擎层 (query_engine.py)
    ↓ submit_message / persist_session
注册表层 (commands.py, tools.py)
    ↓ JSON 快照 + @lru_cache
基础设施层 (session_store, permissions, parity_audit)
```

---

## 六、核心模型

### 不可变 (frozen=True)

```python
@dataclass(frozen=True)
class PortingModule:
    name: str
    responsibility: str
    source_hint: str
    status: str  # 'planned' | 'mirrored' | 'implemented'

@dataclass(frozen=True)
class RoutedMatch:
    kind: str      # 'command' | 'tool'
    name: str
    score: int     # 匹配分数

@dataclass(frozen=True)
class ToolPermissionContext:
    deny_names: frozenset[str]
    deny_prefixes: tuple[str, ...]
```

### 可变状态

```python
@dataclass
class QueryEnginePort:
    mutable_messages: list[str]
    permission_denials: list[PermissionDenial]
    transcript_store: TranscriptStore
```

---

## 七、关键数据流

### JSON 快照加载

```
reference_data/*.json
    ↓ @lru_cache
load_*_snapshot()
    ↓
PORTED_COMMANDS / PORTED_TOOLS
```

### bootstrap_session（12步）

```
build_port_context()
run_setup()
HistoryLog()
route_prompt()          # Token 匹配
build_execution_registry()
执行命令/工具 shim
persist_session()
```

### route_prompt 算法

```
prompt → Token 分词 → 遍历 commands/tools
      → 计算 score = count(token in name/source/responsibility)
      → 交错返回最高分匹配
```

---

## 八、23 个命令速查

| 类别 | 命令 |
|------|------|
| 信息展示 | `summary`, `manifest`, `parity-audit` |
| 清单查询 | `commands`, `tools`, `show-command`, `show-tool` |
| 运行时 | `route`, `bootstrap`, `turn-loop` |
| 会话 | `flush-transcript`, `load-session` |
| 远程 | `remote-mode`, `ssh-mode`, `teleport-mode` |
| 执行 | `exec-command`, `exec-tool` |

详见 `COMMANDS.md`

---

## 九、快速命令

```bash
# 项目摘要
python3 -m src.main summary

# 会话启动
python3 -m src.main bootstrap "review this"

# 意图路由
python3 -m src.main route "commit changes"

# 一致性审计
python3 -m src.main parity-audit

# 测试
python3 -m unittest discover -s tests -v
```

---

## 相关文档

- `COMMANDS.md` - 命令详细手册
- `posts/README.md` - 博客系列导航
- `posts/10-rust-tui/` - Rust 版深度分析
- `../rust/README.md` - Rust 版完整文档