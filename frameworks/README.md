# Compliance Framework Data

Structured, versioned control data that the MCP server (Chunk 3) loads to validate
user architectures, score compliance, generate remediation, and map threats.

## Contents

| File | Category | Controls |
|---|---|---|
| `data/cis-azure.json` | cloud-benchmark | 21 |
| `data/mcsb.json` | cloud-benchmark | 16 |
| `data/nist-800-53.json` | standard | 19 |
| `data/nist-csf.json` | standard | 10 |
| `data/iso-27001.json` | standard | 11 |
| `data/soc2.json` | regulatory | 8 |
| `data/azure-waf.json` | best-practice | 8 |
| `data/owasp-web-top10.json` | best-practice | 10 |
| `data/owasp-api-top10.json` | best-practice | 10 |
| `data/owasp-llm-top10.json` | ai-governance | 10 |
| `data/mitre-attack-azure.json` | threat-model | 14 |
| `data/crosswalks.json` | (index) | 17 groups |
| `data/_manifest.json` | (generated) | coverage summary |

**137 controls · 35 ATT&CK/ATLAS techniques · 17 crosswalk objectives.**

## Schemas

- `schemas/framework.schema.json` — every framework data file.
- `schemas/crosswalks.schema.json` — the crosswalk index.
- `schemas/architecture.schema.json` — the architecture object the AI emits,
  React Flow renders (Chunk 6), and the MCP validator consumes (Chunk 3).

## Adding a framework

1. Create `data/<framework_id>.json` conforming to `framework.schema.json`.
2. Add inline `crosswalk` refs on controls where equivalents exist.
3. Optionally extend `data/crosswalks.json` with new objective groups.
4. Run `python frameworks/validate.py` — it enforces schema **and** referential
   integrity (every crosswalk must resolve to a real control). CI runs this too.

## Notes on sourcing

All `summary` and `remediation` text is paraphrased into plain English. Licensed
standards (ISO 27001, SOC 2 TSC) ship as representative subsets that point to the
authoritative publications via `reference_url`; consult the originals for
certification use. `check_hints` are the machine-evaluable conditions the Chunk 3
scoring engine tests against an architecture's node `properties`.
