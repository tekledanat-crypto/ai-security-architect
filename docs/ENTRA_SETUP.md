# Microsoft Entra ID Setup

Configuring real authentication. Local development needs none of this — the app runs
with mock auth out of the box (ADR-0003).

> **Status:** the code paths here are tested against locally-minted RS256 tokens and a
> fake JWKS (27 tests, `backend/tests/test_entra_auth.py`), including forged
> signatures, tampered payloads, `alg: none`, wrong audience, and wrong tenant. They
> have **not** been run against a live Entra tenant — no tenant was available at
> authoring time. Treat the first real sign-in as the integration test.

## Model

| | |
|---|---|
| **Flow** | Authorization code + PKCE (SPA), access token to the API |
| **Token validation** | Signature via tenant JWKS, plus issuer, audience, `exp`, `nbf` |
| **Roles** | Entra **app roles**, delivered in the token's `roles` claim |
| **Role storage** | In Entra. This application stores no role assignments. |
| **No role assigned** | **Access denied.** Authentication is not authorization. |

Roles live in Entra deliberately: an administrator revoking someone's access should not
need to touch this application's database, and an auditor should be able to answer "who
can do what" from the directory.

## 1. Register the application

```bash
az ad app create \
  --display-name "AI Security Architect" \
  --sign-in-audience AzureADMyOrg \
  --enable-id-token-issuance false \
  --enable-access-token-issuance false

APP_ID=$(az ad app list --display-name "AI Security Architect" --query "[0].appId" -o tsv)
OBJECT_ID=$(az ad app list --display-name "AI Security Architect" --query "[0].id" -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
```

## 2. Expose the API scope

The SPA requests this scope; the backend validates tokens carrying it.

```bash
az ad app update --id "$APP_ID" --identifier-uris "api://$APP_ID"

az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$OBJECT_ID" \
  --headers 'Content-Type=application/json' \
  --body "{
    \"api\": {
      \"requestedAccessTokenVersion\": 2,
      \"oauth2PermissionScopes\": [{
        \"id\": \"$(uuidgen)\",
        \"value\": \"access_as_user\",
        \"type\": \"User\",
        \"adminConsentDisplayName\": \"Access AI Security Architect\",
        \"adminConsentDescription\": \"Allows the app to call the API as the signed-in user.\",
        \"userConsentDisplayName\": \"Access AI Security Architect\",
        \"userConsentDescription\": \"Allows the app to call the API on your behalf.\",
        \"isEnabled\": true
      }]
    }
  }"
```

> `requestedAccessTokenVersion: 2` matters. The backend rejects v1.0 tokens
> (`test_v1_token_is_rejected`) because a v1 token arriving here means this setting is
> wrong, and silently accepting it would mask the misconfiguration.

## 3. Define the four app roles

```bash
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$OBJECT_ID" \
  --headers 'Content-Type=application/json' \
  --body "{
    \"appRoles\": [
      {\"id\": \"$(uuidgen)\", \"allowedMemberTypes\": [\"User\"], \"value\": \"Administrator\",
       \"displayName\": \"Administrator\", \"description\": \"Full access including settings.\", \"isEnabled\": true},
      {\"id\": \"$(uuidgen)\", \"allowedMemberTypes\": [\"User\"], \"value\": \"SecurityArchitect\",
       \"displayName\": \"Security Architect\", \"description\": \"Design, validate, remediate, report.\", \"isEnabled\": true},
      {\"id\": \"$(uuidgen)\", \"allowedMemberTypes\": [\"User\"], \"value\": \"Auditor\",
       \"displayName\": \"Auditor\", \"description\": \"Read, validate, threat-model, export reports.\", \"isEnabled\": true},
      {\"id\": \"$(uuidgen)\", \"allowedMemberTypes\": [\"User\"], \"value\": \"ReadOnly\",
       \"displayName\": \"Read Only\", \"description\": \"View assessments only.\", \"isEnabled\": true}
    ]
  }"
```

The `value` strings must match exactly — they map to the internal roles in
`backend/app/auth/entra.py:APP_ROLE_TO_ROLE`. An unrecognised role grants nothing.

## 4. Configure the SPA redirect URI

```bash
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$OBJECT_ID" \
  --headers 'Content-Type=application/json' \
  --body "{
    \"spa\": { \"redirectUris\": [
      \"http://localhost:3000\",
      \"https://<your-frontend-fqdn>\"
    ]}
  }"
```

Register it under `spa`, not `web`. The `web` platform issues tokens without PKCE and
expects a client secret — wrong for a browser app, and MSAL will reject the flow.

## 5. Assign users

**Entra admin centre → Enterprise applications → AI Security Architect → Users and groups
→ Add user/group.**

Assign a role to every user. A user who authenticates with no assigned role is denied
(`test_no_roles_claim_is_rejected`) rather than defaulted to ReadOnly — granting silent
read access to anyone in the tenant would be the wrong default.

Optionally require assignment:
```bash
SP_ID=$(az ad sp list --filter "appId eq '$APP_ID'" --query "[0].id" -o tsv)
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$SP_ID" \
  --headers 'Content-Type=application/json' \
  --body '{"appRoleAssignmentRequired": true}'
```

## 6. Configure the application

```bash
AUTH_PROVIDER=entra
APP_ENV=production
ENTRA_TENANT_ID=<tenant-id>
ENTRA_CLIENT_ID=<app-id>
```

The frontend needs no build-time configuration: it fetches `/api/auth/config` at
startup, so one image deploys to any tenant.

In Azure, these are set by `infra/modules/container-apps.bicep`. Neither value is
secret — possession of a client ID grants nothing in a PKCE flow — which is why they
are deployment variables rather than secrets.

## Guards

| Guard | Behaviour |
|---|---|
| `AUTH_PROVIDER=mock` + `APP_ENV=production` | **Application refuses to start.** A misconfigured deployment fails loudly at boot rather than serving forgeable identities. |
| `AUTH_PROVIDER=entra` without tenant/client ID | Refuses to start. |
| Dev identity cookie under Entra | Ignored entirely. A signed dev cookie is never a route to identity. |
| Token for another application | Rejected (audience check). |
| Token from another tenant | Rejected (issuer check). |
| Expired / not-yet-valid token | Rejected, with 60s clock-skew allowance. |
| Unrecognised app role | Dropped. If no recognised role remains, access denied. |

## Verify

```bash
cd backend && pytest tests/test_entra_auth.py -v   # 27 tests
```

These mint real RS256-signed JWTs rather than mocking `jwt.decode`, so signature,
audience, issuer, and expiry checks are genuinely exercised. Confirmed by mutation
testing: disabling audience verification makes
`test_token_for_another_application_is_rejected` fail, as it should.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Sign-in succeeds, API returns 401 | No app role assigned, or the role `value` doesn't match `APP_ROLE_TO_ROLE`. Backend logs name the rejected role. |
| `AADSTS650053` invalid scope | Scope must be `api://<client-id>/access_as_user`. |
| `AADSTS9002326` cross-origin token redemption | Redirect URI registered under `web` instead of `spa`. |
| Backend logs "unsupported token version '1.0'" | `requestedAccessTokenVersion` is not 2 (step 2). |
| App won't start: "not permitted when APP_ENV=production" | Working as designed — set `AUTH_PROVIDER=entra`. |
