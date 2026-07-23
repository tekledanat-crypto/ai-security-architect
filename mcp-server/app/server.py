"""AI Security Architect — MCP Server.

Exposes the security & compliance tools over the Model Context Protocol so the
FastAPI backend's AI orchestrator (Chunk 4) can call them. The AI is instructed to
use these tools rather than rely on its own knowledge, keeping findings grounded in
the framework corpus (ADR-0004; OWASP LLM09 mitigation).

Transports:
  * stdio            — `python -m app.server` (default; used by MCP clients that spawn a subprocess)
  * streamable-http  — `python -m app.server --http` (port 8100; used by the backend over the network)

The pure logic lives in app/tools.py; this module is the thin protocol wrapper.
"""
from __future__ import annotations

import argparse
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .repository import FrameworkRepository
from .tools import Tools

repo = FrameworkRepository()
_tools = Tools(repo)

mcp = FastMCP(
    "ai-security-architect",
    instructions=(
        "Security and compliance tools for designing and validating secure Azure "
        "architectures. Prefer these tools over prior knowledge: call "
        "validate_architecture / score_architecture to assess a design, "
        "get_stride_threats for threat modeling, and generate_remediation for a "
        "prioritized fix list. Architecture inputs follow the architecture schema "
        "(nodes with a `service` slug and security `properties`, plus `edges`)."
    ),
    port=int(os.environ.get("MCP_PORT", "8100")),
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
)


# ── discovery ────────────────────────────────────────────────────────
@mcp.tool()
def list_frameworks() -> dict:
    """List all available compliance and security frameworks with metadata."""
    return _tools.list_frameworks()


@mcp.tool()
def find_control(control_id: str, framework_id: Optional[str] = None) -> dict:
    """Look up a specific control by its ID, optionally scoped to one framework."""
    return _tools.find_control(control_id, framework_id)


@mcp.tool()
def search_controls(query: str, framework_id: Optional[str] = None, limit: int = 20) -> dict:
    """Full-text search across all control titles, summaries, and remediation guidance."""
    return _tools.search_controls(query, framework_id, limit)


@mcp.tool()
def list_best_practices(service: Optional[str] = None, framework_id: Optional[str] = None) -> dict:
    """List security best practices, optionally filtered by Azure service or framework."""
    return _tools.list_best_practices(service, framework_id)


@mcp.tool()
def map_service(service: str) -> dict:
    """Map an Azure service to its applicable controls, STRIDE exposure, and ATT&CK techniques."""
    return _tools.map_service(service)


# ── validation / scoring ─────────────────────────────────────────────
@mcp.tool()
def validate_architecture(architecture: dict, framework_ids: Optional[list[str]] = None) -> dict:
    """Validate an architecture against frameworks, returning per-control pass/fail findings and scores."""
    return _tools.validate_architecture(architecture, framework_ids)


@mcp.tool()
def score_architecture(architecture: dict, framework_ids: Optional[list[str]] = None) -> dict:
    """Return a concise compliance scorecard (overall + per-framework scores) without full findings."""
    return _tools.score_architecture(architecture, framework_ids)


@mcp.tool()
def generate_remediation(architecture: dict, framework_ids: Optional[list[str]] = None) -> dict:
    """Produce a prioritized, deduplicated remediation plan for an architecture's failed controls."""
    return _tools.generate_remediation(architecture, framework_ids)


# ── threat modeling ──────────────────────────────────────────────────
@mcp.tool()
def get_stride_threats(architecture: dict) -> dict:
    """Generate a STRIDE threat model for an architecture, grounded in failing controls."""
    return _tools.get_stride_threats(architecture)


@mcp.tool()
def map_threats(service: str) -> dict:
    """Map an Azure service to relevant MITRE ATT&CK/ATLAS techniques and their mitigating controls."""
    return _tools.map_threats(service)


# ── cross-framework ──────────────────────────────────────────────────
@mcp.tool()
def crosswalk_control(framework_id: str, control_id: str) -> dict:
    """Find controls in other frameworks that address the same objective as a given control."""
    return _tools.crosswalk_control(framework_id, control_id)


@mcp.tool()
def compare_frameworks(framework_a: str, framework_b: str) -> dict:
    """Compare two frameworks, listing objectives both address and their corresponding controls."""
    return _tools.compare_frameworks(framework_a, framework_b)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Security Architect MCP Server")
    parser.add_argument("--http", action="store_true", help="Serve over streamable HTTP instead of stdio")
    args = parser.parse_args()
    mcp.run(transport="streamable-http" if args.http else "stdio")


if __name__ == "__main__":
    main()
