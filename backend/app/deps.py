"""Shared FastAPI dependencies."""
from __future__ import annotations

from functools import lru_cache

from fastapi import Cookie, Depends, Header, HTTPException, status

from .ai.mcp_client import MCPClient, build_mcp_client
from .auth.provider import AuthProvider, Principal, build_auth_provider
from .config import Settings, get_settings
from .providers.base import AIProvider
from .providers.openai_provider import build_provider


@lru_cache
def _auth_provider() -> AuthProvider:
    return build_auth_provider()


@lru_cache
def _ai_provider() -> AIProvider:
    return build_provider()


@lru_cache
def _mcp_client() -> MCPClient:
    return build_mcp_client()


def settings_dep() -> Settings:
    return get_settings()


def current_principal(
    dev_identity: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> Principal:
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization[7:]
    principal = _auth_provider().principal_from_request(dev_identity, bearer)
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid identity")
    return principal


def require_permission(permission: str):
    def _dep(principal: Principal = Depends(current_principal)) -> Principal:
        if not principal.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {principal.primary_role.value} lacks '{permission}' permission",
            )
        return principal
    return _dep


def ai_provider_dep() -> AIProvider:
    return _ai_provider()


def mcp_client_dep() -> MCPClient:
    return _mcp_client()
