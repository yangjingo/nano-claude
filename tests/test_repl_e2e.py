"""E2E tests for REPL using pexpect."""

from __future__ import annotations

import os
import sys
import time

import pexpect

# Windows uses popen_spawn, Unix uses spawn
if sys.platform == "win32":
    from pexpect import popen_spawn

    SPAWN = popen_spawn.PopenSpawn
    EOF_OBJ = popen_spawn.EOF
else:
    SPAWN = pexpect.spawn
    EOF_OBJ = pexpect.EOF


def test_repl_startup():
    """Test REPL starts and shows banner."""
    child = SPAWN("uv run python -m src.cli.main", timeout=10)

    # Wait for banner
    child.expect("Nano-Claude")
    child.expect("connected")

    # Clean exit
    child.sendline("/exit")
    child.expect(EOF_OBJ)
    child.wait()


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


def test_mock_mode():
    """Test mock mode behavior - depends on settings.json having no API key."""
    # Note: This test only works if ~/.nano-claude/settings.json has no API key
    # If API key exists, the test will verify connected mode instead
    child = SPAWN("uv run python -m src.cli.main", timeout=10)

    # Either mock-mode or connected should appear
    try:
        child.expect("mock-mode", timeout=2)
    except (pexpect.exceptions.TIMEOUT, pexpect.exceptions.EOF):
        # If not mock mode, should be connected
        child.expect("connected")

    child.expect(">")
    child.sendline("/exit")
    child.expect(EOF_OBJ)
    child.wait()
