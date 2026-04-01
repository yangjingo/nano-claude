"""Agent client using anthropic SDK with async streaming."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic

from .settings import get_api_key, get_base_url, get_model


@dataclass
class AgentResponse:
    """Response from agent."""
    text: str
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


async def stream_agent_prompt(prompt: str, system_prompt: str = "") -> AsyncIterator[str]:
    """Stream a single prompt through the agent."""
    client = create_async_client()
    model = get_model()

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

    async def send_stream(self, prompt: str) -> AsyncIterator[str]:
        """Send a prompt and stream response."""
        if not self.client:
            await self.start()

        self.messages.append({"role": "user", "content": prompt})
        model = get_model()

        full_text = []

        async with self.client.messages.stream(
            model=model,
            max_tokens=1024,
            system=self.system_prompt if self.system_prompt else None,
            messages=self.messages,
        ) as stream:
            async for text in stream.text_stream:
                full_text.append(text)
                yield text

        # Add assistant response to history after streaming completes
        if full_text:
            self.messages.append({"role": "assistant", "content": "".join(full_text)})

    async def send(self, prompt: str) -> AgentResponse:
        """Send a prompt and get full response (non-streaming)."""
        if not self.client:
            await self.start()

        self.messages.append({"role": "user", "content": prompt})
        model = get_model()

        response = await self.client.messages.create(
            model=model,
            max_tokens=1024,
            system=self.system_prompt if self.system_prompt else None,
            messages=self.messages,
        )

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
            elif hasattr(block, "name"):
                tool_calls.append({
                    "name": block.name,
                    "input": getattr(block, "input", {}),
                })

        # Add assistant response to history
        if text_parts:
            self.messages.append({"role": "assistant", "content": "\n".join(text_parts)})

        return AgentResponse(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )