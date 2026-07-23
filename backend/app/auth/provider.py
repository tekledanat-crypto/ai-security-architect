"""Authentication & authorization (ADR-0003).

Routes depend on a `Principal` returned by an `AuthProvider`. In dev we use a
signed-cookie MockAuthProvider with a role switcher; Chunk 11 swaps in an
EntraAuthProvider (JWT validation) with NO changes to route-level authorization,
because everything downstream is written against `Principal` and `Role`.
"""
from __future__ import annotations

from enum import Enum

from itsdangerous import BadSignature, URLSafeSerializer
from pydantic import BaseModel

from ..config import Settings, get_settings


class Role(str, Enum):
    ADMINISTRATOR = "Administrator"
    SECURITY_ARCHITECT = "SecurityArchitect"
    AUDITOR = "Auditor"
    READ_ONLY = "ReadOnly"


# Permission model. Kept coarse and explicit so it reads like a policy table.
# Auditor is read-only-plus-reports; ReadOnly cannot run assessments or chat-mutate.
ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMINISTRATOR: {
        "chat", "design", "validate", "remediate", "threat-model",
        "report", "read", "manage-settings",
    },
    Role.SECURITY_ARCHITECT: {
        "chat", "design", "validate", "remediate", "threat-model", "report", "read",
    },
    Role.AUDITOR: {"read", "report", "validate", "threat-model"},
    Role.READ_ONLY: {"read"},
}


class Principal(BaseModel):
    sub: str
    name: str
    roles: list[Role]

    def has_permission(self, permission: str) -> bool:
        return any(permission in ROLE_PERMISSIONS.get(r, set()) for r in self.roles)

    @property
    def primary_role(self) -> Role:
        # Highest-privilege role wins for display purposes.
        for r in (Role.ADMINISTRATOR, Role.SECURITY_ARCHITECT, Role.AUDITOR, Role.READ_ONLY):
            if r in self.roles:
                return r
        return Role.READ_ONLY


class AuthProvider:
    """Interface. Chunk 11 adds EntraAuthProvider implementing the same methods."""

    def principal_from_request(self, cookie_value: str | None, bearer: str | None) -> Principal | None:
        raise NotImplementedError


class MockAuthProvider(AuthProvider):
    """Dev-only. Reads a signed cookie describing the current principal.

    Hard guard: refuses to operate in production so a fake identity can never be
    minted in a deployed environment.
    """

    COOKIE_NAME = "dev_identity"

    def __init__(self, settings: Settings):
        if settings.app_env == "production":
            raise RuntimeError("MockAuthProvider must never run in production (ADR-0003).")
        self._serializer = URLSafeSerializer(settings.mock_auth_secret, salt="dev-identity")

    def sign(self, principal: Principal) -> str:
        return self._serializer.dumps(
            {"sub": principal.sub, "name": principal.name, "roles": [r.value for r in principal.roles]}
        )

    def principal_from_request(self, cookie_value: str | None, bearer: str | None) -> Principal | None:
        if not cookie_value:
            # Default dev identity: a Security Architect, so the app is usable out of the box.
            return Principal(sub="dev-user", name="Dev Architect", roles=[Role.SECURITY_ARCHITECT])
        try:
            data = self._serializer.loads(cookie_value)
        except BadSignature:
            return None
        return Principal(sub=data["sub"], name=data["name"], roles=[Role(r) for r in data["roles"]])


def build_auth_provider(settings: Settings | None = None) -> AuthProvider:
    """Select the auth provider from configuration.

    The production guard is deliberately here, not only inside MockAuthProvider: a
    misconfigured deployment should fail to start rather than serve traffic with a
    forgeable identity. Failing loudly at boot is the cheapest possible failure.
    """
    settings = settings or get_settings()

    if settings.auth_provider == "mock":
        if settings.app_env == "production":
            raise RuntimeError(
                "AUTH_PROVIDER=mock is not permitted when APP_ENV=production. "
                "Set AUTH_PROVIDER=entra with ENTRA_TENANT_ID and ENTRA_CLIENT_ID (ADR-0003)."
            )
        return MockAuthProvider(settings)

    if settings.auth_provider == "entra":
        # Imported lazily so local dev never needs the JWT/JWKS dependencies.
        from .entra import EntraAuthProvider

        return EntraAuthProvider(settings)

    raise RuntimeError(f"Unknown AUTH_PROVIDER {settings.auth_provider!r}; expected 'mock' or 'entra'.")
