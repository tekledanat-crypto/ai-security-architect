# AI Governance

This system assesses other people's architectures against AI governance frameworks.
It would be incoherent not to hold itself to the same standard — so this directory
applies those frameworks to **this application's own AI layer**.

That dual role is a deliberate decision, recorded in
[ADR-0004](../adr/0004-governance-dual-role.md) before implementation began.

## Documents

| Document | What it is |
|---|---|
| [**system-card.md**](system-card.md) | Start here. What the system does, who it's for, what it can't do, and the division of labour between the model and the deterministic engine. |
| [**owasp-llm-top10-self-assessment.md**](owasp-llm-top10-self-assessment.md) | Per-risk assessment against OWASP LLM Top 10 (2025), each claim citing real code and tests. **4 met, 5 partial, 1 N/A**, with a 6-item gap register. |
| [**nist-ai-rmf.md**](nist-ai-rmf.md) | GOVERN / MAP / MEASURE / MANAGE mapping. MEASURE reports actual eval results, not intentions. |
| [**iso-42001-soa.md**](iso-42001-soa.md) | Annex A statement of applicability. **12 implemented, 5 partial, 21 organisational (out of scope)** — with an explicit statement that a portfolio project cannot be 42001-conformant. |
| [**eu-ai-act-classification.md**](eu-ai-act-classification.md) | Risk classification memo. Concludes **limited risk** (Article 50 transparency), with a detailed analysis of why Annex III(2) critical-infrastructure does *not* apply, and reclassification triggers if that changes. |
| [**atlas-threat-model.md**](atlas-threat-model.md) | MITRE ATLAS threat model of this system, with residual risk stated per technique. |

## The principle these share

**Honest ratings.** Partial is written as partial. Six gaps are published rather than
hidden. Where a framework doesn't apply to a project this size, that's stated instead
of claimed.

A self-assessment that scores itself green everywhere tells a reviewer nothing. These
are written to be read by someone who will check.

## Claims are verifiable

Every statement in these documents cites a file or a test. To check them:

```bash
python tests/evals/run_evals.py     # 6/6 golden architectures (100%)
cd tests/evals && pytest            # 8 tests incl. determinism, monotonic improvement
cd backend && pytest                # 38 tests (guardrails, RBAC, streaming, reports)
cd mcp-server && pytest             # 35 tests (engine, threats, tools)
python frameworks/validate.py       # 12 files, 137 controls, referential integrity
```

## Measurements at Chunk 9

| Suite | Result |
|---|---|
| Golden-architecture evals | 6/6 (100%) |
| Eval suite | 8 passed |
| Backend | 38 passed |
| MCP server | 35 passed |
| Framework corpus | 12 files valid, 137 controls |

The eval harness earned its place during this chunk: it failed a case where the engine
correctly demanded a missing secret store. **The case was wrong, not the engine** — and
the harness is what proved which. That's recorded in `nist-ai-rmf.md` under MEASURE.
