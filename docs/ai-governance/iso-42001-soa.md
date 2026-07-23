# ISO/IEC 42001 — Statement of Applicability (Lite)

**System:** AI Security Architect Assistant · **Version:** 0.9.0
**Standard:** ISO/IEC 42001:2023 — AI Management System (AIMS), Annex A controls

> **Scope statement, stated up front.** ISO/IEC 42001 certifies an *organisation's*
> management system, not a piece of software. A single-developer portfolio project
> cannot be 42001-conformant and this document does not claim it is. What follows is an
> honest applicability assessment: which Annex A controls a system like this would need,
> which are implemented in this repository, and which are organisational controls
> outside its scope. Claiming otherwise would be the kind of compliance theatre this
> project exists to argue against.

**Summary: 12 implemented · 5 partially implemented · 21 organisational (out of scope).**

---

## A.2 — Policies related to AI

| Control | Status | Evidence / Rationale |
|---|---|---|
| A.2.2 AI policy | **Partial** | Design principles recorded as ADRs, incl. the explicit decision that AI governance applies to this system itself (`docs/adr/0004-governance-dual-role.md`). No signed organisational policy exists — there is no organisation. |
| A.2.3 Alignment with other policies | **Implemented** | Security policy (`SECURITY.md`) and AI governance artefacts are consistent and cross-referenced. |
| A.2.4 Review of AI policy | **Out of scope** | Requires a governance body and review cadence. |

## A.3 — Internal organisation

| Control | Status | Evidence / Rationale |
|---|---|---|
| A.3.2 AI roles and responsibilities | **Implemented** | Four-role RBAC model with an explicit permission matrix enforced in code and tested (`backend/app/auth/provider.py:ROLE_PERMISSIONS`; `test_rbac_*`). |
| A.3.3 Reporting of concerns | **Partial** | `SECURITY.md` defines a private advisory process. No internal whistleblowing channel. |

## A.4 — Resources for AI systems

| Control | Status | Evidence / Rationale |
|---|---|---|
| A.4.2 Resource documentation | **Implemented** | Every component, dependency, and data source documented across README files and ADRs. |
| A.4.3 Data resources | **Implemented** | The grounding corpus is version-controlled, schema-validated, and integrity-checked (`frameworks/README.md`, `frameworks/validate.py`). Provenance and paraphrasing stated honestly. |
| A.4.4 Tooling resources | **Implemented** | MCP tool inventory documented with the permission each requires (`mcp-server/README.md`, `guardrails/tool_policy.py`). |
| A.4.5 System & computing resources | **Implemented** | Runtime architecture documented; IaC and deployment topology specified (`infra/`, Chunk 10). |
| A.4.6 Human resources | **Out of scope** | Competence records, training — organisational. |

## A.5 — Assessing impacts of AI systems

| Control | Status | Evidence / Rationale |
|---|---|---|
| A.5.2 AI system impact assessment process | **Implemented** | EU AI Act classification memo performs a structured impact assessment against every Annex III area (`eu-ai-act-classification.md`). |
| A.5.3 Documentation of impact assessments | **Implemented** | Same document, version-controlled, with explicit reclassification triggers. |
| A.5.4 Assessing impacts on individuals | **Implemented** | Assessed and documented as not applicable: no personal data, no determinations about people (`system-card.md`). |
| A.5.5 Assessing societal impacts | **Partial** | Considered in the ATLAS threat model (AML.T0062: wrong verdict → insecure system shipped). Not a formal societal impact study. |

## A.6 — AI system life cycle

| Control | Status | Evidence / Rationale |
|---|---|---|
| A.6.1.2 Objectives for responsible development | **Implemented** | ADR-0004 commits, before implementation, to applying AI governance to this system — not just to the systems it assesses. |
| A.6.1.3 Processes for responsible design | **Implemented** | Chunked build with contracts, ADRs recorded before code, threat model of the system itself. |
| A.6.2.2 AI system requirements | **Implemented** | Purpose, users, and out-of-scope uses documented (`system-card.md`). |
| A.6.2.3 Documentation of design | **Implemented** | ADRs + per-component READMEs + shared JSON Schemas as explicit contracts. |
| A.6.2.4 Verification and validation | **Implemented** | Golden-architecture eval suite (6/6), determinism test, monotonic-improvement test, 38 backend + 35 MCP tests. |
| A.6.2.5 Deployment | **Partial** | Bicep IaC and OIDC-based CI/CD specified (Chunk 10), not yet implemented. |
| A.6.2.6 Operation and monitoring | **Partial** | Tool-call audit trail implemented (`db/models.py:ToolAudit`). Production telemetry is deployment-stage. |
| A.6.2.7 Technical documentation | **Implemented** | This directory plus per-component documentation. |
| A.6.2.8 Recording of event logs | **Implemented** | Every tool invocation logged with principal, arguments, decision, outcome, duration. |

## A.7 — Data for AI systems

| Control | Status | Evidence / Rationale |
|---|---|---|
| A.7.2 Data for development | **Implemented** | No training data. Grounding corpus curated, versioned, validated. |
| A.7.3 Acquisition of data | **Implemented** | Corpus authored from public framework publications, paraphrased; licensed standards shipped as representative subsets with attribution (`frameworks/README.md`). |
| A.7.4 Quality of data | **Implemented** | Schema + referential-integrity validation in CI; has caught a real defect. |
| A.7.5 Provenance of data | **Implemented** | Each framework file records publisher, version, and `reference_url`. |
| A.7.6 Data preparation | **Implemented** | Documented transformation from publications to machine-evaluable `check_hints`. |

## A.8 — Information for interested parties

| Control | Status | Evidence / Rationale |
|---|---|---|
| A.8.2 System documentation for users | **Implemented** | System card states capabilities, limits, and out-of-scope uses plainly. |
| A.8.3 External reporting | **Implemented** | `SECURITY.md` advisory process. |
| A.8.4 Communication of incidents | **Out of scope** | Requires an operating organisation. |
| A.8.5 Information for interested parties | **Implemented** | Governance artefacts are public in the repository. |

## A.9 — Use of AI systems

| Control | Status | Evidence / Rationale |
|---|---|---|
| A.9.2 Processes for responsible use | **Implemented** | Advisory-only framing enforced in the system prompt and every report's Methodology section. |
| A.9.3 Objectives for responsible use | **Implemented** | Out-of-scope uses enumerated in the system card (not a certification, not a runtime scanner, not a replacement for audit). |
| A.9.4 Intended use | **Implemented** | Design-time advisory review of declared Azure architectures. |

## A.10 — Third-party relationships

| Control | Status | Evidence / Rationale |
|---|---|---|
| A.10.2 Allocation of responsibilities | **Implemented** | The model provider (Azure OpenAI) is responsible for GPAI obligations; this system is a downstream deployer (`eu-ai-act-classification.md` §4). |
| A.10.3 Suppliers | **Partial** | Provider abstraction avoids lock-in; no formal supplier due-diligence process. |
| A.10.4 Customers | **Out of scope** | No customers. |

---

## Honest conclusion

Where 42001's Annex A maps onto **artefacts a software project can produce** —
documented design, impact assessment, data governance, verification, logging, user
information — this repository implements them substantively, with evidence. Where it
maps onto **an operating organisation** — policy approval, competence management,
incident communication, supplier audits — it does not, and pretending otherwise would
undermine the point.

The value of this document is the applicability analysis itself: knowing which controls
a system like this genuinely needs, and being straight about the rest.
