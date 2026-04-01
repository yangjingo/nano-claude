# Python 项目配置与 PyPI 发布

> 记录 Nano Claude 的打包发布配置

---

## 0. 遇到的问题

Nano Claude 是一个纯 Python 项目，零第三方依赖。

如何让它：
1. 可以用 `uv run nano-claude` 运行？
2. 可以打包发布到 PyPI？
3. 可以自动发布？

---

## 1. Why：为什么选择这套方案

### 1.1 为什么用 uv

**uv** 是 Astral 出品的现代 Python 包管理器：

| 特性 | pip | uv |
|------|-----|-----|
| 速度 | 慢 | 快 10-100x |
| 依赖解析 | 可能冲突 | 快速精确 |
| 虚拟环境 | 手动管理 | 自动创建 |
| 锁文件 | 无 | 自动生成 |

### 1.2 为什么用 hatchling

**hatchling** 是现代的构建后端：

- 简单配置（pyproject.toml 内）
- 快速构建
- 官方推荐

### 1.3 为什么用 GitHub Actions

- 免费（公开仓库）
- 集成简单
- 自动化发布

---

## 2. How：配置详解

### 2.1 pyproject.toml

```toml
[project]
name = "nano-claude"
version = "0.1.0"
description = "Minimal Python CLI framework - understanding through subtraction"
readme = "README.md"
requires-python = ">=3.12"
dependencies = []
license = "MIT"
authors = [{ name = "Yang Jing", email = "yangjing@example.com" }]
keywords = ["cli", "claude", "agent", "ai"]

[project.scripts]
nano-claude = "src.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.hatch.build.targets.sdist]
include = ["src", "README.md", "LICENSE"]
```

**关键配置说明**：

| 字段 | 作用 |
|------|------|
| `name` | PyPI 包名 |
| `version` | 版本号（打 tag 时更新）|
| `dependencies = []` | **零依赖**，纯标准库 |
| `project.scripts` | 安装后可执行命令 |
| `hatch.build.targets.wheel` | 打包 src 目录 |

### 2.2 CLI 入口点

```toml
[project.scripts]
nano-claude = "src.main:main"
```

这行配置的效果：

```bash
# 安装后
pip install nano-claude
nano-claude summary  # 直接运行

# 等价于
python -m src.main summary
```

`src.main:main` 指向 `src/main.py` 中的 `main()` 函数。

### 2.3 构建命令

```bash
# 构建 wheel 和 sdist
uv build

# 输出
dist/
├── nano_claude-0.1.0-py3-none-any.whl
└── nano_claude-0.1.0.tar.gz
```

### 2.4 手动发布

```bash
# 发布到 PyPI（需要 token）
uv publish --token $PYPI_TOKEN
```

---

## 3. 自动发布配置

### 3.1 GitHub Actions

`.github/workflows/publish.yml`:

```yaml
name: Build and Publish to PyPI

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: read

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Build package
        run: uv build

      - name: Publish to PyPI
        run: uv publish --token ${{ secrets.PYPI_TOKEN }}
```

### 3.2 触发条件

```yaml
on:
  push:
    tags:
      - 'v*'
```

只有推送 `v*` 格式的 tag 才会触发：

```bash
git tag v0.1.0
git push origin v0.1.0
# → 自动构建并发布到 PyPI
```

### 3.3 配置 PyPI Token

1. 登录 [PyPI](https://pypi.org/)
2. Account settings → API tokens → Create API token
3. 复制 token（格式：`pypi-...`）
4. GitHub 仓库 → Settings → Secrets → Actions
5. 添加 `PYPI_TOKEN` secret

---

## 4. 完整发布流程

### 4.1 本地验证

```bash
# 1. 运行测试
uv run python -m unittest discover -s tests -v

# 2. 本地测试
uv run nano-claude summary

# 3. 构建
uv build

# 4. 本地安装测试
uv pip install dist/nano_claude-0.1.0-py3-none-any.whl
nano-claude summary
```

### 4.2 发布

```bash
# 1. 更新版本号（pyproject.toml）
# version = "0.1.0" → "0.2.0"

# 2. 提交更改
git add .
git commit -m "release: v0.2.0"

# 3. 创建 tag
git tag v0.2.0

# 4. 推送
git push origin main
git push origin v0.2.0

# 5. 等待 GitHub Actions 完成
# 自动发布到 PyPI
```

### 4.3 安装验证

```bash
# 发布后，任何人都可以安装
pip install nano-claude
nano-claude summary
```

---

## 5. 如果是我，我会怎么做

### 5.1 版本管理

可以用 `bumpversion` 或手动更新：

```bash
# 手动更新 pyproject.toml
version = "0.2.0"

# 或用脚本
sed -i 's/version = "0.1.0"/version = "0.2.0"/' pyproject.toml
```

### 5.2 变更日志

维护 `CHANGELOG.md`：

```markdown
## 0.2.0 (2026-04-02)

### Added
- 新功能

### Fixed
- 修复内容
```

### 5.3 测试覆盖

发布前运行完整测试：

```bash
uv run python -m pytest tests/ -v --cov=src
```

---

## 6. 常见问题

### Q: 构建失败怎么办？

检查：
1. `pyproject.toml` 格式是否正确
2. `src/` 目录是否存在
3. `src/main.py` 中是否有 `main()` 函数

### Q: 发布失败怎么办？

检查：
1. `PYPI_TOKEN` 是否正确配置
2. 包名是否已被占用
3. 版本号是否重复

### Q: 如何撤销发布？

PyPI 不允许删除已发布的版本，只能 yank：

```bash
twine upload --repository-url https://upload.pypi.org/legacy/ \
  --skip-existing dist/*
```

---

## 7. 关键文件

| 文件 | 作用 |
|------|------|
| `pyproject.toml` | 项目配置 |
| `LICENSE` | 开源许可证 |
| `README.md` | 项目说明 |
| `.github/workflows/publish.yml` | 自动发布 |
| `uv.lock` | 依赖锁定 |

---

## 8. 延伸阅读

- [uv 官方文档](https://docs.astral.sh/uv/)
- [PyPI 发布指南](https://packaging.python.org/en/latest/tutorials/publishing-packages/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)

---

*上一篇: [为什么要拆解 Claude Code](../00-introduction/)*
*下一篇: [Python CLI 入口的五个细节](../01-entrypoint/)*