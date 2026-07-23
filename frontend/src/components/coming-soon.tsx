import { Construction } from "lucide-react";

export function ComingSoon({ title, chunk, blurb }: { title: string; chunk: number; blurb: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-3">
        <Construction className="h-7 w-7 text-ink-faint" />
      </div>
      <h1 className="font-display text-2xl font-semibold text-ink">{title}</h1>
      <p className="mt-2 max-w-md text-sm text-ink-muted">{blurb}</p>
      <span className="mt-4 rounded-full border border-border bg-surface-2 px-3 py-1 font-mono text-[11px] text-ink-faint">
        Arrives in Chunk {chunk}
      </span>
    </div>
  );
}
