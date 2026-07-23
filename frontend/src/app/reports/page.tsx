"use client";

import { useState } from "react";
import Link from "next/link";
import { FileText, Download, Loader2, ArrowRight, Check, AlertTriangle } from "lucide-react";
import { useAssessment } from "@/lib/assessment-store";
import { downloadReport } from "@/lib/api";
import { Panel, Eyebrow } from "@/components/ui";

const SECTIONS = [
  ["Executive Summary", "Score, grade, risk counts, and a written assessment of production readiness"],
  ["Architecture Diagram", "Server-rendered zone diagram with failing components highlighted"],
  ["Compliance Results", "Per-framework score, passed/failed counts, and PASS/FAIL status"],
  ["Security Findings", "Every failing control with severity, remediation, and affected components"],
  ["Threat Model (STRIDE)", "Threats per category with mitigations and MITRE ATT&CK/ATLAS techniques"],
  ["Recommendations", "Prioritized remediation actions, critical first"],
  ["Methodology & Scope", "How findings are produced, and the limits of this assessment"],
];

export default function ReportsPage() {
  const { architecture, result } = useAssessment();
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null);

  async function generate() {
    if (!architecture) return;
    setBusy(true);
    setStatus(null);
    const r = await downloadReport(architecture);
    setStatus(r.ok ? { ok: true, msg: "Report downloaded." } : { ok: false, msg: r.error ?? "Failed." });
    setBusy(false);
  }

  if (!architecture || !result) return <EmptyState />;

  return (
    <div className="px-6 py-6">
      <h1 className="font-display text-lg font-semibold text-ink">Reports</h1>
      <p className="text-sm text-ink-muted">
        Export a professional PDF assessment for {architecture.name}.
      </p>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <Eyebrow>Report contents</Eyebrow>
          <div className="mt-4 space-y-3">
            {SECTIONS.map(([title, desc]) => (
              <div key={title} className="flex gap-3">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-pass" />
                <div>
                  <div className="text-sm text-ink">{title}</div>
                  <div className="text-[13px] text-ink-muted">{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel>
            <Eyebrow>This assessment</Eyebrow>
            <div className="mt-3 space-y-2 font-mono text-[12px]">
              <Row label="Architecture" value={architecture.name} />
              <Row label="Score" value={`${result.overall_score}/100 (${result.grade})`} />
              <Row label="Components" value={String(architecture.nodes.length)} />
              <Row label="Frameworks" value={String(result.frameworks.length)} />
              <Row label="Findings" value={String(result.summary.failed_controls ?? 0)} />
            </div>
          </Panel>

          <Panel>
            <button
              onClick={generate}
              disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-azure px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-azure-bright disabled:opacity-50"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {busy ? "Generating…" : "Generate PDF"}
            </button>
            {status && (
              <div className={`mt-3 flex items-start gap-2 text-[12px] ${status.ok ? "text-pass" : "text-severity-high"}`}>
                {status.ok ? <Check className="mt-0.5 h-3.5 w-3.5 shrink-0" /> : <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />}
                <span>{status.msg}</span>
              </div>
            )}
            <p className="mt-3 font-mono text-[10px] leading-relaxed text-ink-faint">
              The report is re-validated server-side at generation time — its numbers come from the
              engine, never from the browser.
            </p>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-ink-faint">{label}</span>
      <span className="truncate text-ink" title={value}>{value}</span>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <FileText className="mb-4 h-10 w-10 text-ink-faint" />
      <h1 className="font-display text-xl font-semibold text-ink">Nothing to report yet</h1>
      <p className="mt-2 max-w-sm text-sm text-ink-muted">
        Validate an architecture first. The report is generated from a live assessment, so there
        needs to be one to export.
      </p>
      <Link href="/designer" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-azure px-4 py-2 text-sm font-medium text-white hover:bg-azure-bright">
        Open Designer <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
