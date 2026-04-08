"""Demo: test Bash tool directly (no API key needed)."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools import ToolRegistry, ToolResult
from src.tools.bash import bash_tool, get_shell_info


async def main():
    registry = ToolRegistry()
    registry.register(bash_tool)

    print("=== Tool System Demo ===")
    print()

    # 1. Registry info
    print("1. Registry")
    print(f"   Tools: {registry.list_names()}")
    schema = registry.make_schema()
    print(f"   Schema count: {len(schema)}")
    print(f"   Schema[0]: {schema[0]['name']} - {schema[0]['description']}")
    params = schema[0]["input_schema"]
    print(f"   Params: {params['properties']}")
    print(f"   Required: {params['required']}")
    print()

    # 2. Shell detection
    print("2. Shell Detection")
    print(f"   Shell: {get_shell_info()}")
    print(f"   Platform: {sys.platform}")
    print()

    # 3. Execute commands
    print("3. Execute Commands")
    commands = [
        ("pwd", {}),
        ("echo hello from nano-claude", {}),
        ("ls -la src/tools/", {}),
        ("python --version", {}),
    ]

    for cmd, extra in commands:
        print(f"   >>> Bash({cmd!r})")
        result = await registry.run("Bash", {"command": cmd, **extra})
        prefix = "ERROR" if result.is_error else "OK"
        for line in result.output.split("\n")[:8]:
            print(f"   [{prefix}] {line}")
        total = len(result.output.split("\n"))
        if total > 8:
            print(f"   ... +{total - 8} more lines")
        print()

    # 4. Error cases
    print("4. Error Cases")
    print("   >>> unknown tool")
    result = await registry.run("NoSuchTool", {})
    print(f"   [{ 'ERROR' if result.is_error else 'OK' }] {result.output}")
    print()

    print("   >>> Bash with bad command (exit 1)")
    result = await registry.run("Bash", {"command": "nonexistent_command_xyz"})
    print(f"   [{'ERROR' if result.is_error else 'OK'}] {result.output[:200]}")
    print()

    # 5. Schema for API
    print("5. Full API Schema (for Anthropic)")
    import json
    print(json.dumps(schema, indent=2))
    print()

    print("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
