"""Unit tests for src/tools — registry, schema generation, and execution."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from src.tools import ToolDef, ToolParam, ToolRegistry, ToolResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _echo_handler(text: str) -> str:
    return text


async def _fail_handler() -> str:
    raise RuntimeError("boom")


_ECHO_TOOL = ToolDef(
    name="Echo",
    description="Echo back input.",
    params=(ToolParam("text", "string", "Text to echo"),),
    handler=_echo_handler,
)

_FAIL_TOOL = ToolDef(
    name="Fail",
    description="Always fails.",
    params=(),
    handler=_fail_handler,
)

_OPTIONAL_TOOL = ToolDef(
    name="Opt",
    description="Tool with optional params.",
    params=(
        ToolParam("required_field", "string", "A required field"),
        ToolParam("optional_field", "number", "An optional field", required=False),
    ),
    handler=_echo_handler,
)


# ---------------------------------------------------------------------------
# ToolParam / ToolDef / ToolResult
# ---------------------------------------------------------------------------

class TestDataclasses(unittest.TestCase):
    def test_tool_param_frozen(self):
        p = ToolParam(name="x", type="string")
        with self.assertRaises(AttributeError):
            p.name = "y"  # type: ignore[misc]

    def test_tool_def_frozen(self):
        with self.assertRaises(AttributeError):
            _ECHO_TOOL.name = "Renamed"  # type: ignore[misc]

    def test_tool_result_defaults(self):
        r = ToolResult(output="ok")
        self.assertFalse(r.is_error)

    def test_tool_result_error(self):
        r = ToolResult(output="fail", is_error=True)
        self.assertTrue(r.is_error)


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------

class TestToolRegistry(unittest.TestCase):

    def setUp(self):
        self.reg = ToolRegistry()

    def test_register_and_get(self):
        self.reg.register(_ECHO_TOOL)
        self.assertIs(self.reg.get("Echo"), _ECHO_TOOL)

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.reg.get("NoSuchTool"))

    def test_list_names(self):
        self.reg.register(_ECHO_TOOL)
        self.reg.register(_FAIL_TOOL)
        names = self.reg.list_names()
        self.assertIn("Echo", names)
        self.assertIn("Fail", names)
        self.assertEqual(len(names), 2)

    def test_register_overwrites(self):
        self.reg.register(_ECHO_TOOL)
        new_tool = ToolDef(
            name="Echo",
            description="New desc",
            params=(),
            handler=_echo_handler,
        )
        self.reg.register(new_tool)
        self.assertEqual(self.reg.get("Echo").description, "New desc")


# ---------------------------------------------------------------------------
# make_schema
# ---------------------------------------------------------------------------

class TestMakeSchema(unittest.TestCase):

    def setUp(self):
        self.reg = ToolRegistry()
        self.reg.register(_ECHO_TOOL)

    def test_schema_structure(self):
        schema = self.reg.make_schema()
        self.assertEqual(len(schema), 1)
        tool = schema[0]
        self.assertEqual(tool["name"], "Echo")
        self.assertEqual(tool["description"], "Echo back input.")
        self.assertIn("input_schema", tool)

    def test_schema_preserves_string_type(self):
        schema = self.reg.make_schema()
        props = schema[0]["input_schema"]["properties"]
        self.assertEqual(props["text"]["type"], "string")

    def test_schema_preserves_number_type(self):
        self.reg.register(_OPTIONAL_TOOL)
        schema = self.reg.make_schema()
        # Find the Opt tool
        opt_schema = next(s for s in schema if s["name"] == "Opt")
        props = opt_schema["input_schema"]["properties"]
        self.assertEqual(props["optional_field"]["type"], "number")

    def test_required_fields(self):
        self.reg.register(_OPTIONAL_TOOL)
        schema = self.reg.make_schema()
        opt_schema = next(s for s in schema if s["name"] == "Opt")
        required = opt_schema["input_schema"]["required"]
        self.assertIn("required_field", required)
        self.assertNotIn("optional_field", required)

    def test_empty_registry(self):
        empty = ToolRegistry()
        self.assertEqual(empty.make_schema(), [])

    def test_schema_object_type(self):
        schema = self.reg.make_schema()
        input_schema = schema[0]["input_schema"]
        self.assertEqual(input_schema["type"], "object")


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

class TestToolRun(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.reg = ToolRegistry()
        self.reg.register(_ECHO_TOOL)
        self.reg.register(_FAIL_TOOL)

    async def test_run_success(self):
        result = await self.reg.run("Echo", {"text": "hello"})
        self.assertEqual(result.output, "hello")
        self.assertFalse(result.is_error)

    async def test_run_unknown_tool(self):
        result = await self.reg.run("NoSuchTool", {})
        self.assertTrue(result.is_error)
        self.assertIn("unknown tool", result.output)

    async def test_run_handler_exception(self):
        result = await self.reg.run("Fail", {})
        self.assertTrue(result.is_error)
        self.assertIn("boom", result.output)


# ---------------------------------------------------------------------------
# bash.py — shell detection (mocked)
# ---------------------------------------------------------------------------

class TestBashShellDetection(unittest.TestCase):

    def setUp(self):
        # Force cache clear before each test
        import src.tools.bash as bash_mod
        bash_mod._SHELL_CACHE = None

    def tearDown(self):
        import src.tools.bash as bash_mod
        bash_mod._SHELL_CACHE = None

    def test_linux_returns_bash(self):
        import src.tools.bash as bash_mod
        with patch("src.tools.bash.sys.platform", "linux"):
            shell = bash_mod._detect_shell()
        self.assertEqual(shell, ["/bin/bash", "-c"])

    def test_windows_git_bash(self):
        import src.tools.bash as bash_mod
        with patch("src.tools.bash.sys.platform", "win32"), \
             patch("src.tools.bash.shutil.which", return_value="C:\\Git\\bin\\bash.exe"):
            shell = bash_mod._detect_shell()
        self.assertEqual(shell[0], "C:\\Git\\bin\\bash.exe")
        self.assertIn("--norc", shell)
        self.assertIn("--noprofile", shell)

    def test_windows_cmd_fallback(self):
        import src.tools.bash as bash_mod
        with patch("src.tools.bash.sys.platform", "win32"), \
             patch("src.tools.bash.shutil.which", return_value=None), \
             patch.dict("src.tools.bash.os.environ", {"COMSPEC": "C:\\Windows\\cmd.exe"}, clear=False):
            shell = bash_mod._detect_shell()
        self.assertEqual(shell, ["C:\\Windows\\cmd.exe", "/c"])

    def test_windows_no_comspec(self):
        import src.tools.bash as bash_mod
        with patch("src.tools.bash.sys.platform", "win32"), \
             patch("src.tools.bash.shutil.which", return_value=None), \
             patch.dict("src.tools.bash.os.environ", {}, clear=True):
            shell = bash_mod._detect_shell()
        self.assertEqual(shell, ["cmd.exe", "/c"])


# ---------------------------------------------------------------------------
# bash.py — execute (mocked subprocess)
# ---------------------------------------------------------------------------

class TestBashExecute(unittest.IsolatedAsyncioTestCase):

    @patch("src.tools.bash._detect_shell", return_value=["/bin/bash", "-c"])
    async def test_execute_normal(self, mock_shell):
        import src.tools.bash as bash_mod
        mock_proc = unittest.mock.AsyncMock()
        mock_proc.communicate.return_value = (b"hello\n", b"")
        with patch("src.tools.bash.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await bash_mod.execute("echo hello")
        self.assertEqual(result, "hello")

    @patch("src.tools.bash._detect_shell", return_value=["/bin/bash", "-c"])
    async def test_execute_empty_output(self, mock_shell):
        import src.tools.bash as bash_mod
        mock_proc = unittest.mock.AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        with patch("src.tools.bash.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await bash_mod.execute("true")
        self.assertEqual(result, "(empty)")

    @patch("src.tools.bash._detect_shell", return_value=["/bin/bash", "-c"])
    async def test_execute_timeout(self, mock_shell):
        import src.tools.bash as bash_mod
        mock_proc = unittest.mock.Mock()
        mock_proc.wait = unittest.mock.AsyncMock()
        # Patch wait_for to raise TimeoutError — avoids calling proc.communicate at all
        async def fake_wait_for(coro, timeout):
            raise asyncio.TimeoutError()
        with patch("src.tools.bash.asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch("src.tools.bash.asyncio.wait_for", side_effect=fake_wait_for):
            result = await bash_mod.execute("sleep 999", timeout=1)
        self.assertIn("timed out", result)
        mock_proc.kill.assert_called_once()
        mock_proc.wait.assert_called_once()


if __name__ == "__main__":
    unittest.main()
