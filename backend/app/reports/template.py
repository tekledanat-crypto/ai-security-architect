"""Professional report HTML template for WeasyPrint.

Print-oriented styling (light theme, A4, running headers/footers, page numbers) —
deliberately NOT the dark console theme, because this document is meant to be
printed, emailed to stakeholders, and read on paper.
"""
from __future__ import annotations

from datetime import datetime, timezone
from xml.sax.saxutils import escape

SEVERITY_COLOR = {
    "critical": "#c62842",
    "high": "#d1691f",
    "medium": "#a8830c",
    "low": "#1f8a63",
    "informational": "#5a6b85",
}


def _grade_color(score: int) -> str:
    if score >= 90:
        return "#1f8a63"
    if score >= 70:
        return "#a8830c"
    if score >= 50:
        return "#d1691f"
    return "#c62842"


def build_report_html(
    *,
    architecture: dict,
    result: dict,
    threats: dict | None,
    diagram_svg: str,
    generated_by: str,
) -> str:
    name = escape(str(architecture.get("name", "Architecture")))
    score = int(result.get("overall_score", 0))
    grade = escape(str(result.get("grade", "F")))
    summary = result.get("summary", {}) or {}
    findings = result.get("findings", []) or []
    frameworks = result.get("frameworks", []) or []
    fails = [f for f in findings if f.get("status") == "fail"]

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
    fails_sorted = sorted(fails, key=lambda f: order.get(f.get("severity", "low"), 9))

    now = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{
  size: A4; margin: 20mm 16mm 18mm 16mm;
  @top-right {{ content: "{name} — Security Architecture Report"; font-size: 7.5pt; color: #7a8699; }}
  @bottom-left {{ content: "Generated {now}"; font-size: 7.5pt; color: #7a8699; }}
  @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font-size: 7.5pt; color: #7a8699; }}
}}
@page :first {{ @top-right {{ content: ""; }} }}
body {{ font-family: Helvetica, Arial, sans-serif; color: #1a2233; font-size: 9.5pt; line-height: 1.5; }}
h1 {{ font-size: 24pt; margin: 0 0 4pt; letter-spacing: -0.5pt; }}
h2 {{ font-size: 13pt; margin: 0 0 8pt; padding-bottom: 5pt; border-bottom: 1.5pt solid #e3e8f0; }}
h3 {{ font-size: 10pt; margin: 12pt 0 5pt; }}
.section {{ page-break-inside: avoid; margin-bottom: 20pt; }}
.page-break {{ page-break-before: always; }}
.muted {{ color: #5a6b85; }}
.mono {{ font-family: "Courier New", monospace; }}

/* Cover */
.cover {{ padding: 40pt 0 24pt; border-bottom: 2pt solid #1a2233; margin-bottom: 24pt; }}
.eyebrow {{ font-size: 7.5pt; letter-spacing: 2pt; text-transform: uppercase; color: #7a8699; margin-bottom: 10pt; }}
.cover-meta {{ margin-top: 14pt; font-size: 8.5pt; color: #5a6b85; }}

/* Score block */
.score-row {{ display: flex; gap: 14pt; align-items: stretch; margin-bottom: 16pt; }}
.score-box {{ border: 2pt solid {_grade_color(score)}; border-radius: 8pt; padding: 12pt 16pt; text-align: center; min-width: 92pt; }}
.score-num {{ font-size: 30pt; font-weight: bold; color: {_grade_color(score)}; line-height: 1; }}
.score-grade {{ font-size: 9pt; color: {_grade_color(score)}; margin-top: 3pt; }}
.stats {{ display: flex; gap: 8pt; flex: 1; }}
.stat {{ flex: 1; background: #f5f7fa; border-radius: 6pt; padding: 9pt; text-align: center; }}
.stat-num {{ font-size: 16pt; font-weight: bold; }}
.stat-label {{ font-size: 6.5pt; text-transform: uppercase; letter-spacing: 0.8pt; color: #7a8699; margin-top: 2pt; }}

/* Tables */
table {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; }}
th {{ text-align: left; padding: 6pt 5pt; border-bottom: 1pt solid #d7dee9; font-size: 7pt;
     text-transform: uppercase; letter-spacing: 0.6pt; color: #7a8699; }}
td {{ padding: 6pt 5pt; border-bottom: 0.5pt solid #eef1f6; vertical-align: top; }}
.badge {{ display: inline-block; padding: 1.5pt 5pt; border-radius: 3pt; font-size: 6.5pt;
         text-transform: uppercase; letter-spacing: 0.4pt; font-weight: bold; }}
.pass {{ color: #1f8a63; font-weight: bold; }}
.fail {{ color: #c62842; font-weight: bold; }}

/* Findings */
.finding {{ border-left: 2.5pt solid #d7dee9; padding: 7pt 0 7pt 10pt; margin-bottom: 9pt; page-break-inside: avoid; }}
.finding-head {{ display: flex; justify-content: space-between; margin-bottom: 3pt; }}
.finding-msg {{ font-weight: 600; }}
.finding-rem {{ color: #5a6b85; font-size: 8.5pt; margin-top: 3pt; }}
.chip {{ display: inline-block; background: #eef1f6; border-radius: 3pt; padding: 1pt 4pt;
        font-size: 6.5pt; font-family: "Courier New", monospace; margin-right: 3pt; }}

/* Diagram */
.diagram {{ border: 1pt solid #e3e8f0; border-radius: 6pt; padding: 10pt; background: #fbfcfe; text-align: center; }}
.diagram svg {{ max-width: 100%; height: auto; }}

/* STRIDE */
.stride-cat {{ page-break-inside: avoid; margin-bottom: 12pt; }}
.stride-head {{ font-weight: bold; font-size: 9.5pt; margin-bottom: 4pt; }}
.stride-count {{ font-size: 7.5pt; color: #7a8699; font-weight: normal; }}
</style></head><body>

<div class="cover">
  <div class="eyebrow">Security Architecture Assessment</div>
  <h1>{name}</h1>
  <div class="muted">Azure cloud security review · AI Security Architect</div>
  <div class="cover-meta">
    Generated {now}<br>
    Assessed by: {escape(generated_by)}<br>
    Frameworks evaluated: {len(frameworks)}
  </div>
</div>

<div class="section">
  <h2>Executive Summary</h2>
  <div class="score-row">
    <div class="score-box">
      <div class="score-num">{score}</div>
      <div class="score-grade">Grade {grade}</div>
    </div>
    <div class="stats">
      <div class="stat"><div class="stat-num" style="color:#c62842">{summary.get('critical_failures', 0)}</div><div class="stat-label">Critical</div></div>
      <div class="stat"><div class="stat-num" style="color:#d1691f">{summary.get('high_failures', 0)}</div><div class="stat-label">High</div></div>
      <div class="stat"><div class="stat-num" style="color:#1f8a63">{summary.get('passed_controls', 0)}</div><div class="stat-label">Passed</div></div>
      <div class="stat"><div class="stat-num" style="color:#c62842">{summary.get('failed_controls', 0)}</div><div class="stat-label">Failed</div></div>
    </div>
  </div>
  <p>{_exec_narrative(score, grade, summary, len(frameworks))}</p>
</div>

<div class="section">
  <h2>Architecture</h2>
  <div class="diagram">{diagram_svg}</div>
  <p class="muted" style="font-size:8pt;margin-top:6pt">
    Components outlined in red have one or more failing controls. Zones read left to right
    from the public edge inward to data and identity.
  </p>
</div>

<div class="section page-break">
  <h2>Compliance Results</h2>
  <table>
    <thead><tr><th>Framework</th><th style="width:52pt">Score</th><th style="width:46pt">Passed</th><th style="width:46pt">Failed</th><th style="width:46pt">Status</th></tr></thead>
    <tbody>{_framework_rows(frameworks)}</tbody>
  </table>
</div>

<div class="section">
  <h2>Security Findings</h2>
  {_findings_html(fails_sorted)}
</div>

{_threats_html(threats)}

<div class="section page-break">
  <h2>Recommendations</h2>
  <p class="muted">Prioritized by severity. Address critical and high findings before production release.</p>
  <table>
    <thead><tr><th style="width:24pt">#</th><th style="width:52pt">Severity</th><th>Recommended action</th><th style="width:74pt">Control</th></tr></thead>
    <tbody>{_reco_rows(fails_sorted)}</tbody>
  </table>
</div>

<div class="section">
  <h2>Methodology & Scope</h2>
  <p>
    Findings are produced by a deterministic rules engine evaluating this architecture against
    a curated corpus of security and compliance controls. Each control defines machine-evaluable
    conditions checked against the design's declared services and security properties. Scores are
    severity-weighted (critical 10, high 6, medium 3, low 1); a control is assessed only where it
    applies to a service present in the architecture.
  </p>
  <p class="muted" style="font-size:8.5pt">
    This assessment reviews declared architectural design, not a running deployment. It complements
    but does not replace runtime scanning, penetration testing, or formal audit. Control summaries are
    paraphrased; consult the authoritative framework publications for certification purposes.
  </p>
</div>

</body></html>"""


def _exec_narrative(score: int, grade: str, summary: dict, fw_count: int) -> str:
    crit = summary.get("critical_failures", 0)
    high = summary.get("high_failures", 0)
    failed = summary.get("failed_controls", 0)
    passed = summary.get("passed_controls", 0)

    if failed == 0:
        return (
            f"This architecture passes all {passed} applicable controls across {fw_count} frameworks, "
            f"scoring {score}/100 (grade {grade}). No remediation is required for the assessed control set. "
            "Re-assess whenever the design changes."
        )

    urgency = (
        "requires immediate remediation before any production exposure"
        if crit
        else "requires remediation prior to production release"
        if high
        else "has residual findings that should be scheduled"
    )
    lead = (
        f"This architecture scored <strong>{score}/100 (grade {grade})</strong> and {urgency}. "
        f"Of the controls assessed across {fw_count} frameworks, {passed} pass and {failed} fail"
    )
    detail = (
        f", including {crit} critical and {high} high-severity findings."
        if crit or high
        else "."
    )
    close = (
        " Critical findings typically indicate data exposed to the public internet or missing "
        "authentication controls, and should be treated as blocking."
        if crit
        else " Remediation guidance for every finding is provided in the Recommendations section."
    )
    return lead + detail + close


def _framework_rows(frameworks: list) -> str:
    rows = []
    for fw in frameworks:
        status = fw.get("status", "")
        cls = "pass" if status == "PASS" else "fail"
        rows.append(
            f"<tr><td>{escape(str(fw.get('name', fw.get('framework_id', ''))))}</td>"
            f"<td class='mono'>{fw.get('score', 0)}</td>"
            f"<td>{fw.get('passed', 0)}</td><td>{fw.get('failed', 0)}</td>"
            f"<td class='{cls}'>{escape(status)}</td></tr>"
        )
    return "".join(rows) or "<tr><td colspan='5' class='muted'>No frameworks assessed.</td></tr>"


def _findings_html(fails: list) -> str:
    if not fails:
        return "<p class='pass'>No failing controls. This design is compliant with the assessed control set.</p>"
    out = []
    for f in fails:
        sev = f.get("severity", "low")
        color = SEVERITY_COLOR.get(sev, "#5a6b85")
        nodes = "".join(f"<span class='chip'>{escape(str(n))}</span>" for n in (f.get("affected_nodes") or []))
        rem = f.get("remediation")
        rem_html = f"<div class='finding-rem'>{escape(str(rem))}</div>" if rem else ""
        nodes_html = f"<div style='margin-top:4pt'>{nodes}</div>" if nodes else ""
        out.append(
            f"<div class='finding' style='border-left-color:{color}'>"
            f"<div class='finding-head'>"
            f"<span class='badge' style='background:{color}1a;color:{color}'>{escape(sev)}</span>"
            f"<span class='mono muted' style='font-size:7pt'>"
            f"{escape(str(f.get('framework_id', '')))}:{escape(str(f.get('control_id', '')))}</span>"
            f"</div>"
            f"<div class='finding-msg'>{escape(str(f.get('message', '')))}</div>"
            f"{rem_html}{nodes_html}"
            f"</div>"
        )
    return "".join(out)


def _threats_html(threats: dict | None) -> str:
    if not threats or not threats.get("stride"):
        return ""
    cats = []
    for cat in threats["stride"]:
        items = cat.get("threats", [])
        if not items:
            cats.append(
                f"<div class='stride-cat'><div class='stride-head'>{escape(cat['category'])} "
                f"<span class='stride-count'>— no threats identified</span></div></div>"
            )
            continue
        rows = []
        for t in items:
            sev = t.get("severity", "low")
            color = SEVERITY_COLOR.get(sev, "#5a6b85")
            tech = " ".join(f"<span class='chip'>{escape(str(x))}</span>" for x in (t.get("attack_techniques") or []))
            rows.append(
                f"<tr><td><strong>{escape(str(t.get('threat','')))}</strong><br>"
                f"<span class='muted' style='font-size:8pt'>{escape(str(t.get('description','')))}</span></td>"
                f"<td style='width:56pt'><span class='badge' style='background:{color}1a;color:{color}'>{escape(sev)}</span></td>"
                f"<td style='width:150pt'>{escape(str(t.get('mitigation','')))}<div style='margin-top:3pt'>{tech}</div></td></tr>"
            )
        cats.append(
            f"<div class='stride-cat'><div class='stride-head'>{escape(cat['category'])} "
            f"<span class='stride-count'>— {len(items)} threat{'s' if len(items) != 1 else ''}</span></div>"
            f"<table><thead><tr><th>Threat</th><th>Severity</th><th>Mitigation</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>"
        )
    return (
        "<div class='section page-break'><h2>Threat Model (STRIDE)</h2>"
        "<p class='muted' style='font-size:8.5pt'>Threats are derived from failing controls; each traces to a "
        "specific control and MITRE ATT&amp;CK/ATLAS technique.</p>"
        + "".join(cats)
        + "</div>"
    )


def _reco_rows(fails: list) -> str:
    rows = []
    for i, f in enumerate(fails, 1):
        sev = f.get("severity", "low")
        color = SEVERITY_COLOR.get(sev, "#5a6b85")
        rows.append(
            f"<tr><td class='mono'>{i}</td>"
            f"<td><span class='badge' style='background:{color}1a;color:{color}'>{escape(sev)}</span></td>"
            f"<td>{escape(str(f.get('remediation') or f.get('message','')))}</td>"
            f"<td class='mono' style='font-size:7pt'>{escape(str(f.get('framework_id','')))}:{escape(str(f.get('control_id','')))}</td></tr>"
        )
    return "".join(rows) or "<tr><td colspan='4' class='muted'>No remediation required.</td></tr>"
