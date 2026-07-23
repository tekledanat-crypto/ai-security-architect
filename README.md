# AI Security Architect Assistant

An AI-powered Azure cloud security design platform. The assistant interviews you about
your solution, designs a secure Azure architecture, validates it against compliance
frameworks through a custom **MCP (Model Context Protocol) server**, performs STRIDE
threat modeling, renders architecture diagrams, and exports professional PDF reports.

Built as a production-quality portfolio application demonstrating:

Cloud Security · Azure · AI Engineering · MCP · DevSecOps · Compliance Automation ·
Secure SDLC · Modern Full Stack Development

> **Governance note:** this application is itself built and documented against
> OWASP LLM Top 10, MITRE ATLAS, NIST AI RMF, ISO/IEC 42001, and the EU AI Act.
> See [`docs/ai-governance/`](docs/) (Chunk 9) and the ADRs in [`docs/adr/`](docs/adr/).

---

## Status

This repository is built in resumable chunks. **Check [`docs/ROADMAP.md`](docs/ROADMAP.md)
for the current build status before doing anything else.**

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js · React · TypeScript · Tailwind CSS · shadcn/ui · React Flow |
| Backend | FastAPI (Python 3.12) · SQLAlchemy · Pydantic v2 |
| AI | Azure OpenAI (OpenAI-compatible provider abstraction) · tool calling · streaming |
| MCP | Custom Python MCP server (stdio + streamable HTTP) |
| Database | SQLite (dev) → PostgreSQL (prod) via SQLAlchemy |
| Auth | Mock auth (dev) → Microsoft Entra ID (Chunk 11) |
| IaC | Bicep (Azure Container Apps, App Service, Key Vault, Postgres Flexible Server) |
| CI/CD | GitHub Actions with security scanning (CodeQL, Bandit, Semgrep, Trivy, Gitleaks, Checkov) |

## Quick Start (local, no Azure required)

```bash
cp .env.example .env          # fill in an AI provider key (see AI Provider section)
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- MCP server (streamable HTTP): http://localhost:8100/mcp

Or run services natively — see `docs/DEVELOPMENT.md` (Chunk 4/5).

## AI Provider

The AI layer is provider-agnostic behind one interface. Set in `.env`:

```
AI_PROVIDER=azure-openai      # or: openai
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...      # replaced by Managed Identity in Azure deployment
AZURE_OPENAI_DEPLOYMENT=gpt-4o
# fallback for local dev without an Azure subscription:
OPENAI_API_KEY=...
```

## Repository Map

```
frontend/          Next.js app (dashboard, chat, designer, compliance, threats, reports)
backend/           FastAPI app — AI orchestration, LLM guardrails, REST API, persistence
mcp-server/        Custom MCP server exposing security & compliance tools
frameworks/        Compliance framework data (versioned JSON) + JSON Schemas
docs/              Architecture docs, ADRs, roadmap, AI governance artifacts
infra/             Bicep IaC modules
docker/            Dockerfiles per service
tests/             Cross-service integration tests (unit tests live in each service)
.github/workflows/ CI/CD pipelines with DevSecOps scanning stages
```

## Compliance Frameworks Included

**Validation content (MCP server):** CIS Azure Benchmark · Microsoft Cloud Security
Benchmark · NIST CSF · NIST 800-53 · ISO 27001 · SOC 2 · Azure Well-Architected ·
OWASP Web Top 10 · OWASP API Top 10 · MITRE ATT&CK mappings

**Build standards (this app):** OWASP LLM Top 10 · MITRE ATLAS · NIST AI RMF ·
ISO/IEC 42001 · EU AI Act transparency obligations

## License

Portfolio project. Framework control texts are paraphrased summaries with references
to the authoritative sources; consult the original publications for compliance use.

## AI Governance

This system assesses architectures against AI governance frameworks — so it applies them
to itself. See [`docs/ai-governance/`](docs/ai-governance/):

- **[System card](docs/ai-governance/system-card.md)** — capabilities, limits, and the
  division of labour: the model narrates, a deterministic engine decides.
- **[OWASP LLM Top 10 self-assessment](docs/ai-governance/owasp-llm-top10-self-assessment.md)**
  — 4 met, 5 partial, 1 N/A, every claim citing code and tests, with a published gap register.
- **[NIST AI RMF](docs/ai-governance/nist-ai-rmf.md)** — MEASURE backed by a running eval suite.
- **[ISO/IEC 42001 SoA](docs/ai-governance/iso-42001-soa.md)** — honest applicability, not a
  conformance claim.
- **[EU AI Act classification](docs/ai-governance/eu-ai-act-classification.md)** — limited risk,
  with the Annex III(2) analysis spelled out.
- **[MITRE ATLAS threat model](docs/ai-governance/atlas-threat-model.md)** — of this system.

Claims are measured, not asserted: `make evals` runs 6 golden architectures against the
engine (6/6 passing), including determinism and monotonic-improvement checks.

## CI/CD & Infrastructure

Three GitHub Actions workflows and Bicep IaC — see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

- **`ci.yml`** — corpus validation, MCP + backend tests, frontend build, container builds,
  and the **eval suite as a required gate**: if the scoring engine drifts, the build fails.
- **`security.yml`** — CodeQL, Bandit, Semgrep, Gitleaks, Trivy (deps + images), Checkov,
  plus a job that verifies the governance docs still cite real files and tests.
- **`deploy.yml`** — OIDC federated credentials (no stored secret), `what-if` preview,
  Trivy CRITICAL gate, smoke test.

The [Bicep](infra/) deploys infrastructure this product's own engine would score well:
VNet-injected Postgres with no public IP, private-endpoint Key Vault and Azure OpenAI
with `disableLocalAuth` (no API key exists), one managed identity per workload, and an
internal-only backend and MCP server.

> The templates pass static validation but have **not been deployed** — see
> [`infra/README.md`](infra/README.md) for what is and isn't verified.
