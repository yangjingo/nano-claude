"""Agentic turn tests for streamed timing and multi-call usage."""

import asyncio
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch

from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from src.agent.agent import AgentSession, ToolInvocation
from src.cli.hud import HudState
from src.cli.repl import (
    CHOICE_STYLE,
    PT_STYLE,
    _create_prompt_session,
    _display_agent_message,
    _display_thinking,
    _display_tool_invocation,
    _print_banner,
)
from src.cli.tui import CodexBottomPane
from src.cli.theme import BRAND_ACCENT, BRAND_PRIMARY, TEXT_MUTED, TEXT_SUBTLE
from src.tools import ToolResult


class _FakeStream:
    def __init__(self, response):
        self.response = response
        self._events = iter(
            [
                SimpleNamespace(
                    type="content_block_delta",
                    delta=SimpleNamespace(
                        type="thinking_delta",
                        thinking="live thought",
                    ),
                )
            ]
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._events)
        except StopIteration as exc:
            raise StopAsyncIteration from exc

    async def get_final_message(self):
        return self.response


class _FakeMessages:
    def __init__(self, responses):
        self.responses = iter(responses)

    def stream(self, **kwargs):
        return _FakeStream(next(self.responses))


class _FakeClient:
    def __init__(self, responses):
        self.messages = _FakeMessages(responses)


class _RecordingOutput(DummyOutput):
    def __init__(self):
        self.entered_alternate_screen = False
        self.erased_screen = False
        self.erased_down = False
        self.events = []

    def write_raw(self, data):
        self.events.append(("raw", data))

    def enter_alternate_screen(self):
        self.entered_alternate_screen = True

    def erase_screen(self):
        self.erased_screen = True

    def erase_down(self):
        self.erased_down = True
        self.events.append(("erase_down", None))


class AgentStreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_turn_streams_every_model_call_and_aggregates_usage(self):
        tool_block = SimpleNamespace(
            type="tool_use", id="tool-1", name="Read", input={"path": "README.md"}
        )
        first_thinking = SimpleNamespace(type="thinking", thinking="planning")
        final_thinking = SimpleNamespace(
            type="thinking", thinking="answer reasoning"
        )
        text_block = SimpleNamespace(type="text", text="done")
        responses = [
            SimpleNamespace(
                content=[first_thinking, tool_block],
                usage=SimpleNamespace(input_tokens=10, output_tokens=4),
            ),
            SimpleNamespace(
                content=[final_thinking, text_block],
                usage=SimpleNamespace(input_tokens=20, output_tokens=6),
            ),
        ]
        session = AgentSession()
        session.client = _FakeClient(responses)

        async def run_tool(name, args):
            return ToolResult("contents")

        streamed_chunks = []
        with (
            patch.object(session, "save", return_value=None),
            patch.object(session, "_capture_turn_signals"),
        ):
            turn = await session.run_turn(
                "inspect",
                tools=[{"name": "Read"}],
                tool_runner=run_tool,
                on_stream=streamed_chunks.append,
            )

        self.assertEqual(turn.text, "done")
        self.assertEqual(turn.thinking, "planning\n\nanswer reasoning")
        self.assertEqual(turn.context_tokens, 20)
        self.assertEqual(turn.usage, {"input_tokens": 30, "output_tokens": 10})
        self.assertEqual(session._token_usage, {"input": 30, "output": 10})
        self.assertEqual(len(turn.tool_invocations), 1)
        self.assertIsNotNone(turn.performance)
        self.assertEqual(len(turn.performance.requests), 2)
        self.assertEqual(
            [chunk.content for chunk in streamed_chunks],
            ["live thought", "live thought"],
        )
        self.assertTrue(
            all(
                timing.ttft_seconds >= 0
                for timing in turn.performance.requests
            )
        )


class TraceRenderingTests(unittest.TestCase):
    def test_banner_shows_version_and_author_without_hud_metadata(self):
        with (
            patch("src.cli.repl.Status"),
            patch("src.cli.repl.time.sleep"),
            patch("src.cli.repl.get_api_key", return_value="test-key"),
            patch("src.cli.repl.distribution_version", return_value="0.1.0"),
            patch("src.cli.repl.console.print") as print_mock,
        ):
            _print_banner()

        banner = print_mock.call_args_list[0].args[0].plain
        self.assertIn("Nano-Claude (v0.1.0 - whyj)", banner)
        self.assertNotIn("作者", banner)
        self.assertNotIn("Only for Learning", banner)
        self.assertNotIn("connected", banner)
        self.assertNotIn("MiniMax", banner)

    def test_bottom_hud_uses_terminal_background(self):
        attrs = PT_STYLE.get_attrs_for_style_str("class:bottom-toolbar")
        model_attrs = PT_STYLE.get_attrs_for_style_str("class:hud.model")
        metric_attrs = PT_STYLE.get_attrs_for_style_str("class:hud.metric")
        label_attrs = PT_STYLE.get_attrs_for_style_str("class:hud.label")

        self.assertFalse(attrs.reverse)
        self.assertEqual(attrs.bgcolor, "default")
        self.assertFalse(model_attrs.bold)
        self.assertEqual(model_attrs.bgcolor, "")
        self.assertEqual(model_attrs.color, BRAND_PRIMARY.removeprefix("#"))
        self.assertEqual(metric_attrs.color, BRAND_ACCENT.removeprefix("#"))
        self.assertEqual(label_attrs.color, TEXT_SUBTLE.removeprefix("#"))

    def test_interactive_menus_share_the_native_background(self):
        prompt_classes = (
            "class:completion-menu",
            "class:completion-menu.completion",
            "class:completion-menu.completion.selected",
            "class:completion-menu.meta",
        )
        choice_classes = (
            "class:choice",
            "class:choice.selected",
            "class:choice.unselected",
            "class:frame",
        )

        for style_class in prompt_classes:
            attrs = PT_STYLE.get_attrs_for_style_str(style_class)
            self.assertEqual(attrs.bgcolor, "default")
            self.assertFalse(attrs.reverse)
        for style_class in choice_classes:
            attrs = CHOICE_STYLE.get_attrs_for_style_str(style_class)
            self.assertEqual(attrs.bgcolor, "default")
            self.assertFalse(attrs.reverse)

    def test_prompt_preserves_native_scrollback(self):
        hud = HudState(model_name=lambda: "test-model")
        with (
            patch("src.cli.repl.sys.stdin.isatty", return_value=True),
            patch("src.cli.repl.PromptSession") as prompt_session,
        ):
            _create_prompt_session(hud)

        self.assertFalse(prompt_session.call_args.kwargs["erase_when_done"])
        self.assertNotIn("refresh_interval", prompt_session.call_args.kwargs)
        self.assertFalse(prompt_session.call_args.kwargs["full_screen"])
        self.assertFalse(prompt_session.call_args.kwargs["wrap_lines"])

    def test_live_view_contains_streamed_thinking_and_background_free_hud(self):
        hud = HudState(model_name=lambda: "test-model")
        with patch("src.cli.tui.Application") as application:
            status = CodexBottomPane(hud=hud, style=PT_STYLE)
            status.running = True
            status._turn_started_at = 1.0
            status.handle_stream(
                SimpleNamespace(type="thinking", content="step one")
            )
            rendered = status.snapshot_text()

        self.assertIn("Working", rendered)
        self.assertIn("step one", rendered)
        self.assertIn("TTFT --", rendered)
        self.assertIn("Context -- left", rendered)
        self.assertNotIn("on #", repr(hud.rich_text()))
        self.assertFalse(application.call_args.kwargs["full_screen"])
        self.assertFalse(application.call_args.kwargs["erase_when_done"])

        status.finish_turn()
        finished = status.snapshot_text()
        self.assertNotIn("Working", finished)
        self.assertIn("› Ask nano-claude", finished)
        self.assertIn("TTFT --", finished)

    def test_bottom_pane_uses_codex_block_spacing(self):
        with patch("src.cli.tui.Application"):
            pane = CodexBottomPane(
                hud=HudState(model_name=lambda: "test-model"),
                style=PT_STYLE,
            )
        pane.running = True
        pane._turn_started_at = time.monotonic()

        lines = pane.snapshot_text().splitlines()

        self.assertIn("Working", lines[0])
        self.assertEqual(lines[1:3], ["", ""])
        self.assertEqual(lines[3], "› Ask nano-claude to do anything")
        self.assertEqual(lines[4], "")

        pane.thinking = "First detail line\nSecond detail line"
        pane._queued_inputs.append("Queued follow-up question")
        lines = pane.snapshot_text().splitlines()

        self.assertEqual(lines[1], "  └ First detail line")
        self.assertEqual(lines[2], "    Second detail line")
        self.assertEqual(lines[3], "")
        self.assertEqual(lines[4], "• Queued follow-up inputs")
        self.assertEqual(lines[6], "")
        self.assertEqual(lines[7], "› Ask nano-claude to do anything")

    def test_thinking_is_dimmed_and_indented(self):
        with patch("src.cli.repl.console.print") as print_mock:
            _display_thinking("consider the options\nthen verify")

        first = print_mock.call_args_list[1].args[0]
        continuation = print_mock.call_args_list[2].args[0]
        self.assertEqual(first.plain, "• consider the options")
        self.assertEqual(continuation.plain, "  then verify")
        self.assertEqual(str(first.style), BRAND_PRIMARY)
        self.assertEqual(str(first.spans[0].style), f"{TEXT_MUTED} italic")
        self.assertEqual(str(continuation.style), f"{TEXT_MUTED} italic")

    def test_final_answer_leaves_one_line_before_composer(self):
        with patch("src.cli.repl.console.print") as print_mock:
            _display_agent_message("Done")

        self.assertEqual(print_mock.call_args_list[1].args[0].plain, "• Done")
        self.assertEqual(print_mock.call_args_list[-1].args, ())

    def test_tool_trace_is_dimmed_without_background(self):
        invocation = ToolInvocation(
            name="Bash",
            args={"command": "git status"},
            result=ToolResult("clean"),
        )
        with patch("src.cli.repl.console.print") as print_mock:
            _display_tool_invocation(invocation)

        header = print_mock.call_args_list[1].args[0]
        output = print_mock.call_args_list[2].args[0]
        self.assertEqual(header.plain, "• Ran git status")
        self.assertEqual(output.plain, "  └ clean")
        self.assertNotIn("bg:", repr(header))
        self.assertEqual(str(output.style), TEXT_MUTED)


class BottomPaneQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_input_submitted_while_running_is_queued_in_same_pane(self):
        with patch("src.cli.tui.Application"):
            pane = CodexBottomPane(
                hud=HudState(model_name=lambda: "test-model"),
                style=PT_STYLE,
            )
        pane.running = True

        pane.submit_text("follow up")

        self.assertIn("Queued follow-up inputs", pane.snapshot_text())
        self.assertEqual(await pane.next_input(), "follow up")
        self.assertNotIn("Queued follow-up inputs", pane.snapshot_text())

    async def test_real_inline_application_submits_without_clear_sequences(self):
        output = _RecordingOutput()
        with create_pipe_input() as input_pipe:
            pane = CodexBottomPane(
                hud=HudState(model_name=lambda: "test-model"),
                style=PT_STYLE,
                input=input_pipe,
                output=output,
            )
            await pane.start()
            input_pipe.send_text("review changes\r")

            submitted = await asyncio.wait_for(pane.next_input(), timeout=1)
            await pane.close()

        self.assertEqual(submitted, "review changes")
        self.assertFalse(output.entered_alternate_screen)
        self.assertFalse(output.erased_screen)
        self.assertTrue(output.erased_down)

        sync_depth = 0
        for event, value in output.events:
            if event == "raw" and value == "\x1b[?2026h":
                sync_depth += 1
            elif event == "raw" and value == "\x1b[?2026l":
                sync_depth -= 1
            elif event == "erase_down":
                self.assertGreater(sync_depth, 0)
        self.assertEqual(sync_depth, 0)


if __name__ == "__main__":
    unittest.main()
