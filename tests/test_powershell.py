"""Unit tests for src/tools/powershell.py — pwsh detection and execution."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from src.tools.powershell import (
    _detect_pwsh,
    execute,
    get_pwsh_info,
    powershell_tool,
    pwsh_available,
)


# ---------------------------------------------------------------------------
# pwsh detection
# ---------------------------------------------------------------------------


class TestPwshDetection(unittest.TestCase):

    def setUp(self):
        import src.tools.powershell as pwsh_mod
        pwsh_mod._PWSH_CACHE = False

    def tearDown(self):
        import src.tools.powershell as pwsh_mod
        pwsh_mod._PWSH_CACHE = False

    @patch("src.tools.powershell.shutil.which", return_value="/usr/bin/pwsh")
    def test_pwsh_found(self, mock_which):
        self.assertEqual(_detect_pwsh(), ["/usr/bin/pwsh", "-NoProfile", "-Command"])

    @patch("src.tools.powershell.shutil.which", return_value="C:\\Program Files\\PowerShell\\7\\pwsh.exe")
    def test_pwsh_found_windows(self, mock_which):
        result = _detect_pwsh()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "C:\\Program Files\\PowerShell\\7\\pwsh.exe")
        self.assertIn("-NoProfile", result)

    @patch("src.tools.powershell.shutil.which", return_value=None)
    def test_pwsh_not_found(self, mock_which):
        self.assertIsNone(_detect_pwsh())

    @patch("src.tools.powershell.shutil.which", return_value="/usr/bin/pwsh")
    def test_pwsh_available_true(self, mock_which):
        self.assertTrue(pwsh_available())

    @patch("src.tools.powershell.shutil.which", return_value=None)
    def test_pwsh_available_false(self, mock_which):
        self.assertFalse(pwsh_available())

    @patch("src.tools.powershell.shutil.which", return_value="/usr/bin/pwsh")
    def test_get_pwsh_info_found(self, mock_which):
        info = get_pwsh_info()
        self.assertIn("pwsh", info)
        self.assertIn("/usr/bin/pwsh", info)

    @patch("src.tools.powershell.shutil.which", return_value=None)
    def test_get_pwsh_info_not_found(self, mock_which):
        info = get_pwsh_info()
        self.assertIn("not found", info)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


class TestPowerShellExecute(unittest.IsolatedAsyncioTestCase):

    @patch("src.tools.powershell._detect_pwsh", return_value=["/usr/bin/pwsh", "-NoProfile", "-Command"])
    async def test_execute_normal(self, mock_pwsh):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"Hello from PowerShell\n", b"")
        with patch("src.tools.powershell.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await execute("Write-Output 'Hello from PowerShell'")
        self.assertEqual(result, "Hello from PowerShell")

    @patch("src.tools.powershell._detect_pwsh", return_value=["/usr/bin/pwsh", "-NoProfile", "-Command"])
    async def test_execute_empty_output(self, mock_pwsh):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        with patch("src.tools.powershell.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await execute("$null")
        self.assertEqual(result, "(empty)")

    @patch("src.tools.powershell._detect_pwsh", return_value=["/usr/bin/pwsh", "-NoProfile", "-Command"])
    async def test_execute_timeout(self, mock_pwsh):
        mock_proc = unittest.mock.Mock()
        mock_proc.wait = AsyncMock()

        async def fake_wait_for(coro, timeout):
            raise asyncio.TimeoutError()

        with patch("src.tools.powershell.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch("src.tools.powershell.asyncio.wait_for", side_effect=fake_wait_for):
            result = await execute("Start-Sleep -Seconds 999", timeout=1)
        self.assertIn("timed out", result)
        mock_proc.kill.assert_called_once()
        mock_proc.wait.assert_called_once()

    @patch("src.tools.powershell._detect_pwsh", return_value=None)
    async def test_execute_no_pwsh(self, mock_pwsh):
        result = await execute("Get-Process")
        self.assertIn("error", result)
        self.assertIn("not installed", result)


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------


class TestPowerShellToolDef(unittest.TestCase):

    def test_tool_name(self):
        self.assertEqual(powershell_tool.name, "PowerShell")

    def test_tool_params(self):
        names = [p.name for p in powershell_tool.params]
        self.assertIn("command", names)
        self.assertIn("timeout", names)

    def test_command_required(self):
        cmd_param = next(p for p in powershell_tool.params if p.name == "command")
        self.assertTrue(cmd_param.required)

    def test_timeout_optional(self):
        timeout_param = next(p for p in powershell_tool.params if p.name == "timeout")
        self.assertFalse(timeout_param.required)


if __name__ == "__main__":
    unittest.main()
