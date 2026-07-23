"use client";

import { Loader2, CheckCircle2, ShieldAlert, Wrench } from "lucide-react";
import type { ToolActivity } from "@/lib/types";
import { cn } from "@/lib/utils";

// The signature element: a live rail showing the AI invoking MCP tools. This is
// what distinguishes the product from a plain chatbot — you watch it reason with
// real security tooling.
export function ToolActivityRail({ activity }: { activity: ToolActivity[] }) {
  if (activity.length === 0) return null;
  return (
    <div className="my-2 space-y-1.5 border-l-2 border-azure/30 pl-3">
      {activity.map((a, i) => (
        <div key={i} className="flex items-center gap-2 font-mono text-[12px] animate-fade-up">
          {a.status === "running" && <Loader2 className="h-3.5 w-3.5 animate-spin text-azure" />}
          {a.status === "done" && <CheckCircle2 className="h-3.5 w-3.5 text-pass" />}
          {a.status === "denied" && <ShieldAlert className="h-3.5 w-3.5 text-fail" />}
          <Wrench className="h-3 w-3 text-ink-faint" />
          <span className="text-ink-muted">{a.tool}</span>
          {a.summary && (
            <>
              <span className="text-ink-faint">→</span>
              <span className="text-ink">{a.summary}</span>
            </>
          )}
          {a.reason && <span className="text-fail">{a.reason}</span>}
        </div>
      ))}
    </div>
  );
}
