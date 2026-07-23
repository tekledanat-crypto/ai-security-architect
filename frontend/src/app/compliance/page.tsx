"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronRight, ShieldCheck, ShieldAlert, ArrowRight, LayoutList, Layers } from "lucide-react";
import { useAssessment } from "@/lib/assessment-store";
import { Panel, ScoreRing } from "@/components/ui";
import { severityBg } from "@/lib/utils";

type View = "framework" | "severity";
const SEV_ORDER = ["critical", "high", "medium", "low", "informational"];

export default function CompliancePage() {
  const { result, architecture } = useAssessment();
  const [view, setView] = useState<View>("framework");
  const [open, setOpen] = useState<Record<string, boolean>>({});

  if (!result) return <EmptyState />;

  const fails = result.findings.filter((f) => f.status === "fail");
  const toggle = (k: string) => setOpen((o) => ({ ...o, [k]: !o[k] }));

  return (
    <div className="px-6 py-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-lg font-semibold text-ink">Compliance Results</h1>
          <p className="text-sm text-ink-muted">
            {architecture?.name ?? "Architecture"} · assessed against {result.frameworks.length} frameworks
          </p>
        </div>
        <div className="flex rounded-lg border border-border bg-surface-2 p-0.5">
          <ViewBtn active={view === "framework"} onClick={() => setView("framework")} icon={Layers} label="By framework" />
          <ViewBtn active={view === "severity"} onClick={() => setView("severity")} icon={LayoutList} label="By severity" />
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-4 rounded-xl border border-border bg-surface p-5 md:flex-row md:items-center">
        <ScoreRing score={result.overall_score} label="Compliance" />
        <div className="grid flex-1 grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Critical" value={result.summary.critical_failures ?? 0} color="#ff4d6d" />
          <Stat label="High" value={result.summary.high_failures ?? 0} color="#ff8f3f" />
          <Stat label="Passed" value={result.summary.passed_controls ?? 0} color="#4fd1a5" />
          <Stat label="Failed" value={result.summary.failed_controls ?? 0} color="#ff4d6d" />
        </div>
      </div>

      {view === "framework" ? (
        <div className="mt-5 space-y-3">
          {result.frameworks.map((fw) => {
            const fwFails = fails.filter((f) => f.framework_id === fw.framework_id);
            const isOpen = open[fw.framework_id];
            return (
              <Panel key={fw.framework_id} className="p-0">
                <button onClick={() => toggle(fw.framework_id)} className="flex w-full items-center gap-4 px-5 py-4 text-left">
                  {isOpen ? <ChevronDown className="h-4 w-4 text-ink-faint" /> : <ChevronRight className="h-4 w-4 text-ink-faint" />}
                  <div className="flex-1">
                    <div className="text-sm font-medium text-ink">{fw.name}</div>
                    <div className="font-mono text-[11px] text-ink-faint">{fw.passed} passed · {fw.failed} failed</div>
                  </div>
                  <div className="hidden h-2 w-32 overflow-hidden rounded-full bg-surface-3 sm:block">
                    <div className="h-full rounded-full" style={{ width: `${fw.score}%`, background: barColor(fw.score) }} />
                  </div>
                  <span className="w-10 text-right font-mono text-sm text-ink">{fw.score}</span>
                  <span className={`w-14 rounded border px-1.5 py-0.5 text-center font-mono text-[10px] ${
                    fw.status === "PASS" ? "border-pass/30 bg-pass/10 text-pass" : "border-fail/30 bg-fail/10 text-fail"}`}>
                    {fw.status}
                  </span>
                </button>
                {isOpen && (
                  <div className="border-t border-border px-5 py-4">
                    {fwFails.length === 0 ? (
                      <div className="flex items-center gap-2 text-sm text-pass">
                        <ShieldCheck className="h-4 w-4" /> All applicable controls pass.
                      </div>
                    ) : (
                      <div className="space-y-2">{fwFails.map((f, i) => <FindingCard key={i} f={f} />)}</div>
                    )}
                  </div>
                )}
              </Panel>
            );
          })}
        </div>
      ) : (
        <div className="mt-5 space-y-5">
          {SEV_ORDER.map((sev) => {
            const items = fails.filter((f) => f.severity === sev);
            if (!items.length) return null;
            return (
              <div key={sev}>
                <div className="mb-2 flex items-center gap-2">
                  <span className={`rounded border px-2 py-0.5 font-mono text-[10px] uppercase ${severityBg[sev]}`}>{sev}</span>
                  <span className="font-mono text-[11px] text-ink-faint">{items.length} finding{items.length > 1 ? "s" : ""}</span>
                </div>
                <div className="space-y-2">{items.map((f, i) => <FindingCard key={i} f={f} showFramework />)}</div>
              </div>
            );
          })}
          {fails.length === 0 && (
            <Panel className="flex items-center gap-2 text-sm text-pass">
              <ShieldCheck className="h-4 w-4" /> No failing controls across the assessed frameworks.
            </Panel>
          )}
        </div>
      )}
    </div>
  );
}

function FindingCard({ f, showFramework }: { f: any; showFramework?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-surface-2 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-severity-high" />
          <div>
            <div className="text-sm text-ink">{f.message}</div>
            {f.remediation && <div className="mt-1 text-[13px] text-ink-muted">{f.remediation}</div>}
            {f.affected_nodes?.length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {f.affected_nodes.map((n: string) => (
                  <span key={n} className="rounded bg-surface-3 px-1.5 py-0.5 font-mono text-[10px] text-ink-muted">{n}</span>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className={`rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase ${severityBg[f.severity]}`}>{f.severity}</span>
          <span className="font-mono text-[10px] text-ink-faint">{showFramework ? `${f.framework_id}:${f.control_id}` : f.control_id}</span>
        </div>
      </div>
    </div>
  );
}

function ViewBtn({ active, onClick, icon: Icon, label }: { active: boolean; onClick: () => void; icon: React.ElementType; label: string }) {
  return (
    <button onClick={onClick}
      className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs transition-colors ${active ? "bg-surface-3 text-ink" : "text-ink-muted hover:text-ink"}`}>
      <Icon className="h-3.5 w-3.5" /> {label}
    </button>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-lg bg-surface-2 p-3 text-center">
      <div className="font-display text-2xl font-bold" style={{ color }}>{value}</div>
      <div className="font-mono text-[9px] uppercase tracking-wider text-ink-faint">{label}</div>
    </div>
  );
}

const barColor = (s: number) => (s >= 80 ? "#4fd1a5" : s >= 65 ? "#ffcf3f" : "#ff8f3f");

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <ShieldCheck className="mb-4 h-10 w-10 text-ink-faint" />
      <h1 className="font-display text-xl font-semibold text-ink">No assessment yet</h1>
      <p className="mt-2 max-w-sm text-sm text-ink-muted">
        Validate an architecture in the Designer, or ask the AI Assistant to check your design.
        Results appear here with every failed control explained.
      </p>
      <Link href="/designer" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-azure px-4 py-2 text-sm font-medium text-white hover:bg-azure-bright">
        Open Designer <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
