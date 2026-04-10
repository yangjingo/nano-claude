"""Glob tool — file pattern matching using Python's pathlib.glob."""

from __future__ import annotations

import os
from pathlib import Path

from . import ToolDef, ToolParam

MAX_RESULTS = 250


async def execute(
    pattern: str,
    path: str = ".",
) -> str:
    """Find files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g. ``**/*.py``, ``src/**/*.ts``).
        path: Directory to search in (default: current directory).

    Returns:
        Sorted file paths, one per line.
    """
    root = Path(path).resolve()

    if not root.is_dir():
        return f"error: '{path}' is not a directory"

    try:
        matches = sorted(root.glob(pattern))
    except Exception as e:
        return f"error: invalid pattern: {e}"

    # Filter to files only, limit output
    files = [m for m in matches if m.is_file()][:MAX_RESULTS]
    total = len([m for m in matches if m.is_file()])

    if not files:
        return f"(no files matching '{pattern}' in {root})"

    # Show relative paths when possible
    lines: list[str] = []
    for f in files:
        try:
            lines.append(str(f.relative_to(root)))
        except ValueError:
            lines.append(str(f))

    result = "\n".join(lines)

    if total > MAX_RESULTS:
        result += f"\n... {total - MAX_RESULTS} more files not shown"

    return result


glob_tool = ToolDef(
    name="Glob",
    description="Find files matching a glob pattern. Returns sorted file paths.",
    params=(
        ToolParam("pattern", "string", "Glob pattern (e.g. '**/*.py', 'src/**/*.ts')"),
        ToolParam("path", "string", "Directory to search in (default: current directory)", required=False),
    ),
    handler=execute,
)
