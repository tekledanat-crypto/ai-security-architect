# Build Roadmap & Resume Point

**Purpose:** this project is built in self-contained chunks so any interrupted session
can resume without rework. Whoever continues this build (human or AI assistant):

1. Read this file first.
2. Find the first unchecked chunk below — that is the resume point.
3. Read the "Contract" of that chunk and any linked ADRs before writing code.
4. When a chunk is complete, check it off, update "Last completed", and commit.

**Last completed:** Chunk 11 — Entra ID authentication: EntraAuthProvider with full JWT validation (JWKS signature, issuer, audience, exp/nbf), app roles from token claims failing closed on unknown/absent roles, MSAL authorization-code+PKCE frontend with in-memory token cache, real Identity & Access settings page, mock auth blocked in production at startup. 27 new tests minting real RS256 tokens (forged signature, tampered payload, alg:none, wrong audience/tenant all rejected), mutation-tested. ADR-0003's bet confirmed: zero route changes.
**Status:** All 11 chunks complete.

---

## Locked Decisions (do not re-litigate without an ADR)

- AI provider: **Azure OpenAI**, behind an OpenAI-compatible provider abstraction
  (`AI_PROVIDER` env switch; plain OpenAI works as local fallback). → ADR-0001
- Database: **SQLite dev → PostgreSQL prod**, single SQLAlchemy codebase. → ADR-0002
- Auth: **mock auth first** (role-switchable dev identity), Entra ID in Chunk 11. → ADR-0003
- Governance frameworks (OWASP LLM Top 10, MITRE ATLAS, NIST AI RMF, ISO 42001,
  EU AI Act) apply **both** as build standards for this app AND as MCP validation
  content. → ADR-0004
- Framework data depth: deep on CIS Azure + Microsoft Cloud Security Benchmark;
  mid-depth NIST 800-53 / OWASP LLM Top 10 / ATT&CK mappings; representative on rest.
- Diagram: AI generates React Flow graph from conversation; nodes manually editable.
- Local-first: docker-compose is the source of truth until Azure access confirmed.

---

## Chunks

### ✅ Chunk 1 — Scaffold & Foundation
Repo structure, README, this roadmap, docker-compose skeleton, .env.example,
.gitignore, Makefile, ADRs 0001–0004, framework JSON Schema, one sample framework
file proving the schema, security policy stub.

### ✅ Chunk 2 — Framework Data
**Contract:** populate `frameworks/data/` with JSON conforming to
`frameworks/schemas/framework.schema.json`. Files: `cis-azure.json` (deep, ~40+
controls), `mcsb.json` (deep), `nist-800-53.json` (mid, key families: AC, AU, IA,
SC, SI, CM, IR), `nist-csf.json`, `iso-27001.json`, `soc2.json`, `azure-waf.json`,
`owasp-web-top10.json`, `owasp-api-top10.json`, `owasp-llm-top10.json`,
`mitre-attack-azure.json` (technique→service mappings), `crosswalks.json`
(CIS↔800-53↔ISO mappings). Each control needs: id, title, summary (paraphrased,
never verbatim from source), severity, azure_services, check_hints, remediation,
references. Validate all files against the schema in CI (script:
`frameworks/validate.py` — create it in this chunk).

### ✅ Chunk 3 — MCP Server
**Contract:** Python MCP server in `mcp-server/` using the official `mcp` SDK.
Transports: stdio + streamable HTTP (port 8100). Tools: `list_frameworks`,
`find_control`, `search_controls` (FTS over SQLite), `validate_architecture`
(input: architecture JSON per `frameworks/schemas/architecture.schema.json`),
`score_architecture`, `generate_remediation`, `map_service`, `list_best_practices`,
`compare_frameworks`, `crosswalk_control`, `map_threats`, `get_stride_threats`.
Deterministic scoring engine (weighted by severity). Pytest suite per tool.
Dockerfile in `docker/mcp-server.Dockerfile`.

### ✅ Chunk 4 — Backend (FastAPI)
**Contract:** `backend/` FastAPI app. AI orchestration: streaming chat endpoint (SSE),
tool calling routed through an MCP client to the MCP server, conversation + architecture
persistence (SQLAlchemy models: User, Conversation, Message, Architecture, Assessment,
Finding). Provider abstraction per ADR-0001. **LLM guardrails module** (`backend/app/guardrails/`):
input length/content limits, prompt-injection heuristics, tool allow-list per role,
output filtering, token budget, full audit log of tool calls (OWASP LLM01/02/06/08).
Mock auth per ADR-0003. Pytest + httpx tests. Dockerfile.

### ✅ Chunk 5 — Frontend Shell + Chat
**Contract:** Next.js (App Router) + Tailwind + shadcn/ui, dark Azure-Portal-style
theme. Layout with sidebar nav (Dashboard, AI Assistant, Architecture Designer,
Compliance, Threat Model, Reports, Settings). AI Assistant page: streaming chat,
visible tool-call activity panel ("Called validate_architecture → 3 failed controls").
Read `/mnt/skills/public/frontend-design/SKILL.md` before building. Dockerfile.

### ✅ Chunk 6 — Architecture Designer
**Contract:** React Flow canvas. AI emits architecture JSON (schema from Chunk 3);
frontend renders it as an Azure diagram (custom nodes with Azure service icons/colors,
grouped by network zone). Manual add/edit/delete of nodes and edges syncs back to the
architecture JSON. "Validate" button → backend → MCP → results drawer.

### ✅ Chunk 7 — Compliance & Threat Model Pages
**Contract:** Compliance Results page (per-framework pass/fail matrix, failed controls
with plain-English explanation + remediation). Threat Model page (STRIDE table
generated per architecture, mitigations, ATT&CK technique links).

### ✅ Chunk 8 — Dashboard + Reports
**Contract:** Dashboard (security score, compliance score, architecture health,
critical/medium risks, passed/failed controls, recent conversations). PDF export
(server-side, WeasyPrint) containing executive summary, architecture summary,
diagram image (React Flow → PNG via html-to-image upload), findings, STRIDE table,
compliance matrix, recommendations, risk score.

### ✅ Chunk 9 — AI Governance Docs (build-standard evidence)
**Contract:** `docs/ai-governance/`: NIST AI RMF mapping (Govern/Map/Measure/Manage),
ISO 42001 AIMS-lite statement of applicability, EU AI Act classification memo
(limited-risk, transparency obligations + how the UI meets them), OWASP LLM Top 10
self-assessment (control-by-control, pointing at guardrails code), MITRE ATLAS
threat model of this app, model card / system card. Plus an **eval harness**:
golden architectures with expected findings, runnable in CI (`tests/evals/`).

### ✅ Chunk 10 — CI/CD + IaC
**Contract:** GitHub Actions: `ci.yml` (lint, type-check, tests, framework schema
validation, eval harness) and `security.yml` (CodeQL, Bandit, Semgrep, Gitleaks,
Trivy image scan, Checkov/PSRule on Bicep), `deploy.yml` (OIDC federated creds,
no stored secrets → Azure Container Apps for backend+MCP, App Service or Static
Web Apps for frontend). Bicep in `infra/`: Container Apps env, Key Vault, Managed
Identity, Postgres Flexible Server, Log Analytics, App Insights, private endpoints,
Azure OpenAI. Deployment guide in `docs/`.

### ☐ Chunk 11 — Entra ID Auth
**Contract:** Replace mock auth: MSAL (frontend) + JWT validation (backend),
app roles: Administrator, SecurityArchitect, Auditor, ReadOnly. Role enforcement
on API routes and UI routes. Setup guide `docs/ENTRA_SETUP.md`.

---

## How to resume with an AI assistant

Upload this repo (or share the GitHub URL) and say:
"Read docs/ROADMAP.md and continue from the resume point."
