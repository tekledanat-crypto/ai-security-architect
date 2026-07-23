"""Tool authorization and consumption limits (OWASP LLM06 excessive agency, LLM10).

Two controls:
  * ToolPolicy — a per-role allow-list mapping each MCP tool to the permission it
    requires. The AI can only invoke tools the current Principal is authorized for;
    an Auditor cannot trigger remediation generation, a ReadOnly user cannot run
    validation, etc. This bounds the blast radius of a manipulated model.
  * TokenBudget — a per-conversation ceiling on tokens, preventing unbounded
    consumption (denial of wallet / service).

Referenced by docs/ai-governance/owasp-llm-top10.md (Chunk 9).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..auth.provider import Principal

# Each MCP tool → the permission required to call it. Read-only discovery tools
# need only "read"; assessment tools need "validate"; remediation needs
# "remediate". Anything not listed is denied by default.
TOOL_PERMISSIONS: dict[str, str] = {
    "list_frameworks": "read",
    "find_control": "read",
    "search_controls": "read",
    "list_best_practices": "read",
    "map_service": "read",
    "map_threats": "read",
    "crosswalk_control": "read",
    "compare_frameworks": "read",
    "validate_architecture": "validate",
    "score_architecture": "validate",
    "get_stride_threats": "threat-model",
    "generate_remediation": "remediate",
}


class ToolPolicy:
    def __init__(self, principal: Principal):
        self.principal = principal

    def allowed_tools(self) -> list[str]:
        return [t for t, perm in TOOL_PERMISSIONS.items() if self.principal.has_permission(perm)]

    def is_allowed(self, tool_name: str) -> bool:
        perm = TOOL_PERMISSIONS.get(tool_name)
        if perm is None:
            return False  # deny-by-default: unknown tools are never callable
        return self.principal.has_permission(perm)


@dataclass
class TokenBudget:
    limit: int
    used: int = 0
    _history: list[int] = field(default_factory=list)

    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    def would_exceed(self, estimated: int) -> bool:
        return self.used + estimated > self.limit

    def charge(self, tokens: int) -> None:
        self.used += tokens
        self._history.append(tokens)


class BudgetExceeded(Exception):
    def __init__(self, used: int, limit: int):
        super().__init__(f"Conversation token budget exceeded ({used}/{limit}).")
        self.used = used
        self.limit = limit
