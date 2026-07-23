"""RBAC and auth-provider tests (ADR-0003)."""
import pytest
from app.auth.provider import MockAuthProvider, Principal, Role
from app.config import Settings


def _settings(**kw):
    return Settings(_env_file=None, **kw)


def test_permissions_by_role():
    admin = Principal(sub="a", name="A", roles=[Role.ADMINISTRATOR])
    ro = Principal(sub="r", name="R", roles=[Role.READ_ONLY])
    assert admin.has_permission("manage-settings")
    assert not ro.has_permission("validate")
    assert ro.has_permission("read")


def test_mock_provider_default_identity():
    p = MockAuthProvider(_settings(app_env="development", mock_auth_secret="s"))
    principal = p.principal_from_request(None, None)
    assert principal.primary_role == Role.SECURITY_ARCHITECT


def test_mock_provider_roundtrip():
    p = MockAuthProvider(_settings(app_env="development", mock_auth_secret="s"))
    signed = p.sign(Principal(sub="x", name="X", roles=[Role.AUDITOR]))
    back = p.principal_from_request(signed, None)
    assert back.roles == [Role.AUDITOR]


def test_mock_provider_rejects_tampered_cookie():
    p = MockAuthProvider(_settings(app_env="development", mock_auth_secret="s"))
    assert p.principal_from_request("garbage.value", None) is None


def test_mock_provider_forbidden_in_production():
    with pytest.raises(RuntimeError):
        MockAuthProvider(_settings(app_env="production", mock_auth_secret="s"))
