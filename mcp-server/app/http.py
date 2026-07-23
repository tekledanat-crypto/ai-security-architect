"""ASGI app for the streamable-HTTP transport (used by `uvicorn app.http:app`).

Exposes the MCP server as a mountable Starlette app so it can run behind uvicorn
in the container and in docker-compose. The MCP endpoint is served at /mcp.
"""
from .server import mcp

app = mcp.streamable_http_app()
