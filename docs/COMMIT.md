# Commit Convention

> Git commit message 规范

---

## Format

```
<type>(<scope>): <subject>

<body>
```

---

## Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code refactoring (no feature/fix) |
| `test` | Adding/updating tests |
| `chore` | Build, config, dependencies |
| `style` | Formatting (no code change) |
| `perf` | Performance improvement |

---

## Scopes

| Scope | Description |
|-------|-------------|
| `repl` | REPL interactive prompt |
| `agent` | API client and streaming |
| `settings` | Configuration management |
| `command` | CLI commands (summary, route, etc.) |
| `docs` | Documentation files |
| `build` | Build and dependencies |

---

## Examples

```
feat(repl): add interactive prompt with banner

- Add src/repl.py for REPL loop
- Add /help, /exit, /model, /config commands
- Support mock mode when no API key

refs: docs/posts/introduction.md
```

```
feat(agent): implement async streaming with anthropic SDK

- Add src/agent.py with AsyncAnthropic client
- Stream response with rich.spinner animation
- Support multi-turn conversation history

deps: anthropic, rich
```

```
docs: update architecture and API documentation

- Update ARCHITECTURE.md with new modules
- Add async streaming examples to introduction.md
- Add COMMIT.md convention guide
```

```
refactor(repl): simplify banner and help output

- Remove redundant status lines
- Use rich.console for colored output
- Clean up mock mode messaging
```

---

## Best Practices

1. **Use English** for commit messages
2. **Lowercase** subject line
3. **Imperative mood** ("add" not "added")
4. **No period** at end of subject
5. **Body explains why**, not what
6. **Reference related files** or issues

---

## Related

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Angular Commit Guidelines](https://github.com/angular/angular/blob/master/CONTRIBUTING.md#commit)