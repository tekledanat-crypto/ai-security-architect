# MITRE ATLAS — Threat Model of This System

**System:** AI Security Architect Assistant · **Version:** 0.9.0
**Framework:** MITRE ATLAS (Adversarial Threat Landscape for AI Systems)

The product threat-models *user* architectures. This document threat-models **the
product itself** — the AI layer described in `docs/ai-governance/system-card.md` —
using ATLAS techniques. Where a mitigation is weak, that is stated.

---

## System boundary

```
User (browser)
  → Next.js frontend                    [renders text; no eval, no dangerouslySetInnerHTML]
  → FastAPI backend                     [RBAC, guardrails, orchestration, audit]
      → Azure OpenAI                    [inference only; no training, no fine-tuning]
      → MCP server                      [read-only tools over a static corpus]
          → frameworks/data/*.json      [version-controlled, schema-validated]
```

**Assets worth attacking:** the framework corpus (integrity of findings), the audit
trail (accountability), the model's tool access (agency), the API budget (cost).

**Key structural property:** the tool surface is **read-only by construction**. No
tool writes data, calls an external service, or mutates infrastructure. This bounds
the impact of every AI-specific technique below.

---

## Threat analysis by ATLAS tactic

### Reconnaissance — AML.T0000 / AML.T0002

**Threat:** An attacker probes the system to learn its prompt, tools, and model.

**Assessed risk: Low.** The repository is public by design; the system prompt is
committed in plaintext (`backend/app/ai/prompts.py`). There is nothing to discover
that is not already published. This is deliberate — see LLM07 in the self-assessment.
Reconnaissance yields no advantage because no security depends on secrecy of the
prompt.

---

### Initial Access — AML.T0051: LLM Prompt Injection

**Threat:** A crafted input overrides the system prompt, coercing the model to ignore
instructions or misuse tools. This is the highest-likelihood technique against any
LLM application.

**Mitigations**
- Heuristic detection at `backend/app/guardrails/input_filter.py:inspect_input`,
  applied every turn (`orchestrator.py:60`); detections are logged and surfaced.
- System/user separation with the prompt explicitly framing user content as data.
- **Primary mitigation is not the filter — it is LLM06 below.** Even a fully
  successful injection reaches only read-only analysis tools.

**Residual risk: Medium likelihood, Low impact.** Injection *will* succeed against
regex heuristics given effort. It buys the attacker the ability to make the assistant
say things and call read-only tools it was going to be allowed to call anyway. There is
no confused-deputy path to data or infrastructure.

**Indirect injection:** the system does not fetch web content or ingest user documents
into the model context, so the indirect-injection surface (the more dangerous variant)
is absent by architecture.

---

### Execution — AML.T0053: LLM Plugin Compromise / Excessive Agency

**Threat:** The model is induced to invoke tools beyond its authority.

**Mitigations**
- `ToolPolicy` deny-by-default: a tool not in `TOOL_PERMISSIONS` is unreachable
  (`backend/app/guardrails/tool_policy.py:is_allowed`).
- Per-role filtering of the offered tool list *before* the provider call, plus
  re-checking at execution time — a hallucinated tool name is denied and audited.
- Tool-call rounds capped per turn (`MAX_TOOL_CALLS_PER_TURN`).
- **Tools cannot cause harm:** they read framework data and compute scores.
- Tests: `test_unknown_tool_denied_by_default`, `test_tool_policy_readonly_denied_validation`,
  `test_tool_policy_auditor_cannot_remediate`.

**Residual risk: Low.** This is the system's strongest control.

---

### Persistence — AML.T0018 / AML.T0020: Model & Data Poisoning

**Threat:** An attacker corrupts training data or the grounding corpus so findings
become systematically wrong — the most damaging attack on a *security assessment* tool,
because poisoned output looks authoritative.

**Mitigations**
- No training or fine-tuning occurs; there is no model to poison.
- The grounding corpus (`frameworks/data/`) is version-controlled and changes only via
  reviewed commits — poisoning it requires repository write access, which is a
  conventional supply-chain problem, not an AI one.
- Schema + referential-integrity validation runs on every change
  (`frameworks/validate.py`); it has already caught a real defect (a dangling crosswalk
  reference in Chunk 2).
- The eval suite (`tests/evals/`) asserts expected findings for 6 golden architectures:
  silently degrading the corpus fails the build.

**Residual risk: Low**, conditional on repository access control.

---

### Exfiltration — AML.T0057: LLM Data Leakage

**Threat:** The model discloses sensitive context or connected data.

**Mitigations**
- Output scrubbing of secret-shaped strings (`output_filter.py:scrub_output`).
- Tools are role-scoped, so the model cannot retrieve what the user may not see.
- **Small surface:** the model's context contains framework controls and the user's own
  architecture — not customer data, credentials, or third-party secrets.

**Residual risk: Low**, driven mainly by the small sensitive-data surface rather than
by the strength of the redaction (which is pattern-based — see LLM02).

---

### Impact — AML.T0034: Cost Harvesting / Denial of Wallet

**Threat:** An attacker drives inference volume to exhaust budget or availability.

**Mitigations**
- Per-conversation token budget (`TokenBudget`, default 200k).
- Input length cap and per-turn tool-round cap.
- Per-client rate limiting (`backend/app/middleware.py`).

**Residual risk: Medium.** The rate limiter is in-memory and per-instance; it does not
hold across horizontal scale. A real deployment relies on Front Door/APIM at the edge
(Chunk 10). Recorded as gap #3 in the self-assessment.

---

### Impact — AML.T0062: Erode Trust / Misinformation

**Threat:** The system confidently produces a wrong compliance verdict, and a user ships
an insecure design believing it was approved. **This is the most consequential risk in
the system** — not because it is likely, but because the product's entire value rests on
its findings being right.

**Mitigations**
- **The model cannot produce a finding.** Scores and findings come from a deterministic
  engine (`mcp-server/app/engine.py`); the model narrates tool output.
- Report numbers are re-validated server-side at generation
  (`backend/app/routers/reports.py`) rather than trusting the client.
- Continuous measurement: 6/6 golden architectures assert expected outcomes;
  determinism is tested explicitly (`tests/evals/test_evals.py`).
- Users are told the division of labour in the UI and in every report's Methodology
  section — the tool does not present itself as an oracle.
- Reports state the scope limit plainly: this assesses *declared design*, not a running
  deployment.

**Residual risk: Low-Medium.** The numbers are grounded and tested. The model's prose
*around* them is not independently verified, and a user could over-trust a passing grade
as a security guarantee rather than as "passed the assessed control set". The
Methodology section exists precisely to counter that reading.

---

## Summary

| Technique | Likelihood | Impact | Residual risk |
|---|---|---|---|
| AML.T0051 Prompt injection | Medium | Low | **Low-Medium** |
| AML.T0053 Excessive agency | Low | Low | **Low** |
| AML.T0018/20 Poisoning | Low | High | **Low** (gated on repo access) |
| AML.T0057 Data leakage | Low | Low | **Low** |
| AML.T0034 Cost harvesting | Medium | Medium | **Medium** |
| AML.T0062 Misinformation | Low | High | **Low-Medium** |

**The architectural decision that most reduces risk** is not any single guardrail: it is
that the model has no destructive capability and no authority over findings. Injection
and excessive-agency attacks are contained because there is nothing valuable on the
other side of them.
