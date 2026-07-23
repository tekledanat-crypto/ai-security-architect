"use client";

import Link from "next/link";
import { X, ArrowRight, ShieldAlert, ShieldCheck } from "lucide-react";
import type { ValidationResult } from "@/lib/api";
import { severityBg } from "@/lib/utils";

// Slides over the canvas after Validate. Fast feedback: score, framework rollup, and
// the top failing controls. A link hands off to the full Compliance page (Chunk 7).
export function ValidationDrawer({
  result, loading, onClose,
}: { result: ValidationResult | null; loading: boolean; onClose: () => void }) {
  if (!loading && !result) return null;

  const fails = result?.findings.filter((f) => f.status === "fail") ?? [];
  const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, informational: 4 };
  fails.sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9));

  const gradeColor =
    !result ? "#5f6f8f"
    : result.overall_score >= 90 ? "#4fd1a5"
    : result.overall_score >= 70 ? "#ffcf3f"
    : result.overall_score >= 50 ? "#ff8f3f" : "#ff4d6d";

  return (
    <div className="absolute right-0 top-0 z-20 flex h-full w-[380px] animate-fade-up flex-col border-l border-border bg-surface shadow-panel">
      <div className="flex items-center justify-between border-b border-border p-4">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">Validation results</div>
        <button onClick={onClose} className="text-ink-faint hover:text-ink"><X className="h-4 w-4" /></button>
      </div>

      {loading ? (
        <div className="flex flex-1 items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-ink-muted">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-azure" />
            <span className="font-mono text-xs">Scoring against 137 controls…</span>
          </div>
        </div>
      ) : result ? (
        <div className="flex-1 overflow-y-auto">
          <div className="border-b border-border p-5">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-xl border-2" style={{ borderColor: gradeColor }}>
                <span className="font-display text-2xl font-bold" style={{ color: gradeColor }}>{result.grade}</span>
              </div>
              <div>
                <div className="font-display text-3xl font-bold text-ink">{result.overall_score}<span className="text-lg text-ink-faint">/100</span></div>
                <div className="font-mono text-[11px] text-ink-muted">
                  {result.summary.failed_controls} failing · {result.summary.passed_controls} passing
                </div>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2">
              <Stat label="Critical" value={result.summary.critical_failures} color="#ff4d6d" />
              <Stat label="High" value={result.summary.high_failures} color="#ff8f3f" />
              <Stat label="Medium" value={result.summary.medium_failures} color="#ffcf3f" />
            </div>
          </div>

          <div className="p-4">
            <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">
              Top findings
            </div>
            {fails.length === 0 ? (
              <div className="flex items-center gap-2 rounded-lg border border-pass/30 bg-pass/10 px-3 py-3 text-sm text-pass">
                <ShieldCheck className="h-4 w-4" /> No failing controls. This design is compliant with the assessed set.
              </div>
            ) : (
              <div className="space-y-2">
                {fails.slice(0, 8).map((f, i) => (
                  <div key={i} className="rounded-lg border border-border bg-surface-2 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className={`rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase ${severityBg[f.severity]}`}>{f.severity}</span>
                      <span className="font-mono text-[10px] text-ink-faint">{f.framework_id}:{f.control_id}</span>
                    </div>
                    <div className="mt-1.5 flex items-start gap-2">
                      <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-severity-high" />
                      <span className="text-[13px] text-ink">{f.message}</span>
                    </div>
                    {f.remediation && <div className="mt-1.5 pl-5.5 text-[12px] text-ink-muted">{f.remediation}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}

      {result && (
        <div className="border-t border-border p-4">
          <Link href="/compliance" className="flex items-center justify-center gap-2 rounded-lg bg-surface-2 px-3 py-2 text-sm text-azure transition-colors hover:bg-surface-3">
            View full compliance report <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-lg bg-surface-2 p-2 text-center">
      <div className="font-display text-xl font-bold" style={{ color }}>{value}</div>
      <div className="font-mono text-[9px] uppercase tracking-wider text-ink-faint">{label}</div>
    </div>
  );
}
