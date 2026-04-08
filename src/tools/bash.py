"""Bash tool — execute shell commands with cross-platform support.

Platform detection order:
  1. Unix: /bin/bash
  2. Windows + Git Bash: $(which bash) --norc --noprofile -c
  3. Windows fallback: %COMSPEC% /c  (cmd.exe)
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys

from . import ToolDef, ToolParam

# ---------------------------------------------------------------------------
# Shell detection (cached after first call)
# ---------------------------------------------------------------------------

_SHELL_CACHE: list[str] | None = None


def _detect_shell() -> list[str]:
    """Return the shell command prefix, e.g. ['/bin/bash', '-c']."""
    global _SHELL_CACHE
    if _SHELL_CACHE is not None:
        return _SHELL_CACHE

    if sys.platform != "win32":
        _SHELL_CACHE = ["/bin/bash", "-c"]
        return _SHELL_CACHE

    # Windows — try Git Bash first, then cmd.exe
    git_bash = shutil.which("bash")
    if git_bash:
        # --norc --noprofile for clean, predictable environment
        _SHELL_CACHE = [git_bash, "--norc", "--noprofile", "-c"]
    else:
        _SHELL_CACHE = [os.environ.get("COMSPEC", "cmd.exe"), "/c"]

    return _SHELL_CACHE


def get_shell_info() -> str:
    """Human-readable shell info for diagnostics."""
    shell = _detect_shell()
    return " ".join(shell)


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
