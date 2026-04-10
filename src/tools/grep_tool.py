"""Grep tool — search file contents with regex using Python's re module."""

from __future__ import annotations

import os
import re
from pathlib import Path

from . import ToolDef, ToolParam

MAX_MATCHES = 250
CONTEXT_LINES = 2


async def execute(
    pattern: str,
    path: str = ".",
    glob: str | None = None,
    case_insensitive: bool = False,
    context: int = CONTEXT_LINES,
) -> str:
    r"""Search file contents with a regex pattern.

    Args:
        pattern: Regular expression to search for.
        path: File or directory to search in.
        glob: Filter files by glob pattern (e.g. ``*.py``). Only used when path is a directory.
        case_insensitive: Case-insensitive matching (default false).
        context: Number of context lines before and after each match (default 2).

    Returns:
        Matching lines with file paths and line numbers.
    """
    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"error: invalid regex: {e}"

    root = Path(path).resolve()

    # Single file mode
    if root.is_file():
        results = _search_file(root, root.parent, regex, context)
        return "\n".join(results) if results else "(no matches)"

    # Directory mode
    if not root.is_dir():
        return f"error: '{path}' is not a file or directory"

    all_results: list[str] = []
    file_count = 0

    for filepath in sorted(root.rglob(glob or "*")):
        if not filepath.is_file():
            continue
        # Skip binary-ish and hidden paths
        parts = filepath.relative_to(root).parts
        if any(p.startswith(".") or p == "__pycache__" for p in parts):
            continue

        results = _search_file(filepath, root, regex, context)
        if results:
            all_results.extend(results)
            all_results.append("")  # blank line between files
            file_count += 1

        if len(all_results) >= MAX_MATCHES * 3:
            all_results.append(f"... (truncated, over {MAX_MATCHES} matches)")
            break

    if not all_results:
        return "(no matches)"

    return "\n".join(all_results)


def _search_file(
    filepath: Path,
    root: Path,
    regex: re.Pattern[str],
    context: int,
) -> list[str]:
    """Search a single file, return formatted match lines."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = text.splitlines()
    matches: list[str] = []

    for i, line in enumerate(lines):
        if regex.search(line):
            try:
                rel = str(filepath.relative_to(root))
            except ValueError:
                rel = str(filepath)

            # Context before
            for j in range(max(0, i - context), i):
                matches.append(f"{rel}:{j + 1}:  {lines[j]}")

            # Match line
            matches.append(f"{rel}:{i + 1}>> {line}")

            # Context after
            for j in range(i + 1, min(len(lines), i + 1 + context)):
                matches.append(f"{rel}:{j + 1}:  {lines[j]}")

            if len(matches) > MAX_MATCHES * 3:
                break

    return matches


grep_tool = ToolDef(
    name="Grep",
    description="Search file contents with a regex pattern. Supports glob filtering and context lines.",
    params=(
        ToolParam("pattern", "string", "Regular expression pattern to search for"),
        ToolParam("path", "string", "File or directory to search in (default: current directory)", required=False),
        ToolParam("glob", "string", "Filter files by glob pattern (e.g. '*.py')", required=False),
        ToolParam("case_insensitive", "boolean", "Case-insensitive matching (default false)", required=False),
        ToolParam("context", "integer", "Context lines before/after each match (default 2)", required=False),
    ),
    handler=execute,
)
