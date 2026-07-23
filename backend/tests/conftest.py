"""Backend test fixtures.

Forces the keyless, in-process configuration so the whole suite runs offline and
deterministically (fake AI provider + in-process MCP tools + throwaway SQLite DB).
"""
from __future__ import annotations

import os
import tempfile

import pytest

# Configure BEFORE importing the app so settings pick these up.
_tmp_db = os.path.join(tempfile.gettempdir(), "ai_sec_test.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)
os.environ.update(
    APP_ENV="development",
    AI_PROVIDER="fake",
    MCP_TRANSPORT="in-process",
    DATABASE_URL=f"sqlite+aiosqlite:///{_tmp_db}",
    AUTH_PROVIDER="mock",
    MOCK_AUTH_SECRET="test-secret",
)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    # Context manager triggers lifespan → init_db().
    with TestClient(app) as c:
        yield c


def sse_events(response) -> list[dict]:
    """Parse an SSE stream body into a list of {'event','data'} dicts."""
    import json
    events = []
    cur_event = None
    for raw in response.iter_lines():
        line = raw if isinstance(raw, str) else raw.decode()
        if line.startswith("event:"):
            cur_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = line.split(":", 1)[1].strip()
            events.append({"event": cur_event, "data": json.loads(data) if data else {}})
    return events
