"""PDF report generation via WeasyPrint.

WeasyPrint renders the HTML+SVG template to PDF entirely in-process — no headless
browser — which keeps the container small and deployment simple in Azure Container
Apps (Chunk 10).

If WeasyPrint's native dependencies (cairo/pango) are unavailable, generation falls
back to returning printable HTML rather than failing outright, so the feature always
degrades gracefully.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .diagram import render_architecture_svg
from .template import build_report_html

log = logging.getLogger(__name__)


@dataclass
class Report:
    content: bytes
    media_type: str
    filename: str


def _collect_failed_nodes(result: dict) -> set[str]:
    nodes: set[str] = set()
    for f in result.get("findings", []) or []:
        if f.get("status") == "fail":
            nodes.update(f.get("affected_nodes") or [])
    return nodes


def generate_report(
    *,
    architecture: dict,
    result: dict,
    threats: dict | None = None,
    generated_by: str = "AI Security Architect",
) -> Report:
    """Build the report. Returns PDF bytes, or printable HTML if WeasyPrint is unavailable."""
    svg = render_architecture_svg(architecture, _collect_failed_nodes(result))
    html = build_report_html(
        architecture=architecture,
        result=result,
        threats=threats,
        diagram_svg=svg,
        generated_by=generated_by,
    )

    safe_name = _slug(str(architecture.get("name", "architecture")))

    try:
        from weasyprint import HTML  # imported lazily: heavy native deps

        pdf = HTML(string=html).write_pdf()
        return Report(content=pdf, media_type="application/pdf", filename=f"{safe_name}-security-report.pdf")
    except Exception as exc:  # noqa: BLE001 — any WeasyPrint/native failure degrades to HTML
        log.warning("WeasyPrint unavailable (%s); returning printable HTML instead", exc)
        return Report(
            content=html.encode("utf-8"),
            media_type="text/html",
            filename=f"{safe_name}-security-report.html",
        )


def _slug(text: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "-" for c in text)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "architecture"
