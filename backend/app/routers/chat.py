"""Chat router: streaming AI conversation over Server-Sent Events.

POST /api/chat/{conversation_id}/message streams orchestrator events as SSE so the
frontend renders text incrementally and shows a live tool-activity panel. Messages,
token usage, and the tool-call audit trail are persisted.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from ..ai.mcp_client import MCPClient
from ..ai.orchestrator import Orchestrator
from ..auth.provider import Principal
from ..config import get_settings
from ..db.models import Conversation, Message as DBMessage, ToolAudit, User
from ..db.session import get_session
from ..deps import ai_provider_dep, mcp_client_dep, require_permission
from ..guardrails.output_filter import AuditLog, ToolCallRecord
from ..guardrails.tool_policy import TokenBudget
from ..providers.base import AIProvider, Message
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["chat"])


class MessageIn(BaseModel):
    content: str


async def _get_or_create_user(session: AsyncSession, principal: Principal) -> User:
    user = (await session.execute(select(User).where(User.sub == principal.sub))).scalar_one_or_none()
    if user is None:
        user = User(sub=principal.sub, name=principal.name, roles=[r.value for r in principal.roles])
        session.add(user)
        await session.flush()
    return user


async def _get_or_create_conversation(
    session: AsyncSession, user: User, conversation_id: str
) -> Conversation:
    conv = (await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )).scalar_one_or_none()
    if conv is None:
        conv = Conversation(id=conversation_id, user_id=user.id)
        session.add(conv)
        await session.flush()
    return conv


@router.post("/{conversation_id}/message")
async def send_message(
    conversation_id: str,
    body: MessageIn,
    principal: Principal = Depends(require_permission("chat")),
    provider: AIProvider = Depends(ai_provider_dep),
    mcp: MCPClient = Depends(mcp_client_dep),
    session: AsyncSession = Depends(get_session),
):
    settings = get_settings()
    user = await _get_or_create_user(session, principal)
    conv = await _get_or_create_conversation(session, user, conversation_id)

    # Rebuild history from persisted messages.
    rows = (await session.execute(
        select(DBMessage).where(DBMessage.conversation_id == conv.id).order_by(DBMessage.created_at)
    )).scalars().all()
    history = [Message(role=m.role, content=m.content) for m in rows if m.role in ("user", "assistant")]

    budget = TokenBudget(limit=settings.token_budget_per_conversation, used=conv.tokens_used)
    audit_records: list[ToolCallRecord] = []
    audit = AuditLog(conversation_id=conv.id, sink=audit_records.append)

    orch = Orchestrator(
        provider=provider, mcp=mcp, principal=principal,
        budget=budget, audit=audit,
        max_input_chars=settings.max_input_chars,
        max_tool_calls_per_turn=settings.max_tool_calls_per_turn,
    )

    # Persist the user message up front.
    session.add(DBMessage(conversation_id=conv.id, role="user", content=body.content))
    await session.commit()

    async def event_stream() -> AsyncIterator[str]:
        assistant_text = ""
        tool_summaries: list[dict] = []
        async for ev in orch.run_turn(history, body.content):
            if ev.type == "done":
                assistant_text = ev.data.get("assistant_text", assistant_text)
            elif ev.type == "tool_result":
                tool_summaries.append(ev.data)
            yield f"event: {ev.type}\ndata: {json.dumps(ev.data)}\n\n"

        # Persist assistant message, token usage, and audit trail after streaming.
        async with get_session_ctx() as s2:
            s2.add(DBMessage(
                conversation_id=conv.id, role="assistant",
                content=assistant_text, tool_calls=tool_summaries,
            ))
            c = (await s2.execute(select(Conversation).where(Conversation.id == conv.id))).scalar_one()
            c.tokens_used = budget.used
            for rec in audit_records:
                s2.add(ToolAudit(
                    conversation_id=conv.id, principal_sub=rec.principal_sub,
                    tool_name=rec.tool_name, arguments=rec.arguments,
                    decision=rec.decision, reason=rec.reason or "",
                    success=rec.success, duration_ms=rec.duration_ms,
                ))
            await s2.commit()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# Separate session context for the post-stream write (the dependency session is
# closed once the generator starts streaming).
from contextlib import asynccontextmanager  # noqa: E402
from ..db.session import SessionLocal  # noqa: E402


@asynccontextmanager
async def get_session_ctx():
    async with SessionLocal() as session:
        yield session


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    principal: Principal = Depends(require_permission("read")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rows = (await session.execute(
        select(DBMessage).where(DBMessage.conversation_id == conversation_id).order_by(DBMessage.created_at)
    )).scalars().all()
    return {"messages": [
        {"role": m.role, "content": m.content, "tool_calls": m.tool_calls,
         "created_at": m.created_at.isoformat()}
        for m in rows
    ]}


@router.get("/{conversation_id}/audit")
async def get_audit(
    conversation_id: str,
    principal: Principal = Depends(require_permission("read")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rows = (await session.execute(
        select(ToolAudit).where(ToolAudit.conversation_id == conversation_id).order_by(ToolAudit.created_at)
    )).scalars().all()
    return {"audit": [
        {"tool": r.tool_name, "decision": r.decision, "reason": r.reason,
         "success": r.success, "duration_ms": r.duration_ms,
         "at": r.created_at.isoformat()}
        for r in rows
    ]}
