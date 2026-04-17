"""Tool framework for nano-claude.

Minimal tool registry inspired by nanocode's TOOLS dict pattern:
  (description, schema, handler) → auto-generates API schema.

Reference: https://github.com/1rgs/nanocode/blob/master/nanocode.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Callable, Coroutine

ToolFunc = Callable[..., Coroutine[Any, Any, str]]


@dataclass(frozen=True)
class ToolParam:
    """A single parameter in a tool's input schema."""

    name: str
    type: str  # "string", "integer", "boolean", "number"
    description: str = ""
    required: bool = True


@dataclass(frozen=True)
class ToolDef:
    """Tool definition: name, description, parameter schema, and async handler."""

    name: str
    description: str
    params: tuple[ToolParam, ...]
    handler: ToolFunc


@dataclass(frozen=True)
class ToolResult:
    """Result from executing a tool."""

    output: str
    is_error: bool = False


class ToolRegistry:
    """Tool registry. Register tools, generate API schemas, execute by name.

    Usage::

        registry = ToolRegistry(security=my_security_gate)
        registry.register(bash_tool)

        # For the Anthropic API
        tools_schema = registry.make_schema()

        # Execute a tool
        result = await registry.run("Bash", {"command": "ls"})
    """

    def __init__(self, security: Any = None) -> None:
        self._tools: dict[str, ToolDef] = {}
        self._security = security

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def set_security(self, security: Any) -> None:
        self._security = security

    def make_schema(self) -> list[dict[str, Any]]:
        """Generate tool definitions for the Anthropic Messages API.

        Each tool becomes a dict with name, description, input_schema —
        ready to pass as the ``tools`` parameter.
        """
        result: list[dict[str, Any]] = []
        for tool in self._tools.values():
            properties: dict[str, Any] = {}
            required: list[str] = []
            for p in tool.params:
                prop: dict[str, Any] = {
                    "type": p.type,
                }
                if p.description:
                    prop["description"] = p.description
                properties[p.name] = prop
                if p.required:
                    required.append(p.name)
            result.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                }
            )
        return result

    async def run(self, name: str, args: dict[str, Any]) -> ToolResult:
        """Execute a tool by name. Returns ToolResult with output or error."""
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                output=f"error: unknown tool '{name}'", is_error=True
            )

        # Security check before execution
        warning = ""
        if self._security is not None:
            decision = await self._security.check(name, args)
            if not decision.allowed:
                return ToolResult(
                    output=f"security: {decision.reason}",
                    is_error=True,
                )
            warning = decision.warning

        try:
            output = await tool.handler(**args)
            if warning:
                output = f"{warning}\n{output}"
            return ToolResult(output=output)
        except Exception as err:
            return ToolResult(output=f"error: {err}", is_error=True)


def default_registry(security: Any = None) -> ToolRegistry:
    """Create a registry pre-loaded with built-in tools for the current platform.

    Platform auto-select:
      - Linux / macOS / WSL:  Bash + 5 file tools
      - Windows + pwsh:        PowerShell + 5 file tools
      - Windows, no pwsh:      Bash (fallback) + 5 file tools

    Args:
        security: Optional SecurityGate instance for command/file safety.
    """
    from .bash import bash_tool
    from .edit import edit_tool
    from .glob_tool import glob_tool
    from .grep_tool import grep_tool
    from .read import read_tool
    from .write import write_tool

    registry = ToolRegistry(security=security)

    # File tools (always available on all platforms)
    for tool in (read_tool, write_tool, edit_tool, glob_tool, grep_tool):
        registry.register(tool)

    # Shell tool: platform auto-select
    if sys.platform == "win32":
        from .powershell import powershell_tool, pwsh_available
        if pwsh_available():
            registry.register(powershell_tool)
        else:
            registry.register(bash_tool)
    else:
        registry.register(bash_tool)

    return registry
