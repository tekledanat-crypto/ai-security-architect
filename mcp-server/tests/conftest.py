"""Shared fixtures for the MCP server test suite."""
from __future__ import annotations

import pytest

from app.repository import FrameworkRepository
from app.tools import Tools


@pytest.fixture(scope="session")
def repo() -> FrameworkRepository:
    return FrameworkRepository()


@pytest.fixture(scope="session")
def tools(repo) -> Tools:
    return Tools(repo)


@pytest.fixture
def insecure_arch() -> dict:
    return {
        "name": "Insecure Ecommerce",
        "context": {"internet_facing": True, "stores_customer_data": True, "regulatory": ["PCI-DSS"]},
        "nodes": [
            {"id": "web", "service": "app-service",
             "properties": {"https_only": False, "managed_identity": False, "tls_min_version": "1.0"}},
            {"id": "sql", "service": "azure-sql",
             "properties": {"public_access": True, "private_endpoint": False, "auditing_enabled": False}},
            {"id": "kv", "service": "key-vault",
             "properties": {"firewall_enabled": False, "purge_protection": False}},
            {"id": "store", "service": "storage-account",
             "properties": {"public_access": True, "allow_blob_public_access": True,
                            "https_only": False, "private_endpoint": False}},
        ],
        "edges": [{"source": "web", "target": "sql"}, {"source": "web", "target": "store"}],
    }


@pytest.fixture
def hardened_arch() -> dict:
    return {
        "name": "Hardened Ecommerce",
        "context": {"internet_facing": True, "stores_customer_data": True},
        "nodes": [
            {"id": "fd", "service": "front-door"},
            {"id": "waf", "service": "app-gateway-waf"},
            {"id": "web", "service": "app-service",
             "properties": {"https_only": True, "managed_identity": True, "tls_min_version": "1.2"}},
            {"id": "sql", "service": "azure-sql",
             "properties": {"public_access": False, "private_endpoint": True,
                            "auditing_enabled": True, "tde_enabled": True}},
            {"id": "kv", "service": "key-vault",
             "properties": {"firewall_enabled": True, "purge_protection": True}},
            {"id": "store", "service": "storage-account",
             "properties": {"public_access": False, "allow_blob_public_access": False,
                            "https_only": True, "private_endpoint": True}},
            {"id": "entra", "service": "entra-id",
             "properties": {"mfa_enabled": True, "mfa_all_users": True,
                            "legacy_auth_blocked": True, "pim_enabled": True}},
            {"id": "def", "service": "defender-for-cloud"},
            {"id": "log", "service": "log-analytics"},
            {"id": "vnet", "service": "vnet"},
            {"id": "pe", "service": "private-endpoint"},
        ],
        "edges": [
            {"source": "fd", "target": "waf"},
            {"source": "waf", "target": "web"},
            {"source": "web", "target": "sql", "private": True},
            {"source": "web", "target": "kv", "private": True},
        ],
    }
