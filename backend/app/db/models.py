"""SQLAlchemy 2.x async models (ADR-0002).

Single codebase over SQLite (dev) and Postgres (prod); the engine is chosen by
DATABASE_URL. JSON columns use SQLAlchemy's portable JSON type.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    sub: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    roles: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(256), default="New conversation")
    tokens_used: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    architectures: Mapped[list["Architecture"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | tool | system
    content: Mapped[str] = mapped_column(Text, default="")
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)  # summaries for the UI activity panel
    created_at: Mapped[datetime] = mapped_column(default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Architecture(Base):
    __tablename__ = "architectures"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    name: Mapped[str] = mapped_column(String(256))
    definition: Mapped[dict] = mapped_column(JSON, default=dict)  # architecture schema JSON
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="architectures")
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="architecture", cascade="all, delete-orphan"
    )


class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    architecture_id: Mapped[str] = mapped_column(ForeignKey("architectures.id"), index=True)
    overall_score: Mapped[int] = mapped_column(default=0)
    grade: Mapped[str] = mapped_column(String(2), default="F")
    framework_scores: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    architecture: Mapped["Architecture"] = relationship(back_populates="assessments")
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True)
    framework_id: Mapped[str] = mapped_column(String(64))
    control_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(256))
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text, default="")
    remediation: Mapped[str] = mapped_column(Text, default="")
    affected_nodes: Mapped[list] = mapped_column(JSON, default=list)

    assessment: Mapped["Assessment"] = relationship(back_populates="findings")


class ToolAudit(Base):
    """Persistent tool-call audit trail (OWASP LLM06/LLM08; NIST AI RMF Manage)."""
    __tablename__ = "tool_audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    principal_sub: Mapped[str] = mapped_column(String(128), index=True)
    tool_name: Mapped[str] = mapped_column(String(64))
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    decision: Mapped[str] = mapped_column(String(16))  # allowed | denied
    reason: Mapped[str] = mapped_column(String(256), default="")
    success: Mapped[bool | None] = mapped_column(default=None)
    duration_ms: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)
