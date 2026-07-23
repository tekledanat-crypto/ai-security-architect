"""Real AI providers: Azure OpenAI and OpenAI (ADR-0001).

Both use the `openai` SDK's streaming chat completions with tool calling. Azure
uses AzureOpenAI with the deployment name as the model; OpenAI uses the plain
client. Streaming assembles partial tool-call deltas into complete ToolCall objects
before emitting them.

In Azure deployment, the API key is replaced by Managed Identity (Chunk 10); here
we read it from settings for local dev.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from ..config import Settings, get_settings
from .base import AIProvider, Message, StreamEvent, ToolCall, ToolSpec
from .fake import FakeProvider


def _to_openai_messages(messages: list[Message]) -> list[dict]:
    out = []
    for m in messages:
        if m.role == "tool":
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
        elif m.role == "assistant" and m.tool_calls:
            out.append({
                "role": "assistant",
                "content": m.content or None,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}}
                    for tc in m.tool_calls
                ],
            })
        else:
            out.append({"role": m.role, "content": m.content})
    return out


def _to_openai_tools(tools: list[ToolSpec]) -> list[dict]:
    return [
        {"type": "function",
         "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
        for t in tools
    ]


class _OpenAICompatibleProvider(AIProvider):
    def __init__(self, client, model: str, name: str):
        self._client = client
        self._model = model
        self.name = name

    async def stream(
        self, messages: list[Message], tools: list[ToolSpec]
    ) -> AsyncIterator[StreamEvent]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=_to_openai_messages(messages),
            tools=_to_openai_tools(tools) or None,
            stream=True,
            stream_options={"include_usage": True},
        )
        # Accumulate tool-call deltas by index.
        pending: dict[int, dict] = {}
        in_tokens = out_tokens = 0

        async for chunk in stream:
            if chunk.usage:
                in_tokens = chunk.usage.prompt_tokens
                out_tokens = chunk.usage.completion_tokens
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield StreamEvent(type="text", text=delta.content)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    slot = pending.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        slot["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["args"] += tc.function.arguments

        for slot in pending.values():
            try:
                args = json.loads(slot["args"]) if slot["args"] else {}
            except json.JSONDecodeError:
                args = {}
            yield StreamEvent(
                type="tool_call",
                tool_call=ToolCall(id=slot["id"] or f"call_{slot['name']}", name=slot["name"], arguments=args),
            )
        yield StreamEvent(type="done", input_tokens=in_tokens, output_tokens=out_tokens)


def build_provider(settings: Settings | None = None) -> AIProvider:
    settings = settings or get_settings()
    resolved = settings.resolved_ai_provider()

    if resolved == "azure-openai":
        from openai import AsyncAzureOpenAI
        client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        return _OpenAICompatibleProvider(client, settings.azure_openai_deployment, "azure-openai")

    if resolved == "openai":
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        return _OpenAICompatibleProvider(client, settings.openai_model, "openai")

    return FakeProvider()
