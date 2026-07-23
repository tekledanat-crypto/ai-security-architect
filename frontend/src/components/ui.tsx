import { cn } from "@/lib/utils";

export function Panel({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("rounded-xl border border-border bg-surface p-5 shadow-panel", className)}>
      {children}
    </div>
  );
}

export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">{children}</div>
  );
}

// Circular score gauge — the dashboard's focal metric.
export function ScoreRing({ score, label }: { score: number; label: string }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color =
    score >= 90 ? "#4fd1a5" : score >= 70 ? "#ffcf3f" : score >= 50 ? "#ff8f3f" : "#ff4d6d";
  return (
    <div className="relative flex h-36 w-36 items-center justify-center">
      <svg className="h-36 w-36 -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#243049" strokeWidth="8" />
        <circle
          cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s ease-out" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-display text-3xl font-bold text-ink">{score}</span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-ink-faint">{label}</span>
      </div>
    </div>
  );
}

export function Metric({
  label, value, sub, accent,
}: { label: string; value: string | number; sub?: string; accent?: string }) {
  return (
    <Panel className="flex flex-col">
      <Eyebrow>{label}</Eyebrow>
      <div className={cn("mt-2 font-display text-3xl font-bold", accent ?? "text-ink")}>{value}</div>
      {sub && <div className="mt-1 text-xs text-ink-muted">{sub}</div>}
    </Panel>
  );
}
