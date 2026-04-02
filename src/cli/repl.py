"""Minimal terminal REPL with `>` prompt and command suggestions."""
from __future__ import annotations

import asyncio
import sys
import time

from rich.console import Console
from rich.status import Status

from ..agent.agent import AgentSession
from ..agent.settings import get_api_key, get_base_url, get_model, get_actual_model, load_settings, save_settings
from ..buddy import roll_buddy

# Force UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

console = Console(force_terminal=True)

COMMANDS = ("/help", "/exit", "/model", "/config", "/buddy")
MODEL_TIERS = ("sonnet", "opus", "haiku")  # Sonnet as default first


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
        frame = self._frames[self._frame_idx % len(self._frames)]
        elapsed = self._format_time()
        phase = self._phases[self._phase_idx % len(self._phases)]

        if self.tokens > 0:
            tokens_str = self._format_tokens()
            status = f"{frame} {phase}... ({elapsed} · ↑ {tokens_str} tokens)"
        else:
            status = f"{frame} {phase}... ({elapsed})"

        # Clear previous line content, then print new status
        # Use \r to return to start, clear to end of line, then print
        print(f"\r\x1b[K{status}", end="", flush=True)
        self._last_status_len = len(status)
        self._frame_idx += 1

    async def _animate(self):
        """Animation loop."""
        while not self._stop_event.is_set():
            self._print_status()
            # Update phase every 5 seconds
            if int(time.time() - self.start_time) % 5 == 0 and int(time.time() - self.start_time) > 0:
                self._phase_idx = min(int((time.time() - self.start_time) // 5), len(self._phases) - 1)
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
        self._stop_event.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=0.5)
            except asyncio.TimeoutError:
                pass
        # Clear the status line
        print("\r\x1b[K", end="", flush=True)
        return time.time() - self.start_time, self.tokens


def _print_banner() -> None:
    """Render startup banner with animation."""
    model = get_model()
    api_key = get_api_key()
    status = "connected" if api_key else "mock-mode"

    # Loading animation (ASCII spinner for Windows compatibility)
    with Status("[bold green]Initializing Nano-Claude...", console=console, spinner="line"):
        time.sleep(0.5)

    # Banner
    banner = f"""
 ⎿ ▐▛███▜▌
 ▝▜█████▛▘
 ▘▘ ▝▝
Nano-Claude (Only for Learning)
{model} · {status}
"""
    console.print(banner)

    if status == "mock-mode":
        console.print("[yellow]No API key. Running in mock mode.[/]")
        console.print("[dim]Edit ~/.nano-claude/settings.json[/]\n")


def _resolve_command(line: str) -> tuple[str, list[str]]:
    if not line.startswith("/"):
        return line, []
    # Show all commands when just "/" is entered
    if line == "/":
        return line, list(COMMANDS)
    matches = [cmd for cmd in COMMANDS if cmd.startswith(line)]
    if len(matches) == 1:
        return matches[0], []
    return line, matches


def _print_buddy() -> None:
    """Roll and display buddy with gacha animation."""
    # Gacha rolling animation (ASCII spinner)
    with Status("[bold cyan]Rolling buddy...", console=console, spinner="line"):
        time.sleep(0.6)

    # Reveal dots
    for _ in range(3):
        console.print("[dim]...[/]", end="")
        time.sleep(0.15)
    console.print()

    buddy = roll_buddy()

    # Result reveal with delay
    console.print("=" * 40)
    time.sleep(0.1)

    # Name with rarity color
    rarity_color = buddy.rarity.color
    console.print(f"[{rarity_color}]{buddy.species.name}[/{rarity_color}] [{buddy.rarity.name}]")
    time.sleep(0.05)

    if buddy.species.divine_beast:
        console.print(f"Divine Beast: {buddy.species.divine_beast}")
    console.print(f"Weapon: {buddy.species.signature_weapon}")

    if buddy.is_shiny:
        time.sleep(0.1)
        console.print("[bold yellow]SHINY![/]")

    time.sleep(0.1)
    console.print(buddy.render())
    time.sleep(0.05)
    console.print(buddy.attributes.summary())
    console.print("=" * 40)


def _print_help() -> None:
    console.print("\n[bold]Commands:[/]")
    console.print("  /help           - Show this help")
    console.print("  /exit           - Exit REPL")
    console.print("  /model          - Show current model and available options")
    console.print("  /model <tier>   - Switch to specified tier (sonnet/opus/haiku)")
    console.print("  /config         - Show full configuration")
    console.print("  /buddy          - Roll a random buddy pet\n")


async def _handle_model_async(arg: str = "") -> None:
    """Handle /model command - show info or switch model tier."""
    current_tier = get_model()
    url = get_base_url() or "default"
    actual_model = get_actual_model(current_tier)

    if arg:
        # Direct switch by tier name
        if arg in MODEL_TIERS:
            new_tier = arg
        else:
            console.print(f"[red]Unknown tier: {arg}. Use: {', '.join(MODEL_TIERS)}[/]\n")
            return

        settings = load_settings()
        settings.env["NANO_CLAUDE_MODEL"] = new_tier
        save_settings(settings)
        new_actual = get_actual_model(new_tier)
        console.print(f"[green]Switched to {new_tier} ({new_actual})[/]\n")
        return

    # Show current and available options
    console.print(f"\n[bold]Current tier:[/] {current_tier}")
    console.print(f"[bold]Actual model:[/] {actual_model}")
    console.print(f"[bold]URL:[/]         {url}\n")

    console.print("[bold]Select model tier:[/]")
    for i, tier in enumerate(MODEL_TIERS, 1):
        model_name = get_actual_model(tier)
        marker = " (current)" if tier == current_tier else ""
        console.print(f"  {i}. {tier} ({model_name}){marker}")

    console.print("\n[dim]Enter number or tier name, or press Enter to cancel[/]")

    try:
        choice = input("> ").strip()
        if not choice:
            console.print("[dim]Cancelled[/]\n")
            return

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(MODEL_TIERS):
                new_tier = MODEL_TIERS[idx]
            else:
                console.print("[red]Invalid number[/]\n")
                return
        elif choice in MODEL_TIERS:
            new_tier = choice
        else:
            console.print(f"[red]Unknown: {choice}[/]\n")
            return

        if new_tier == current_tier:
            console.print("[dim]No change[/]\n")
            return

        settings = load_settings()
        settings.env["NANO_CLAUDE_MODEL"] = new_tier
        save_settings(settings)
        new_actual = get_actual_model(new_tier)
        console.print(f"[green]Switched to {new_tier} ({new_actual})[/]\n")

    except KeyboardInterrupt:
        console.print("[dim]Cancelled[/]\n")


def _parse_command(line: str) -> tuple[str, str]:
    """Parse command and argument from line."""
    parts = line.split(maxsplit=1)
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""
    return cmd, arg


async def _handle_local_command(line: str) -> tuple[bool, bool]:
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
    return False, False


async def _run_connected(session: AgentSession) -> None:
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        line, matches = _resolve_command(raw)
        if matches:
            console.print(f"[dim]Suggestions:[/] {' '.join(matches)}")
            continue
        handled, should_exit = await _handle_local_command(line)
        if should_exit:
            break
        if handled:
            continue
        if line.startswith("/"):
            console.print(f"[red]Unknown:[/] {line}")
            continue
        try:
            # Start streaming status animation
            status = StreamingStatus()
            status.start()

            # Stream response
            first_chunk = True
            total_chars = 0
            async for chunk in session.send_stream(line):
                if first_chunk:
                    # Stop animation and print newline before output
                    await status.stop()
                    print()
                    first_chunk = False
                total_chars += len(chunk)
                print(chunk, end="", flush=True)

            # If we never got any chunks, still stop the animation
            if first_chunk:
                await status.stop()

            print()

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

            console.print(f"[dim]Completed in {time_str} · ~{tokens_str} tokens[/]")

        except Exception as exc:  # pragma: no cover - runtime guard
            console.print(f"[red]Error:[/] {exc}")


async def _run_mock() -> None:
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        line, matches = _resolve_command(raw)
        if matches:
            console.print(f"[dim]Suggestions:[/] {' '.join(matches)}")
            continue
        handled, should_exit = await _handle_local_command(line)
        if should_exit:
            break
        if handled:
            continue
        if line.startswith("/"):
            console.print(f"[red]Unknown:[/] {line}")
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