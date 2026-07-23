# OWASP Top 10 for LLM Applications — Self-Assessment

**System:** AI Security Architect Assistant
**Assessed:** Chunk 9 · **Version:** 0.9.0
**Scope:** This application's own AI layer (not the architectures it evaluates).

This is a self-assessment of the software in this repository against the OWASP Top 10
for LLM Applications (2025). Every claim below cites the file and test that substantiate
it. Where a control is partially met or not met, it says so — a self-assessment that
scores itself green across the board is worthless to a reviewer.

**Summary: 4 met · 5 partially met · 1 not met.** The gaps are stated in the Gaps
section and are honest reflections of what a portfolio-scale build does and does not
implement.

---

## LLM01 — Prompt Injection · **Partially met**

**Implemented**
- `backend/app/guardrails/input_filter.py:inspect_input` applies a hard input length
  limit and seven prompt-injection heuristics, returning an `InputVerdict`.
- Called on every turn before any model invocation:
  `backend/app/ai/orchestrator.py:60`.
- The system prompt (`backend/app/ai/prompts.py`) explicitly frames user and tool
  content as **data to analyse, never instructions**.
- Detections are surfaced to the UI as a `guardrail` SSE event and written to the
  audit log — attempts are visible, not silent.
- Tests: `backend/tests/test_guardrails.py::test_injection_heuristic_flags_but_allows`,
  `::test_input_length_limit_blocks`, `::test_clean_input_passes`.

**Deliberate design decision:** heuristic matches **flag and log, but do not block**.
This application's users are security professionals who legitimately paste attack
strings for analysis; hard-blocking them would break the product's core use case. The
real defence is architectural (system/user separation, per-role tool allow-listing,
deterministic tools with no destructive capability), not string matching.

**Why not fully met:** regex heuristics are trivially bypassed by paraphrase and offer
no defence against indirect injection via retrieved content. There is no classifier
(e.g. Azure AI Content Safety Prompt Shields) in the pipeline. The residual risk is
bounded — see LLM06 — but the control itself is shallow.

---

## LLM02 — Sensitive Information Disclosure · **Partially met**

**Implemented**
- `backend/app/guardrails/output_filter.py:scrub_output` redacts five classes of
  secret-shaped strings (API keys, bearer tokens, storage `AccountKey`, passwords,
  `sk-` prefixed keys) from model output before it reaches the user.
- Applied to every streamed text token: `backend/app/ai/orchestrator.py:89`.
- Tool results are scoped by the caller's role, so the model cannot retrieve data the
  user is not authorised for (see LLM06).
- Test: `backend/tests/test_guardrails.py::test_output_scrub_redacts_secrets`.

**Why not fully met:** pattern-based redaction is best-effort, not a DLP guarantee. It
catches secrets in recognisable formats and would miss novel ones. There is no PII
classification. Mitigating factor: this system's tools return framework control data
and scores, not customer data — the sensitive-data surface is small by design.

---

## LLM03 — Supply Chain Vulnerabilities · **Partially met**

**Implemented**
- Dependencies are pinned with minimum versions in `backend/requirements.txt`,
  `mcp-server/requirements.txt`, `frontend/package.json`.
- The model provider is a first-party managed service (Azure OpenAI) rather than an
  arbitrary third-party endpoint — `backend/app/providers/openai_provider.py`.
- CI security scanning (dependency, container, secret, SAST) is specified in Chunk 10
  (`docs/ROADMAP.md`) — **not yet implemented at time of writing.**

**Why not fully met:** the scanning pipeline is planned, not running. There is no SBOM
or AI bill of materials. Versions use `>=` rather than exact pins with a lockfile for
Python.

---

## LLM04 — Data and Model Poisoning · **Not applicable → treated as met by design**

The system performs no training, fine-tuning, or RAG ingestion. There is no vector
store and no user-supplied data enters any training corpus. The framework corpus in
`frameworks/data/` is version-controlled, schema-validated
(`frameworks/validate.py`), and referentially integrity-checked in CI — it is the only
"knowledge" the system grounds on, and it is reviewed like code.

**Honest caveat:** this is met because the architecture avoids the risk, not because a
control was built. Introducing RAG later would reopen it.

---

## LLM05 — Improper Output Handling · **Met**

**Implemented**
- Model output is never executed. It is rendered as text or used to populate a
  schema-validated architecture object — there is no `eval`, no generated SQL, no
  shell invocation anywhere in the request path.
- Tool arguments from the model are validated against Pydantic models before use
  (`mcp-server/app/models.py`); malformed input raises rather than propagating.
- The frontend renders assistant text into React text nodes (no `dangerouslySetInnerHTML`),
  so model output cannot inject markup.
- Report generation escapes every model-influenced string:
  `backend/app/reports/template.py` (via `xml.sax.saxutils.escape`), tested by
  `backend/tests/test_reports.py::test_diagram_escapes_labels`.

---

## LLM06 — Excessive Agency · **Met**

This is the strongest control in the system and the primary mitigation for LLM01.

**Implemented**
- `backend/app/guardrails/tool_policy.py:ToolPolicy` maps every MCP tool to a required
  permission and enforces **deny-by-default**: a tool absent from `TOOL_PERMISSIONS`
  can never be called, regardless of what the model requests.
- The model is only *offered* tools the current principal may use — the tool list is
  filtered per-role before the provider call (`orchestrator.py:73-75`).
- Every call is re-checked at execution time (`orchestrator.py:130`), so a model that
  hallucinates a tool name is denied and the denial is audited.
- **The tools have no destructive capability by construction.** They are read-only
  analysis functions over a static corpus: no writes, no external calls, no
  infrastructure mutation. A fully-compromised model can, at worst, read framework data.
- Tests: `test_tool_policy_readonly_denied_validation`, `test_tool_policy_auditor_cannot_remediate`,
  `test_unknown_tool_denied_by_default`, plus API-level RBAC tests
  (`test_rbac_readonly_cannot_validate`, `test_rbac_auditor_cannot_remediate`).

---

## LLM07 — System Prompt Leakage · **Met**

**Implemented**
- The system prompt (`backend/app/ai/prompts.py`) contains **no secrets and no
  security-critical logic**. It is committed in plaintext to the repository, which is
  the honest test: if leaking it caused harm, it could not be public.
- All authorisation is enforced server-side by `ToolPolicy` and FastAPI route
  dependencies — never by prompt instruction.
- The prompt file's own docstring documents this as an explicit design decision.

---

## LLM08 — Vector and Embedding Weaknesses · **Not applicable**

No embeddings, no vector store, no RAG. Retrieval is exact-match and full-text search
over a version-controlled corpus (`mcp-server/app/repository.py`, SQLite FTS5), with no
per-tenant data to leak across.

---

## LLM09 — Misinformation · **Met** — *and continuously measured*

This is the control most specific to what this product claims to do.

**Implemented**
- **The model never produces a finding, score, or compliance verdict.** All are
  computed by a deterministic rules engine (`mcp-server/app/engine.py`) over a curated
  corpus. The model's role is to narrate results it received from a tool.
- The system prompt forbids claiming a score not obtained from a tool.
- Report numbers are **re-validated server-side at generation time** rather than
  trusting the client (`backend/app/routers/reports.py`) — the report is evidence, so
  its numbers come from the engine.
- The UI states this to the user rather than hiding it: the chat composer footer reads
  *"Findings are produced by a deterministic engine over 137 controls — the assistant
  narrates, it doesn't invent."*
- Tool calls are shown live in the UI's tool-activity rail, so users can see which
  claims are tool-derived.

**Measured, not asserted** — `tests/evals/`:
- 6/6 golden architectures produce expected outcomes (100%).
- `test_scoring_is_deterministic` — identical input yields identical score across runs.
- `test_hardening_strictly_improves_score` — remediation is falsifiable, not vibes.

**Residual risk:** the model's *narration* of correct tool output can still be
imprecise. The numbers are grounded; the prose around them is not independently
verified.

---

## LLM10 — Unbounded Consumption · **Partially met**

**Implemented**
- `backend/app/guardrails/tool_policy.py:TokenBudget` enforces a per-conversation token
  ceiling (`TOKEN_BUDGET_PER_CONVERSATION`, default 200k), charged after each provider
  response (`orchestrator.py:_charge_budget`).
- Tool-call rounds are capped per turn (`MAX_TOOL_CALLS_PER_TURN`, default 8) to prevent
  runaway tool loops.
- Input length is hard-capped before reaching the model.
- Per-client rate limiting: `backend/app/middleware.py:RateLimitMiddleware`.
- Test: `backend/tests/test_guardrails.py::test_token_budget`.

**Why not fully met:** the rate limiter is in-memory and per-instance, so it does not
hold across horizontal scale — Front Door/APIM would be the authoritative edge control
in a real deployment (Chunk 10). There are no per-user spend alerts.

---

## Gaps and honest limitations

| # | Gap | Risk | Status |
|---|---|---|---|
| 1 | No prompt-injection classifier (heuristics only) | Sophisticated injection may reach the model | Accepted — bounded by read-only tools (LLM06) |
| 2 | CI security scanning specified but not implemented | Vulnerable dependency could ship | Planned — Chunk 10 |
| 3 | Rate limiting is per-instance, in-memory | Ineffective under horizontal scale | Accepted for portfolio scope; edge control documented |
| 4 | Output redaction is pattern-based | Novel secret formats could pass through | Accepted — low sensitive-data surface |
| 5 | No independent verification of model narration | Prose around correct numbers could mislead | Accepted — numbers are grounded and shown |
| 6 | No SBOM / AI-BOM | Supply chain not fully attestable | Planned |

## Verification

```bash
cd backend && pytest tests/test_guardrails.py   # 10 guardrail tests
cd backend && pytest                            # 38 backend tests incl. RBAC
python tests/evals/run_evals.py                 # 6/6 golden architectures
```
