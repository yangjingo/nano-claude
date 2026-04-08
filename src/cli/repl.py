"""Minimal terminal REPL with `>` prompt and command auto-completion."""

from __future__ import annotations

import asyncio
import sys
import time

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.styles import Style as PtStyle
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.shortcuts.choice_input import ChoiceInput

from rich.console import Console
from rich.status import Status
from rich.style import Style as RichStyle

from ..agent.agent import AgentSession, StreamChunk
from ..agent.settings import (
    get_api_key,
    get_base_url,
    get_model,
    get_actual_model,
    load_settings,
    save_settings,
)
from ..buddy import roll_buddy

# Force UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    # Enable ANSI support on Windows
    import os

    os.system("")  # Enables ANSI escape sequences on Windows

console = Console(force_terminal=True, force_interactive=True)

# Command definitions with descriptions
COMMANDS = {
    "/help": "Show available commands",
    "/exit": "Exit REPL",
    "/model": "Show or switch model",
    "/config": "Show configuration",
    "/buddy": "Roll a random buddy pet",
    "/memory": "List, show, or manage memories",
    "/dream": "Run blood moon consolidation",
    "/sessions": "List saved sessions",
    "/resume": "Resume a previous session",
}
MODEL_TIERS = ("sonnet", "opus", "haiku")

# Prompt-toolkit style - black background theme
PT_STYLE = PtStyle.from_dict(
    {
        "prompt": "bold",
        # Completion menu colors - black background
        "completion-menu": "bg:#000000",
        "completion-menu.completion": "bg:#000000 #e0e0e0",
        "completion-menu.completion.selected": "bg:#000000 #00ff88 bold",
        "completion-menu.meta": "bg:#000000 #808080",
        "completion-menu.meta.selected": "bg:#000000 #00ff88",
        # Scrollbar
        "scrollbar": "bg:#1a1a1a",
        "scrollbar.button": "bg:#404040",
    }
)


class CommandCompleter(Completer):
    """Auto-completer for slash commands."""

    # Sub-command completions for /memory
    MEMORY_SUBCOMMANDS = ("list", "show", "delete", "summary")

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.strip()
        if text.startswith("/"):
            for cmd, desc in COMMANDS.items():
                if cmd.startswith(text):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display=f"{cmd}",
                        display_meta=desc,
                    )
            # /memory subcommands
            if text.startswith("/memory "):
                partial = text[len("/memory "):]
                for sub in self.MEMORY_SUBCOMMANDS:
                    if sub.startswith(partial):
                        yield Completion(
                            sub,
                            start_position=-len(partial),
                            display=f"/memory {sub}",
                        )


class StreamingStatus:
    """Real-time status display for streaming responses."""

    def __init__(self):
        self.start_time = time.time()
        self.tokens = 0
        self._stop_event = asyncio.Event()
        self._task = None
        import random
        self._frames = random.sample(["*", ".", ":", "+", "~", "o"], 3)
        self._frame_idx = 0
        self._phase_idx = 0
        self._phases = ["Thinking", "Processing"]

    def _format_time(self) -> str:
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            return f"{int(elapsed)}s"
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        return f"{mins}m {secs}s"

    def _format_tokens(self) -> str:
        if self.tokens < 1000:
            return str(self.tokens)
        return f"{self.tokens / 1000:.1f}k"

    def _print_status(self):
        import sys

        elapsed = self._format_time()
        frame = self._frames[self._frame_idx % len(self._frames)]
        self._frame_idx += 1
        phase = self._phases[self._phase_idx % len(self._phases)]

        if self.tokens > 0:
            tokens_str = self._format_tokens()
            rich_str = f"[bold cyan]{frame}[/] [dim]{phase}... ({elapsed} · {tokens_str} tokens)[/]"
        else:
            rich_str = f"[bold cyan]{frame}[/] [dim]{phase}... ({elapsed})[/]"

        # Rich render → single atomic \r overwrite (no flicker)
        rendered = console.render_str(rich_str, highlight=False)
        sys.stdout.write(f"\r{rendered}\033[K")
        sys.stdout.flush()

    async def _animate(self):
        while not self._stop_event.is_set():
            self._print_status()
            if (time.time() - self.start_time) > 5:
                self._phase_idx = 1
            await asyncio.sleep(0.3)

    def start(self):
        self._task = asyncio.create_task(self._animate())

    def update_tokens(self, new_tokens: int):
        """Update token count and refresh display."""
        self.tokens += new_tokens
        self._print_status()

    async def stop(self) -> tuple[float, int]:
        """Stop the animation and return stats."""
        import sys

        self._stop_event.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=0.5)
            except asyncio.TimeoutError:
                pass
        # Clear the status line with raw ANSI
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        return time.time() - self.start_time, self.tokens


def _print_banner() -> None:
    """Render startup banner with animation."""
    model = get_model()
    api_key = get_api_key()
    status = "connected" if api_key else "mock-mode"

    # Loading animation (ASCII spinner for Windows compatibility)
    with Status(
        "[bold green]Initializing Nano-Claude...", console=console, spinner="line"
    ):
        time.sleep(0.5)

    # Banner
    banner = f"""
 ⎿ ▐▛███▜▌
 ▝▜█████▛▘
 ▘▘ ▝▝
Nano-Claude (Only for Learning)
{model} · {status}
"""
    console.print(banner, highlight=False, style=RichStyle(bold=True, color="#8C6239"))

    if status == "mock-mode":
        console.print("[yellow]No API key. Running in mock mode.[/]")
        console.print("[dim]Edit ~/.nano-claude/settings.json[/]\n")


def _create_prompt_session() -> PromptSession | None:
    """Create prompt session with command completion, or None if non-interactive."""
    if not sys.stdin.isatty():
        return None  # Fall back to simple input in non-interactive mode
    return PromptSession(
        completer=CommandCompleter(),
        style=PT_STYLE,
        complete_while_typing=True,
        complete_style=CompleteStyle.MULTI_COLUMN,
    )


async def _get_input(prompt_session: PromptSession | None) -> str:
    """Get user input, using prompt_toolkit or simple input."""
    if prompt_session is None:
        # Non-interactive mode: use simple input
        return input("> ").strip()
    else:
        # Interactive mode: use prompt_toolkit
        raw = await prompt_session.prompt_async(">", multiline=False)
        return raw.strip()


def _print_buddy() -> None:
    """Roll and display buddy with gacha animation."""
    from rich.panel import Panel

    # Gacha rolling animation (ASCII spinner)
    with Status("[bold cyan]Rolling buddy...", console=console, spinner="line"):
        time.sleep(0.6)

    buddy = roll_buddy()

    # Rarity colors from design doc
    rarity_colors = {
        "common": "#99a5b2",
        "uncommon": "#a4bf8d",
        "rare": "#86c0d0",
        "epic": "#b78aaf",
        "legendary": "#ebca89",
    }
    rarity_color = rarity_colors.get(buddy.rarity.id, "#ffffff")

    console.print()

    # Header with character name and rarity
    console.print(
        f"[bold {rarity_color}]{buddy.species.name}[/] [{rarity_color}]{buddy.rarity.name}[/]"
    )

    # Divine Beast and Weapon info
    if buddy.species.divine_beast:
        console.print(f"[dim]Divine Beast:[/] [cyan]{buddy.species.divine_beast}[/]")
    console.print(f"[dim]Weapon:[/] [white]{buddy.species.signature_weapon}[/]")

    # Shiny indicator
    if buddy.is_shiny:
        console.print()
        console.print("[bold yellow]* SHINY! *[/]")

    console.print()

    # Combined panel with ASCII art and attributes
    attr = buddy.attributes
    health_filled = attr.health // 10
    stamina_filled = attr.stamina // 10
    skill_filled = attr.skill // 10

    # Build attribute bars
    health_bar = f"[red]{'+' * health_filled}{'-' * (10 - health_filled)}[/]"
    stamina_bar = f"[green]{'#' * stamina_filled}{':' * (10 - stamina_filled)}[/]"
    skill_bar = f"[blue]{'#' * skill_filled}{':' * (10 - skill_filled)}[/]"

    # Combine art and attributes
    combined_text = f"""{buddy.render()}

[dim]Health[/]   {health_bar} {attr.health}
[dim]Stamina[/]  {stamina_bar} {attr.stamina}
[dim]Skill[/]    {skill_bar} {attr.skill}"""

    buddy_panel = Panel(
        combined_text, title=buddy.species.name, style=rarity_color, padding=(0, 1)
    )
    console.print(buddy_panel)

    console.print()


def _print_help() -> None:
    console.print("\n[bold]Commands:[/]")
    console.print("  /help           - Show this help")
    console.print("  /exit           - Exit REPL")
    console.print("  /model          - Show current model and available options")
    console.print("  /model <tier>   - Switch to specified tier (sonnet/opus/haiku)")
    console.print("  /config         - Show full configuration")
    console.print("  /buddy          - Roll a random buddy pet")
    console.print("  /memory         - List all memories")
    console.print("  /memory show N  - Show memory by name")
    console.print("  /memory delete N- Delete a memory")
    console.print("  /memory summary - Memory statistics")
    console.print("  /dream          - Run blood moon consolidation")
    console.print("  /sessions       - List saved sessions")
    console.print("  /resume         - Resume latest session")
    console.print("  /resume <id>    - Resume specific session\n")


# Choice menu style - dark theme with black background
CHOICE_STYLE = PtStyle.from_dict(
    {
        "choice": "bg:#000000 #e0e0e0",
        "choice.selected": "bg:#000000 #00ff88 bold",
        "choice.unselected": "bg:#000000 #606060",
        "prompt": "bg:#000000 #00ff88 bold",
        "separator": "bg:#000000 #404040",
        "frame": "bg:#000000 #606060",
        "frame.label": "bg:#000000 #ffffff",
    }
)


async def _handle_model_async(arg: str = "") -> None:
    """Handle /model command asynchronously."""
    current_model = get_model()
    url = get_base_url() or "default"

    # Show current configuration
    console.print(f"\n[bold]Current model:[/] {current_model}")
    console.print(f"[bold]URL:[/]         {url}\n")

    # Build options for choice menu with numbers
    options = []
    for i, tier in enumerate(MODEL_TIERS, 1):
        model_name = get_actual_model(tier)
        label = f"{i}. {tier} → {model_name}"
        if model_name == current_model:
            label += " (active)"
        options.append((tier, label))

    try:
        # Use ChoiceInput.prompt_async for async selection
        choice_dialog = ChoiceInput(
            message="Select model tier:",
            options=options,
            style=CHOICE_STYLE,
            show_frame=True,
        )
        selected = await choice_dialog.prompt_async()

        if selected is None:
            console.print("[dim]Cancelled[/]\n")
            return

        new_model = get_actual_model(selected)
        if new_model == current_model:
            console.print("[dim]No change[/]\n")
            return

        # Update settings.env with new default model
        settings = load_settings()
        settings.env["NANO_CLAUDE_DEFAULT_SONNET_MODEL"] = new_model
        save_settings(settings)
        console.print(f"[green]Switched default model to {new_model}[/]\n")

    except (KeyboardInterrupt, EOFError):
        console.print("[dim]Cancelled[/]\n")


def _parse_command(line: str) -> tuple[str, str]:
    """Parse command and argument from line."""
    parts = line.split(maxsplit=1)
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""
    return cmd, arg


async def _select_command() -> str | None:
    """Show command selection menu. Returns selected command or None."""
    # Build options for choice menu with numbers
    options = []
    for i, (cmd, desc) in enumerate(COMMANDS.items(), 1):
        label = f"{i}. {desc}"
        options.append((cmd, label))

    try:
        choice_dialog = ChoiceInput(
            message="Select command:",
            options=options,
            style=CHOICE_STYLE,
            show_frame=True,
        )
        selected = await choice_dialog.prompt_async()
        return selected
    except (KeyboardInterrupt, EOFError):
        return None


async def _handle_local_command(line: str) -> tuple[bool, bool]:
    """Handle local command. Returns (handled, should_exit)."""
    # If just "/" entered, show command selection menu
    if line == "/":
        selected = await _select_command()
        if selected:
            # Recursively handle the selected command
            return await _handle_local_command(selected)
        return True, False

    cmd, arg = _parse_command(line)

    if cmd in {"/exit", "/quit"}:
        return True, True
    if cmd == "/help":
        _print_help()
        return True, False
    if cmd == "/model":
        await _handle_model_async(arg)
        return True, False
    if cmd == "/config":
        tier = get_model()
        actual = get_actual_model(tier)
        console.print(f"\n[bold]Tier:[/]  {tier}")
        console.print(f"[bold]Model:[/] {actual}")
        console.print(f"[bold]API:[/]   {'***' if get_api_key() else 'none'}")
        console.print(f"[bold]URL:[/]   {get_base_url() or 'default'}\n")
        return True, False
    if cmd == "/buddy":
        _print_buddy()
        return True, False
    if cmd == "/memory":
        _handle_memory(arg)
        return True, False
    if cmd == "/dream":
        await _handle_dream()
        return True, False
    if cmd == "/sessions":
        _handle_sessions()
        return True, False
    if cmd == "/resume":
        return True, True  # Signal exit — caller relaunches with --resume
    return False, False


def _handle_memory(arg: str) -> None:
    """Handle /memory command."""
    from ..memory import load_memories, get_memory, delete_memory, memory_summary, LocalStorage

    subcmd = arg.strip().split()[0] if arg.strip() else "list"
    rest = arg.strip().split(None, 1)[1] if len(arg.strip().split(None, 1)) > 1 else ""

    if subcmd == "list":
        entries = load_memories()
        if not entries:
            console.print("\n[dim]No memories stored yet.[/]\n")
            return
        console.print(f"\n[bold]Memories ({len(entries)}):[/]\n")
        for e in entries:
            console.print(
                f"  [cyan]{e.name}[/] [dim]({e.type.value})[/] {e.description}"
            )
        console.print()

    elif subcmd == "show":
        if not rest:
            console.print("[red]Usage: /memory show <name>[/]\n")
            return
        entry = get_memory(rest)
        if not entry:
            console.print(f"[red]Memory not found:[/] {rest}\n")
            return
        console.print(f"\n[bold cyan]{entry.name}[/] [dim]({entry.type.value})[/]")
        console.print(f"[dim]{entry.description}[/]")
        console.print()
        console.print(entry.content)
        console.print()

    elif subcmd == "delete":
        if not rest:
            console.print("[red]Usage: /memory delete <name>[/]\n")
            return
        if delete_memory(rest):
            console.print(f"[green]Deleted:[/] {rest}\n")
        else:
            console.print(f"[red]Not found:[/] {rest}\n")

    elif subcmd == "summary":
        console.print(f"\n{memory_summary()}\n")

    else:
        console.print(f"[red]Unknown subcommand:[/] {subcmd}")
        console.print("[dim]Usage: /memory [list|show|delete|summary]\n")


def _handle_sessions() -> None:
    """Handle /sessions command."""
    sessions = AgentSession.list_sessions()
    if not sessions:
        console.print("\n[dim]No saved sessions.[/]\n")
        return
    console.print(f"\n[bold]Sessions ({len(sessions)}):[/]\n")
    for s in sessions:
        console.print(
            f"  [cyan]{s['session_id']}[/]  "
            f"[dim]updated={s['updated']}  messages={s['messages']}[/]"
        )
    console.print()


async def _handle_dream() -> None:
    """Handle /dream command — run blood moon consolidation."""
    from rich.status import Status
    from ..memory import dream

    console.print("\n[bold red]Blood Moon rises...[/]")
    with Status("[bold red]Consolidating memories...[/]", console=console, spinner="moon"):
        result = dream()

    if result.created > 0 or result.updated > 0:
        console.print(f"[green]  Created:[/] {result.created}  [cyan]Updated:[/] {result.updated}  [dim]Skipped:[/] {result.skipped}")
        if result.names:
            console.print(f"[dim]  {', '.join(result.names)}[/]")
    else:
        console.print("[dim]  No new signals found. Nothing to consolidate.[/]")
    console.print()


def _display_tool_invocation(inv) -> None:
    """Display a tool invocation with its output."""
    # Header: tool name + arg preview
    args = inv.args
    if args:
        first_val = str(list(args.values())[0])[:60]
        console.print(f"\n[green]  {inv.name}[/]([dim]{first_val}[/])")
    else:
        console.print(f"\n[green]  {inv.name}[/]")

    # Output lines (dim, with | prefix)
    output = inv.result.output
    lines = output.split("\n")
    max_lines = 20
    for line in lines[:max_lines]:
        console.print(f"[dim]  | {line}[/]")
    remaining = len(lines) - max_lines
    if remaining > 0:
        console.print(f"[dim]  \u2026 +{remaining} more lines[/]")


async def _run_connected(agent_session: AgentSession) -> None:
    """Run connected REPL with prompt-toolkit and tool support."""
    from ..tools import ToolRegistry
    from ..tools.bash import bash_tool

    # Set up tool registry
    registry = ToolRegistry()
    registry.register(bash_tool)
    tools_schema = registry.make_schema()

    prompt_session = _create_prompt_session()

    while True:
        try:
            raw = await _get_input(prompt_session)
        except (EOFError, KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[dim]Goodbye![/]")
            break
        if not raw:
            continue

        try:
            handled, should_exit = await _handle_local_command(raw)
            if should_exit:
                break
            if handled:
                continue
            if raw.startswith("/"):
                console.print(f"[red]Unknown command:[/] {raw}")
                continue
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[dim]Cancelled[/]")
            continue

        try:
            # Spinner while waiting for API
            status = StreamingStatus()
            status.start()

            # Run agentic turn (handles tool loop internally)
            turn = await agent_session.run_turn(
                raw,
                tools=tools_schema,
                tool_runner=registry.run,
            )

            elapsed, _ = await status.stop()

            # Display tool invocations
            for inv in turn.tool_invocations:
                _display_tool_invocation(inv)

            # Display final text
            if turn.text:
                console.print()
                console.print(turn.text)
                console.print()

            # Summary
            total_tokens = turn.usage.get("input_tokens", 0) + turn.usage.get(
                "output_tokens", 0
            )
            if total_tokens >= 1000:
                tokens_str = f"{total_tokens / 1000:.1f}k"
            else:
                tokens_str = str(total_tokens)

            if elapsed < 60:
                time_str = f"{elapsed:.1f}s"
            else:
                mins = int(elapsed // 60)
                secs = elapsed % 60
                time_str = f"{mins}m {secs:.0f}s"

            parts = [f"{time_str}", f"~{tokens_str} tokens"]
            tool_count = len(turn.tool_invocations)
            if tool_count:
                parts.append(f"{tool_count} tool call{'s' if tool_count > 1 else ''}")
            console.print(f"[dim]* {' \u00b7 '.join(parts)}[/]")
            console.print()

        except asyncio.CancelledError:
            if "status" in locals():
                await status.stop()
            console.print("\n[dim]Interrupted[/]")
        except KeyboardInterrupt:
            if "status" in locals():
                await status.stop()
            console.print("\n[dim]Interrupted[/]")
        except Exception as exc:  # pragma: no cover - runtime guard
            console.print(f"[red]Error:[/] {exc}")


async def _run_mock() -> None:
    """Run mock REPL with prompt-toolkit."""
    prompt_session = _create_prompt_session()

    while True:
        try:
            raw = await _get_input(prompt_session)
        except (EOFError, KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[dim]Goodbye![/]")
            break
        if not raw:
            continue

        try:
            handled, should_exit = await _handle_local_command(raw)
            if should_exit:
                break
            if handled:
                continue
            if raw.startswith("/"):
                console.print(f"[red]Unknown command:[/] {raw}")
                continue
            console.print(f"[dim][Mock][/] {raw}")
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[dim]Cancelled[/]")
            continue


def run_repl(resume: str | None = None) -> int:
    _print_banner()

    async def runner() -> None:
        if not get_api_key():
            await _run_mock()
            return

        if resume:
            # Resolve session_id
            if resume == "latest":
                sid = AgentSession.latest_session_id()
                if not sid:
                    console.print("[yellow]No sessions to resume.[/]")
                    return
            else:
                sid = resume

            session = AgentSession.load(sid)
            if session is None:
                console.print(f"[red]Session not found:[/] {sid}")
                return
            await session.start()  # Only creates client, doesn't reload memory
            msg_count = len(session.messages)
            console.print(
                f"[dim]Resumed session {session.session_id} ({msg_count} messages)[/]"
            )
        else:
            session = AgentSession()
            await session.start()

        try:
            await _run_connected(session)
        finally:
            await session.stop()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        pass  # Already handled in _run_connected
    return 0
