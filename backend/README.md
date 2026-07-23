# Backend — AI Security Architect

FastAPI service providing AI orchestration, the LLM guardrails, RBAC, and the REST
API. Streams the assistant over SSE and routes tool calls through an MCP client to
the Chunk 3 server.

## Layout
```
app/
  config.py            Settings (AI provider, DB, auth, guardrail limits)
  main.py              App factory: middleware, CORS, routers, lifespan
  deps.py              DI: principal, permission guards, provider, MCP client
  middleware.py        Secure headers + rate limiting
  auth/provider.py     Principal, Role, RBAC, MockAuthProvider (ADR-0003)
  providers/           AI provider abstraction: fake, azure-openai, openai (ADR-0001)
  ai/
    mcp_client.py      HTTP + in-process MCP transports
    orchestrator.py    Streaming tool-calling loop with guardrails
    prompts.py         System prompt
  guardrails/
    input_filter.py    Length limit + prompt-injection heuristics (LLM01)
    tool_policy.py     Per-role tool allow-list + token budget (LLM06/LLM10)
    output_filter.py   Secret scrubbing + tool-call audit log (LLM02/LLM06/LLM08)
  db/                  SQLAlchemy async models + session (ADR-0002)
  routers/             meta, auth, chat (SSE), architecture
```

## Run (keyless, offline)
```bash
pip install -r requirements-dev.txt
# fake AI + in-process tools — no keys, no separate MCP server needed:
AI_PROVIDER=fake MCP_TRANSPORT=in-process uvicorn app.main:app --port 8000 --reload
```
Docs at http://localhost:8000/docs

## Run against the real MCP server (production-faithful)
```bash
# terminal 1
cd ../mcp-server && uvicorn app.http:app --port 8100
# terminal 2
MCP_TRANSPORT=http MCP_SERVER_URL=http://localhost:8100/mcp uvicorn app.main:app --port 8000
```

## Provider selection (ADR-0001)
`AI_PROVIDER=fake` auto-upgrades to `azure-openai` when
`AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` are set, or to `openai` with
`OPENAI_API_KEY`. No code change required.

## Guardrails (OWASP LLM Top 10 — evidence for Chunk 9)
- **LLM01** input length limit + injection heuristics (flag + log, not naive block)
- **LLM02** output secret-scrubbing before the user sees model text
- **LLM06** per-role tool allow-list; deny-by-default for unknown tools
- **LLM08** full tool-call audit trail persisted to `tool_audit`
- **LLM09** deterministic scoring engine is authoritative; the model narrates, never invents
- **LLM10** per-conversation token budget

## Test
```bash
pytest      # 25 tests: guardrails, RBAC, streaming chat, tool calls, audit, RBAC-403s
```

## Reports (Chunk 8)
`POST /api/reports/generate` → PDF (requires the `report` permission; Auditors included,
ReadOnly denied).

- `app/reports/diagram.py` — renders the architecture JSON to inline SVG server-side
  (zone columns, failing nodes outlined red). No browser, no screenshot pipeline.
- `app/reports/template.py` — print-oriented HTML/CSS (A4, running headers, page numbers).
  Deliberately light-themed: this document gets printed and emailed, unlike the console UI.
- `app/reports/generator.py` — WeasyPrint render, with graceful fallback to printable HTML
  if native cairo/pango deps are unavailable.

The endpoint **re-validates server-side** rather than trusting client-supplied results —
the report is evidence, so its numbers must come from the engine (OWASP LLM09).
WeasyPrint native deps are installed in `docker/backend.Dockerfile`.
