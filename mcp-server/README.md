# MCP Server — AI Security Architect

A custom **Model Context Protocol** server exposing 12 security & compliance tools.
The backend's AI orchestrator (Chunk 4) calls these instead of relying on model
knowledge, keeping every finding grounded in the framework corpus (ADR-0004).

## Tools

| Tool | Purpose |
|---|---|
| `list_frameworks` | List all frameworks with metadata |
| `find_control` | Look up a control by ID |
| `search_controls` | Full-text search (SQLite FTS5) over all controls |
| `list_best_practices` | Best practices, filterable by service/framework |
| `map_service` | Map an Azure service → controls, STRIDE, ATT&CK |
| `validate_architecture` | Full per-control pass/fail findings + scores |
| `score_architecture` | Concise compliance scorecard |
| `generate_remediation` | Prioritized, deduplicated fix plan |
| `get_stride_threats` | STRIDE threat model grounded in failing controls |
| `map_threats` | Service → MITRE ATT&CK/ATLAS techniques + mitigations |
| `crosswalk_control` | Equivalent controls in other frameworks |
| `compare_frameworks` | Shared objectives between two frameworks |

## Architecture

```
app/
  models.py       Pydantic domain models (mirror the JSON Schemas)
  repository.py   Loads framework JSON + SQLite FTS5 search index
  engine.py       Deterministic validation & severity-weighted scoring
  threats.py      STRIDE threat modeling + remediation generation
  tools.py        Pure tool logic (fully unit-tested, protocol-free)
  server.py       FastMCP protocol wrapper (stdio + streamable HTTP)
  http.py         ASGI entrypoint for uvicorn
```

The scoring engine is **deterministic** — the AI narrates results but never
invents them (NIST AI RMF; OWASP LLM09 mitigation).

## Run

```bash
pip install -r requirements-dev.txt

# stdio transport (spawned by an MCP client)
python -m app.server

# streamable HTTP transport (network; backend connects here)
python -m app.server --http           # or: uvicorn app.http:app --port 8100
```

MCP endpoint: `http://localhost:8100/mcp`

## Test

```bash
pytest            # 35 tests: data integrity, engine, tools, threat modeling
```

## Scoring model

Severity-weighted (critical 10 / high 6 / medium 3 / low 1). A control is scored
only when *applicable* — i.e. at least one `check_hint` targets a service present
in the architecture (or is a global/presence check on a non-empty design). Score =
100 × (earned weight / possible weight). Grades: A ≥90, B ≥80, C ≥70, D ≥60, else F.
