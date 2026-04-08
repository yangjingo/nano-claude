"""Agent client using anthropic SDK with async streaming."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic
from anthropic.types import ContentBlockStopEvent, ContentBlockDeltaEvent

from .settings import get_api_key, get_base_url, get_model

# Re-export tool types for convenience
from ..tools import ToolResult  # noqa: F401

import uuid
from datetime import datetime


@dataclass
class StreamChunk:
    """A chunk from streaming response."""

    type: str  # "thinking" or "text"
    content: str


@dataclass
class AgentResponse:
    """Response from agent."""

    text: str
    thinking: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str = "completed"
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class ToolInvocation:
    """Record of a single tool execution during a turn."""

    name: str
    args: dict[str, Any]
    result: ToolResult


@dataclass
class TurnOutput:
    """Output from a complete agentic turn (may include multiple tool rounds)."""

    text: str
    tool_invocations: list[ToolInvocation] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


def create_async_client() -> AsyncAnthropic:
    """Create Async Anthropic client from settings."""
    api_key = get_api_key()
    base_url = get_base_url()

    if base_url:
        return AsyncAnthropic(api_key=api_key, base_url=base_url)
    return AsyncAnthropic(api_key=api_key)


async def stream_agent_prompt(
    prompt: str, system_prompt: str = ""
) -> AsyncIterator[str]:
    """Stream a single prompt through the agent."""
    client = create_async_client()
    model = get_model()  # Direct model name from settings

    messages = [{"role": "user", "content": prompt}]

    async with client.messages.stream(
        model=model,
        max_tokens=1024,
        system=system_prompt if system_prompt else None,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


SYSTEM_PROMPT = (
    "You are nano-claude, WhyJ's learning project — a Python port of Claude Code.\n"
    "You are concise, direct, and Chinese-friendly. Keep responses short."
)


def _build_context_block() -> str:
    """Build runtime context (platform, shell, cwd) as a message-level block."""
    from ..tools.bash import get_shell_info

    shell = get_shell_info()
    if "bash" in shell.lower():
        shell_hint = "bash (use Unix shell syntax: forward slashes, /dev/null, &&, etc.)"
    elif "cmd" in shell.lower():
        shell_hint = "cmd.exe (use Windows syntax: backslashes, NUL, &, dir, etc.)"
    else:
        shell_hint = shell

    return (
        f"[context] Platform: {sys.platform} | "
        f"Shell: {shell_hint} | "
        f"CWD: {os.getcwd()}"
    )


class AgentSession:
    """Continuous conversation session with async streaming.

    Integrates with memory system:
    - On start: loads MEMORY.md into system prompt
    - During turns: captures signals in SessionNotes, auto-saves to disk
    - On stop: final save + flush transcript for blood moon
    """

    def __init__(self, system_prompt: str = ""):
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.client: AsyncAnthropic | None = None
        self.messages: list[dict[str, Any]] = []
        self.session_id: str = uuid.uuid4().hex[:8]
        self._notes: Any = None  # Lazy-loaded SessionNotes
        self._notes_enabled: bool = True
        self._created: datetime = datetime.now()
        self._updated: datetime = datetime.now()
        self._token_usage: dict[str, int] = {"input": 0, "output": 0}

    # ── Session persistence ──────────────────────────────────

    @staticmethod
    def _session_dir() -> str:
        """Return the session storage directory path."""
        from ..memory.storage import find_project_root
        return os.path.join(find_project_root(), ".nano_claude", "sessions")

    def _session_path(self) -> str:
        """Return the JSON file path for this session."""
        return os.path.join(self._session_dir(), f"{self.session_id}.json")

    def save(self) -> str | None:
        """Persist session to disk. Returns file path or None on failure."""
        if not self.messages:
            return None

        try:
            os.makedirs(self._session_dir(), exist_ok=True)
            notes_data: dict[str, list[str]] = {}
            notes = self._get_notes()
            if notes is not None and notes.has_content():
                notes_data = notes.get_all()

            data = {
                "session_id": self.session_id,
                "created": self._created.isoformat(),
                "updated": datetime.now().isoformat(),
                "model": get_model(),
                "system_prompt": self.system_prompt,
                "messages": self._serialize_messages(),
                "notes": notes_data,
                "token_usage": self._token_usage,
            }
            path = self._session_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            self._updated = datetime.now()
            return path
        except Exception:
            return None

    def _serialize_messages(self) -> list[dict[str, Any]]:
        """Serialize messages for JSON persistence.

        Handles both simple string content and API content blocks.
        """
        result = []
        for msg in self.messages:
            serialized: dict[str, Any] = {"role": msg["role"]}
            content = msg.get("content")
            if isinstance(content, str):
                serialized["content"] = content
            elif isinstance(content, list):
                # Serialize content blocks (text, tool_use, tool_result)
                blocks = []
                for block in content:
                    if isinstance(block, dict):
                        blocks.append(block)
                    elif hasattr(block, "model_dump"):
                        blocks.append(block.model_dump())
                    elif hasattr(block, "type"):
                        # Minimal serialization for SDK objects
                        b: dict[str, Any] = {"type": block.type}
                        for attr in ("id", "name", "text", "input", "content",
                                     "tool_use_id", "is_error"):
                            if hasattr(block, attr):
                                b[attr] = getattr(block, attr)
                        blocks.append(b)
                    else:
                        blocks.append(str(block))
                serialized["content"] = blocks
            else:
                serialized["content"] = str(content) if content else ""
            result.append(serialized)
        return result

    @classmethod
    def load(cls, session_id: str) -> AgentSession | None:
        """Load a session from disk by session_id.

        Returns:
            Restored AgentSession, or None if not found.
        """
        session_dir = cls._session_dir()
        path = os.path.join(session_dir, f"{session_id}.json")
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError):
            return None

        session = cls.__new__(cls)
        session.session_id = data.get("session_id", session_id)
        session.system_prompt = data.get("system_prompt", SYSTEM_PROMPT)
        session.messages = data.get("messages", [])
        session._notes = None
        session._notes_enabled = True
        session._token_usage = data.get("token_usage", {"input": 0, "output": 0})
        session._created = datetime.fromisoformat(data["created"]) if "created" in data else datetime.now()
        session._updated = datetime.fromisoformat(data["updated"]) if "updated" in data else datetime.now()
        session.client = None

        # Restore SessionNotes if present
        notes_data = data.get("notes", {})
        if notes_data:
            try:
                from ..memory.notes import SessionNotes
                notes = SessionNotes(session_id=session.session_id)
                for module, entries in notes_data.items():
                    for entry in entries:
                        notes.add(module, entry)
                session._notes = notes
            except Exception:
                pass

        return session

    @classmethod
    def list_sessions(cls) -> list[dict[str, str]]:
        """List all persisted sessions.

        Returns:
            List of dicts with session_id, created, updated, message_count.
            Sorted by updated descending (most recent first).
        """
        session_dir = cls._session_dir()
        sessions: list[dict[str, str]] = []
        if not os.path.isdir(session_dir):
            return sessions

        for filename in os.listdir(session_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(session_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sid = data.get("session_id", filename[:-5])
                sessions.append({
                    "session_id": sid,
                    "created": data.get("created", "?"),
                    "updated": data.get("updated", "?"),
                    "messages": str(len(data.get("messages", []))),
                })
            except (IOError, json.JSONDecodeError):
                sessions.append({
                    "session_id": filename[:-5],
                    "created": "?",
                    "updated": "?",
                    "messages": "?",
                })

        sessions.sort(key=lambda s: s["updated"], reverse=True)
        return sessions

    @classmethod
    def latest_session_id(cls) -> str | None:
        """Return the session_id of the most recently updated session."""
        sessions = cls.list_sessions()
        return sessions[0]["session_id"] if sessions else None

    def _get_notes(self) -> Any:
        """Lazy-load SessionNotes to avoid import overhead if unused."""
        if self._notes is None and self._notes_enabled:
            try:
                from ..memory.notes import SessionNotes
                self._notes = SessionNotes(session_id=self.session_id)
            except ImportError:
                self._notes_enabled = False
        return self._notes

    def _load_memory_context(self) -> str:
        """Load MEMORY.md and inject into system prompt.

        Returns:
            Memory context string, or empty string if no memories.
        """
        try:
            from ..memory.storage import LocalStorage
            from ..memory.index import load_index
            storage = LocalStorage()
            index = load_index(storage)
            if not index.entries:
                return ""
            lines = ["\n## Memory (auto-loaded)\n"]
            for entry in index.entries[:20]:
                lines.append(f"- [{entry.name}] {entry.description}")
            return "\n".join(lines)
        except Exception:
            return ""

    async def start(self) -> None:
        """Start the session and load memory context.

        If messages already exist (restored from load), only creates the client
        without reloading memory (already embedded in system_prompt).
        """
        self.client = create_async_client()
        if not self.messages:
            memory_ctx = self._load_memory_context()
            if memory_ctx:
                self.system_prompt += memory_ctx

    async def stop(self) -> None:
        """Stop the session: save, flush transcript, close client."""
        self.save()
        self._flush_transcript()
        if self.client:
            await self.client.close()
        self.client = None
        self.messages = []

    def _flush_transcript(self) -> None:
        """Flush messages to transcript file for blood moon consolidation."""
        if not self.messages:
            return
        try:
            from ..memory.storage import get_memory_dir
            transcript_dir = os.path.join(
                os.path.dirname(get_memory_dir()), "transcripts"
            )
            os.makedirs(transcript_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            path = os.path.join(
                transcript_dir, f"session_{self.session_id}_{timestamp}.md"
            )
            with open(path, "w", encoding="utf-8") as f:
                for msg in self.messages:
                    role = msg.get("role", "?")
                    content = msg.get("content", "")
                    f.write(f"[{role}] {content}\n")
        except Exception:
            pass  # Best-effort

    async def send_stream(self, prompt: str) -> AsyncIterator[StreamChunk]:
        """Send a prompt and stream response with thinking support."""
        if not self.client:
            await self.start()

        self.messages.append({"role": "user", "content": prompt})
        model = get_model()

        full_text = []
        full_thinking = []

        async with self.client.messages.stream(
            model=model,
            max_tokens=1024,
            system=self.system_prompt if self.system_prompt else None,
            messages=self.messages,
        ) as stream:
            # Iterate over raw events
            async for event in stream:
                if event.type == "content_block_start":
                    # Track which block type we're in
                    if hasattr(event, "content_block") and hasattr(
                        event.content_block, "type"
                    ):
                        current_block_type = event.content_block.type
                elif event.type == "content_block_delta":
                    if hasattr(event, "delta"):
                        delta = event.delta
                        if hasattr(delta, "type") and delta.type == "thinking_delta":
                            if hasattr(delta, "thinking"):
                                chunk = StreamChunk(
                                    type="thinking", content=delta.thinking
                                )
                                full_thinking.append(delta.thinking)
                                yield chunk
                        elif hasattr(delta, "type") and delta.type == "text_delta":
                            if hasattr(delta, "text"):
                                chunk = StreamChunk(type="text", content=delta.text)
                                full_text.append(delta.text)
                                yield chunk
                elif event.type == "content_block_stop":
                    pass

        # Add assistant response to history
        if full_text:
            self.messages.append({"role": "assistant", "content": "".join(full_text)})

    async def send(self, prompt: str) -> AgentResponse:
        """Send a prompt and get full response (non-streaming)."""
        if not self.client:
            await self.start()

        self.messages.append({"role": "user", "content": prompt})
        model = get_model()  # Direct model name from settings

        response = await self.client.messages.create(
            model=model,
            system=self.system_prompt if self.system_prompt else None,
            messages=self.messages,
        )

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
            elif hasattr(block, "name"):
                tool_calls.append(
                    {
                        "name": block.name,
                        "input": getattr(block, "input", {}),
                    }
                )

        # Add assistant response to history
        if text_parts:
            self.messages.append(
                {"role": "assistant", "content": "\n".join(text_parts)}
            )

        return AgentResponse(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    async def run_turn(
        self,
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        tool_runner: Any = None,
    ) -> TurnOutput:
        """Run a complete agentic turn with tool-use loop.

        Args:
            prompt: User message.
            tools: API tool schema list (from ToolRegistry.make_schema()).
            tool_runner: Callable(name, args) -> ToolResult, e.g. registry.run.

        Returns:
            TurnOutput with final text, tool invocations, and token usage.
        """
        if not self.client:
            await self.start()

        # Inject runtime context as prefix to every user message (refreshed per turn)
        context = _build_context_block()
        enriched = f"{context}\n\n{prompt}"
        self.messages.append({"role": "user", "content": enriched})
        model = get_model()
        invocations: list[ToolInvocation] = []

        while True:
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": 8192,
                "messages": self.messages,
            }
            if self.system_prompt:
                kwargs["system"] = self.system_prompt
            if tools:
                kwargs["tools"] = tools

            response = await self.client.messages.create(**kwargs)

            # Store full content blocks (including tool_use) in history
            self.messages.append(
                {"role": "assistant", "content": response.content}
            )

            # Collect tool_use blocks
            tool_uses = [
                b for b in response.content if b.type == "tool_use"
            ]
            if not tool_uses or tool_runner is None:
                break

            # Execute each tool and collect results
            tool_results: list[dict[str, Any]] = []
            for block in tool_uses:
                result: ToolResult = await tool_runner(block.name, block.input)
                invocations.append(
                    ToolInvocation(
                        name=block.name,
                        args=block.input,
                        result=result,
                    )
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result.output,
                        "is_error": result.is_error,
                    }
                )

            # Feed tool results back to the model
            self.messages.append({"role": "user", "content": tool_results})

        # Extract text from the final response
        text_parts: list[str] = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)

        # Capture signals in session notes
        self._capture_turn_signals(prompt, text_parts, invocations)

        # Track token usage and auto-save
        input_tokens = getattr(response.usage, "input_tokens", 0)
        output_tokens = getattr(response.usage, "output_tokens", 0)
        self._token_usage["input"] += input_tokens
        self._token_usage["output"] += output_tokens
        self.save()

        return TurnOutput(
            text="\n".join(text_parts),
            tool_invocations=invocations,
            usage={
                "input_tokens": getattr(response.usage, "input_tokens", 0),
                "output_tokens": getattr(response.usage, "output_tokens", 0),
            },
        )

    def _capture_turn_signals(
        self,
        prompt: str,
        response_parts: list[str],
        invocations: list[ToolInvocation],
    ) -> None:
        """Capture notable signals from this turn into SessionNotes."""
        notes = self._get_notes()
        if notes is None:
            return

        text = prompt + "\n" + "\n".join(response_parts)

        # Track files touched via tool invocations
        touched_files = set()
        for inv in invocations:
            if inv.name in ("Read", "Write", "Edit", "Glob", "Grep"):
                for val in inv.args.values():
                    if isinstance(val, str) and len(val) < 200:
                        touched_files.add(val)

        for f in sorted(touched_files):
            notes.add("files_touched", f)

        # Detect decision signals
        import re
        decision_kw = ["决定", "我们选", "go with", "switch to", "let's use"]
        for kw in decision_kw:
            if kw.lower() in text.lower():
                # Extract the sentence containing the keyword
                for sentence in text.split("。"):
                    if kw.lower() in sentence.lower() and len(sentence.strip()) > 5:
                        notes.add("decisions", sentence.strip())
                        break
