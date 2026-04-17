"""Bash tool — execute shell commands on Unix-like systems.

This tool is designed for Linux, macOS, and WSL environments.
On native Windows, use the PowerShell tool instead.

Detection:
  - Linux / macOS / WSL:  /bin/bash -c
  - Windows (native):     None (bash not available natively)
"""

from __future__ import annotations

import asyncio
import sys

from . import ToolDef, ToolParam

# ---------------------------------------------------------------------------
# Shell detection (cached after first call)
# ---------------------------------------------------------------------------

_SHELL_CACHE: list[str] | None = False  # False = not yet detected


def _detect_shell() -> list[str] | None:
    """Return the shell command prefix, e.g. ``['/bin/bash', '-c']``.

    Returns None on Windows (use PowerShell tool instead).
    """
    global _SHELL_CACHE
    if _SHELL_CACHE is not False:
        return _SHELL_CACHE

    if sys.platform == "win32":
        _SHELL_CACHE = None
        return None

    _SHELL_CACHE = ["/bin/bash", "-c"]
    return _SHELL_CACHE


def bash_available() -> bool:
    """True when bash is available on the system."""
    return _detect_shell() is not None


def get_shell_info() -> str:
    """Human-readable shell info for diagnostics."""
    shell = _detect_shell()
    if shell is None:
        return "[bash] not available (Windows native — use PowerShell)"
    return f"[bash] {' '.join(shell)}"


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


async def execute(command: str, timeout: int = 120) -> str:
    """Execute a shell command and return its stdout+stderr output.

    Args:
        command: Shell command string.
        timeout: Max seconds to wait (default 120).

    Returns:
        Combined stdout+stderr as a string.
    """
    shell_cmd = _detect_shell()
    if shell_cmd is None:
        return "error: bash is not available on this platform (use PowerShell)"

    full_cmd = shell_cmd + [command]

    proc = await asyncio.create_subprocess_exec(
        *full_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return f"(timed out after {timeout}s)"

    output = stdout.decode("utf-8", errors="replace").strip()
    return output or "(empty)"


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

bash_tool = ToolDef(
    name="Bash",
    description="Execute a shell command and return its output.",
    params=(
        ToolParam("command", "string", "The shell command to execute"),
        ToolParam(
            "timeout",
            "number",
            "Timeout in seconds (default 120)",
            required=False,
        ),
    ),
    handler=execute,
)
