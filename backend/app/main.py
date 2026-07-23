"""FastAPI application entrypoint.

Wires security middleware, CORS, routers, and DB init. Startup validates that the
mock auth provider is not somehow active in production (defense in depth, ADR-0003).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db.session import init_db
from .middleware import RateLimitMiddleware, SecureHeadersMiddleware
from .routers import architecture, auth, chat, meta, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.app_env == "production" and settings.auth_provider == "mock":
        raise RuntimeError("Refusing to start: mock auth in production (ADR-0003).")
    await init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Security Architect — Backend",
        version="0.4.0",
        lifespan=lifespan,
    )

    app.add_middleware(SecureHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=120)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(meta.router)
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(architecture.router)
    app.include_router(reports.router)
    return app


app = create_app()
