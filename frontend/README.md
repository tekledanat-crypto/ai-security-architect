# Frontend — AI Security Architect

Next.js (App Router) + TypeScript + Tailwind, styled as a dark "Azure SOC Console".
Streams the AI assistant over SSE and renders a live MCP tool-activity rail — the
signature element that distinguishes this from a chatbot.

## Design system
- **Surfaces**: layered slate-blue (not pure black) — `base → surface → surface-3`
- **Primary**: Azure blue (`#3b9bff`)
- **Severity spectrum**: color is functional — critical/high/medium/low/info each
  have a dedicated hue, used consistently across findings, bars, and metrics
- **Type**: Space Grotesk (display) · Inter (body) · JetBrains Mono (telemetry/data)
- Fonts load via `<link>` with system fallbacks so the app builds in
  network-restricted CI (no `next/font` build-time fetch)

## Pages
- `/` **Dashboard** — posture snapshot: score ring, risk metrics, framework
  compliance bars, recent activity
- `/assistant` **AI Assistant** — streaming chat with the tool-activity rail
- `/designer` `/compliance` `/threats` `/reports` `/settings` — navigable
  placeholders labeled with the chunk that delivers them (6/7/7/8/11)

## Data
`src/lib/api.ts` calls the real backend (`/api/*`, proxied to FastAPI via
`next.config.mjs` rewrites). When the backend is unreachable it falls back to
`src/lib/mock.ts`, which mimics the backend's fake provider — so the UI is
demonstrable online or off, same philosophy as the backend (ADR-0001).

## Run
```bash
npm install
npm run dev          # http://localhost:3000
# with the backend up (proxied):
BACKEND_URL=http://localhost:8000 npm run dev
```

## Build
```bash
npm run build        # verified: all 8 routes compile and prerender
```

## Preview without Node
`preview.html` is a single self-contained file mirroring the real UI (dashboard +
chat + tool rail). Open it in any browser to see the design without running the
Next.js toolchain. The Next.js app is the source of truth; this is a visual proxy.

## Architecture Designer (Chunk 6)
`/designer` is a React Flow canvas over the shared architecture schema:
- **Custom Azure nodes** styled per service (icon, zone color) with an at-a-glance
  risk dot when a security property deviates from its secure default.
- **Service palette** (`src/lib/azure-services.ts`) — the catalog that drives node
  styling and each service's editable security properties. Slugs and property keys
  match the framework `check_hints`, so a toggle maps to a real control.
- **Zone auto-layout** (internet → edge → app → data → security → identity) with
  manual drag and an "Auto-layout" reset.
- **Editable property panel** — toggles write into the architecture JSON.
- **Live Validate** → `/api/architecture/validate` → results drawer (score, grade,
  severity rollup, top findings) with a link to the Compliance page (Chunk 7).
- **AI-generated diagrams** render here via `useArchitecture.loadArchitecture` using
  the same schema the assistant emits.

Offline, `validateArchitecture` falls back to `mockValidate` in `src/lib/mock.ts`,
a compact mirror of the backend engine (verified: insecure design → 0/F, hardened
→ 100/A). `preview.html` includes a fully interactive SVG version of the Designer.

## Compliance & Threat Model (Chunk 7)
- `/compliance` — toggle between **By framework** (expandable per-framework rollup with
  score bar and PASS/FAIL) and **By severity** (fix-first grouping). Every failed control
  shows the plain-English finding, its remediation, and the affected nodes.
- `/threats` — six STRIDE category cards with expandable threat rows. Each threat shows
  description, affected components, mitigation, and its MITRE ATT&CK/ATLAS technique,
  plus the source control it derives from.

**Shared assessment store** (`src/lib/assessment-store.tsx`): the Designer writes the
architecture + result here (sessionStorage-backed) so "View full report" carries state
across pages. Without it the handoff would land on an empty page.

Threats are derived from **failing controls**, mirroring the backend (`threats.py`) —
verified: insecure design → 19 threats across all six categories, each traceable to a
control and technique; hardened design → 0.
