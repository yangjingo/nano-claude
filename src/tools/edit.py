"""Edit tool — exact string replacement in files."""

from __future__ import annotations

import os

from . import ToolDef, ToolParam


async def execute(
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> str:
    """Replace exact text in a file.

    Args:
        file_path: Absolute or relative path to the file.
        old_string: The exact text to find.
        new_string: The replacement text.
        replace_all: If true, replace all occurrences; otherwise only the first.

    Returns:
        Confirmation message or error.
    """
    if not os.path.isfile(file_path):
        return f"error: '{file_path}' does not exist"

    if old_string == new_string:
        return "error: old_string and new_string are identical"

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError as e:
        return f"error: {e}"

    count = content.count(old_string)
    if count == 0:
        return "error: old_string not found in file"
    if count > 1 and not replace_all:
        return (
            f"error: old_string matches {count} locations — "
            "use replace_all=true or provide more context to make it unique"
        )

    if replace_all:
        new_content = content.replace(old_string, new_string)
    else:
        new_content = content.replace(old_string, new_string, 1)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except OSError as e:
        return f"error: {e}"

    replaced = count if replace_all else 1
    return f"replaced {replaced} occurrence(s) in {file_path}"


edit_tool = ToolDef(
    name="Edit",
    description="Replace exact text in a file. The old_string must be unique unless replace_all is true.",
    params=(
        ToolParam("file_path", "string", "Absolute or relative path to the file"),
        ToolParam("old_string", "string", "The exact text to find and replace"),
        ToolParam("new_string", "string", "The replacement text"),
        ToolParam("replace_all", "boolean", "Replace all occurrences (default false)", required=False),
    ),
    handler=execute,
)
