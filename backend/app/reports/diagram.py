"""Server-side architecture diagram rendering.

Renders an architecture JSON into inline SVG for the PDF report. Deterministic and
headless — no browser, no screenshot pipeline — so report generation works the same
in Container Apps as it does locally.

Layout mirrors the frontend Designer: nodes grouped into trust zones (internet →
edge → app → data → security → identity), left to right.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

# Zone metadata mirrors frontend/src/lib/azure-services.ts so the PDF diagram reads
# the same as the on-screen canvas.
ZONES: dict[str, tuple[str, str, int]] = {
    "internet": ("Internet", "#5f6f8f", 0),
    "edge": ("Edge", "#3b9bff", 1),
    "app": ("Application", "#7c8cff", 2),
    "data": ("Data", "#4fd1a5", 3),
    "security": ("Security & Ops", "#ff8f3f", 4),
    "identity": ("Identity", "#c88bff", 5),
}

SERVICE_ZONE: dict[str, str] = {
    "front-door": "edge", "app-gateway-waf": "edge", "apim": "edge", "firewall": "edge",
    "app-service": "app", "container-apps": "app", "aks": "app", "azure-openai": "app",
    "service-bus": "app", "vnet": "app", "virtual-machine": "app",
    "azure-sql": "data", "cosmos-db": "data", "storage-account": "data",
    "key-vault": "data", "private-endpoint": "data",
    "entra-id": "identity",
    "defender-for-cloud": "security", "log-analytics": "security",
}

SERVICE_NAME: dict[str, str] = {
    "front-door": "Front Door", "app-gateway-waf": "App Gateway + WAF", "apim": "API Management",
    "firewall": "Azure Firewall", "app-service": "App Service", "container-apps": "Container Apps",
    "aks": "AKS", "azure-openai": "Azure OpenAI", "service-bus": "Service Bus", "vnet": "Virtual Network",
    "virtual-machine": "Virtual Machine", "azure-sql": "Azure SQL", "cosmos-db": "Cosmos DB",
    "storage-account": "Storage Account", "key-vault": "Key Vault", "private-endpoint": "Private Endpoint",
    "entra-id": "Microsoft Entra ID", "defender-for-cloud": "Defender for Cloud",
    "log-analytics": "Log Analytics",
}

NODE_W, NODE_H = 118, 46
COL_W, ROW_H = 138, 66
MARGIN_X, MARGIN_Y = 12, 34


def render_architecture_svg(architecture: dict, failed_node_ids: set[str] | None = None) -> str:
    """Return an inline SVG string for the architecture.

    Nodes whose IDs appear in failed_node_ids are outlined in the failure colour, so
    the report diagram itself communicates where the findings live.
    """
    failed = failed_node_ids or set()
    nodes = architecture.get("nodes", []) or []
    edges = architecture.get("edges", []) or []

    if not nodes:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="40"></svg>'

    # Assign positions by zone column / stacked row.
    per_zone: dict[str, int] = {}
    pos: dict[str, tuple[int, int, str]] = {}
    for n in nodes:
        svc = n.get("service", "")
        zone = n.get("zone") or SERVICE_ZONE.get(svc, "app")
        if zone not in ZONES:
            zone = "app"
        col = ZONES[zone][2]
        row = per_zone.get(zone, 0)
        per_zone[zone] = row + 1
        x = MARGIN_X + col * COL_W
        y = MARGIN_Y + row * ROW_H
        pos[n["id"]] = (x, y, zone)

    used_cols = {ZONES[z][2] for z in per_zone}
    width = MARGIN_X * 2 + (max(used_cols) + 1) * COL_W if used_cols else 200
    height = MARGIN_Y + max(per_zone.values(), default=1) * ROW_H + 10

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" font-family="Helvetica, Arial, sans-serif">'
    ]

    # Edges first so nodes draw on top.
    for e in edges:
        a, b = pos.get(e.get("source")), pos.get(e.get("target"))
        if not a or not b:
            continue
        x1, y1 = a[0] + NODE_W, a[1] + NODE_H // 2
        x2, y2 = b[0], b[1] + NODE_H // 2
        parts.append(
            f'<path d="M{x1},{y1} C{x1 + 20},{y1} {x2 - 20},{y2} {x2},{y2}" '
            f'stroke="#c4cddd" stroke-width="1.2" fill="none"/>'
        )

    # Zone headers
    for zone, count in per_zone.items():
        label, color, col = ZONES[zone]
        cx = MARGIN_X + col * COL_W + NODE_W // 2
        parts.append(
            f'<text x="{cx}" y="{MARGIN_Y - 12}" fill="{color}" font-size="7" '
            f'text-anchor="middle" letter-spacing="1">{escape(label.upper())}</text>'
        )

    # Nodes
    for n in nodes:
        nid = n["id"]
        x, y, zone = pos[nid]
        color = ZONES[zone][1]
        svc = n.get("service", "")
        label = n.get("label") or SERVICE_NAME.get(svc, svc)
        is_failed = nid in failed
        stroke = "#dc2f4a" if is_failed else "#d7dee9"
        stroke_w = "1.6" if is_failed else "1"

        parts.append(
            f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="8" '
            f'fill="#ffffff" stroke="{stroke}" stroke-width="{stroke_w}"/>'
        )
        parts.append(f'<rect x="{x}" y="{y}" width="3.5" height="{NODE_H}" rx="1.75" fill="{color}"/>')
        parts.append(
            f'<text x="{x + 12}" y="{y + 20}" fill="#1a2233" font-size="8.5" '
            f'font-weight="600">{escape(_truncate(label, 17))}</text>'
        )
        parts.append(
            f'<text x="{x + 12}" y="{y + 33}" fill="{color}" font-size="6.5" '
            f'letter-spacing="0.5">{escape(ZONES[zone][0].upper())}</text>'
        )
        if is_failed:
            parts.append(f'<circle cx="{x + NODE_W - 9}" cy="{y + 9}" r="3.2" fill="#dc2f4a"/>')

    parts.append("</svg>")
    return "".join(parts)


def _truncate(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"
