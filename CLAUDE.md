# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python porting workspace for a Claude Code rewrite effort. The `src/` tree contains the active Python implementation that is being ported from an exposed TypeScript snapshot (no longer part of the tracked repository).

## Repository Structure

```
src/
├── __init__.py          # Package exports
├── main.py              # CLI entrypoint with argparse subcommands
├── port_manifest.py     # Workspace introspection and manifest generation
├── query_engine.py      # Aggregates and renders porting summaries
├── models.py            # Dataclasses: Subsystem, PortingModule, PortingBacklog
├── commands.py          # Command backlog metadata (ported commands registry)
├── tools.py             # Tool backlog metadata (ported tools registry)
└── task.py              # Task-level planning structures (PortingTask)
```

## Development Commands

### Run the CLI

```bash
python3 -m src.main summary       # Render Markdown summary of porting workspace
python3 -m src.main manifest      # Print workspace manifest
python3 -m src.main subsystems    # List Python modules with file counts
```

### Run Tests

```bash
python3 -m unittest discover -s tests -v
```

Or run a single test:

```bash
python3 -m unittest tests.test_workspace.PortingWorkspaceTests.test_manifest_counts_python_files -v
```

## Architecture

### Core Flow

1. **`main.py`** - CLI entrypoint using `argparse` with subcommands (`summary`, `manifest`, `subsystems`)
2. **`port_manifest.py`** - Introspects the `src/` directory to count Python files and identify top-level modules; returns a `PortManifest` dataclass
3. **`query_engine.py`** - `QueryEnginePort` aggregates the manifest with command/tool backlogs to render a complete summary
4. **`models.py`** - Shared dataclasses: `Subsystem`, `PortingModule`, `PortingBacklog`
5. **`commands.py`** & **`tools.py`** - Static registries of what has been ported (`PORTED_COMMANDS`, `PORTED_TOOLS`)

### Key Dataclasses

- `Subsystem` - Represents a top-level Python module with name, path, file count, and notes
- `PortingModule` - Represents a ported component with name, responsibility, source hint, and status
- `PortingBacklog` - Collection of `PortingModule`s with summary rendering
- `PortingTask` - Individual task tracking (defined but not yet integrated)

## Important Notes

- No external dependencies (stdlib only)
- Uses `__future__` annotations for forward compatibility
- The `archive/` directory and `__pycache__/` are gitignored
- This is a work-in-progress Python port; completeness is tracked via the backlog metadata in `commands.py` and `tools.py`
