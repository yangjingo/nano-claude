"""Write tool — create or overwrite a file with the given content."""

from __future__ import annotations

import os

from . import ToolDef, ToolParam


async def execute(file_path: str, content: str) -> str:
    """Write content to a file, creating parent directories as needed.

    Args:
        file_path: Absolute or relative path to the file.
        content: The text content to write.

    Returns:
        Confirmation message with line count.
    """
    try:
        parent = os.path.dirname(file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        return f"error: {e}"

    line_count = content.count("\n") + (0 if content.endswith("\n") else 1)
    return f"wrote {line_count} lines to {file_path}"


write_tool = ToolDef(
    name="Write",
    description="Create or overwrite a file with the given content. Creates parent directories automatically.",
    params=(
        ToolParam("file_path", "string", "Absolute or relative path to the file"),
        ToolParam("content", "string", "The text content to write"),
    ),
    handler=execute,
)
