# ADR-0002: SQLite (dev) → PostgreSQL (prod)

**Status:** Accepted · **Chunk:** 1

## Context
Local-first development; production target is Azure Database for PostgreSQL
Flexible Server. MCP server also needs full-text search over controls.

## Decision
Single SQLAlchemy 2.x codebase + Alembic migrations. `DATABASE_URL` selects the
engine (sqlite:///./dev.db locally, postgresql+psycopg://... in Azure).
MCP server uses SQLite FTS5 locally and Postgres tsvector in prod behind one
search interface.

## Consequences
+ Zero-infrastructure local dev; docker-compose offers optional Postgres profile.
- Two FTS implementations to maintain (kept behind one small interface).
