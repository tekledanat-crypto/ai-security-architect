# Security Policy

This is a portfolio project, but it is built to production security standards.

## Application security controls (implemented per chunk)
- LLM guardrails: input limits, prompt-injection heuristics, tool allow-listing,
  output filtering, token budgets, tool-call audit logging (Chunk 4;
  OWASP LLM Top 10 self-assessment in docs/ai-governance/, Chunk 9)
- RBAC on every API route via the Principal abstraction (Chunk 4/11)
- HTTPS-only, secure headers, rate limiting, strict input validation (Chunk 4)
- Secrets: never in code; .env locally, Azure Key Vault + Managed Identity in cloud
- Dependency, container, secret, SAST, and IaC scanning in CI (Chunk 10)

## Reporting
Open a private GitHub security advisory on this repository.
