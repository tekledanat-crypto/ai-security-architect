"""Application settings, loaded from environment / .env (ADRs 0001-0003)."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "production"] = "development"

    # ── AI provider (ADR-0001) ──
    ai_provider: Literal["azure-openai", "openai", "fake"] = "fake"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-10-21"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # ── MCP connection ──
    # 'http' = real MCP protocol over the network; 'in-process' = import tool logic.
    mcp_transport: Literal["http", "in-process"] = "http"
    mcp_server_url: str = "http://localhost:8100/mcp"

    # ── database (ADR-0002) ──
    database_url: str = "sqlite+aiosqlite:///./data/dev.db"

    # ── auth (ADR-0003) ──
    auth_provider: Literal["mock", "entra"] = "mock"
    mock_auth_secret: str = "change-me-dev-only"
    entra_tenant_id: str = ""
    entra_client_id: str = ""

    # ── guardrails ──
    max_input_chars: int = 8000
    token_budget_per_conversation: int = 200_000
    tool_call_audit_log: bool = True
    max_tool_calls_per_turn: int = 8

    frontend_url: str = "http://localhost:3000"

    def resolved_ai_provider(self) -> str:
        """Auto-upgrade from 'fake' when real credentials are present."""
        if self.ai_provider != "fake":
            return self.ai_provider
        if self.azure_openai_endpoint and self.azure_openai_api_key:
            return "azure-openai"
        if self.openai_api_key:
            return "openai"
        return "fake"


@lru_cache
def get_settings() -> Settings:
    return Settings()
