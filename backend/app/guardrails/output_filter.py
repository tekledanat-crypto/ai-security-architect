"""Output filtering + tool-call audit logging (OWASP LLM02/LLM05/LLM08).

  * scrub_output — a light DLP pass that redacts obvious secret-shaped strings the
    model might echo (keys, connection strings, bearer tokens). Defense in depth,
    not a guarantee.
  * AuditLog — records every tool invocation with principal, arguments, decision
    (allowed/denied), and outcome. This is the tamper-evident trail that makes the
    AI's actions reviewable (OWASP LLM06/LLM08; NIST AI RMF "Manage").

The audit log persists via the DB layer (Chunk 4 models). Here it is defined as an
in-memory-plus-callback structure so the streaming orchestrator can emit entries
without coupling to SQLAlchemy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

# Secret-shaped patterns to redact from model output before it reaches the user.
_SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)[A-Za-z0-9_\-]{16,}"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{20,}"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(AccountKey=)[A-Za-z0-9+/=]{20,}"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(password\s*[=:]\s*)\S{6,}"), r"\1[REDACTED]"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "[REDACTED]"),
]


def scrub_output(text: str) -> str:
    for pattern, repl in _SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text


@dataclass
class ToolCallRecord:
    timestamp: str
    principal_sub: str
    tool_name: str
    arguments: dict
    decision: str          # "allowed" | "denied"
    reason: Optional[str]
    success: Optional[bool] = None
    duration_ms: Optional[int] = None


@dataclass
class AuditLog:
    conversation_id: str
    sink: Optional[Callable[[ToolCallRecord], None]] = None
    records: list[ToolCallRecord] = field(default_factory=list)

    def record(
        self,
        principal_sub: str,
        tool_name: str,
        arguments: dict,
        decision: str,
        reason: str | None = None,
        success: bool | None = None,
        duration_ms: int | None = None,
    ) -> ToolCallRecord:
        rec = ToolCallRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            principal_sub=principal_sub,
            tool_name=tool_name,
            arguments=_safe_args(arguments),
            decision=decision,
            reason=reason,
            success=success,
            duration_ms=duration_ms,
        )
        self.records.append(rec)
        if self.sink:
            self.sink(rec)
        return rec


def _safe_args(args: dict) -> dict:
    """Truncate large arg blobs (e.g. full architecture JSON) for the audit trail."""
    out = {}
    for k, v in args.items():
        s = repr(v)
        out[k] = v if len(s) <= 500 else f"<{type(v).__name__}, {len(s)} chars>"
    return out
