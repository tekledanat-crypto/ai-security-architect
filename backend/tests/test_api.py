"""End-to-end API tests using the fake provider + in-process MCP (offline)."""
from tests.conftest import sse_events


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_ready_reports_tools(client):
    data = client.get("/api/ready").json()
    assert data["mcp_ok"] is True
    assert data["tool_count"] == 12
    assert data["ai_provider"] == "fake"


def test_whoami_default_architect(client):
    data = client.get("/api/auth/me").json()
    assert data["primary_role"] == "SecurityArchitect"


def test_secure_headers_present(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in r.headers


def test_frameworks_passthrough(client):
    data = client.get("/api/frameworks").json()
    assert len(data["frameworks"]) == 11


def test_chat_greeting_streams(client):
    with client.stream("POST", "/api/chat/c1/message",
                       json={"content": "I want to build an ecommerce site"}) as r:
        evs = sse_events(r)
    kinds = [e["event"] for e in evs]
    assert "text" in kinds
    assert kinds[-1] == "done"


def test_chat_triggers_tool_call_and_audit(client):
    # seed a turn, then ask to validate
    with client.stream("POST", "/api/chat/c2/message", json={"content": "ecommerce site"}) as r0:
        sse_events(r0)
    with client.stream("POST", "/api/chat/c2/message",
                       json={"content": "validate my architecture"}) as r:
        evs = sse_events(r)
    kinds = [e["event"] for e in evs]
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    # audit trail persisted
    audit = client.get("/api/chat/c2/audit").json()["audit"]
    assert any(a["tool"] == "validate_architecture" and a["decision"] == "allowed" for a in audit)


def test_direct_validation_endpoint(client):
    body = {"architecture": {"name": "t", "nodes": [
        {"id": "s", "service": "storage-account",
         "properties": {"public_access": True, "allow_blob_public_access": True}}], "edges": []}}
    data = client.post("/api/architecture/validate", json=body).json()
    assert "overall_score" in data
    assert data["grade"] in {"A", "B", "C", "D", "F"}


def test_rbac_readonly_cannot_validate(client):
    # switch to ReadOnly, then attempt validation
    client.post("/api/auth/dev/switch-role", params={"role": "ReadOnly"})
    body = {"architecture": {"name": "t", "nodes": [], "edges": []}}
    r = client.post("/api/architecture/validate", json=body)
    assert r.status_code == 403


def test_rbac_auditor_cannot_remediate(client):
    client.post("/api/auth/dev/switch-role", params={"role": "Auditor"})
    body = {"architecture": {"name": "t", "nodes": [], "edges": []}}
    assert client.post("/api/architecture/remediate", json=body).status_code == 403
    # but CAN validate
    assert client.post("/api/architecture/validate", json=body).status_code == 200


def test_report_endpoint_generates(client):
    body = {"architecture": {"name": "API Test", "nodes": [
        {"id": "s", "service": "storage-account",
         "properties": {"public_access": True, "allow_blob_public_access": True}}], "edges": []}}
    r = client.post("/api/reports/generate", json=body)
    assert r.status_code == 200
    assert r.headers["content-type"] in ("application/pdf", "text/html; charset=utf-8")
    assert "attachment" in r.headers["content-disposition"]
    assert len(r.content) > 1000


def test_report_rbac_readonly_denied(client):
    client.post("/api/auth/dev/switch-role", params={"role": "ReadOnly"})
    body = {"architecture": {"name": "x", "nodes": [], "edges": []}}
    assert client.post("/api/reports/generate", json=body).status_code == 403


def test_report_rbac_auditor_allowed(client):
    # Auditors legitimately need to export evidence.
    client.post("/api/auth/dev/switch-role", params={"role": "Auditor"})
    body = {"architecture": {"name": "x", "nodes": [
        {"id": "s", "service": "app-service", "properties": {"https_only": True}}], "edges": []}}
    assert client.post("/api/reports/generate", json=body).status_code == 200
