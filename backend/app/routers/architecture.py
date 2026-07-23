"""Architecture router: direct (non-chat) access to the assessment tools.

These endpoints let the frontend's Architecture Designer and Compliance pages call
the MCP tools without going through the AI, and persist the results as Assessments
and Findings. Permissions are enforced per route (RBAC via Principal).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai.mcp_client import MCPClient
from ..auth.provider import Principal
from ..db.models import Architecture, Assessment, Conversation, Finding, User
from ..db.session import get_session
from ..deps import mcp_client_dep, require_permission

router = APIRouter(prefix="/api/architecture", tags=["architecture"])


class ArchitectureIn(BaseModel):
    architecture: dict
    framework_ids: list[str] | None = None
    conversation_id: str | None = None


@router.post("/validate")
async def validate(
    body: ArchitectureIn,
    principal: Principal = Depends(require_permission("validate")),
    mcp: MCPClient = Depends(mcp_client_dep),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await mcp.call_tool(
        "validate_architecture",
        {"architecture": body.architecture, "framework_ids": body.framework_ids},
    )
    # Persist assessment if tied to a conversation.
    if body.conversation_id:
        await _persist_assessment(session, principal, body, result)
    return result


@router.post("/score")
async def score(
    body: ArchitectureIn,
    principal: Principal = Depends(require_permission("validate")),
    mcp: MCPClient = Depends(mcp_client_dep),
) -> dict:
    return await mcp.call_tool(
        "score_architecture",
        {"architecture": body.architecture, "framework_ids": body.framework_ids},
    )


@router.post("/threats")
async def threats(
    body: ArchitectureIn,
    principal: Principal = Depends(require_permission("threat-model")),
    mcp: MCPClient = Depends(mcp_client_dep),
) -> dict:
    return await mcp.call_tool("get_stride_threats", {"architecture": body.architecture})


@router.post("/remediate")
async def remediate(
    body: ArchitectureIn,
    principal: Principal = Depends(require_permission("remediate")),
    mcp: MCPClient = Depends(mcp_client_dep),
) -> dict:
    return await mcp.call_tool(
        "generate_remediation",
        {"architecture": body.architecture, "framework_ids": body.framework_ids},
    )


async def _persist_assessment(
    session: AsyncSession, principal: Principal, body: ArchitectureIn, result: dict
) -> None:
    user = (await session.execute(select(User).where(User.sub == principal.sub))).scalar_one_or_none()
    if user is None:
        user = User(sub=principal.sub, name=principal.name, roles=[r.value for r in principal.roles])
        session.add(user)
        await session.flush()
    conv = (await session.execute(
        select(Conversation).where(Conversation.id == body.conversation_id)
    )).scalar_one_or_none()
    if conv is None:
        conv = Conversation(id=body.conversation_id, user_id=user.id)
        session.add(conv)
        await session.flush()

    arch = Architecture(
        conversation_id=conv.id,
        name=result.get("architecture_name", body.architecture.get("name", "Architecture")),
        definition=body.architecture,
    )
    session.add(arch)
    await session.flush()

    assessment = Assessment(
        architecture_id=arch.id,
        overall_score=result.get("overall_score", 0),
        grade=result.get("grade", "F"),
        framework_scores=[{k: fs[k] for k in ("framework_id", "name", "status", "score")}
                          for fs in result.get("frameworks", [])],
        summary=result.get("summary", {}),
    )
    session.add(assessment)
    await session.flush()

    for f in result.get("findings", []):
        session.add(Finding(
            assessment_id=assessment.id,
            framework_id=f["framework_id"], control_id=f["control_id"],
            title=f["title"], severity=f["severity"], status=f["status"],
            message=f["message"], remediation=f.get("remediation") or "",
            affected_nodes=f.get("affected_nodes", []),
        ))
    await session.commit()
