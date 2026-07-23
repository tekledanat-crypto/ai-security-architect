"use client";

import Link from "next/link";
import { ArrowRight, ShieldAlert, ShieldCheck, Activity, Boxes, Sparkles } from "lucide-react";
import { useAssessment } from "@/lib/assessment-store";
import { Panel, Eyebrow, ScoreRing, Metric } from "@/components/ui";

export default function DashboardPage() {
  const { result, architecture, updatedAt } = useAssessment();

  if (!result || !architecture) return <EmptyState />;

  const s = result.summary;
  const fails = result.findings.filter((f) => f.status === "fail");
  const applicable = (s.passed_controls ?? 0) + (s.failed_controls ?? 0);

  // Architecture health: share of services with no failing controls against them.
  const failingNodes = new Set(fails.flatMap((f) => f.affected_nodes ?? []));
  const total = architecture.nodes.length || 1;
  const health = Math.round(100 * (1 - Math.min(failingNodes.size, total) / total));

  // Compliance = share of assessed frameworks fully passing.
  const passingFw = result.frameworks.filter((f) => f.status === "PASS").length;
  const compliance = result.frameworks.length
    ? Math.round((100 * passingFw) / result.frameworks.length)
    : 0;

  const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  const recent = [...fails].sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9)).slice(0, 4);

  return (
    <div className="px-6 py-6">
      <div className="relative overflow-hidden rounded-2xl border border-border bg-surface p-6">
        <div className="grid-texture pointer-events-none absolute inset-0 opacity-40" />
        <div className="relative flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div>
            <Eyebrow>Current security posture</Eyebrow>
            <h1 className="mt-2 font-display text-2xl font-semibold text-ink">{architecture.name}</h1>
            <p className="mt-1 max-w-md text-sm text-ink-muted">
              Assessed against {result.frameworks.length} frameworks
              {updatedAt ? ` · ${new Date(updatedAt).toLocaleString()}` : ""}. Resolve critical and
              high findings first — remediation is prioritized by severity.
            </p>
            <div className="mt-4 flex gap-2">
              <Link href="/designer" className="inline-flex items-center gap-2 rounded-lg bg-azure px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-azure-bright">
                Open Designer <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/reports" className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm text-ink-muted transition-colors hover:text-ink">
                Export report
              </Link>
            </div>
          </div>
          <div className="flex items-center gap-8">
            <ScoreRing score={result.overall_score} label="Security" />
            <div className="hidden gap-6 sm:flex">
              <MiniStat label="Compliance" value={`${compliance}%`} />
              <MiniStat label="Arch health" value={`${health}%`} />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Metric label="Critical risks" value={s.critical_failures ?? 0} accent="text-severity-critical" sub="Fix immediately" />
        <Metric label="High risks" value={s.high_failures ?? 0} accent="text-severity-high" sub="Address this sprint" />
        <Metric label="Passed controls" value={s.passed_controls ?? 0} accent="text-pass" sub={`of ${applicable} applicable`} />
        <Metric label="Failed controls" value={s.failed_controls ?? 0} accent="text-fail" sub="Across all frameworks" />
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <div className="flex items-center justify-between">
            <Eyebrow>Framework compliance</Eyebrow>
            <Link href="/compliance" className="font-mono text-[10px] text-azure hover:text-azure-bright">
              View details →
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {result.frameworks.map((f) => (
              <div key={f.framework_id} className="flex items-center gap-4">
                <span className="w-44 truncate text-sm text-ink-muted" title={f.name}>{f.name}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-3">
                  <div className="h-full rounded-full transition-all" style={{ width: `${f.score}%`, background: barColor(f.score) }} />
                </div>
                <span className="w-10 text-right font-mono text-xs text-ink">{f.score}</span>
                <span className={`w-14 rounded border px-1.5 py-0.5 text-center font-mono text-[10px] ${
                  f.status === "PASS" ? "border-pass/30 bg-pass/10 text-pass" : "border-fail/30 bg-fail/10 text-fail"}`}>
                  {f.status}
                </span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <Eyebrow>Top risks</Eyebrow>
          <div className="mt-4 space-y-4">
            {recent.length === 0 ? (
              <div className="flex items-center gap-2 text-sm text-pass">
                <ShieldCheck className="h-4 w-4" /> No failing controls.
              </div>
            ) : (
              recent.map((f, i) => (
                <div key={i} className="flex gap-3">
                  <ShieldAlert className={`mt-0.5 h-4 w-4 shrink-0 ${
                    f.severity === "critical" ? "text-severity-critical" : "text-severity-high"}`} />
                  <div className="min-w-0">
                    <div className="truncate text-sm text-ink" title={f.message}>{f.message}</div>
                    <div className="font-mono text-[11px] text-ink-faint">{f.framework_id}:{f.control_id}</div>
                  </div>
                </div>
              ))
            )}
          </div>
          <Link href="/threats" className="mt-4 inline-flex items-center gap-1.5 text-xs text-azure hover:text-azure-bright">
            View threat model <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Panel>
      </div>
    </div>
  );
}

const barColor = (s: number) => (s >= 80 ? "#4fd1a5" : s >= 65 ? "#ffcf3f" : "#ff8f3f");

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-display text-2xl font-bold text-ink">{value}</div>
      <div className="font-mono text-[10px] uppercase tracking-wider text-ink-faint">{label}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-azure/15 shadow-glow">
        <Sparkles className="h-7 w-7 text-azure" />
      </div>
      <h1 className="font-display text-2xl font-semibold text-ink">No assessment yet</h1>
      <p className="mt-2 max-w-md text-sm text-ink-muted">
        Describe your solution to the AI Assistant, or build a design in the Architecture Designer
        and validate it. Your security posture will appear here.
      </p>
      <div className="mt-6 flex gap-2">
        <Link href="/assistant" className="inline-flex items-center gap-2 rounded-lg bg-azure px-4 py-2 text-sm font-medium text-white hover:bg-azure-bright">
          Talk to the assistant <ArrowRight className="h-4 w-4" />
        </Link>
        <Link href="/designer" className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm text-ink-muted hover:text-ink">
          Open Designer
        </Link>
      </div>
    </div>
  );
}
