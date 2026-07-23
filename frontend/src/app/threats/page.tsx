"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bug, ChevronDown, ChevronRight, ArrowRight, Crosshair, Wrench } from "lucide-react";
import { useAssessment } from "@/lib/assessment-store";
import { fetchThreats } from "@/lib/api";
import { Panel } from "@/components/ui";
import { severityBg } from "@/lib/utils";
import type { StrideCategory, Threat } from "@/lib/types";

// STRIDE category glyphs — a compact visual language so the six categories are
// recognizable at a glance, which is how threat modelers actually scan a model.
const CAT_META: Record<string, { color: string; hint: string }> = {
  spoofing: { color: "#c88bff", hint: "Impersonating identity" },
  tampering: { color: "#ff8f3f", hint: "Modifying data or code" },
  repudiation: { color: "#ffcf3f", hint: "Denying actions occurred" },
  "information-disclosure": { color: "#ff4d6d", hint: "Exposing data" },
  "denial-of-service": { color: "#3b9bff", hint: "Degrading availability" },
  "elevation-of-privilege": { color: "#4fd1a5", hint: "Gaining unauthorized rights" },
};

export default function ThreatsPage() {
  const { architecture, threats, setThreats } = useAssessment();
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (architecture && !threats) {
      setLoading(true);
      fetchThreats(architecture)
        .then(setThreats)
        .finally(() => setLoading(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [architecture]);

  if (!architecture) return <EmptyState />;

  if (loading || !threats) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-ink-muted">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-azure" />
          <span className="font-mono text-xs">Modeling threats from failing controls…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="px-6 py-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-lg font-semibold text-ink">Threat Model</h1>
          <p className="text-sm text-ink-muted">
            {threats.architecture_name} · {threats.total_threats} threats derived from failing controls
          </p>
        </div>
        <Link href="/compliance" className="flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-ink-muted hover:text-ink">
          Compliance results <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <p className="mt-4 rounded-lg border border-border bg-surface-2 px-4 py-3 font-mono text-[11px] leading-relaxed text-ink-muted">
        Each threat traces to a specific failing control and its MITRE technique — the model is
        derived from the framework corpus, not generated freehand.
      </p>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {threats.stride.map((cat) => (
          <CategoryCard key={cat.category_id} cat={cat} open={open} setOpen={setOpen} />
        ))}
      </div>
    </div>
  );
}

function CategoryCard({
  cat, open, setOpen,
}: { cat: StrideCategory; open: Record<string, boolean>; setOpen: (f: (o: Record<string, boolean>) => Record<string, boolean>) => void }) {
  const meta = CAT_META[cat.category_id] ?? { color: "#6b7fa8", hint: "" };
  const clean = cat.threat_count === 0;

  return (
    <Panel className="p-0">
      <div className="flex items-center gap-3 border-b border-border px-5 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg" style={{ background: `${meta.color}22`, color: meta.color }}>
          <Bug className="h-[18px] w-[18px]" />
        </div>
        <div className="flex-1">
          <div className="text-sm font-medium text-ink">{cat.category}</div>
          <div className="font-mono text-[10px] text-ink-faint">{meta.hint}</div>
        </div>
        <span
          className="rounded-full px-2.5 py-1 font-mono text-[11px]"
          style={{
            background: clean ? "rgba(79,209,165,0.12)" : `${meta.color}1f`,
            color: clean ? "#4fd1a5" : meta.color,
          }}
        >
          {clean ? "clear" : `${cat.threat_count} threat${cat.threat_count > 1 ? "s" : ""}`}
        </span>
      </div>

      {clean ? (
        <div className="px-5 py-4 text-[13px] text-ink-muted">
          No failing controls map to this category in the current design.
        </div>
      ) : (
        <div className="divide-y divide-border">
          {cat.threats.map((t, i) => {
            const key = `${cat.category_id}-${i}`;
            const isOpen = open[key];
            return (
              <div key={key}>
                <button
                  onClick={() => setOpen((o) => ({ ...o, [key]: !o[key] }))}
                  className="flex w-full items-center gap-2.5 px-5 py-3 text-left"
                >
                  {isOpen ? <ChevronDown className="h-3.5 w-3.5 shrink-0 text-ink-faint" /> : <ChevronRight className="h-3.5 w-3.5 shrink-0 text-ink-faint" />}
                  <span className="flex-1 truncate text-[13px] text-ink">{t.threat}</span>
                  <span className={`rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase ${severityBg[t.severity]}`}>{t.severity}</span>
                </button>
                {isOpen && <ThreatDetail t={t} />}
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}

function ThreatDetail({ t }: { t: Threat }) {
  return (
    <div className="space-y-3 bg-surface-2/50 px-5 pb-4 pt-1">
      <p className="pl-6 text-[13px] text-ink-muted">{t.description}</p>

      {t.components.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pl-6">
          <span className="font-mono text-[10px] uppercase tracking-wider text-ink-faint">Affects</span>
          {t.components.map((c) => (
            <span key={c} className="rounded bg-surface-3 px-1.5 py-0.5 font-mono text-[10px] text-ink-muted">{c}</span>
          ))}
        </div>
      )}

      <div className="flex items-start gap-2 pl-6">
        <Wrench className="mt-0.5 h-3.5 w-3.5 shrink-0 text-pass" />
        <span className="text-[13px] text-ink">{t.mitigation}</span>
      </div>

      <div className="flex flex-wrap items-center gap-2 pl-6">
        {t.attack_techniques.map((tech) => (
          <span key={tech} className="flex items-center gap-1 rounded border border-border bg-surface-3 px-1.5 py-0.5 font-mono text-[10px] text-ink-muted">
            <Crosshair className="h-3 w-3" /> {tech}
          </span>
        ))}
        <span className="font-mono text-[10px] text-ink-faint">via {t.source_control}</span>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <Bug className="mb-4 h-10 w-10 text-ink-faint" />
      <h1 className="font-display text-xl font-semibold text-ink">No architecture to model</h1>
      <p className="mt-2 max-w-sm text-sm text-ink-muted">
        Build and validate a design first. The STRIDE model is generated from the controls your
        architecture fails, so each threat is traceable to a real finding.
      </p>
      <Link href="/designer" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-azure px-4 py-2 text-sm font-medium text-white hover:bg-azure-bright">
        Open Designer <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
