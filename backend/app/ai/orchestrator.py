"""AI orchestration: the streaming tool-calling loop with guardrails.

Ties together the AI provider, MCP tools, and the guardrails. For each user turn it:
  1. Inspects input (length limit + injection heuristics; OWASP LLM01).
  2. Streams model output; when the model requests a tool, it is checked against the
     per-role ToolPolicy (OWASP LLM06) and the token budget (LLM10) before execution.
  3. Every tool decision + outcome is written to the AuditLog (LLM06/LLM08).
  4. Tool results are fed back to the model, which narrates them.
  5. Model text is scrubbed for secret-shaped strings before the user sees it (LLM02).

Yields typed events the router serializes as SSE for the frontend's chat + tool
activity panel.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from ..auth.provider import Principal
from ..guardrails.input_filter import inspect_input
from ..guardrails.output_filter import AuditLog, scrub_output
from ..guardrails.tool_policy import BudgetExceeded, TokenBudget, ToolPolicy
from ..providers.base import AIProvider, Message, ToolCall, ToolSpec
from .mcp_client import MCPClient
from .prompts import SYSTEM_PROMPT


@dataclass
class OrchestratorEvent:
    type: str  # "text" | "tool_call" | "tool_result" | "guardrail" | "done" | "error"
    data: dict


class Orchestrator:
    def __init__(
        self,
        provider: AIProvider,
        mcp: MCPClient,
        principal: Principal,
        budget: TokenBudget,
        audit: AuditLog,
        max_input_chars: int,
        max_tool_calls_per_turn: int = 8,
    ):
        self.provider = provider
        self.mcp = mcp
        self.principal = principal
        self.budget = budget
        self.audit = audit
        self.policy = ToolPolicy(principal)
        self.max_input_chars = max_input_chars
        self.max_tool_calls = max_tool_calls_per_turn

    async def run_turn(
        self, history: list[Message], user_text: str
    ) -> AsyncIterator[OrchestratorEvent]:
        # ── 1. Input guardrail ──
        verdict = inspect_input(user_text, self.max_input_chars)
        if verdict.suspicious:
            yield OrchestratorEvent("guardrail", {
                "stage": "input", "ok": verdict.ok,
                "suspicious": True, "reasons": verdict.reasons,
            })
        if not verdict.ok:
            yield OrchestratorEvent("error", {"message": verdict.reasons[0]})
            yield OrchestratorEvent("done", {})
            return

        # ── 2. Assemble context, filtered to the user's allowed tools (LLM06) ──
        all_specs = await self.mcp.list_tool_specs()
        allowed = set(self.policy.allowed_tools())
        specs: list[ToolSpec] = [s for s in all_specs if s.name in allowed]

        messages: list[Message] = [Message(role="system", content=SYSTEM_PROMPT)]
        messages.extend(history)
        messages.append(Message(role="user", content=user_text))

        tool_rounds = 0
        assistant_text_parts: list[str] = []

        while True:
            pending_calls: list[ToolCall] = []
            round_text: list[str] = []

            async for ev in self.provider.stream(messages, specs):
                if ev.type == "text":
                    clean = scrub_output(ev.text)
                    round_text.append(clean)
                    yield OrchestratorEvent("text", {"text": clean})
                elif ev.type == "tool_call" and ev.tool_call:
                    pending_calls.append(ev.tool_call)
                elif ev.type == "done":
                    if ev.input_tokens or ev.output_tokens:
                        self._charge_budget(ev.input_tokens + ev.output_tokens)

            if round_text:
                assistant_text_parts.append("".join(round_text))

            if not pending_calls:
                break

            if tool_rounds >= self.max_tool_calls:
                yield OrchestratorEvent("guardrail", {
                    "stage": "tool-loop", "ok": False,
                    "reasons": [f"Exceeded max tool rounds ({self.max_tool_calls})."],
                })
                break

            # Record the assistant turn that requested the tools.
            messages.append(Message(role="assistant", content="".join(round_text), tool_calls=pending_calls))

            for call in pending_calls:
                tool_rounds += 1
                async for ev in self._execute_tool(call, messages):
                    yield ev

        final_text = "".join(assistant_text_parts)
        yield OrchestratorEvent("done", {
            "assistant_text": final_text,
            "tokens_used": self.budget.used,
            "tokens_remaining": self.budget.remaining(),
        })

    async def _execute_tool(
        self, call: ToolCall, messages: list[Message]
    ) -> AsyncIterator[OrchestratorEvent]:
        # ── Authorization (LLM06) ──
        if not self.policy.is_allowed(call.name):
            self.audit.record(
                self.principal.sub, call.name, call.arguments,
                decision="denied", reason="role not permitted", success=False,
            )
            yield OrchestratorEvent("guardrail", {
                "stage": "tool-auth", "ok": False, "tool": call.name,
                "reasons": [f"Your role may not call '{call.name}'."],
            })
            messages.append(Message(
                role="tool", tool_call_id=call.id, name=call.name,
                content=json.dumps({"error": "not authorized for this tool"}),
            ))
            return

        yield OrchestratorEvent("tool_call", {"tool": call.name, "arguments": _preview(call.arguments)})

        # ── Execute ──
        start = time.perf_counter()
        try:
            result = await self.mcp.call_tool(call.name, call.arguments)
            duration = int((time.perf_counter() - start) * 1000)
            self.audit.record(
                self.principal.sub, call.name, call.arguments,
                decision="allowed", success=True, duration_ms=duration,
            )
            summary = _summarize_result(call.name, result)
            yield OrchestratorEvent("tool_result", {"tool": call.name, "summary": summary})
            messages.append(Message(
                role="tool", tool_call_id=call.id, name=call.name,
                content=json.dumps(result),
            ))
        except Exception as exc:  # noqa: BLE001 — surface tool errors to the model gracefully
            duration = int((time.perf_counter() - start) * 1000)
            self.audit.record(
                self.principal.sub, call.name, call.arguments,
                decision="allowed", success=False, reason=str(exc)[:200], duration_ms=duration,
            )
            yield OrchestratorEvent("error", {"message": f"Tool '{call.name}' failed: {exc}"})
            messages.append(Message(
                role="tool", tool_call_id=call.id, name=call.name,
                content=json.dumps({"error": str(exc)}),
            ))

    def _charge_budget(self, tokens: int) -> None:
        if self.budget.would_exceed(tokens):
            self.budget.charge(tokens)
            raise BudgetExceeded(self.budget.used, self.budget.limit)
        self.budget.charge(tokens)


def _preview(args: dict) -> dict:
    out = {}
    for k, v in args.items():
        s = json.dumps(v) if not isinstance(v, str) else v
        out[k] = v if len(s) <= 120 else f"<{type(v).__name__}>"
    return out


def _summarize_result(tool: str, result: dict) -> str:
    """One-line summary for the UI tool-activity panel."""
    if "overall_score" in result:
        return f"score {result['overall_score']}/100 ({result.get('grade','')}), " \
               f"{result.get('summary',{}).get('failed_controls',0)} failing controls"
    if "total_threats" in result:
        return f"{result['total_threats']} STRIDE threats"
    if "remediation_count" in result:
        return f"{result['remediation_count']} remediation items"
    if "frameworks" in result and isinstance(result["frameworks"], list):
        return f"{len(result['frameworks'])} frameworks"
    if "count" in result:
        return f"{result['count']} results"
    if "control_count" in result:
        return f"{result['control_count']} controls"
    return "done"
