"""Deterministic fake provider (ADR-0001 local fallback).

No credentials required. It inspects the conversation and either (a) asks a
sensible interview question, (b) decides to call an MCP tool when the user signals
readiness ("validate", "score", "threats", "remediate"), or (c) narrates the tool
results that were fed back to it. Behavior is deterministic so tests are stable and
the app is fully demonstrable offline. It intentionally uses the SAME tool-calling
contract as the real providers.
"""
from __future__ import annotations

import json
import re
from typing import AsyncIterator

from .base import AIProvider, Message, StreamEvent, ToolCall, ToolSpec

_INTERVIEW = [
    "Will end users authenticate to this application?",
    "Will it store customer or personal data?",
    "Is it internet-facing or internal only?",
    "Are you using containers or App Service to host it?",
    "Do you have regulatory obligations (PCI-DSS, GDPR, HIPAA)?",
]

_TOOL_TRIGGERS = {
    "validate": "validate_architecture",
    "score": "score_architecture",
    "threat": "get_stride_threats",
    "stride": "get_stride_threats",
    "remediat": "generate_remediation",
    "fix": "generate_remediation",
    "best practice": "list_best_practices",
    "framework": "list_frameworks",
}


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)


class FakeProvider(AIProvider):
    name = "fake"

    async def stream(
        self, messages: list[Message], tools: list[ToolSpec]
    ) -> AsyncIterator[StreamEvent]:
        last_user = next((m for m in reversed(messages) if m.role == "user"), None)
        last_tool = next((m for m in reversed(messages) if m.role == "tool"), None)
        user_text = (last_user.content if last_user else "").lower()

        in_tokens = sum(_tokens(m.content) for m in messages)

        # If the most recent turn is a tool result, narrate it grounded in the data.
        if last_tool is not None and (not last_user or messages.index(last_tool) > messages.index(last_user)):
            narration = self._narrate_tool_result(last_tool)
            async for ev in self._emit_text(narration, in_tokens):
                yield ev
            return

        # Decide whether to call a tool.
        tool_names = {t.name for t in tools}
        chosen = None
        for trigger, tool in _TOOL_TRIGGERS.items():
            if trigger in user_text and tool in tool_names:
                chosen = tool
                break

        if chosen:
            args = self._args_for(chosen, messages)
            yield StreamEvent(
                type="tool_call",
                tool_call=ToolCall(id=f"call_{chosen}", name=chosen, arguments=args),
                input_tokens=in_tokens,
            )
            yield StreamEvent(type="done", output_tokens=0)
            return

        # Otherwise, greet or ask the next interview question.
        reply = self._conversational_reply(messages, user_text)
        async for ev in self._emit_text(reply, in_tokens):
            yield ev

    # ── helpers ──
    async def _emit_text(self, text: str, in_tokens: int) -> AsyncIterator[StreamEvent]:
        # stream word by word to exercise the SSE path
        words = text.split(" ")
        for i, w in enumerate(words):
            yield StreamEvent(type="text", text=w + (" " if i < len(words) - 1 else ""))
        yield StreamEvent(type="done", input_tokens=in_tokens, output_tokens=_tokens(text))

    def _conversational_reply(self, messages: list[Message], user_text: str) -> str:
        user_turns = [m for m in messages if m.role == "user"]
        if len(user_turns) <= 1 and not user_text.strip():
            return (
                "Hi, I'm your AI Security Architect. I'll help you design a secure "
                "Azure architecture. Tell me about the solution you're building."
            )
        idx = min(len(user_turns) - 1, len(_INTERVIEW) - 1)
        lead = "Thanks — that helps. " if len(user_turns) > 1 else "Great. "
        return (
            f"{lead}{_INTERVIEW[idx]} When you've described the design, say "
            f'"validate my architecture" and I\'ll check it against the frameworks.'
        )

    def _args_for(self, tool: str, messages: list[Message]) -> dict:
        if tool in {"validate_architecture", "score_architecture", "get_stride_threats", "generate_remediation"}:
            arch = self._extract_architecture(messages)
            return {"architecture": arch}
        if tool == "list_best_practices":
            return {}
        return {}

    def _extract_architecture(self, messages: list[Message]) -> dict:
        # Look for a JSON architecture the user pasted; otherwise use a default demo.
        for m in reversed(messages):
            if m.role == "user":
                match = re.search(r"\{.*\}", m.content, re.DOTALL)
                if match:
                    try:
                        obj = json.loads(match.group(0))
                        if "nodes" in obj:
                            return obj
                    except json.JSONDecodeError:
                        pass
        return {
            "name": "Demo Web Application",
            "context": {"internet_facing": True, "stores_customer_data": True},
            "nodes": [
                {"id": "web", "service": "app-service",
                 "properties": {"https_only": False, "managed_identity": False}},
                {"id": "sql", "service": "azure-sql",
                 "properties": {"public_access": True, "private_endpoint": False}},
            ],
            "edges": [{"source": "web", "target": "sql"}],
        }

    def _narrate_tool_result(self, tool_msg: Message) -> str:
        try:
            data = json.loads(tool_msg.content)
        except (json.JSONDecodeError, TypeError):
            return "I've reviewed the results. Let me know if you'd like to go deeper on any finding."

        if "overall_score" in data:
            score = data["overall_score"]
            grade = data.get("grade", "")
            summ = data.get("summary", {})
            crit = summ.get("critical_failures", 0)
            high = summ.get("high_failures", 0)
            failed = summ.get("failed_controls", 0)
            return (
                f"Your architecture scored {score}/100 (grade {grade}). I found {failed} "
                f"failing controls, including {crit} critical and {high} high-severity issues. "
                "The most urgent items are exposed data services and missing encryption. "
                'Say "remediate" for a prioritized fix plan, or "show threats" for a STRIDE model.'
            )
        if "total_threats" in data:
            return (
                f"I generated a STRIDE threat model with {data['total_threats']} threats across "
                "the six categories, each linked to a mitigating control and MITRE technique."
            )
        if "remediation_count" in data:
            n = data["remediation_count"]
            top = data.get("remediation_plan", [{}])[0].get("title", "")
            return (
                f"Here's a prioritized remediation plan with {n} items. The top priority is: "
                f"{top}. Work down the list from critical to low severity."
            )
        if "frameworks" in data:
            return f"There are {len(data['frameworks'])} frameworks available for validation."
        return "I've reviewed the results — ask me about any specific finding."
