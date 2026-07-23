"""Async database engine and session management (ADR-0002)."""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from ..config import get_settings
from .models import Base

_settings = get_settings()

# Ensure the SQLite directory exists for the default dev path.
if _settings.database_url.startswith("sqlite"):
    db_path = _settings.database_url.split("///")[-1]
    if db_path and db_path != ":memory:":
        Path(os.path.dirname(db_path) or ".").mkdir(parents=True, exist_ok=True)

engine = create_async_engine(_settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:  # FastAPI dependency
    async with SessionLocal() as session:
        yield session
