"""Agent client using anthropic SDK with async streaming."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic
from anthropic.types import ContentBlockStopEvent, ContentBlockDeltaEvent

from .settings import get_api_key, get_base_url, get_model


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


class AgentSession:
    """Continuous conversation session with async streaming."""

    def __init__(self, system_prompt: str = ""):
        self.system_prompt = system_prompt
        self.client: AsyncAnthropic | None = None
        self.messages: list[dict[str, str]] = []

    async def start(self) -> None:
        """Start the session."""
        self.client = create_async_client()

    async def stop(self) -> None:
        """Stop the session."""
        if self.client:
            await self.client.close()
        self.client = None
        self.messages = []

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
