"""Input guardrails: length limits and prompt-injection heuristics (OWASP LLM01).

These are deliberately conservative heuristics, not a security boundary on their
own — the real protection is architectural (system/user separation, per-role tool
allow-listing, human-in-the-loop for consequential actions). The heuristics raise
the cost of trivial injection and feed the audit log so attempts are visible.

Referenced by docs/ai-governance/owasp-llm-top10.md (Chunk 9).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Patterns that commonly appear in direct prompt-injection / instruction-override
# attempts. Matching does NOT hard-block by default (to avoid false positives on
# legitimate security discussion, e.g. a user pasting an attack for analysis); it
# flags the input as suspicious for logging and optional stricter handling.
INJECTION_PATTERNS = [
    r"\bignore (?:all |your |the )?(?:previous|prior|above) (?:instructions|prompts?)\b",
    r"\bdisregard (?:all |your |the )?(?:previous|prior|above)\b",
    r"\byou are now\b.{0,40}\b(?:dan|developer mode|jailbroken|unrestricted)\b",
    r"\b(?:reveal|print|show|repeat|leak) (?:your |the )?(?:system prompt|instructions|initial prompt)\b",
    r"\bpretend (?:to be|you are)\b.{0,40}\b(?:no (?:rules|restrictions|filter))\b",
    r"\boverride (?:your |the )?(?:safety|guardrails?|restrictions?)\b",
    r"\bact as\b.{0,30}\b(?:with no restrictions|without restrictions|unfiltered)\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


@dataclass
class InputVerdict:
    ok: bool
    suspicious: bool
    reasons: list[str]
    matched_patterns: list[str]


def inspect_input(text: str, max_chars: int) -> InputVerdict:
    reasons: list[str] = []
    matched: list[str] = []

    if len(text) > max_chars:
        # Length is a hard failure — it protects the token budget and the model.
        return InputVerdict(
            ok=False, suspicious=True,
            reasons=[f"Input exceeds {max_chars} character limit ({len(text)})."],
            matched_patterns=[],
        )

    for pat in _COMPILED:
        if pat.search(text):
            matched.append(pat.pattern)

    if matched:
        reasons.append("Input matched prompt-injection heuristic(s).")
        # suspicious but NOT blocked: security professionals legitimately discuss
        # these strings. The signal is logged and the system prompt reinforces
        # that user content is data, never instructions.
        return InputVerdict(ok=True, suspicious=True, reasons=reasons, matched_patterns=matched)

    return InputVerdict(ok=True, suspicious=False, reasons=[], matched_patterns=[])
