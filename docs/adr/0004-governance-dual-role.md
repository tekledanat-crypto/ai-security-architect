# ADR-0004: AI Governance Frameworks Apply Twice

**Status:** Accepted · **Chunk:** 1

## Context
OWASP LLM Top 10, MITRE ATLAS, NIST AI RMF, ISO/IEC 42001, and the EU AI Act
were requested as build targets. They can be (a) content the MCP server
validates user architectures against, and/or (b) standards this application
itself is built and documented to.

## Decision
Both:
- **Content:** owasp-llm-top10.json and ATLAS mappings ship as framework data
  so users designing AI workloads on Azure get AI-specific findings.
- **Build standard:** the app implements LLM guardrails (Chunk 4) and ships
  auditable governance evidence (Chunk 9): AI RMF mapping, ISO 42001 SoA-lite,
  EU AI Act transparency memo, LLM Top 10 self-assessment, ATLAS threat model,
  system card, and a CI eval harness.

## Consequences
+ Strong differentiation: the app can score itself ("Secure my own app" page).
- Governance docs must be kept in sync with code; the LLM Top 10 self-assessment
  links directly to guardrail modules to reduce drift.
