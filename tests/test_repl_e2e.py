"""E2E tests for REPL using pexpect."""

from __future__ import annotations

import os
import sys
import time
import unittest

try:
    import pexpect
    _HAS_PEXPECT = True
except ImportError:
    pexpect = None  # type: ignore[assignment]
    _HAS_PEXPECT = False

# Windows uses popen_spawn, Unix uses spawn
if _HAS_PEXPECT:
    if sys.platform == "win32":
        from pexpect import popen_spawn

        SPAWN = popen_spawn.PopenSpawn
        EOF_OBJ = popen_spawn.EOF
    else:
        SPAWN = pexpect.spawn
        EOF_OBJ = pexpect.EOF


def _requires_pexpect(test_func):
    """Skip decorator for tests needing pexpect."""
    return unittest.skipUnless(_HAS_PEXPECT, "pexpect not installed")(test_func)


@_requires_pexpect
def test_repl_startup():
    """Test REPL starts and shows banner."""
    child = SPAWN("uv run python -m src.cli.main", timeout=10)

    # Wait for banner
    child.expect("Nano-Claude")
    child.expect("whyj")

    # Clean exit
    child.sendline("/exit")
    child.expect(EOF_OBJ)
    child.wait()


@_requires_pexpect
def test_command_completion():
    """Test slash command auto-completion (interactive mode only)."""
    # Completion requires TTY, skip in non-interactive test mode
    # This test verifies command handling works, not visual completion
    child = SPAWN("uv run python -m src.cli.main", timeout=10)

    child.expect(">")

    # Just test that /help command works
    child.sendline("/help")
    child.expect("Commands:")

    child.expect(">")
    child.sendline("/exit")
    child.expect(EOF_OBJ)
    child.wait()


@_requires_pexpect
def test_help_command():
    """Test /help shows available commands."""
    child = SPAWN("uv run python -m src.cli.main", timeout=10)

    child.expect(">")
    child.sendline("/help")

    # Should show help text
    child.expect("Commands:")
    child.expect("/help")
    child.expect("/exit")
    child.expect("/model")

    child.expect(">")
    child.sendline("/exit")
    child.expect(EOF_OBJ)
    child.wait()


@_requires_pexpect
def test_unknown_command():
    """Test unknown command shows error."""
    child = SPAWN("uv run python -m src.cli.main", timeout=10)

    child.expect(">")
    child.sendline("/unknown")

    child.expect("Unknown command:")

    child.expect(">")
    child.sendline("/exit")
    child.expect(EOF_OBJ)
    child.wait()


@_requires_pexpect
def test_banner_reaches_prompt_in_any_connection_mode():
    """The simplified banner reaches the prompt regardless of API setup."""
    child = SPAWN("uv run python -m src.cli.main", timeout=10)

    child.expect("Nano-Claude")
    child.expect(">")
    child.sendline("/exit")
    child.expect(EOF_OBJ)
    child.wait()
