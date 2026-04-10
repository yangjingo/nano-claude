# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nano CC is a minimal Python CLI that mirrors Claude Code's agent loop: REPL, tool calling, memory, and session persistence. Built with `anthropic` SDK + `rich` + `prompt-toolkit`.

## Repository Structure

```
src/
├── cli/
│   ├── main.py              # CLI entrypoint (argparse subcommands + REPL launcher)
│   └── repl.py              # Interactive REPL with prompt-toolkit, streaming, commands
├── agent/
│   ├── agent.py             # AsyncAnthropic session, streaming, tool calling loop
│   └── settings.py          # API key/model/base_url config, settings.json read/write
├── engine/
│   ├── query_engine.py      # QueryEnginePort — multi-turn submit/persist/summarize
│   └── runtime.py           # PortRuntime — route/bootstrap/turn-loop orchestration
├── registry/
│   ├── commands.py          # PORTED_COMMANDS registry, command lookup/execution
│   ├── tools.py             # PORTED_TOOLS registry, tool lookup/execution
│   ├── command_graph.py     # Command dependency graph builder
│   ├── tool_pool.py         # Tool pool assembly with permission filtering
│   └── execution_registry.py # Execution dispatch shim
├── memory/
│   ├── __init__.py          # Memory subsystem facade (save/load/search/dream)
│   ├── storage.py           # .nano_claude/memory/*.md file I/O
│   ├── index.py             # MEMORY.md index management
│   ├── models.py            # MemoryEntry, MemoryType dataclasses
│   ├── dreamer.py           # /dream consolidation engine (signal matching + integration)
│   ├── keywords.py          # Keyword extraction and signal matching
│   ├── scheduler.py         # Auto-dream scheduling
│   └── notes.py             # SessionNotes (decisions, files, preferences, errors)
├── buddy/
│   ├── __init__.py          # roll_buddy() entry point
│   ├── species.py           # 10 species definitions (Zelda Champions + Monsters)
│   ├── rarities.py          # 5 rarity tiers
│   ├── models.py            # Buddy, BuddyStats dataclasses
│   ├── generator.py         # Deterministic generation via Mulberry32 PRNG
│   ├── prng.py              # Mulberry32 PRNG implementation
│   ├── hats.py              # Hat assignment logic
│   └── eyes.py              # Eye color assignment
├── tools/
│   ├── __init__.py
│   └── bash.py              # Bash tool implementation
├── __init__.py              # Package exports
├── models.py                # Shared dataclasses (Subsystem, PortingModule, etc.)
├── context.py               # System prompt context builder
├── session_store.py         # JSON session persistence (.nano_claude/sessions/)
├── transcript.py            # Plain-text transcript logging (for /dream scanning)
├── history.py               # Conversation history management
├── permissions.py           # ToolPermissionContext — permission filtering
├── costHook.py              # Cost tracking hook
├── cost_tracker.py          # Token usage / cost accumulator
├── bootstrap_graph.py       # Runtime bootstrap phase graph
├── port_manifest.py         # Workspace introspection (file counts, module listing)
├── parity_audit.py          # TS vs Python consistency audit
├── setup.py                 # System init and prefetch config
├── system_init.py           # System init message builder
├── prefetch.py              # Prefetch helpers
├── deferred_init.py         # Deferred initialization
├── remote_runtime.py        # Remote/SSH/teleport mode stubs
├── direct_modes.py          # Deep-link and direct-connect mode stubs
├── ink.py                   # Rich rendering helpers
├── interactiveHelpers.py    # Interactive prompt helpers (ChoiceInput, etc.)
├── dialogLaunchers.py       # Dialog launcher utilities
├── replLauncher.py          # REPL launch helper
├── task.py                  # PortingTask dataclass
├── tasks.py                 # Task management
├── query.py                 # Query helpers
├── projectOnboardingState.py # Project onboarding state
├── QueryEngine.py           # Legacy query engine (top-level)
└── Tool.py                  # Legacy tool base (top-level)
```

## Development Commands

### Run the CLI

```bash
uv run nano-claude                      # Start REPL (default)
uv run nano-claude repl                 # Same as above
uv run nano-claude repl --resume        # Resume latest session
uv run nano-claude summary              # Project status report
uv run nano-claude manifest             # Source manifest
uv run nano-claude parity-audit         # TS vs Python consistency check
uv run nano-claude route "commit"       # Intent routing simulation
uv run nano-claude bootstrap "review"   # Session bootstrap simulation
```

### Run Tests

```bash
uv run python -m pytest tests/ -v
```

## Architecture

### Core Loop

```
REPL (cli/repl.py)
  → AgentSession (agent/agent.py) — AsyncAnthropic streaming + tool calls
  → ToolRegistry — dispatches Bash (tools/bash.py) + registered tools
  → Memory (memory/) — auto-save session notes, /dream consolidation
  → SessionStore (session_store.py) — JSON persistence + /resume
```

### Key Data Flows

1. **REPL → Agent**: User input → `AgentSession.chat()` → streaming response → rich output
2. **Tool Calling**: Agent emits tool_use → `BashTool.run()` → result returned to agent
3. **Memory**: `/dream` scans transcripts → keyword extraction → dreamer consolidation → MEMORY.md update
4. **Session**: `/save` or auto → `SessionStore.save()` → JSON file → `/resume` reloads

### REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/exit` | Exit REPL |
| `/model` | Show or switch model (sonnet/opus/haiku) |
| `/config` | Show current configuration |
| `/buddy` | Roll a random buddy pet |
| `/memory` | List, show, or manage memories |
| `/dream` | Scan transcripts, consolidate into persistent memory |
| `/sessions` | List saved sessions |
| `/resume` | Resume a previous session |
| `/save` | Save current session |
| `/clear` | Clear session messages |

## Environment

- **OS**: Windows 11 (WSL2 for development)
- **Python**: 3.12+ (managed by uv)
- **Dependencies**: `anthropic`, `rich`, `prompt-toolkit`, `questionary`, `claude-agent-sdk`
- **Build**: `uv` + `hatchling`

## Important Notes

- Commit convention: conventional commits (`feat(scope):`, `fix:`, `docs:`, etc.) — see `docs/COMMIT.md`
- User config at `~/.nano-claude/settings.json`; project data at `.nano_claude/`
- The `archive/` directory, `__pycache__/`, and `.nano_claude/` are gitignored
- Docs in `docs/`: `ARCHITECTURE.md` (architecture), `COMMANDS.md` (CLI commands), `COMMIT.md` (commit convention), `posts/` (blog posts)
