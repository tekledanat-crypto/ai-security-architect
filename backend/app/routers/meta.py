"""Meta router: health, readiness, and framework/tool discovery passthrough."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..ai.mcp_client import MCPClient
from ..config import get_settings
from ..deps import mcp_client_dep

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(mcp: MCPClient = Depends(mcp_client_dep)) -> dict:
    settings = get_settings()
    try:
        specs = await mcp.list_tool_specs()
        mcp_ok, tool_count = True, len(specs)
    except Exception:  # noqa: BLE001
        mcp_ok, tool_count = False, 0
    return {
        "status": "ready" if mcp_ok else "degraded",
        "ai_provider": settings.resolved_ai_provider(),
        "mcp_transport": settings.mcp_transport,
        "mcp_ok": mcp_ok,
        "tool_count": tool_count,
    }


@router.get("/frameworks")
async def frameworks(mcp: MCPClient = Depends(mcp_client_dep)) -> dict:
    return await mcp.call_tool("list_frameworks", {})
