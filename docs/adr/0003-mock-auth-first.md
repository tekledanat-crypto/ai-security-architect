# ADR-0003: Mock Auth First, Entra ID in Chunk 11

**Status:** Accepted · **Chunk:** 1

## Context
Entra ID requires tenant configuration the developer cannot yet confirm.
Role-based behavior (Administrator, SecurityArchitect, Auditor, ReadOnly) must
be designed in from the start or retrofitting RBAC becomes expensive.

## Decision
Backend depends on an `AuthProvider` interface returning a Principal
{sub, name, roles[]}. Dev implementation: `MockAuthProvider` reading a
signed dev cookie; the UI gets a role-switcher in Settings (dev builds only).
Chunk 11 swaps in `EntraAuthProvider` (JWT validation, app roles) with **no
changes to route-level authorization code**, which is written against Principal
from day one.

## Consequences
+ RBAC is real from Chunk 4 even though the IdP is fake.
+ Interviews can demo role behavior without a tenant.
- Mock provider must be impossible to enable in production (env guard + startup check).

## Outcome (recorded at Chunk 11)

**The bet paid off.** Adding `EntraAuthProvider` required:

- one new file (`backend/app/auth/entra.py`),
- a change to `build_auth_provider` to dispatch on config,
- **zero changes to any route or authorization check.**

All 38 pre-existing backend tests passed unchanged after the swap. Route handlers
depend on `Principal` and `require_permission(...)`; neither knows or cares whether the
principal came from a signed dev cookie or a validated Entra JWT.

What made this work was resisting the temptation to let auth details leak outward:
`current_principal` extracts the bearer token in one place, and everything downstream
sees only a `Principal`. Had routes inspected cookies or tokens directly, this would
have been a rewrite rather than a swap.

One addition: the production guard moved up into `build_auth_provider`, so a deployment
configured with `AUTH_PROVIDER=mock` and `APP_ENV=production` fails at startup rather
than serving forgeable identities.
