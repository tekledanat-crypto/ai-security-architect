# NIST AI Risk Management Framework — Mapping

**System:** AI Security Architect Assistant · **Version:** 0.9.0
**Framework:** NIST AI RMF 1.0 (AI 100-1), functions: GOVERN, MAP, MEASURE, MANAGE

This maps the AI RMF's four functions onto what this repository actually implements.
It is scoped honestly: this is a portfolio system built by one person, not an
enterprise AI programme. Organisational controls that would exist in a real deployment
(review boards, incident drills, third-party audit) are marked as such rather than
claimed.

---

## GOVERN — Policies, accountability, culture

| Subcategory | Implementation | Evidence |
|---|---|---|
| GOVERN 1.1 — Legal/regulatory requirements understood | EU AI Act classification performed; obligations identified and implemented | `docs/ai-governance/eu-ai-act-classification.md` |
| GOVERN 1.2 — Trustworthy AI characteristics integrated into policy | Design decisions recorded as ADRs before implementation, incl. the decision that AI governance applies to this system itself | `docs/adr/0004-governance-dual-role.md` |
| GOVERN 1.4 — Risk management processes documented | Threat model of this system using MITRE ATLAS; OWASP LLM self-assessment with an explicit gap register | `docs/ai-governance/atlas-threat-model.md`, `owasp-llm-top10-self-assessment.md` |
| GOVERN 2.1 — Roles and responsibilities documented | Four-role RBAC model (Administrator, SecurityArchitect, Auditor, ReadOnly) with a permission matrix enforced in code | `backend/app/auth/provider.py:ROLE_PERMISSIONS` |
| GOVERN 4.1 — Culture of risk-awareness | Self-assessment publishes 6 open gaps rather than claiming full coverage; system card states limitations | this directory |
| GOVERN 6.1 — Third-party risks addressed | Model provider is a first-party managed service (Azure OpenAI); provider abstraction prevents lock-in to an unvetted endpoint | `backend/app/providers/` |

**Not implemented (organisational, out of scope for this build):** AI review board,
formal risk acceptance sign-off, staff training records, vendor due-diligence files.

---

## MAP — Context and risk identification

| Subcategory | Implementation | Evidence |
|---|---|---|
| MAP 1.1 — Intended purpose and context defined | Purpose, users, and out-of-scope uses stated in the system card | `docs/ai-governance/system-card.md` |
| MAP 1.5 — Risk tolerances determined | Deliberate decisions recorded: injection heuristics flag rather than block; tools are read-only by construction | self-assessment LLM01, LLM06 |
| MAP 2.2 — AI system knowledge limits documented | The system card states plainly that the model narrates but never computes findings; the UI tells users the same | `system-card.md`, chat composer footer |
| MAP 2.3 — Scientific integrity of the approach | Findings derive from a version-controlled, schema-validated corpus with referential integrity enforced in CI | `frameworks/validate.py`, `frameworks/README.md` |
| MAP 3.4 — Operator proficiency accounted for | Target users are cloud/security practitioners; output is advisory and states that final decisions require human review | system prompt, report Methodology section |
| MAP 5.1 — Impacts to individuals/groups identified | No personal data processed; assessments concern infrastructure designs, not people | `system-card.md` |

---

## MEASURE — Analysis, benchmarking, monitoring

This is the function most systems claim and least often evidence. Here it is executed.

| Subcategory | Implementation | Evidence |
|---|---|---|
| MEASURE 1.1 — Approaches and metrics identified | Golden-architecture eval suite with explicit expected outcomes per case | `tests/evals/cases/golden_architectures.json` |
| MEASURE 2.3 — System performance demonstrated | **6/6 golden architectures produce expected findings (100% pass rate)** | `tests/evals/run_evals.py` |
| MEASURE 2.5 — System is validated and reliable | **Determinism proven by test:** identical input yields identical score across repeated runs | `tests/evals/test_evals.py::test_scoring_is_deterministic` |
| MEASURE 2.7 — Security and resilience evaluated | 10 guardrail unit tests + RBAC denial tests at API level | `backend/tests/test_guardrails.py`, `test_api.py` |
| MEASURE 2.9 — Model explained and interpretable | Every finding traces to a named control ID with a paraphrased summary and remediation; every threat traces to a control and MITRE technique | `mcp-server/app/engine.py`, `threats.py` |
| MEASURE 2.11 — Fairness/bias evaluated | Not applicable: no demographic inference, no decisions about people. Assessment is rule-based over infrastructure configuration | — |
| MEASURE 4.2 — Measurement results tracked over time | Eval suite runs in CI on every change; regressions fail the build | Chunk 10 (`ci.yml`) |

### Current measurements (recorded at Chunk 9)

| Case | Score | Grade | Expectation | Result |
|---|---|---|---|---|
| insecure-ecommerce | 19 | F | ≤40, ≥1 critical, 7 named controls fail | PASS |
| hardened-ecommerce | 100 | A | ≥90, 0 critical, 5 named controls pass | PASS |
| unguarded-ai-workload | 72 | C | ≤85, LLM01/06/10 fail | PASS |
| guarded-ai-workload | 100 | A | ≥90, LLM01/06/10 pass | PASS |
| empty-canvas | 100 | A | 0 findings (unassessable, not "compliant") | PASS |
| storage-only-scoping | 41 | F | storage controls assessed; SQL/KV property controls not | PASS |

**Total: 6/6 (100%).** Suite: 8 tests including determinism and monotonic-improvement
checks. Backend: 38 tests. MCP server: 35 tests. Framework corpus: 12 files, 137
controls, referential integrity verified.

**A finding from building this harness:** the initial `guarded-ai-workload` case failed
because the engine correctly reported a missing secret store — the case, not the
engine, was wrong. It is recorded here because it is precisely what MEASURE is for:
the harness found a defect in the assessor's own assumptions.

---

## MANAGE — Risk treatment and monitoring

| Subcategory | Implementation | Evidence |
|---|---|---|
| MANAGE 1.2 — Risks prioritised and treated | Gap register with 6 open items, each rated and either accepted with rationale or scheduled | self-assessment "Gaps" table |
| MANAGE 2.2 — Mechanisms to sustain value | Deterministic engine + eval suite means behaviour cannot silently drift | `tests/evals/` |
| MANAGE 2.3 — Mechanisms to supersede/deactivate | Provider abstraction allows swapping or disabling the model layer via config with no code change; the deterministic tools function without any model | `backend/app/providers/openai_provider.py:build_provider` |
| MANAGE 4.1 — Post-deployment monitoring | Every tool invocation persisted with principal, arguments, decision, outcome, and duration | `backend/app/db/models.py:ToolAudit`, `guardrails/output_filter.py:AuditLog` |
| MANAGE 4.2 — Feedback captured | Tool-call audit is queryable per conversation (`GET /api/chat/{id}/audit`); guardrail events surface in the UI | `backend/app/routers/chat.py` |

**Not implemented:** incident response drills, user appeal process, production
telemetry dashboards. These are deployment-stage activities.

---

## Honest scope statement

This mapping demonstrates that AI RMF's structure has been applied substantively —
particularly MEASURE, where claims are backed by a running eval suite. It does not
claim organisational conformance: an AI RMF programme in a real enterprise includes
governance bodies, audits, and lifecycle processes that a single-developer portfolio
project cannot and should not pretend to have.
