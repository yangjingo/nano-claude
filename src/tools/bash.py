"""Bash tool — execute shell commands with cross-platform support.

Platform detection order:
  1. Windows inside WSL:  /bin/bash -c  (native Linux bash)
  2. Windows + WSL available:  wsl bash -c  (delegate to WSL)
  3. Windows + Git Bash:  <git-bash-path> --norc --noprofile -c
  4. Windows fallback:  %COMSPEC% /c  (cmd.exe)
  5. macOS / Linux:  /bin/bash -c
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys

from . import ToolDef, ToolParam

# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------

def _is_wsl() -> bool:
    """True when Python is running inside Windows Subsystem for Linux."""
    return "microsoft" in os.uname().release.lower() if hasattr(os, "uname") else False


def _wsl_available() -> bool:
    """True when the host is Windows AND `wsl` command is reachable."""
    if sys.platform != "win32":
        return False
    return shutil.which("wsl") is not None


def _git_bash_path() -> str | None:
    """Return Git Bash executable path on Windows, or None."""
    if sys.platform != "win32":
        return None
    # `which bash` on Windows usually resolves to Git Bash
    return shutil.which("bash")


# ---------------------------------------------------------------------------
# Shell detection (cached after first call)
# ---------------------------------------------------------------------------

_SHELL_CACHE: list[str] | None = None


def _detect_shell() -> list[str]:
    """Return the shell command prefix, e.g. ``['/bin/bash', '-c']``."""
    global _SHELL_CACHE
    if _SHELL_CACHE is not None:
        return _SHELL_CACHE

    # --- macOS / Linux / WSL-inside-Linux ---
    if sys.platform != "win32":
        _SHELL_CACHE = ["/bin/bash", "-c"]
        return _SHELL_CACHE

    # --- Windows host ---

    # 1. Prefer WSL if available
    if _wsl_available():
        _SHELL_CACHE = ["wsl", "bash", "-c"]
        return _SHELL_CACHE

    # 2. Git Bash
    git_bash = _git_bash_path()
    if git_bash:
        _SHELL_CACHE = [git_bash, "--norc", "--noprofile", "-c"]
        return _SHELL_CACHE

    # 3. cmd.exe fallback
    _SHELL_CACHE = [os.environ.get("COMSPEC", "cmd.exe"), "/c"]
    return _SHELL_CACHE


def get_shell_info() -> str:
    """Human-readable shell info for diagnostics."""
    shell = _detect_shell()
    tag = (
        "wsl" if shell[0] == "wsl"
        else "git-bash" if "bash" in shell[0].lower() and sys.platform == "win32"
        else "cmd" if shell[0].endswith("cmd.exe")
        else "native"
    )
    return f"[{tag}] {' '.join(shell)}"


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
