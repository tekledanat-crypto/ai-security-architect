"""Reports router: generate a professional PDF assessment report.

Requires the "report" permission (Administrator, SecurityArchitect, Auditor — an
Auditor legitimately needs to export evidence; ReadOnly does not).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.responses import Response

from ..ai.mcp_client import MCPClient
from ..auth.provider import Principal
from ..deps import mcp_client_dep, require_permission
from ..reports.generator import generate_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportIn(BaseModel):
    architecture: dict
    framework_ids: list[str] | None = None
    include_threats: bool = True


@router.post("/generate")
async def generate(
    body: ReportIn,
    principal: Principal = Depends(require_permission("report")),
    mcp: MCPClient = Depends(mcp_client_dep),
) -> Response:
    # Always re-validate server-side rather than trusting client-supplied results:
    # the report is evidence, so its numbers must come from the engine (OWASP LLM09).
    result = await mcp.call_tool(
        "validate_architecture",
        {"architecture": body.architecture, "framework_ids": body.framework_ids},
    )

    threats = None
    if body.include_threats:
        try:
            threats = await mcp.call_tool("get_stride_threats", {"architecture": body.architecture})
        except Exception:  # noqa: BLE001 — a threat-model failure shouldn't sink the report
            threats = None

    report = generate_report(
        architecture=body.architecture,
        result=result,
        threats=threats,
        generated_by=f"{principal.name} ({principal.primary_role.value})",
    )

    return Response(
        content=report.content,
        media_type=report.media_type,
        headers={"Content-Disposition": f'attachment; filename="{report.filename}"'},
    )
