"""PowerShell tool — execute commands using pwsh (PowerShell 7+).

Uses pwsh exclusively (cross-platform PowerShell Core).
Detection order:
  1. pwsh via shutil.which() → pwsh -NoProfile -Command
  2. Not found → tool returns error
"""

from __future__ import annotations

import asyncio
import shutil

from . import ToolDef, ToolParam

# ---------------------------------------------------------------------------
# pwsh detection (cached after first call)
# ---------------------------------------------------------------------------

_PWSH_CACHE: list[str] | None = False  # False = not yet detected


def _detect_pwsh() -> list[str] | None:
    """Return the pwsh command prefix, e.g. ``['/usr/bin/pwsh', '-NoProfile', '-Command']``."""
    global _PWSH_CACHE
    if _PWSH_CACHE is not False:
        return _PWSH_CACHE

    pwsh_path = shutil.which("pwsh")
    if pwsh_path:
        _PWSH_CACHE = [pwsh_path, "-NoProfile", "-Command"]
        return _PWSH_CACHE

    _PWSH_CACHE = None
    return None


def pwsh_available() -> bool:
    """True when pwsh (PowerShell 7+) is available on the system."""
    return _detect_pwsh() is not None


def get_pwsh_info() -> str:
    """Human-readable pwsh info for diagnostics."""
    cmd = _detect_pwsh()
    if cmd is None:
        return "[pwsh] not found"
    return f"[pwsh] {' '.join(cmd)}"


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


async def execute(command: str, timeout: int = 120) -> str:
    """Execute a PowerShell command and return its stdout+stderr output.

    Args:
        command: PowerShell command string.
        timeout: Max seconds to wait (default 120).

    Returns:
        Combined stdout+stderr as a string.
    """
    pwsh_cmd = _detect_pwsh()
    if pwsh_cmd is None:
        return "error: pwsh (PowerShell 7+) is not installed"

    full_cmd = pwsh_cmd + [command]

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

powershell_tool = ToolDef(
    name="PowerShell",
    description="Execute a PowerShell command using pwsh (PowerShell 7+) and return its output.",
    params=(
        ToolParam("command", "string", "The PowerShell command to execute"),
        ToolParam(
            "timeout",
            "number",
            "Timeout in seconds (default 120)",
            required=False,
        ),
    ),
    handler=execute,
)
