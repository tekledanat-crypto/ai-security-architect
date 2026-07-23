"""Auth router: identity introspection and (dev-only) role switching."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from ..auth.provider import MockAuthProvider, Principal, Role
from ..config import get_settings
from ..deps import _auth_provider, current_principal

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
def whoami(principal: Principal = Depends(current_principal)) -> dict:
    return {
        "sub": principal.sub,
        "name": principal.name,
        "roles": [r.value for r in principal.roles],
        "primary_role": principal.primary_role.value,
    }


@router.post("/dev/switch-role")
def switch_role(role: str, response: Response) -> dict:
    """DEV ONLY: mint a signed dev identity cookie with the requested role.

    Guarded to non-production; the MockAuthProvider itself refuses to construct in
    production, so this is defense in depth (ADR-0003).
    """
    settings = get_settings()
    if settings.app_env == "production":
        raise HTTPException(status_code=404, detail="Not available")
    try:
        role_enum = Role(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown role '{role}'")

    provider = _auth_provider()
    if not isinstance(provider, MockAuthProvider):
        raise HTTPException(status_code=400, detail="Role switching requires the mock auth provider")

    principal = Principal(sub="dev-user", name=f"Dev {role_enum.value}", roles=[role_enum])
    cookie = provider.sign(principal)
    response.set_cookie(
        "dev_identity", cookie, httponly=True, samesite="lax",
        secure=settings.app_env == "production",
    )
    return {"switched_to": role_enum.value}


@router.get("/roles")
def list_roles() -> dict:
    return {"roles": [r.value for r in Role]}


@router.get("/config")
def auth_config() -> dict:
    """Public auth configuration for the frontend.

    Lets the SPA configure MSAL without hard-coding tenant details at build time, so
    the same image deploys to any tenant. Nothing here is sensitive: the client ID and
    authority are public by design in the OAuth authorization-code + PKCE flow.
    """
    settings = get_settings()
    if settings.auth_provider != "entra":
        return {"provider": "mock", "loginRequired": False}

    return {
        "provider": "entra",
        "loginRequired": True,
        "clientId": settings.entra_client_id,
        "authority": f"https://login.microsoftonline.com/{settings.entra_tenant_id}",
        "scopes": [f"api://{settings.entra_client_id}/access_as_user"],
    }
