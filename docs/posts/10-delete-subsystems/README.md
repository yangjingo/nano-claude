# 删除 29 个空目录

> 减法记录 — 为什么可以删

---

## 0. 遇到的问题

打开 `src/` 目录，看到 29 个子目录：

```
src/assistant/
src/bootstrap/
src/bridge/
src/buddy/
... (25 more)
```

每个目录只有 1 个文件：`__init__.py`

这些是什么？能删吗？

---

## 1. Why：为什么存在

这些目录是 **占位符**。

原始 Claude Code (TypeScript) 有这些子系统：
- `assistant/` - AI 助手交互
- `buddy/` - AI 伴侣 UI
- `hooks/` - 生命周期钩子
- `plugins/` - 插件系统
- ... 等

Python 移植时，保留了目录结构，但没有实现内容。

每个 `__init__.py` 只是从 JSON 加载元数据：

```python
# src/buddy/__init__.py
SNAPSHOT_PATH = Path(__file__).parent.parent / 'reference_data' / 'subsystems' / 'buddy.json'
_SNAPSHOT = json.loads(SNAPSHOT_PATH.read_text())

ARCHIVE_NAME = _SNAPSHOT['archive_name']
MODULE_COUNT = _SNAPSHOT['module_count']
```

---

## 2. How：确认可以删除

### 检查依赖

```bash
# 搜索是否有其他代码引用这些目录
grep -r "from .assistant" src/
grep -r "from .buddy" src/
# ... 无结果
```

### 检查导出

```python
# src/__init__.py
__all__ = [
    'PortManifest',
    'QueryEnginePort',
    # ... 没有导出 assistant, buddy 等
]
```

### 运行测试

```bash
uv run nano-claude summary
# 成功运行
```

---

## 3. 删除操作

```bash
rm -rf src/assistant src/bootstrap src/bridge src/buddy src/cli \
       src/components src/constants src/coordinator src/entrypoints \
       src/hooks src/keybindings src/memdir src/migrations \
       src/moreright src/native_ts src/outputStyles src/plugins \
       src/remote src/schemas src/screens src/server src/services \
       src/skills src/state src/types src/upstreamproxy src/utils \
       src/vim src/voice

rm -rf src/reference_data/subsystems/
```

**结果**：
- 删除 29 个目录
- 删除 29 个 `__init__.py`
- 删除 29 个 JSON 元数据文件

---

## 4. 验证

```bash
uv run nano-claude summary
```

输出：

```
Port root: `...\src`
Total Python files: **37**  (从 66 减少)
```

✅ 运行正常

---

## 5. 理解收获

### 占位符的作用

占位符存在的意义：
1. **结构映射** — 保留原始项目的目录结构
2. **扩展预留** — 方便未来实现这些子系统
3. **法律缓冲** — 展示"我知道这里有东西"

### 占位符的问题

占位符的问题：
1. **虚假完整** — 看起来有很多模块，实际都是空的
2. **理解障碍** — 新人看到这么多目录，以为都很重要
3. **维护负担** — 每个目录都有 `__init__.py`，增加复杂度

### 删除的勇气

**删除的前提是理解**：

- 我知道这些目录是什么（占位符）
- 我知道它们没有被使用（无依赖）
- 我知道删了不会坏（测试通过）

---

## 6. 后续

删除空目录只是第一步。

接下来要问：
- `src/` 下的 37 个文件都必要吗？
- 哪些可以合并？
- 哪些可以删除？

---

## 关键代码引用

| 文件 | 操作 |
|------|------|
| `src/*/__init__.py` (29个) | 删除 |
| `src/reference_data/subsystems/*.json` (29个) | 删除 |

---

*上一篇: [JSON 快照镜像哲学](../09-json-snapshot/)*
*下一篇: 待定*