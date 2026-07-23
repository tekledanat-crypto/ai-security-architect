# Tests

| Suite | Location | Run |
|---|---|---|
| Framework corpus validation | `frameworks/validate.py` | `python3 frameworks/validate.py` |
| MCP server (engine, threats, tools) | `mcp-server/tests/` | `cd mcp-server && pytest` |
| Backend (guardrails, RBAC, streaming, reports) | `backend/tests/` | `cd backend && pytest` |
| **Scoring-engine evals** | `tests/evals/` | `make evals` or `cd tests/evals && pytest` |

Everything at once: `make verify`

## Evals (`tests/evals/`)

Golden architectures with expected outcomes, asserted against the real engine. This is
the regression suite for the component the product's credibility rests on: if scoring
drifts, the build fails.

`cases/golden_architectures.json` defines each case and what must be true of it —
score bounds, grade, named controls that must pass or fail, applicability scoping, and
which nodes findings must attribute to.

| Case | Proves |
|---|---|
| `insecure-ecommerce` | The canonical bad design fails the controls it should (19/F) |
| `hardened-ecommerce` | The remediated design passes (100/A) |
| `unguarded-ai-workload` | OWASP LLM controls fire on unguarded AI workloads (72/C) |
| `guarded-ai-workload` | Those controls can actually be satisfied (100/A) |
| `empty-canvas` | An empty design is unassessable, **not** "compliant" |
| `storage-only-scoping` | Controls apply only to services present; presence checks still fire |

Plus `test_scoring_is_deterministic` (same input → same score) and
`test_hardening_strictly_improves_score` (remediation is falsifiable).

**Why this exists:** during Chunk 9 the harness failed `guarded-ai-workload` because the
engine correctly reported a missing secret store. The case was wrong, not the engine.
That is exactly the defect class evals are for — including defects in the assessor's own
assumptions.
