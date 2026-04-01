"""REPL for nano-claude with async streaming output."""
from __future__ import annotations

import asyncio
import sys

# Force UTF-8 for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.status import Status

from .agent import AgentSession
from .settings import get_model, get_api_key, get_base_url

console = Console()


def render_banner() -> None:
    """Render startup banner like Claude Code."""
    model = get_model()
    api_key = get_api_key()

    status = "connected" if api_key else "mock-mode"

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


def print_help() -> None:
    """Print help."""
    from .commands import PORTED_COMMANDS

    console.print("\n[bold]CLI Commands:[/]")
    cmds = [
        ("summary", "Project summary"),
        ("manifest", "Source structure"),
        ("commands", "Command list"),
        ("tools", "Tool list"),
    ]
    for cmd, desc in cmds:
        console.print(f"  [cyan]{cmd:<12}[/] {desc}")

    console.print(f"\n[dim]Mirrored: {len(PORTED_COMMANDS)} commands[/]")

    console.print("\n[bold]REPL:[/]")
    console.print("  /help   /exit   /model   /config")


async def async_input() -> str:
    """Async input using thread."""
    loop = asyncio.get_event_loop()
    # Use regular input, rich markup won't work here
    return await loop.run_in_executor(None, lambda: input("\n> "))


async def stream_response(session: AgentSession, prompt: str) -> None:
    """Stream response from agent with spinner."""
    console.print()
    try:
        # Show spinner while waiting for first chunk
        with Status("[bold green]Thinking...", console=console, spinner="dots") as status:
            first_chunk = True
            async for text in session.send_stream(prompt):
                if first_chunk:
                    status.stop()
                    first_chunk = False
                console.print(text, end="")

        console.print()  # newline after output
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/]")


def handle_mock(prompt: str) -> None:
    """Mock mode handler."""
    console.print(f"\n[dim][Mock: {prompt}][/]")
    console.print("[yellow]Configure API key in ~/.nano-claude/settings.json[/]")


async def async_repl() -> None:
    """Async REPL main loop."""
    api_key = get_api_key()

    if api_key:
        session = AgentSession()
        await session.start()
        try:
            while True:
                try:
                    line = await async_input()
                    line = line.strip()
                except (EOFError, KeyboardInterrupt):
                    console.print()
                    break

                if not line:
                    continue

                if line in ("/exit", "/quit"):
                    break

                if line == "/help":
                    print_help()
                    continue

                if line == "/model":
                    console.print(f"[cyan]Model:[/] {get_model()}")
                    continue

                if line == "/config":
                    console.print(f"[cyan]API:[/] {'***' if get_api_key() else 'none'}")
                    console.print(f"[cyan]URL:[/] {get_base_url() or 'default'}")
                    console.print(f"[cyan]Model:[/] {get_model()}")
                    continue

                if line.startswith("/"):
                    console.print(f"[red]Unknown: {line}[/]")
                    continue

                await stream_response(session, line)
        finally:
            await session.stop()
    else:
        # Mock mode
        while True:
            try:
                line = await async_input()
                line = line.strip()
            except (EOFError, KeyboardInterrupt):
                console.print()
                break

            if not line:
                continue

            if line in ("/exit", "/quit"):
                break

            if line == "/help":
                print_help()
                continue

            if line.startswith("/"):
                console.print(f"[red]Unknown: {line}[/]")
                continue

            handle_mock(line)


def run_repl() -> int:
    """Run REPL entry point."""
    render_banner()
    asyncio.run(async_repl())
    return 0