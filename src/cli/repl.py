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
    "/dream": "Scan transcripts for memorable signals and consolidate into persistent memory",
    "/sessions": "Resume a previous session (alias for /resume)",
    "/resume": "Resume a previous session",
    "/save": "Save current session to disk",
    "/clear": "Clear current session messages",
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
    console.print("  /memory         - Browse and manage memories")
    console.print("  /dream          - Scan transcripts for memorable signals and consolidate into persistent memory")
    console.print("  /resume         - Resume a previous session")
    console.print("  /resume <id>    - Resume specific session by ID")
    console.print("  /sessions       - Same as /resume")
    console.print("  /save           - Save current session to disk")
    console.print("  /clear          - Clear current session messages\n")


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
        await _handle_memory_async()
        return True, False
    if cmd == "/dream":
        await _handle_dream()
        return True, False
    if cmd in ("/resume", "/sessions"):
        return True, True  # Mock mode: exit (no session to resume)
    return False, False


async def _handle_connected_command(
    line: str,
    agent_session: AgentSession,
    session_holder: list[AgentSession],
) -> tuple[bool, bool]:
    """Handle commands in connected mode.

    Supports all local commands plus session-aware /resume, /save, /clear.
    Returns (handled, should_exit).
    """
    if line == "/":
        selected = await _select_command()
        if selected:
            return await _handle_connected_command(selected, agent_session, session_holder)
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
        await _handle_memory_async()
        return True, False
    if cmd == "/dream":
        await _handle_dream()
        return True, False
    if cmd == "/sessions":
        _handle_sessions()
        return True, False

    # Session-aware commands (connected mode only)
    if cmd in ("/resume", "/sessions"):
        # If arg provided, resume directly; otherwise show picker
        target = arg.strip()
        if target:
            sid = (
                AgentSession.latest_session_id()
                if target == "latest"
                else target
            )
            if not sid:
                console.print("[yellow]No sessions to resume.[/]")
            else:
                new_session = AgentSession.load(sid)
                if new_session:
                    await agent_session.stop()
                    new_session.client = None
                    await new_session.start()
                    session_holder[0] = new_session
                    console.print(
                        f"[dim]Resumed {sid} ({len(new_session.messages)} messages)[/]"
                    )
                    _show_session_history(new_session)
                else:
                    console.print(f"[red]Session not found:[/] {sid}")
        else:
            await _resume_picker(agent_session, session_holder)
        return True, False

    if cmd == "/save":
        path = agent_session.save()
        if path:
            console.print(f"[dim]Saved: {path}[/]")
        else:
            console.print("[yellow]Nothing to save (no messages).[/]")
        return True, False

    if cmd == "/clear":
        agent_session.messages.clear()
        agent_session._token_usage = {"input": 0, "output": 0}
        console.print("[dim]Session cleared.[/]")
        return True, False

    return False, False


async def _handle_memory_async() -> None:
    """Handle /memory with two-level choice menu.

    Level 1: Select action (Browse / Summary / Delete)
    Level 2: Select memory (for Browse / Delete)
    """
    from ..memory import load_memories, get_memory, delete_memory, memory_summary

    entries = load_memories()

    # Build level-1 options
    options: list[tuple[str, str]] = [
        ("browse", f"Browse memories ({len(entries)})"),
        ("summary", "Show statistics"),
    ]
    if entries:
        options.append(("delete", f"Delete a memory ({len(entries)})"))

    try:
        dialog = ChoiceInput(
            message="Memory:",
            options=options,
            style=CHOICE_STYLE,
            show_frame=True,
        )
        action = await dialog.prompt_async()
    except (KeyboardInterrupt, EOFError):
        action = None

    if action is None:
        console.print("[dim]Cancelled[/]\n")
        return

    if action == "summary":
        console.print(f"\n{memory_summary()}\n")
        return

    if action == "browse":
        if not entries:
            console.print("\n[dim]No memories stored yet.[/]\n")
            return

        mem_options = [
            (e.name, f"{e.name}  ({e.type.value})  {e.description}")
            for e in entries
        ]
        try:
            dialog = ChoiceInput(
                message="Select memory:",
                options=mem_options,
                style=CHOICE_STYLE,
                show_frame=True,
            )
            selected = await dialog.prompt_async()
        except (KeyboardInterrupt, EOFError):
            selected = None

        if selected is None:
            console.print("[dim]Cancelled[/]\n")
            return

        entry = get_memory(selected)
        if not entry:
            console.print(f"[red]Not found:[/] {selected}\n")
            return
        console.print(f"\n[bold cyan]{entry.name}[/] [dim]({entry.type.value})[/]")
        console.print(f"[dim]{entry.description}[/]")
        console.print()
        console.print(entry.content)
        console.print()
        return

    if action == "delete":
        if not entries:
            console.print("\n[dim]No memories to delete.[/]\n")
            return

        mem_options = [
            (e.name, f"{e.name}  ({e.type.value})  {e.description}")
            for e in entries
        ]
        try:
            dialog = ChoiceInput(
                message="Delete which memory:",
                options=mem_options,
                style=CHOICE_STYLE,
                show_frame=True,
            )
            selected = await dialog.prompt_async()
        except (KeyboardInterrupt, EOFError):
            selected = None

        if selected is None:
            console.print("[dim]Cancelled[/]\n")
            return

        if delete_memory(selected):
            console.print(f"[green]Deleted:[/] {selected}\n")
        else:
            console.print(f"[red]Not found:[/] {selected}\n")


def _show_session_history(session: AgentSession) -> None:
    """Display recent conversation history after resume."""
    messages = session.messages
    if not messages:
        return

    # Show last N user/assistant pairs (skip context blocks and tool_result)
    pairs: list[tuple[str, str]] = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user" and isinstance(content, str):
            # Skip context-only messages
            clean = _strip_context_block(content)
            if clean.strip():
                pairs.append(("user", clean[:80]))
        elif role == "assistant" and isinstance(content, str):
            pairs.append(("assistant", content[:80]))
        elif role == "assistant" and isinstance(content, list):
            # Extract text from content blocks
            texts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif hasattr(block, "text"):
                    texts.append(block.text)
            if texts:
                pairs.append(("assistant", " ".join(texts)[:80]))

    # Show last 6 messages (3 pairs)
    recent = pairs[-6:]
    if recent:
        console.print()
        for role, text in recent:
            if role == "user":
                console.print(f"  [dim]> {text}[/]")
            else:
                console.print(f"  [dim]{text}[/]")
        console.print()


def _strip_context_block(content: str) -> str:
    """Strip [context] ... prefix from user message content."""
    lines = content.split("\n")
    clean = [l for l in lines if not l.startswith("[context]")]
    # Remove leading blank lines left after stripping context
    while clean and not clean[0].strip():
        clean.pop(0)
    return "\n".join(clean)


async def _resume_picker(
    agent_session: AgentSession,
    session_holder: list[AgentSession],
) -> None:
    """Show interactive session picker and resume selected session."""
    sessions = AgentSession.list_sessions()
    if not sessions:
        console.print("\n[dim]No saved sessions.[/]\n")
        return

    # Build choice options
    options: list[tuple[str, str]] = []
    for s in sessions[:20]:
        sid = s["session_id"]
        preview = s.get("preview", "")[:30]
        msg_count = s.get("messages", "?")
        updated = s.get("updated", "?")[:16]
        label = f"{sid}"
        if preview:
            label += f"  {preview}"
        label += f"  [{msg_count} msgs]"
        options.append((sid, label))

    try:
        dialog = ChoiceInput(
            message="Resume session:",
            options=options,
            style=CHOICE_STYLE,
            show_frame=True,
        )
        selected = await dialog.prompt_async()
    except (KeyboardInterrupt, EOFError):
        console.print("[dim]Cancelled[/]\n")
        return

    if selected is None:
        console.print("[dim]Cancelled[/]\n")
        return

    new_session = AgentSession.load(selected)
    if new_session:
        await agent_session.stop()
        new_session.client = None
        await new_session.start()
        session_holder[0] = new_session
        console.print(
            f"\n[dim]Resumed {selected} ({len(new_session.messages)} messages)[/]"
        )
        _show_session_history(new_session)
    else:
        console.print(f"\n[red]Session not found:[/] {selected}\n")


async def _handle_dream() -> None:
    """Handle /dream command — run blood moon consolidation, show history + next scheduled."""
    from rich.status import Status
    from rich.panel import Panel
    from rich.table import Table
    from ..memory import dream

    console.print()
    console.rule("[bold red] Blood Moon [/]")
    with Status("[bold red]Scanning transcripts...[/]", console=console, spinner="moon"):
        result = dream()

    # ── Result panel ──
    if result.created > 0 or result.updated > 0:
        lines: list[str] = []
        if result.created:
            lines.append(f"[green]+ {result.created} created[/]")
        if result.updated:
            lines.append(f"[cyan]~ {result.updated} updated[/]")
        if result.skipped:
            lines.append(f"[dim]- {result.skipped} skipped[/]")
        if result.names:
            lines.append("")
            for name in result.names[:8]:
                lines.append(f"  [bold]{name}[/]")
        if result.files:
            from ..memory.storage import find_project_root
            root = find_project_root()
            lines.append("")
            lines.append("[dim]files:[/]")
            for fp in result.files:
                rel = os.path.relpath(fp, root) if os.path.isabs(fp) else fp
                bak = fp + ".bak"
                if os.path.exists(bak):
                    bak_rel = os.path.relpath(bak, root) if os.path.isabs(bak) else bak
                    lines.append(f"  [cyan]{rel}[/] [dim]<-- {bak_rel}[/]")
                else:
                    lines.append(f"  [green]{rel}[/]")
        console.print(Panel("\n".join(lines), title="Consolidated", border_style="red"))
    else:
        console.print(Panel("[dim]No new signals found. Nothing to consolidate.[/]",
                            border_style="dim"))

    # Append to dream log
    _append_dream_log(result)

    # ── History + schedule ──
    _show_dream_summary()


def _dream_log_path() -> str:
    """Return the dream log file path."""
    from ..memory.storage import find_project_root
    return os.path.join(find_project_root(), ".nano_claude", "dream_log.jsonl")


def _append_dream_log(result) -> None:
    """Append dream result to log file."""
    import json
    from datetime import datetime

    try:
        os.makedirs(os.path.dirname(_dream_log_path()), exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "total": result.total,
            "created": result.created,
            "updated": result.updated,
            "merged": result.merged,
            "pruned": result.pruned,
            "names": list(result.names) if result.names else [],
        }
        with open(_dream_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _show_dream_summary() -> None:
    """Show dream history, next scheduled run, and memory locations."""
    import json
    from datetime import datetime, timedelta
    from rich.table import Table

    log_path = _dream_log_path()
    entries: list[dict] = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    # ── History table ──
    if entries:
        table = Table(show_header=True, header_style="bold dim", border_style="dim",
                      padding=(0, 1))
        table.add_column("Time", style="dim", min_width=19)
        table.add_column("Changes", min_width=16)
        table.add_column("Signals", style="dim")

        for entry in entries[-8:]:
            ts = entry.get("timestamp", "?")[:19]
            created = entry.get("created", 0)
            updated = entry.get("updated", 0)
            names = entry.get("names", [])

            parts = []
            if created:
                parts.append(f"[green]+{created}[/]")
            if updated:
                parts.append(f"[cyan]~{updated}[/]")
            changes = " ".join(parts) if parts else "[dim]--[/]"
            signals = ", ".join(names[:4]) if names else "--"

            table.add_row(ts, changes, signals)

        console.print()
        console.print(table)

    # ── Footer info ──
    footer_parts: list[str] = []

    # Next scheduled
    next_run = datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)
    if next_run < datetime.now():
        next_run += timedelta(days=1)
    hours_left = (next_run - datetime.now()).total_seconds() / 3600
    footer_parts.append(f"next: [bold]{next_run.strftime('%Y-%m-%d %H:%M')}[/] [dim](~{hours_left:.0f}h)[/]")

    # Memory count
    from ..memory.storage import find_project_root
    memory_dir = os.path.join(find_project_root(), ".nano_claude", "memory")
    memory_count = 0
    if os.path.isdir(memory_dir):
        memory_count = sum(1 for f in os.listdir(memory_dir)
                           if f.endswith(".md") and f != "MEMORY.md")
    footer_parts.append(f"[dim]{memory_count} memories[/]")

    console.print("  " + "  ".join(footer_parts))
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


async def _run_connected(session_holder: list[AgentSession]) -> None:
    """Run connected REPL with prompt-toolkit and tool support.

    ``session_holder`` is a single-element list so /resume can swap the
    active session without changing the reference in the caller.
    """
    from ..tools import ToolRegistry
    from ..tools.bash import bash_tool

    # Set up tool registry
    registry = ToolRegistry()
    registry.register(bash_tool)
    tools_schema = registry.make_schema()

    prompt_session = _create_prompt_session()

    while True:
        agent_session = session_holder[0]

        try:
            raw = await _get_input(prompt_session)
        except (EOFError, KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[dim]Goodbye![/]")
            break
        if not raw:
            continue

        try:
            handled, should_exit = await _handle_connected_command(
                raw, agent_session, session_holder
            )
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
            _show_session_history(session)
        else:
            session = AgentSession()
            await session.start()

        holder = [session]
        try:
            await _run_connected(holder)
        finally:
            await holder[0].stop()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        pass  # Already handled in _run_connected
    return 0
