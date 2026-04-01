# Claw Code CLI 命令功能清单

> Project Claw Code - Python 重写的 Claude Code  harness 系统

---

## 一、信息展示类命令

### `summary` —— 项目全景摘要
```bash
python3 -m src.main summary
```
输出完整的项目状态报告，包括：源码统计、模块清单、命令清单、工具清单。

---

### `manifest` —— 源码结构清单
```bash
python3 -m src.main manifest
```
输出当前 Python 源码目录的结构化清单（模块名、文件数、说明）。

---

### `subsystems --limit N` —— 子系统列表
```bash
python3 -m src.main subsystems --limit 32
```
以 TSV 格式输出模块列表，便于管道处理。

---

### `parity-audit` —— 一致性审计
```bash
python3 -m src.main parity-audit
```
对比 Python 实现与本地 TypeScript 归档的差异（需要本地存在归档文件）。

---

### `setup-report` —— 启动配置报告
```bash
python3 -m src.main setup-report
```
展示系统启动时的预取配置和初始化状态。

---

## 二、架构分析类命令

### `command-graph` —— 命令依赖图
```bash
python3 -m src.main command-graph
```
显示命令系统的分层结构（核心层、插件层、技能层）。

---

### `tool-pool` —— 工具池状态
```bash
python3 -m src.main tool-pool
```
展示当前组装好的工具池，包括权限过滤后的工具清单。

---

### `bootstrap-graph` —— 启动阶段图
```bash
python3 -m src.main bootstrap-graph
```
显示运行时启动的各个阶段（初始化 → 权限 → 远程 → 交互）。

---

## 三、清单查询类命令

### `commands` —— 命令清单查询
```bash
# 列出前20个命令
python3 -m src.main commands

# 搜索命令
python3 -m src.main commands --query "git"

# 排除插件命令
python3 -m src.main commands --no-plugin-commands

# 排除技能命令
python3 -m src.main commands --no-skill-commands

# 自定义数量
python3 -m src.main commands --limit 10
```

---

### `tools` —— 工具清单查询
```bash
# 列出前20个工具
python3 -m src.main tools

# 搜索工具
python3 -m src.main tools --query "file"

# 简单模式（仅内置工具）
python3 -m src.main tools --simple-mode

# 排除 MCP 工具
python3 -m src.main tools --no-mcp

# 禁用特定工具
python3 -m src.main tools --deny-tool "Bash" --deny-tool "Agent"

# 按前缀禁用
python3 -m src.main tools --deny-prefix "danger_"
```

---

### `show-command <name>` —— 查看命令详情
```bash
python3 -m src.main show-command "commit"
```
显示指定命令的完整信息（名称、来源、职责描述）。

---

### `show-tool <name>` —— 查看工具详情
```bash
python3 -m src.main show-tool "Read"
```
显示指定工具的完整信息。

---

## 四、运行时模拟类命令

### `route <prompt>` —— 意图路由
```bash
python3 -m src.main route "commit these changes" --limit 5
```
模拟 Claw 如何根据用户输入匹配最合适的命令/工具。

输出格式：`类型 名称 匹配分数 来源`

---

### `bootstrap <prompt>` —— 会话启动
```bash
python3 -m src.main bootstrap "review this PR" --limit 5
```
模拟完整会话启动流程：加载上下文 → 组装工具 → 初始化运行时。

---

### `turn-loop <prompt>` —— 多轮对话模拟
```bash
# 基础用法
python3 -m src.main turn-loop "fix the bug" --max-turns 3

# 结构化输出
python3 -m src.main turn-loop "refactor this" --max-turns 5 --structured-output
```
模拟 agent 的多轮执行循环，展示每轮的输出和停止原因。

---

## 五、会话管理类命令

### `flush-transcript <prompt>` —— 持久化会话
```bash
python3 -m src.main flush-transcript "user message here"
```
将当前对话持久化到磁盘，返回会话文件路径。

---

### `load-session <session_id>` —— 加载会话
```bash
python3 -m src.main load-session "session_abc123"
```
加载并显示已持久化的会话状态（消息数、token 消耗）。

---

## 六、远程模式类命令

### `remote-mode <target>` —— 远程控制模式
```bash
python3 -m src.main remote-mode "wsl://ubuntu"
```
模拟远程控制运行时分支。

---

### `ssh-mode <target>` —— SSH 模式
```bash
python3 -m src.main ssh-mode "user@host"
```
模拟 SSH 远程运行时。

---

### `teleport-mode <target>` —— 传送模式
```bash
python3 -m src.main teleport-mode "/path/to/dir"
```
模拟目录传送运行时（快速切换工作目录）。

---

### `direct-connect-mode <target>` —— 直连模式
```bash
python3 -m src.main direct-connect-mode "container_id"
```
模拟直接连接运行时（如容器、WSL）。

---

### `deep-link-mode <target>` —— 深度链接模式
```bash
python3 -m src.main deep-link-mode "file://path#L10"
```
模拟深度链接运行时（打开特定文件位置）。

---

## 七、执行 shim 类命令

### `exec-command <name> <prompt>` —— 执行命令 shim
```bash
python3 -m src.main exec-command "commit" "fix typo"
```
执行指定命令的模拟实现，返回执行结果。

退出码：0（成功）或 1（失败）

---

### `exec-tool <name> <payload>` —— 执行工具 shim
```bash
python3 -m src.main exec-tool "Read" '{"file_path": "/etc/hosts"}'
```
执行指定工具的模拟实现。

---

## 八、命令分类速查

| 类别 | 命令 |
|------|------|
| **信息展示** | `summary`, `manifest`, `subsystems`, `parity-audit`, `setup-report` |
| **架构分析** | `command-graph`, `tool-pool`, `bootstrap-graph` |
| **清单查询** | `commands`, `tools`, `show-command`, `show-tool` |
| **运行时模拟** | `route`, `bootstrap`, `turn-loop` |
| **会话管理** | `flush-transcript`, `load-session` |
| **远程模式** | `remote-mode`, `ssh-mode`, `teleport-mode`, `direct-connect-mode`, `deep-link-mode` |
| **执行 shim** | `exec-command`, `exec-tool` |

---

## 九、关键实现文件对应

| 功能领域 | 核心文件 |
|---------|---------|
| CLI 入口 | `src/main.py` |
| 命令注册表 | `src/commands.py` |
| 工具注册表 | `src/tools.py` |
| 运行时核心 | `src/runtime.py` |
| 启动图 | `src/bootstrap_graph.py` |
| 命令图 | `src/command_graph.py` |
| 工具池 | `src/tool_pool.py` |
| 权限控制 | `src/permissions.py` |
| 远程运行时 | `src/remote_runtime.py` |
| 直接模式 | `src/direct_modes.py` |
| 会话存储 | `src/session_store.py` |
| 一致性审计 | `src/parity_audit.py` |
| 初始化配置 | `src/setup.py` |

