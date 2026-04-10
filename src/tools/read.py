"""Read tool — read file contents with line numbers."""

from __future__ import annotations

import os

from . import ToolDef, ToolParam

MAX_LINES = 2000


async def execute(
    file_path: str,
    offset: int = 0,
    limit: int = MAX_LINES,
) -> str:
    """Read a file and return its contents with line numbers.

    Args:
        file_path: Absolute or relative path to the file.
        offset: Line number to start from (0-based).
        limit: Max number of lines to return.

    Returns:
        File content with line-number prefix (``cat -n`` style).
    """
    if not os.path.isfile(file_path):
        return f"error: '{file_path}' is not a file or does not exist"

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        return f"error: {e}"

    # Clamp range
    start = max(0, offset)
    end = min(len(lines), start + limit)
    selected = lines[start:end]

    if not selected:
        return "(empty range)"

    # cat -n format: line_number<tab>content
    numbered = [f"{i + 1}\t{line}" for i, line in zip(range(start, end), selected)]

    # Ensure last line ends with newline
    result = "".join(numbered)
    if selected and not selected[-1].endswith("\n"):
        result += "\n"

    if end < len(lines):
        result += f"\n... {len(lines) - end} more lines not shown"

    return result


read_tool = ToolDef(
    name="Read",
    description="Read a file's contents with line numbers. Supports offset and limit for large files.",
    params=(
        ToolParam("file_path", "string", "Absolute or relative path to the file"),
        ToolParam("offset", "integer", "Line number to start from (0-based)", required=False),
        ToolParam("limit", "integer", f"Max lines to return (default {MAX_LINES})", required=False),
    ),
    handler=execute,
)
