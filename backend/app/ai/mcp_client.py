"""MCP client: how the backend reaches the security tools.

Two transports selected by settings.mcp_transport:
  * "http"       — a real MCP client over streamable HTTP to the Chunk 3 server.
                   This is the production-faithful path.
  * "in-process" — import the Chunk 3 tool logic directly. No network, ideal for
                   tests and single-container demos.

Both expose the same async surface: `list_tool_specs()` and `call_tool(name, args)`,
so the orchestrator is transport-agnostic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ..config import get_settings
from ..providers.base import ToolSpec


class MCPClient:
    async def list_tool_specs(self) -> list[ToolSpec]:
        raise NotImplementedError

    async def call_tool(self, name: str, arguments: dict) -> dict:
        raise NotImplementedError


class HTTPMCPClient(MCPClient):
    def __init__(self, url: str):
        self._url = url

    async def list_tool_specs(self) -> list[ToolSpec]:
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(self._url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [
                    ToolSpec(name=t.name, description=t.description or "", parameters=t.inputSchema)
                    for t in tools.tools
                ]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(self._url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                if result.content and hasattr(result.content[0], "text"):
                    return json.loads(result.content[0].text)
                return {}


class InProcessMCPClient(MCPClient):
    """Imports the Chunk 3 tool logic directly (no protocol overhead).

    The MCP server also uses an `app` package, which would collide with the
    backend's `app`. We load it under a distinct top-level name (`mcp_app`) via
    importlib so both packages coexist in one process.
    """

    def __init__(self):
        tools_cls, repo_cls = _load_mcp_server_modules()
        self._tools = tools_cls(repo_cls())
        self._specs = self._build_specs()

    def _build_specs(self) -> list[ToolSpec]:
        # Minimal JSON Schemas matching the tool signatures.
        arch = {"type": "object", "properties": {
            "architecture": {"type": "object"},
            "framework_ids": {"type": "array", "items": {"type": "string"}},
        }, "required": ["architecture"]}
        return [
            ToolSpec("list_frameworks", "List all frameworks.", {"type": "object", "properties": {}}),
            ToolSpec("find_control", "Look up a control by ID.",
                     {"type": "object", "properties": {"control_id": {"type": "string"},
                      "framework_id": {"type": "string"}}, "required": ["control_id"]}),
            ToolSpec("search_controls", "Full-text search over controls.",
                     {"type": "object", "properties": {"query": {"type": "string"},
                      "framework_id": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]}),
            ToolSpec("list_best_practices", "List best practices by service/framework.",
                     {"type": "object", "properties": {"service": {"type": "string"},
                      "framework_id": {"type": "string"}}}),
            ToolSpec("map_service", "Map a service to controls/threats.",
                     {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}),
            ToolSpec("validate_architecture", "Validate an architecture; full findings.", arch),
            ToolSpec("score_architecture", "Concise compliance scorecard.", arch),
            ToolSpec("generate_remediation", "Prioritized remediation plan.", arch),
            ToolSpec("get_stride_threats", "STRIDE threat model.",
                     {"type": "object", "properties": {"architecture": {"type": "object"}}, "required": ["architecture"]}),
            ToolSpec("map_threats", "Service to ATT&CK/ATLAS techniques.",
                     {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}),
            ToolSpec("crosswalk_control", "Equivalent controls across frameworks.",
                     {"type": "object", "properties": {"framework_id": {"type": "string"},
                      "control_id": {"type": "string"}}, "required": ["framework_id", "control_id"]}),
            ToolSpec("compare_frameworks", "Compare two frameworks.",
                     {"type": "object", "properties": {"framework_a": {"type": "string"},
                      "framework_b": {"type": "string"}}, "required": ["framework_a", "framework_b"]}),
        ]

    async def list_tool_specs(self) -> list[ToolSpec]:
        return self._specs

    async def call_tool(self, name: str, arguments: dict) -> dict:
        fn = getattr(self._tools, name, None)
        if fn is None:
            raise ValueError(f"Unknown tool: {name}")
        return fn(**arguments)


def build_mcp_client() -> MCPClient:
    settings = get_settings()
    if settings.mcp_transport == "in-process":
        return InProcessMCPClient()
    return HTTPMCPClient(settings.mcp_server_url)


def _load_mcp_server_modules():
    """Load the mcp-server's app.repository and app.tools under isolated names.

    Both the backend and the MCP server define a top-level `app` package. To use
    the MCP tool logic in-process we load its modules via importlib with unique
    module names so they don't shadow the backend's own `app`.
    """
    import importlib.util
    import types

    mcp_root = Path(__file__).resolve().parents[3] / "mcp-server"
    # Register a synthetic package so intra-package imports resolve.
    pkg_name = "mcp_server_app"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(mcp_root / "app")]
        sys.modules[pkg_name] = pkg

    def _load(mod: str):
        full = f"{pkg_name}.{mod}"
        if full in sys.modules:
            return sys.modules[full]
        spec = importlib.util.spec_from_file_location(full, mcp_root / "app" / f"{mod}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[full] = module
        spec.loader.exec_module(module)
        return module

    # Order matters: models → repository/engine/threats → tools.
    _load("models")
    _load("engine")
    _load("threats")
    repository = _load("repository")
    tools = _load("tools")
    return tools.Tools, repository.FrameworkRepository
