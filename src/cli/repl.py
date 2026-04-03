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

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/"):
            for cmd, desc in COMMANDS.items():
                if cmd.startswith(text):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display=f"{cmd}",
                        display_meta=desc,
                    )


class StreamingStatus:
    """Real-time status display for streaming responses."""

    def __init__(self):
        self.start_time = time.time()
        self.tokens = 0
        self._stop_event = asyncio.Event()
        self._task = None
        # Animation frames
        self._frames = ["*", ".", ":", "+", "x"]
        self._frame_idx = 0
        self._phase_idx = 0
        self._phases = ["Thinking", "Grooving", "Composing", "Processing"]
        self._last_status_len = 0

    def _format_time(self) -> str:
        """Format elapsed time."""
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            return f"{int(elapsed)}s"
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        return f"{mins}m {secs}s"

    def _format_tokens(self) -> str:
        """Format token count."""
        if self.tokens < 1000:
            return str(self.tokens)
        return f"{self.tokens / 1000:.1f}k"

    def _print_status(self):
        """Print current status (overwrites previous)."""
        import sys

        frame = self._frames[self._frame_idx % len(self._frames)]
        elapsed = self._format_time()
        phase = self._phases[self._phase_idx % len(self._phases)]

        if self.tokens > 0:
            tokens_str = self._format_tokens()
            status = f"[bold cyan]{frame}[/] [dim]{phase}...[/] [dim]({elapsed} · ↑ {tokens_str} tokens)[/]"
        else:
            status = f"[bold cyan]{frame}[/] [dim]{phase}...[/] [dim]({elapsed})[/]"

        # Clear line with raw ANSI, then render with Rich
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        console.print(status, end="", highlight=False)
        self._last_status_len = len(status)
        self._frame_idx += 1

    async def _animate(self):
        """Animation loop."""
        while not self._stop_event.is_set():
            self._print_status()
            # Update phase every 5 seconds
            if (
                int(time.time() - self.start_time) % 5 == 0
                and int(time.time() - self.start_time) > 0
            ):
                self._phase_idx = min(
                    int((time.time() - self.start_time) // 5), len(self._phases) - 1
                )
            await asyncio.sleep(0.2)

    def start(self):
        """Start the animation."""
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
    console.print("  /buddy          - Roll a random buddy pet\n")


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


def _handle_model_sync(arg: str = "") -> bool:
    """Handle /model command synchronously. Returns True if should exit."""
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
        # Use prompt_toolkit choice for selection
        selected = choice(
            message="Select model tier:",
            options=options,
            style=CHOICE_STYLE,
            show_frame=True,
        )

        if selected is None:
            console.print("[dim]Cancelled[/]\n")
            return False

        new_model = get_actual_model(selected)
        if new_model == current_model:
            console.print("[dim]No change[/]\n")
            return False

        # Update settings.env with new default model
        settings = load_settings()
        settings.env["NANO_CLAUDE_DEFAULT_SONNET_MODEL"] = new_model
        save_settings(settings)
        console.print(f"[green]Switched default model to {new_model}[/]\n")
        return False

    except (KeyboardInterrupt, EOFError):
        console.print("[dim]Cancelled[/]\n")
        return False


def _parse_command(line: str) -> tuple[str, str]:
    """Parse command and argument from line."""
    parts = line.split(maxsplit=1)
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""
    return cmd, arg


def _select_command() -> str | None:
    """Show command selection menu. Returns selected command or None."""
    # Build options for choice menu with numbers
    options = []
    for i, (cmd, desc) in enumerate(COMMANDS.items(), 1):
        label = f"{i}. {desc}"
        options.append((cmd, label))

    try:
        selected = choice(
            message="Select command:",
            options=options,
            style=CHOICE_STYLE,
            show_frame=True,
        )
        return selected
    except (KeyboardInterrupt, EOFError):
        return None


async def _handle_local_command(line: str) -> tuple[bool, bool]:
    """Handle local command. Returns (handled, should_exit)."""
    # If just "/" entered, show command selection menu
    if line == "/":
        selected = _select_command()
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
        _handle_model_sync(arg)
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
    return False, False


async def _run_connected(agent_session: AgentSession) -> None:
    """Run connected REPL with prompt-toolkit."""
    prompt_session = _create_prompt_session()

    while True:
        try:
            raw = await _get_input(prompt_session)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if not raw:
            continue

        handled, should_exit = await _handle_local_command(raw)
        if should_exit:
            break
        if handled:
            continue
        if raw.startswith("/"):
            console.print(f"[red]Unknown command:[/] {raw}")
            continue

        try:
            # Start streaming status animation
            status = StreamingStatus()
            status.start()

            # Stream response with thinking support
            first_chunk = True
            in_thinking = False
            total_chars = 0
            async for chunk in agent_session.send_stream(raw):
                if first_chunk:
                    # Stop animation and print newline before output
                    await status.stop()
                    console.print()
                    first_chunk = False

                if chunk.type == "thinking":
                    if not in_thinking:
                        # Start thinking block with dim style
                        console.print("[dim]∴ Thinking…[/]")
                        in_thinking = True
                    console.print(chunk.content, end="", style="dim")
                else:
                    if in_thinking:
                        # End thinking block with separator
                        console.print("\n")
                        in_thinking = False
                    total_chars += len(chunk.content)
                    console.print(chunk.content, end="")

            # Close thinking block if still open
            if in_thinking:
                console.print()

            # If we never got any chunks, still stop the animation
            if first_chunk:
                await status.stop()

            console.print()

            # Show summary
            elapsed = time.time() - status.start_time
            approx_tokens = total_chars // 4

            if elapsed < 60:
                time_str = f"{elapsed:.1f}s"
            else:
                mins = int(elapsed // 60)
                secs = elapsed % 60
                time_str = f"{mins}m {secs:.0f}s"

            if approx_tokens >= 1000:
                tokens_str = f"{approx_tokens/1000:.1f}k"
            else:
                tokens_str = str(approx_tokens)

            console.print(f"[dim]* Completed in {time_str} · ~{tokens_str} tokens[/]")

        except Exception as exc:  # pragma: no cover - runtime guard
            console.print(f"[red]Error:[/] {exc}")


async def _run_mock() -> None:
    """Run mock REPL with prompt-toolkit."""
    prompt_session = _create_prompt_session()

    while True:
        try:
            raw = await _get_input(prompt_session)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if not raw:
            continue

        handled, should_exit = await _handle_local_command(raw)
        if should_exit:
            break
        if handled:
            continue
        if raw.startswith("/"):
            console.print(f"[red]Unknown command:[/] {raw}")
            continue
        console.print(f"[dim][Mock][/] {raw}")


def run_repl() -> int:
    _print_banner()

    async def runner() -> None:
        if not get_api_key():
            await _run_mock()
            return
        session = AgentSession()
        await session.start()
        try:
            await _run_connected(session)
        finally:
            await session.stop()

    asyncio.run(runner())
    return 0
