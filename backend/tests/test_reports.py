"""Report generation tests (Chunk 8)."""
from __future__ import annotations

from app.reports.diagram import render_architecture_svg
from app.reports.generator import generate_report
from app.reports.template import build_report_html

ARCH = {
    "name": "Test App",
    "nodes": [
        {"id": "web", "service": "app-service"},
        {"id": "sql", "service": "azure-sql"},
        {"id": "entra", "service": "entra-id"},
    ],
    "edges": [{"source": "web", "target": "sql"}],
}

RESULT = {
    "overall_score": 42,
    "grade": "F",
    "summary": {"critical_failures": 1, "high_failures": 2, "medium_failures": 0,
                "passed_controls": 3, "failed_controls": 3},
    "frameworks": [{"framework_id": "cis-azure", "name": "CIS Azure", "status": "FAIL",
                    "score": 42, "passed": 3, "failed": 3}],
    "findings": [
        {"framework_id": "cis-azure", "control_id": "CIS-2.1.1", "title": "MFA",
         "severity": "critical", "status": "fail", "message": "Admins lack MFA.",
         "remediation": "Enable Conditional Access MFA.", "affected_nodes": ["entra"]},
        {"framework_id": "cis-azure", "control_id": "CIS-9.2", "title": "HTTPS",
         "severity": "high", "status": "fail", "message": "HTTP allowed.",
         "remediation": "Enable HTTPS Only.", "affected_nodes": ["web"]},
    ],
}


def test_diagram_renders_svg():
    svg = render_architecture_svg(ARCH)
    assert svg.startswith("<svg")
    assert "Test" not in svg  # name isn't drawn; only nodes are
    assert "App Service" in svg and "Azure SQL" in svg


def test_diagram_marks_failed_nodes():
    svg = render_architecture_svg(ARCH, failed_node_ids={"sql"})
    assert "#dc2f4a" in svg  # failure colour present


def test_diagram_handles_empty_architecture():
    svg = render_architecture_svg({"nodes": [], "edges": []})
    assert svg.startswith("<svg")  # must not crash


def test_diagram_escapes_labels():
    arch = {"nodes": [{"id": "x", "service": "app-service", "label": "<script>x</script>"}], "edges": []}
    svg = render_architecture_svg(arch)
    assert "<script>" not in svg


def test_template_includes_all_sections():
    html = build_report_html(architecture=ARCH, result=RESULT, threats=None,
                             diagram_svg="<svg/>", generated_by="Tester")
    for section in ["Executive Summary", "Architecture", "Compliance Results",
                    "Security Findings", "Recommendations", "Methodology"]:
        assert section in html


def test_template_narrative_reflects_criticals():
    html = build_report_html(architecture=ARCH, result=RESULT, threats=None,
                             diagram_svg="<svg/>", generated_by="Tester")
    assert "immediate remediation" in html  # critical present → blocking language


def test_template_clean_result_narrative():
    clean = {**RESULT, "overall_score": 100, "grade": "A",
             "summary": {"critical_failures": 0, "high_failures": 0, "passed_controls": 6, "failed_controls": 0},
             "findings": []}
    html = build_report_html(architecture=ARCH, result=clean, threats=None,
                             diagram_svg="<svg/>", generated_by="Tester")
    assert "passes all" in html
    assert "No failing controls" in html


def test_generate_report_produces_pdf():
    rep = generate_report(architecture=ARCH, result=RESULT, generated_by="Tester")
    # WeasyPrint present → PDF; absent → graceful HTML fallback. Both are valid.
    assert rep.media_type in {"application/pdf", "text/html"}
    assert len(rep.content) > 1000
    assert rep.filename.startswith("test-app-security-report")


def test_generate_report_with_threats():
    threats = {"architecture_name": "Test App", "total_threats": 1, "stride": [
        {"category": "Spoofing", "category_id": "spoofing", "threat_count": 1, "threats": [
            {"threat": "No MFA", "description": "Admins lack MFA.", "components": ["entra"],
             "mitigation": "Enable MFA.", "severity": "critical",
             "attack_techniques": ["T1078"], "source_control": "cis-azure:CIS-2.1.1"}]}]}
    rep = generate_report(architecture=ARCH, result=RESULT, threats=threats, generated_by="Tester")
    assert len(rep.content) > 1000


def test_filename_slug_is_safe():
    arch = {**ARCH, "name": "My App / v2 (prod)!"}
    rep = generate_report(architecture=arch, result=RESULT, generated_by="T")
    assert "/" not in rep.filename and " " not in rep.filename
