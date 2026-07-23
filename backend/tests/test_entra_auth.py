"""Entra ID authentication tests (Chunk 11).

These mint **real RS256-signed JWTs** with a locally-generated keypair and serve them
against a fake JWKS client. That matters: mocking `jwt.decode` would prove nothing,
because the whole risk in token validation is that signature, audience, issuer, and
expiry checks are skipped or misconfigured. Here they are genuinely exercised — a test
that passes a tampered token must actually fail.
"""
from __future__ import annotations

import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.entra import APP_ROLE_TO_ROLE, EntraAuthError, EntraAuthProvider
from app.auth.provider import Principal, Role, build_auth_provider
from app.config import Settings

TENANT_ID = "11111111-2222-3333-4444-555555555555"
CLIENT_ID = "66666666-7777-8888-9999-000000000000"
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"


# ── Key material: one signing key, one attacker key ──

@pytest.fixture(scope="module")
def keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key


@pytest.fixture(scope="module")
def attacker_keypair():
    """A different key, to prove signature verification actually rejects forgeries."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeSigningKey:
    def __init__(self, public_key):
        self.key = public_key


class FakeJWKClient:
    """Stands in for PyJWKClient without network access.

    Returns the real public key, so signature verification runs for real.
    """

    def __init__(self, public_key):
        self._public_key = public_key
        self.calls = 0

    def get_signing_key_from_jwt(self, token: str) -> FakeSigningKey:
        self.calls += 1
        return FakeSigningKey(self._public_key)


@pytest.fixture
def provider(keypair) -> EntraAuthProvider:
    settings = Settings(
        auth_provider="entra",
        entra_tenant_id=TENANT_ID,
        entra_client_id=CLIENT_ID,
        app_env="production",
    )
    return EntraAuthProvider(settings, jwk_client=FakeJWKClient(keypair.public_key()))


def make_token(
    key,
    *,
    roles: list[str] | None = None,
    audience: str = CLIENT_ID,
    issuer: str = ISSUER,
    expires_in: int = 3600,
    not_before_offset: int = 0,
    sub: str = "user-object-id",
    name: str | None = "Alex Architect",
    ver: str | None = "2.0",
    omit: tuple[str, ...] = (),
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": sub,
        "aud": audience,
        "iss": issuer,
        "iat": now,
        "nbf": now + not_before_offset,
        "exp": now + expires_in,
        "tid": TENANT_ID,
    }
    if name is not None:
        claims["name"] = name
    if roles is not None:
        claims["roles"] = roles
    if ver is not None:
        claims["ver"] = ver
    for field in omit:
        claims.pop(field, None)

    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(claims, pem, algorithm="RS256")


# ── Happy path ──

def test_valid_token_yields_principal(provider, keypair):
    token = make_token(keypair, roles=["SecurityArchitect"])
    principal = provider.principal_from_request(None, token)
    assert isinstance(principal, Principal)
    assert principal.sub == "user-object-id"
    assert principal.name == "Alex Architect"
    assert principal.roles == [Role.SECURITY_ARCHITECT]


def test_all_four_app_roles_map(provider, keypair):
    for app_role, expected in APP_ROLE_TO_ROLE.items():
        token = make_token(keypair, roles=[app_role])
        principal = provider.principal_from_request(None, token)
        assert principal is not None, f"{app_role} should authenticate"
        assert expected in principal.roles


def test_multiple_roles_preserved_and_primary_is_highest(provider, keypair):
    token = make_token(keypair, roles=["Auditor", "Administrator"])
    principal = provider.principal_from_request(None, token)
    assert set(principal.roles) == {Role.AUDITOR, Role.ADMINISTRATOR}
    assert principal.primary_role == Role.ADMINISTRATOR


def test_permissions_flow_through_from_token(provider, keypair):
    """The whole point of the swap: RBAC behaves identically to mock auth."""
    readonly = provider.principal_from_request(None, make_token(keypair, roles=["ReadOnly"]))
    assert readonly.has_permission("read")
    assert not readonly.has_permission("validate")
    assert not readonly.has_permission("report")

    auditor = provider.principal_from_request(None, make_token(keypair, roles=["Auditor"]))
    assert auditor.has_permission("report")      # auditors export evidence
    assert not auditor.has_permission("remediate")


# ── Signature ──

def test_token_signed_by_wrong_key_is_rejected(provider, attacker_keypair):
    """The single most important test here: a forged signature must not authenticate."""
    forged = make_token(attacker_keypair, roles=["Administrator"])
    assert provider.principal_from_request(None, forged) is None


def test_tampered_payload_is_rejected(provider, keypair):
    """Editing the payload of a validly-signed token must invalidate it."""
    import base64
    import json

    token = make_token(keypair, roles=["ReadOnly"])
    header_b64, payload_b64, signature = token.split(".")

    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    payload["roles"] = ["Administrator"]  # privilege escalation attempt

    new_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    tampered = f"{header_b64}.{new_payload}.{signature}"

    assert provider.principal_from_request(None, tampered) is None


def test_unsigned_alg_none_token_is_rejected(provider):
    """`alg: none` is the classic JWT bypass. It must not work."""
    unsigned = jwt.encode(
        {"sub": "x", "aud": CLIENT_ID, "iss": ISSUER, "exp": int(time.time()) + 600,
         "roles": ["Administrator"]},
        key="",
        algorithm="none",
    )
    assert provider.principal_from_request(None, unsigned) is None


# ── Audience / issuer ──

def test_token_for_another_application_is_rejected(provider, keypair):
    token = make_token(keypair, roles=["Administrator"], audience="some-other-app-id")
    assert provider.principal_from_request(None, token) is None


def test_token_from_another_tenant_is_rejected(provider, keypair):
    other = "https://login.microsoftonline.com/99999999-9999-9999-9999-999999999999/v2.0"
    token = make_token(keypair, roles=["Administrator"], issuer=other)
    assert provider.principal_from_request(None, token) is None


# ── Lifetime ──

def test_expired_token_is_rejected(provider, keypair):
    token = make_token(keypair, roles=["SecurityArchitect"], expires_in=-3600)
    assert provider.principal_from_request(None, token) is None


def test_not_yet_valid_token_is_rejected(provider, keypair):
    # Beyond the 60s clock-skew allowance.
    token = make_token(keypair, roles=["SecurityArchitect"], not_before_offset=600)
    assert provider.principal_from_request(None, token) is None


def test_small_clock_skew_is_tolerated(provider, keypair):
    """Clocks drift; a token 10s in the future should still work."""
    token = make_token(keypair, roles=["SecurityArchitect"], not_before_offset=10)
    assert provider.principal_from_request(None, token) is not None


# ── Roles: fail closed ──

def test_no_roles_claim_is_rejected(provider, keypair):
    """Authenticated but unassigned is NOT authorized. Authentication != authorization."""
    token = make_token(keypair, roles=None)
    assert provider.principal_from_request(None, token) is None


def test_empty_roles_claim_is_rejected(provider, keypair):
    token = make_token(keypair, roles=[])
    assert provider.principal_from_request(None, token) is None


def test_unknown_role_grants_nothing(provider, keypair):
    token = make_token(keypair, roles=["SuperAdmin", "GlobalOwner"])
    assert provider.principal_from_request(None, token) is None


def test_unknown_role_alongside_known_role_keeps_only_known(provider, keypair):
    token = make_token(keypair, roles=["SuperAdmin", "Auditor"])
    principal = provider.principal_from_request(None, token)
    assert principal.roles == [Role.AUDITOR]


def test_single_string_role_claim_is_handled(provider, keypair):
    """Defensive: some issuers emit a bare string rather than a list."""
    token = make_token(keypair, roles=None)
    claims = provider.validate_token(token)
    claims["roles"] = "Auditor"
    principal = provider.principal_from_claims(claims)
    assert principal.roles == [Role.AUDITOR]


# ── Claim handling ──

def test_missing_required_claim_is_rejected(provider, keypair):
    token = make_token(keypair, roles=["Auditor"], omit=("sub",))
    assert provider.principal_from_request(None, token) is None


def test_name_falls_back_to_preferred_username(provider, keypair):
    token = make_token(keypair, roles=["Auditor"], name=None)
    claims = provider.validate_token(token)
    claims["preferred_username"] = "alex@contoso.com"
    principal = provider.principal_from_claims(claims)
    assert principal.name == "alex@contoso.com"


def test_v1_token_is_rejected(provider, keypair):
    """A v1.0 token usually means accessTokenAcceptedVersion is misconfigured."""
    token = make_token(keypair, roles=["Auditor"], ver="1.0")
    assert provider.principal_from_request(None, token) is None


# ── Request handling ──

def test_no_bearer_token_yields_none(provider):
    assert provider.principal_from_request(None, None) is None


def test_dev_cookie_is_ignored_under_entra(provider):
    """A signed dev cookie must never be a route to identity in Entra mode."""
    assert provider.principal_from_request("some-dev-cookie-value", None) is None


def test_garbage_token_is_rejected(provider):
    assert provider.principal_from_request(None, "not-a-jwt") is None


# ── Configuration guards ──

def test_entra_requires_tenant_and_client_id():
    with pytest.raises(RuntimeError, match="ENTRA_TENANT_ID"):
        EntraAuthProvider(Settings(auth_provider="entra", entra_tenant_id="", entra_client_id=""))


def test_mock_auth_refused_in_production():
    """A misconfigured deployment must fail to start, not serve forgeable identities."""
    settings = Settings(auth_provider="mock", app_env="production")
    with pytest.raises(RuntimeError, match="not permitted when APP_ENV=production"):
        build_auth_provider(settings)


def test_mock_auth_allowed_in_development():
    settings = Settings(auth_provider="mock", app_env="development")
    assert build_auth_provider(settings) is not None


def test_unknown_auth_provider_rejected():
    settings = Settings(app_env="development")
    settings.auth_provider = "something-else"  # type: ignore[assignment]
    with pytest.raises(RuntimeError, match="Unknown AUTH_PROVIDER"):
        build_auth_provider(settings)
