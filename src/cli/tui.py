"""Codex-style persistent inline bottom pane for the terminal REPL."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
import time

from prompt_toolkit.application import Application, in_terminal
from prompt_toolkit.application.current import set_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    Window,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import (
    AfterInput,
    BeforeInput,
    ConditionalProcessor,
)
from prompt_toolkit.input import Input
from prompt_toolkit.output import Output
from prompt_toolkit.styles import BaseStyle

from .hud import HudState


class PlainBottomPane:
    """Line-oriented fallback for redirected stdin/stdout and test runners."""

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    @asynccontextmanager
    async def output_region(self) -> AsyncIterator[None]:
        yield

    async def print_above(self, printer: Callable[[], None]) -> None:
        printer()

    async def next_input(self) -> str:
        return await asyncio.to_thread(input, "> ")

    def begin_turn(self, turn_task: asyncio.Task) -> None:
        return None

    def handle_stream(self, chunk) -> None:
        return None

    def set_final_thinking(self, thinking: str) -> None:
        return None

    def finish_turn(self) -> None:
        return None


class CodexBottomPane:
    """One long-lived inline application for composer, activity, and HUD.

    Finalized transcript content is printed above this pane by the REPL. The
    application never enters the alternate screen and never erases itself on
    exit, matching Codex's scrollback-preserving inline mode.
    """

    _FRAMES = ("•", "◦", "•", "·")
    _FRAME_INTERVAL = 0.16

    def __init__(
        self,
        *,
        hud: HudState,
        style: BaseStyle,
        completer: Completer | None = None,
        placeholder: str = "Ask nano-claude to do anything",
        input: Input | None = None,
        output: Output | None = None,
    ) -> None:
        self.hud = hud
        self.style = style
        self.placeholder = placeholder
        self._input = input
        self._output = output
        self.running = False
        self.thinking = ""
        self._turn_started_at = 0.0
        self._frame_index = 0
        self._queued_inputs: list[str] = []
        self._turn_task: asyncio.Task | None = None
        self._submissions: asyncio.Queue[str | None] = asyncio.Queue()
        self._app_task: asyncio.Task | None = None
        self._animation_task: asyncio.Task | None = None
        self._closed = False
        self._synchronized_update_depth = 0

        self.buffer = Buffer(
            completer=completer,
            complete_while_typing=True,
            multiline=True,
        )
        self._bindings = self._create_key_bindings()
        self.app = self._create_application()

    def _create_key_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        @bindings.add("enter")
        def _submit(event) -> None:
            completion_state = self.buffer.complete_state
            if completion_state and completion_state.current_completion:
                self.buffer.apply_completion(completion_state.current_completion)
                return
            text = self.buffer.text.strip()
            if not text:
                return
            self.buffer.reset()
            self.submit_text(text)

        @bindings.add("escape", "enter")
        def _newline(event) -> None:
            self.buffer.insert_text("\n")

        @bindings.add("escape")
        def _interrupt(event) -> None:
            if self.buffer.complete_state:
                self.buffer.cancel_completion()
                return
            if self.running and self._turn_task and not self._turn_task.done():
                self._turn_task.cancel()

        @bindings.add("c-c")
        def _control_c(event) -> None:
            if self.running and self._turn_task and not self._turn_task.done():
                self._turn_task.cancel()
            elif self.buffer.text:
                self.buffer.reset()
            else:
                self.request_exit()

        @bindings.add("c-d")
        def _control_d(event) -> None:
            if not self.buffer.text and not self.running:
                self.request_exit()

        return bindings

    def _elapsed_text(self) -> str:
        elapsed = max(time.monotonic() - self._turn_started_at, 0.0)
        if elapsed < 60:
            return f"{int(elapsed)}s"
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"{minutes}m {seconds}s"

    def _status_text(self):
        frame = self._FRAMES[self._frame_index % len(self._FRAMES)]
        return [
            ("class:status.spinner", frame),
            ("class:status.label", " Working "),
            (
                "class:status.meta",
                f"({self._elapsed_text()} • esc to interrupt)",
            ),
        ]

    def _thinking_text(self):
        lines = self.thinking.strip().splitlines()[-4:]
        if not lines:
            return []
        fragments = [
            ("class:trace.branch", "  └ "),
            ("class:trace.content", lines[0]),
        ]
        for line in lines[1:]:
            fragments.append(("class:trace.content", f"\n    {line}"))
        return fragments

    def _queued_text(self):
        fragments = [
            ("class:status.spinner", "•"),
            ("class:status.label", " Queued follow-up inputs"),
        ]
        for text in self._queued_inputs[-3:]:
            one_line = " ".join(text.splitlines())
            fragments.extend(
                [
                    ("class:trace.branch", "\n  ↳ "),
                    ("class:trace.content", one_line),
                ]
            )
        return fragments

    def _create_application(self) -> Application:
        placeholder_visible = Condition(lambda: self.buffer.text == "")
        input_control = BufferControl(
            buffer=self.buffer,
            input_processors=[
                BeforeInput(lambda: [("class:prompt", "› ")]),
                ConditionalProcessor(
                    AfterInput(
                        lambda: [("class:composer.placeholder", self.placeholder)]
                    ),
                    filter=placeholder_visible,
                ),
            ],
        )

        status = ConditionalContainer(
            HSplit(
                [
                    Window(
                        FormattedTextControl(self._status_text),
                        height=1,
                        dont_extend_height=True,
                        always_hide_cursor=True,
                    ),
                    ConditionalContainer(
                        Window(
                            FormattedTextControl(self._thinking_text),
                            height=Dimension(min=1, max=4),
                            wrap_lines=True,
                            dont_extend_height=True,
                            always_hide_cursor=True,
                        ),
                        Condition(lambda: bool(self.thinking.strip())),
                    ),
                ]
            ),
            Condition(lambda: self.running),
        )
        queued = ConditionalContainer(
            Window(
                FormattedTextControl(self._queued_text),
                height=Dimension(min=1, max=4),
                wrap_lines=True,
                dont_extend_height=True,
                always_hide_cursor=True,
            ),
            Condition(lambda: bool(self._queued_inputs)),
        )
        status_spacer = ConditionalContainer(
            Window(height=1),
            Condition(lambda: self.running),
        )
        composer_spacer = ConditionalContainer(
            Window(height=1),
            Condition(lambda: self.running or bool(self._queued_inputs)),
        )
        composer = Window(
            input_control,
            height=Dimension(min=1, max=5),
            wrap_lines=True,
            dont_extend_height=True,
        )
        hud = Window(
            FormattedTextControl(self.hud.formatted_text),
            height=1,
            dont_extend_height=True,
            always_hide_cursor=True,
        )
        body = HSplit(
            [
                status,
                status_spacer,
                queued,
                composer_spacer,
                composer,
                Window(height=1),
                hud,
            ]
        )
        root = FloatContainer(
            content=body,
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=8, scroll_offset=1),
                )
            ],
        )
        return Application(
            layout=Layout(root, focused_element=input_control),
            style=self.style,
            key_bindings=self._bindings,
            full_screen=False,
            erase_when_done=False,
            input=self._input,
            output=self._output,
        )

    def _refresh(self) -> None:
        if self.app.is_running:
            self.app.invalidate()

    async def _animate(self) -> None:
        while not self._closed:
            if self.running:
                self._frame_index += 1
                self._refresh()
            await asyncio.sleep(self._FRAME_INTERVAL)

    async def start(self) -> None:
        if self._app_task and not self._app_task.done():
            return
        self._closed = False
        self._begin_synchronized_update()
        try:
            self._app_task = asyncio.create_task(self.app.run_async())
            if not self._animation_task or self._animation_task.done():
                self._animation_task = asyncio.create_task(self._animate())
            await asyncio.sleep(0)
            await asyncio.sleep(0)
        finally:
            self._end_synchronized_update()

    async def pause(self) -> None:
        if self.app.is_running:
            self.app.exit()
        if self._app_task:
            await asyncio.gather(self._app_task, return_exceptions=True)

    async def resume(self) -> None:
        if self._closed:
            return
        self.app = self._create_application()
        self._app_task = asyncio.create_task(self.app.run_async())
        await asyncio.sleep(0)

    async def close(self) -> None:
        self._closed = True
        self._begin_synchronized_update()
        try:
            if self.app.is_running:
                self.app.exit()
            if self._app_task:
                await asyncio.gather(self._app_task, return_exceptions=True)
        finally:
            self._end_synchronized_update()
        if self._animation_task:
            self._animation_task.cancel()
            await asyncio.gather(self._animation_task, return_exceptions=True)

    def _begin_synchronized_update(self) -> None:
        if self._synchronized_update_depth == 0:
            self.app.output.write_raw("\x1b[?2026h")
            self.app.output.flush()
        self._synchronized_update_depth += 1

    def _end_synchronized_update(self) -> None:
        self._synchronized_update_depth = max(
            self._synchronized_update_depth - 1, 0
        )
        if self._synchronized_update_depth == 0:
            self.app.output.write_raw("\x1b[?2026l")
            self.app.output.flush()

    @asynccontextmanager
    async def output_region(self) -> AsyncIterator[None]:
        """Atomically insert scrollback output above the persistent pane."""
        if not self.app.is_running:
            yield
            return
        self._begin_synchronized_update()
        try:
            with set_app(self.app):
                async with in_terminal():
                    yield
        finally:
            self._end_synchronized_update()

    async def print_above(self, printer: Callable[[], None]) -> None:
        async with self.output_region():
            printer()

    def submit_text(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        if self.running:
            self._queued_inputs.append(text)
        self._submissions.put_nowait(text)
        self._refresh()

    def request_exit(self) -> None:
        self._submissions.put_nowait(None)

    async def next_input(self) -> str:
        text = await self._submissions.get()
        if text is None:
            raise EOFError
        if self._queued_inputs and self._queued_inputs[0] == text:
            self._queued_inputs.pop(0)
            self._refresh()
        return text

    def begin_turn(self, turn_task: asyncio.Task) -> None:
        self.running = True
        self.thinking = ""
        self._turn_task = turn_task
        self._turn_started_at = time.monotonic()
        self._frame_index = 0
        self._refresh()

    def handle_stream(self, chunk) -> None:
        if getattr(chunk, "type", None) != "thinking":
            return
        content = getattr(chunk, "content", "")
        if content:
            self.thinking += content
            self._refresh()

    def set_final_thinking(self, thinking: str) -> None:
        if thinking.strip():
            self.thinking = thinking
            self._refresh()

    def finish_turn(self) -> None:
        self.running = False
        self.thinking = ""
        self._turn_task = None
        self._refresh()

    def snapshot_text(self) -> str:
        """Return a plain-text state snapshot for behavioral tests."""
        lines: list[str] = []
        if self.running:
            lines.append("".join(text for _, text in self._status_text()))
            if self.thinking.strip():
                lines.extend(
                    "".join(text for _, text in self._thinking_text()).splitlines()
                )
            lines.append("")
        if self._queued_inputs:
            lines.extend(
                "".join(text for _, text in self._queued_text()).splitlines()
            )
        if self.running or self._queued_inputs:
            lines.append("")
        lines.extend(
            [
                f"› {self.buffer.text or self.placeholder}",
                "",
                self.hud.plain_text(),
            ]
        )
        return "\n".join(lines)
