"""AI provider abstraction (ADR-0001).

One interface, three implementations selected at runtime:
  * FakeProvider     — deterministic, no credentials; drives tools from keywords so
                       the whole app is demonstrable offline.
  * AzureOpenAIProvider / OpenAIProvider — real streaming + tool calling.

The orchestrator (ai/orchestrator.py) depends only on this interface, so swapping
providers is configuration, never code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal, Optional

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str = ""
    tool_calls: list["ToolCall"] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass
class StreamEvent:
    """Emitted during streaming. type ∈ {text, tool_call, done}."""
    type: Literal["text", "tool_call", "done"]
    text: str = ""
    tool_call: Optional[ToolCall] = None
    input_tokens: int = 0
    output_tokens: int = 0


class AIProvider:
    name: str = "base"

    async def stream(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
    ) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover
