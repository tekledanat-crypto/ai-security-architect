# Infrastructure (Bicep)

Azure infrastructure for the AI Security Architect Assistant.

## Verification status — read this first

| Check | Status |
|---|---|
| Structure, module wiring, dependency graph | **Verified** — `python scripts/validate_bicep.py` |
| `az bicep build` (compilation) | **Not run at authoring time** — no Azure CLI available. Runs in `deploy.yml`. |
| `az deployment sub what-if` | **Not run** — requires a subscription. Runs in `deploy.yml` before every apply. |
| Actual deployment | **Never executed.** |

These templates are written to Azure's documented resource schemas and pass static
validation, but they have **not been deployed**. Treat the first `what-if` as the real
test. Saying so here is cheaper than letting someone discover it during an incident.

The static validator is not decorative: it caught a genuine circular dependency between
the frontend and backend container apps (each needed the other's FQDN) that would have
failed deployment. That's fixed — the FQDNs are now composed from the environment's
default domain.

## Design

The topology is one the product's own engine would score well. That's deliberate:
shipping infrastructure that fails our own CIS checks would be indefensible.

```
Internet
   │  HTTPS only
   ▼
┌──────────────────────────────────────────────┐
│ Container Apps Environment (VNet-injected)   │
│                                              │
│  frontend  ── external ingress               │
│     │                                        │
│     ▼                                        │
│  backend   ── internal ingress only          │
│     │                                        │
│     ▼                                        │
│  mcp-server ─ internal ingress only          │
│              (the scoring engine is not      │
│               internet-addressable)          │
└──────────────────────────────────────────────┘
   │ private endpoints / VNet injection
   ▼
Key Vault · PostgreSQL · Azure OpenAI   (no public network access)
```

## Modules

| Module | Purpose | Notable controls |
|---|---|---|
| `network.bicep` | VNet, 3 delegated subnets, NSGs (deny-by-default), private DNS zones | MCSB NS-1, NS-2 |
| `identity.bicep` | One user-assigned identity **per workload** — the backend's Key Vault access doesn't implicitly grant the frontend the same | CIS 9.5, MCSB IM-1 |
| `monitoring.bicep` | Log Analytics + App Insights, deployed first so everything diagnoses into it | CIS 5.1.1, MCSB LT-1/LT-3 |
| `keyvault.bicep` | RBAC (not access policies), private endpoint, purge protection in prod | CIS 8.1, 8.4 |
| `database.bicep` | PostgreSQL Flexible Server, VNet-injected — no public IP exists at all | CIS 5.1.2, MCSB DP-3 |
| `registry.bicep` | ACR with `adminUserEnabled: false` — no registry password to leak | MCSB IM-1 |
| `openai.bicep` | Private endpoint, `disableLocalAuth: true` — **no API key exists** | ADR-0001, OWASP LLM10 |
| `container-apps.bicep` | The three workloads, secrets resolved from Key Vault via managed identity | CIS 9.2, 9.5 |

## Deploy

```bash
az login
az account set --subscription <id>

# Preview — always do this first
az deployment sub what-if \
  --location westeurope \
  --template-file infra/main.bicep \
  --parameters infra/params/dev.bicepparam \
  --parameters postgresAdminPassword='<strong-password>'

# Apply
az deployment sub create \
  --location westeurope \
  --template-file infra/main.bicep \
  --parameters infra/params/dev.bicepparam \
  --parameters postgresAdminPassword='<strong-password>'
```

`dev` sets `deployOpenAI = false` by default — Azure OpenAI quota isn't available on
every subscription, and the app falls back to its fake provider. The deterministic
engine needs no model, so the product stays fully demonstrable either way.

## Secrets

No secret is committed. `postgresAdminPassword` is a `@secure()` parameter supplied at
deploy time; the resulting connection string is written to Key Vault and read by the
backend through its managed identity. Container Apps resolves `secretRef` values from
Key Vault at runtime — the value never appears in the template, the repo, or the
deployment log.
