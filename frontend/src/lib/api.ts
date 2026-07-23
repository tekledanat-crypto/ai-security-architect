// API client. Talks to the real FastAPI backend; falls back to a local mock that
// mimics the backend's fake provider so the UI is demonstrable with no server
// (same philosophy as the backend's keyless fake provider, ADR-0001).

import type { ChatEvent, Framework, Principal, ThreatModel } from "./types";
import { mockChatStream, mockFrameworks, mockPrincipal } from "./mock";
import { getAuthHeader } from "./auth-context";

/**
 * fetch with the Entra bearer token attached when one is available.
 * Under mock auth getAuthHeader() returns {} and the backend falls back to the dev
 * identity cookie, so the same call site works in both modes.
 */
async function authFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const auth = await getAuthHeader();
  return fetch(input, {
    ...init,
    headers: { ...(init.headers ?? {}), ...auth },
  });
}

async function reachable(): Promise<boolean> {
  try {
    const r = await authFetch("/api/health", { signal: AbortSignal.timeout(1200) });
    return r.ok;
  } catch {
    return false;
  }
}

export async function getPrincipal(): Promise<Principal> {
  try {
    const r = await authFetch("/api/auth/me");
    if (r.ok) return (await r.json()) as Principal;
  } catch {
    /* fall through */
  }
  return mockPrincipal();
}

export async function getFrameworks(): Promise<Framework[]> {
  try {
    const r = await authFetch("/api/frameworks");
    if (r.ok) return ((await r.json()).frameworks ?? []) as Framework[];
  } catch {
    /* fall through */
  }
  return mockFrameworks();
}

/**
 * Stream a chat turn. Yields typed ChatEvents. Uses the real SSE endpoint when the
 * backend is up, otherwise a mock generator with the same event shape.
 */
export async function* streamChat(
  conversationId: string,
  content: string,
): AsyncGenerator<ChatEvent> {
  if (!(await reachable())) {
    yield* mockChatStream(content);
    return;
  }

  const resp = await authFetch(`/api/chat/${conversationId}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });

  if (!resp.body) {
    yield* mockChatStream(content);
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const evt = parseFrame(frame);
      if (evt) yield evt;
    }
  }
}

function parseFrame(frame: string): ChatEvent | null {
  let event = "";
  let data = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!event) return null;
  try {
    return { event, data: data ? JSON.parse(data) : {} } as ChatEvent;
  } catch {
    return null;
  }
}

export async function switchRole(role: string): Promise<void> {
  try {
    await authFetch(`/api/auth/dev/switch-role?role=${encodeURIComponent(role)}`, { method: "POST" });
  } catch {
    /* mock mode: no-op */
  }
}

export interface ValidationResult {
  overall_score: number;
  grade: string;
  summary: Record<string, number>;
  frameworks: Array<{ framework_id: string; name: string; status: string; score: number; passed: number; failed: number }>;
  findings: Array<{
    framework_id: string; control_id: string; title: string;
    severity: string; status: string; message: string; remediation?: string; affected_nodes?: string[];
  }>;
}

// Validate an architecture directly (Designer "Validate" button, Compliance page).
export async function validateArchitecture(architecture: unknown): Promise<ValidationResult> {
  try {
    const r = await authFetch("/api/architecture/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ architecture }),
    });
    if (r.ok) return (await r.json()) as ValidationResult;
  } catch {
    /* fall through */
  }
  const { mockValidate } = await import("./mock");
  return mockValidate(architecture);
}

// STRIDE threat model for an architecture (Threat Model page).
export async function fetchThreats(architecture: unknown): Promise<ThreatModel> {
  try {
    const r = await authFetch("/api/architecture/threats", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ architecture }),
    });
    if (r.ok) return (await r.json()) as ThreatModel;
  } catch {
    /* fall through */
  }
  const { mockThreats } = await import("./mock");
  return mockThreats(architecture);
}

/**
 * Generate the PDF report server-side and trigger a download.
 * Returns false when the backend is unreachable (no client-side PDF fallback —
 * the report must come from the engine, not the browser).
 */
export async function downloadReport(architecture: unknown): Promise<{ ok: boolean; error?: string }> {
  try {
    const r = await authFetch("/api/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ architecture, include_threats: true }),
    });
    if (!r.ok) {
      if (r.status === 403) return { ok: false, error: "Your role may not export reports." };
      return { ok: false, error: `Report generation failed (${r.status}).` };
    }
    const blob = await r.blob();
    const disposition = r.headers.get("Content-Disposition") ?? "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match?.[1] ?? "security-report.pdf";

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    return { ok: true };
  } catch {
    return { ok: false, error: "Backend unreachable. Start the API to generate reports." };
  }
}
