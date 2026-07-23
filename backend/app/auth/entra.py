"""Microsoft Entra ID authentication (ADR-0003, Chunk 11).

Validates access tokens issued by Entra ID against the tenant's published JWKS.
Roles come from the token's `roles` claim, populated by app role assignments in the
Entra app registration — so role management lives in Entra where an administrator
expects it, not in this application's database.

What is deliberately strict here:

* **Signature is always verified** against the tenant JWKS. No `verify_signature=False`
  path exists, not even for tests — the tests mint real RSA-signed tokens instead.
* **Audience and issuer are checked.** A token minted for a different application, or
  by a different tenant, is rejected even if the signature is valid. Skipping these is
  the classic JWT validation failure.
* **`nbf`/`exp` are enforced** with no leeway beyond a small clock-skew allowance.
* **Unknown roles are dropped, not defaulted.** A token carrying a role this app does
  not recognise yields no permission rather than a fallback — failing closed.
* **No role claim means no access.** A validly-authenticated user with no app role
  assignment is rejected, rather than silently treated as ReadOnly. Authentication is
  not authorization.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from ..config import Settings
from .provider import AuthProvider, Principal, Role

log = logging.getLogger(__name__)

# Entra app roles use the same string values as the internal Role enum, so the
# mapping is identity — but it is explicit, so a rename in Entra can be absorbed
# here without touching authorization logic.
APP_ROLE_TO_ROLE: dict[str, Role] = {
    "Administrator": Role.ADMINISTRATOR,
    "SecurityArchitect": Role.SECURITY_ARCHITECT,
    "Auditor": Role.AUDITOR,
    "ReadOnly": Role.READ_ONLY,
}

CLOCK_SKEW_SECONDS = 60


class EntraAuthError(Exception):
    """Raised for a token that fails validation. Never surfaced verbatim to clients."""


class EntraAuthProvider(AuthProvider):
    """Validates Entra ID access tokens and maps app roles to internal roles."""

    def __init__(self, settings: Settings, jwk_client: PyJWKClient | None = None):
        if not settings.entra_tenant_id or not settings.entra_client_id:
            raise RuntimeError(
                "AUTH_PROVIDER=entra requires ENTRA_TENANT_ID and ENTRA_CLIENT_ID to be set."
            )

        self.tenant_id = settings.entra_tenant_id
        self.client_id = settings.entra_client_id

        # v2.0 issuer. Tokens issued by any other tenant are rejected.
        self.issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"

        # PyJWKClient caches signing keys and refreshes on unknown `kid`, which is what
        # makes Entra's key rollover a non-event.
        self._jwks = jwk_client or PyJWKClient(self.jwks_uri, cache_keys=True, lifespan=3600)

    # ── AuthProvider interface ──

    def principal_from_request(self, cookie_value: str | None, bearer: str | None) -> Principal | None:
        """Return a Principal for a valid bearer token, else None.

        The dev cookie is ignored entirely: under Entra, a signed dev cookie must not
        be a route to identity.
        """
        if not bearer:
            return None
        try:
            claims = self.validate_token(bearer)
            return self.principal_from_claims(claims)
        except EntraAuthError as exc:
            # Logged for operators; the client only ever sees a generic 401.
            log.warning("Rejected Entra token: %s", exc)
            return None

    # ── Validation ──

    def validate_token(self, token: str) -> dict[str, Any]:
        """Verify signature, issuer, audience, and lifetime. Returns claims."""
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
        except Exception as exc:  # noqa: BLE001 — network/JWKS failures are auth failures
            raise EntraAuthError(f"could not resolve signing key: {exc}") from exc

        try:
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                leeway=CLOCK_SKEW_SECONDS,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "require": ["exp", "iss", "aud", "sub"],
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise EntraAuthError("token expired") from exc
        except jwt.InvalidAudienceError as exc:
            raise EntraAuthError("audience mismatch — token was issued for another application") from exc
        except jwt.InvalidIssuerError as exc:
            raise EntraAuthError("issuer mismatch — token was issued by another tenant") from exc
        except jwt.InvalidTokenError as exc:
            raise EntraAuthError(f"invalid token: {exc}") from exc

        # Entra v2.0 access tokens carry `ver: 2.0`. A v1.0 token reaching this endpoint
        # usually means the app registration's accessTokenAcceptedVersion is misconfigured.
        if claims.get("ver") not in (None, "2.0"):
            raise EntraAuthError(f"unsupported token version {claims.get('ver')!r}; expected 2.0")

        return claims

    def principal_from_claims(self, claims: dict[str, Any]) -> Principal:
        """Map validated claims onto a Principal, failing closed on roles."""
        raw_roles = claims.get("roles") or []
        if isinstance(raw_roles, str):  # defensive: some issuers emit a single string
            raw_roles = [raw_roles]

        roles: list[Role] = []
        for raw in raw_roles:
            mapped = APP_ROLE_TO_ROLE.get(raw)
            if mapped is None:
                # Unknown role grants nothing. Logged so misconfiguration is visible.
                log.warning("Ignoring unrecognised app role %r in token", raw)
                continue
            if mapped not in roles:
                roles.append(mapped)

        if not roles:
            # Authenticated but unassigned. Rejecting is the safe default: granting
            # ReadOnly here would let anyone in the tenant read the application.
            raise EntraAuthError(
                f"principal {claims.get('sub')!r} has no recognised app role assignment"
            )

        name = (
            claims.get("name")
            or claims.get("preferred_username")
            or claims.get("upn")
            or claims.get("sub", "Unknown")
        )
        return Principal(sub=str(claims["sub"]), name=str(name), roles=roles)


def fetch_openid_configuration(tenant_id: str, timeout: float = 5.0) -> dict[str, Any]:
    """Fetch the tenant's OpenID configuration.

    Used by the /api/auth/config endpoint so the frontend does not need the discovery
    document hard-coded, and by operators verifying tenant setup.
    """
    url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
    response = httpx.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _now() -> int:
    return int(time.time())
