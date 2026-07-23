# System Card — AI Security Architect Assistant

**Version:** 0.9.0 · **Type:** Advisory AI system (design-time)
**Provider:** Portfolio project · **Model:** Azure OpenAI (GPT-4o class), inference only

---

## What it does

Interviews a user about a solution they intend to build on Microsoft Azure, proposes a
secure architecture, and validates that architecture against 11 security and compliance
frameworks (137 controls). Produces compliance scores, STRIDE threat models, prioritized
remediation, and exportable PDF reports.

## The division of labour (the most important thing on this card)

| The model does | The model does **not** do |
|---|---|
| Ask interview questions | Compute scores |
| Propose architecture structure | Decide pass/fail |
| Choose which tool to call | Produce findings |
| Narrate tool results in plain English | Determine severity |

**All findings, scores, and verdicts come from a deterministic rules engine**
(`mcp-server/app/engine.py`) evaluating machine-readable control conditions against the
architecture. The model narrates results it received from a tool. This is enforced
architecturally (the model has no scoring capability), stated in the system prompt,
disclosed in the UI, and verified by tests.

## Intended users

Cloud architects, security engineers, and DevSecOps practitioners — people qualified to
evaluate the advice they receive.

## Intended use

Design-time advisory review of a *declared* Azure architecture.

## Out-of-scope uses

- **Not** a compliance certification. A passing grade means "passed the assessed control
  set", not "compliant" or "audited".
- **Not** a runtime scanner. It reviews declared design, not deployed infrastructure. It
  cannot detect drift, misconfiguration in practice, or vulnerabilities in code.
- **Not** a replacement for penetration testing, formal audit, or professional judgment.
- **Not** for decisions about people. It evaluates infrastructure, not individuals.

## Data

| | |
|---|---|
| **Personal data processed** | None. Architectures describe infrastructure, not people. |
| **Training data** | None. No training or fine-tuning is performed. |
| **Grounding corpus** | `frameworks/data/` — 12 version-controlled JSON files, 137 controls, schema-validated with referential integrity enforced in CI |
| **Retention** | Conversations, architectures, assessments, and tool-call audit records persist in the application database |
| **Data sent to the model** | The conversation and the user's architecture. No credentials or customer data. |

## Corpus provenance and honesty

Control summaries and remediation text are **paraphrased into plain English**, not
reproduced from source publications. ISO 27001 and SOC 2 ship as *representative
subsets* pointing to the licensed originals — `frameworks/README.md` says so explicitly.
Anyone relying on this for certification must consult the authoritative publications.

## Capabilities and limits

**Capable of:** identifying missing or misconfigured security controls in a declared
Azure design across CIS Azure, Microsoft Cloud Security Benchmark, NIST 800-53, NIST
CSF, ISO 27001, SOC 2, Azure Well-Architected, OWASP Web/API/LLM Top 10, and MITRE
ATT&CK/ATLAS mappings; STRIDE threat modeling traceable to controls and techniques.

**Not capable of:**
- Assessing anything not declared in the architecture (it cannot see your real tenant)
- Evaluating application code, IaC correctness, or runtime behaviour
- Controls outside the curated corpus (which is a subset of each framework)
- Judging whether a control's *implementation* is correct — only whether it is declared

## Known limitations

1. **Assessment ≠ audit.** Coverage is a curated subset of each framework.
2. **Declared vs actual.** The system trusts the architecture description it is given.
3. **Prompt-injection defences are heuristic** — bounded by read-only tools, not by the
   filter (see `owasp-llm-top10-self-assessment.md`, LLM01).
4. **Narration is not independently verified.** The numbers are grounded; the prose
   around them can still be imprecise.
5. **Rate limiting is per-instance**, not effective across horizontal scale.
6. Six open gaps are published in the self-assessment's gap register rather than hidden.

## Human oversight

Output is advisory. The system prompt instructs the assistant to state that final
security decisions require the user's own review; every exported report carries a
Methodology & Scope section stating what the assessment does and does not cover.

## Governance

| Artefact | Location |
|---|---|
| OWASP LLM Top 10 self-assessment (with gap register) | `owasp-llm-top10-self-assessment.md` |
| NIST AI RMF mapping | `nist-ai-rmf.md` |
| ISO/IEC 42001 statement of applicability | `iso-42001-soa.md` |
| EU AI Act classification (limited risk) | `eu-ai-act-classification.md` |
| MITRE ATLAS threat model of this system | `atlas-threat-model.md` |
| Eval harness | `../../tests/evals/` |

## Verification status (Chunk 9)

| Suite | Result |
|---|---|
| Golden-architecture evals | **6/6 (100%)** |
| Eval suite total (incl. determinism, monotonicity) | 8 passed |
| Backend tests (guardrails, RBAC, streaming, reports) | 38 passed |
| MCP server tests | 35 passed |
| Framework corpus validation | 12 files valid, referential integrity verified |

## Contact

Portfolio project. Report issues via the repository's security advisory process
(`SECURITY.md`).
