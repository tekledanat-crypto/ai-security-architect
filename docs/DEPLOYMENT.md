# Deployment Guide

End-to-end setup for deploying to Azure via GitHub Actions with OIDC.

> **Status:** the pipelines and templates in this repository pass static validation but
> have **not been executed** — authoring happened without an Azure subscription or a
> GitHub Actions runner. The first run should be treated as the real test. See
> `infra/README.md`.

## Why OIDC (and not a stored credential)

The conventional approach stores an `AZURE_CREDENTIALS` JSON blob — a client secret —
in GitHub. That secret is long-lived, copied into every fork's threat model, and
useful to anyone who exfiltrates it.

With OIDC federated credentials, GitHub mints a **short-lived token per run**, and
Azure validates it against a federated identity credential scoped to this repository
and environment. There is no secret to leak. A compromised repo yields nothing reusable.

This is what `AZURE_CLIENT_ID` being a **variable, not a secret**, signals: it isn't
sensitive, because possession of it grants nothing.

## 1. Create the Entra app registration

```bash
APP_NAME="ai-security-architect-deploy"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

APP_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)
az ad sp create --id "$APP_ID"
SP_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)

echo "AZURE_CLIENT_ID       = $APP_ID"
echo "AZURE_TENANT_ID       = $TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID = $SUBSCRIPTION_ID"
```

## 2. Add federated credentials

One per trust context. The `subject` must match exactly — a mismatch is the most common
cause of `AADSTS700213` at deploy time.

```bash
GH_ORG="your-org"; GH_REPO="ai-security-architect"

# main branch pushes
az ad app federated-credential create --id "$APP_ID" --parameters "{
  \"name\": \"github-main\",
  \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"repo:${GH_ORG}/${GH_REPO}:ref:refs/heads/main\",
  \"audiences\": [\"api://AzureADTokenExchange\"]
}"

# environment-scoped (required because deploy.yml uses `environment:`)
for ENV in dev prod; do
  az ad app federated-credential create --id "$APP_ID" --parameters "{
    \"name\": \"github-env-${ENV}\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:${GH_ORG}/${GH_REPO}:environment:${ENV}\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
done

# pull requests (what-if only; no apply)
az ad app federated-credential create --id "$APP_ID" --parameters "{
  \"name\": \"github-pr\",
  \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"repo:${GH_ORG}/${GH_REPO}:pull_request\",
  \"audiences\": [\"api://AzureADTokenExchange\"]
}"
```

## 3. Grant Azure permissions

`main.bicep` is subscription-scoped (it creates the resource group), so the deployer
needs subscription-level rights.

```bash
# Contributor: create resources
az role assignment create --assignee "$APP_ID" \
  --role Contributor --scope "/subscriptions/$SUBSCRIPTION_ID"

# User Access Administrator: the templates create role assignments
# (managed identity → Key Vault, ACR, OpenAI). Contributor alone cannot do this.
az role assignment create --assignee "$APP_ID" \
  --role "User Access Administrator" --scope "/subscriptions/$SUBSCRIPTION_ID"
```

> **Least privilege note.** `User Access Administrator` at subscription scope is broad.
> A hardened setup would scope both roles to a pre-created resource group and have the
> template target `resourceGroup` instead. That is the right trade for production; this
> repo optimises for one-command bootstrap and says so rather than hiding it.

## 4. Configure GitHub

**Repository → Settings → Secrets and variables → Actions**

Variables (not sensitive):
| Name | Value |
|---|---|
| `AZURE_CLIENT_ID` | `$APP_ID` |
| `AZURE_TENANT_ID` | `$TENANT_ID` |
| `AZURE_SUBSCRIPTION_ID` | `$SUBSCRIPTION_ID` |

**Settings → Environments → `dev` / `prod`**, each with secret:
| Name | Value |
|---|---|
| `POSTGRES_ADMIN_PASSWORD` | a strong generated password |

Add required reviewers on `prod` to gate production behind human approval.

## 5. Deploy

```
Actions → Deploy → Run workflow → environment: dev
```

The pipeline runs: static validation → `az bicep build` → `what-if` → build & push
images → **Trivy CRITICAL gate** → deploy → smoke test.

## Pipelines

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yml` | push, PR | Corpus validation, MCP tests, backend tests, **eval suite**, frontend build+typecheck, container builds |
| `security.yml` | push, PR, weekly | CodeQL, Bandit, Semgrep, Gitleaks, Trivy (deps + images), Checkov, governance-claim verification |
| `deploy.yml` | push to main, manual | OIDC → what-if → build/push → scan gate → deploy → smoke test |

The eval suite is a **required** CI job. If the scoring engine drifts, the build fails —
otherwise Chunk 9's harness would be decorative.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `AADSTS700213: No matching federated identity record` | The `subject` doesn't match. An `environment:`-scoped job needs an `environment:` federated credential, not a branch one. |
| `AuthorizationFailed` creating role assignments | Missing `User Access Administrator` (step 3). |
| `SubnetIsFull` | Container Apps needs a `/23` minimum. |
| Postgres unreachable from the app | Check the private DNS zone link — without it, private endpoints resolve to public IPs and the private plane silently does nothing. |
| OpenAI deployment fails with quota error | Set `deployOpenAI = false`; the app falls back to its fake provider. |

## Cost

Rough monthly estimate, `dev` with `deployOpenAI = false`:

| Resource | Est. |
|---|---|
| Container Apps (scale-to-zero) | ~€0–15 |
| PostgreSQL Flexible Server (B1ms) | ~€13 |
| Log Analytics | ~€2–5 |
| Key Vault, ACR (Standard) | ~€5 |
| **Total** | **~€20–40** |

`prod` (zone-redundant HA, min replicas, GP database, OpenAI) is materially higher —
budget €200+/month before inference costs. Run `az deployment sub what-if` and price it
before enabling.
