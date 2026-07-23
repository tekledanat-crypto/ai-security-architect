"use client";

import { useState } from "react";
import { Plus, Search } from "lucide-react";
import { SERVICES, ZONE_META, type Zone } from "@/lib/azure-services";

// Grouped, searchable palette of Azure services. Click to drop one on the canvas.
export function ServicePalette({ onAdd }: { onAdd: (slug: string) => void }) {
  const [q, setQ] = useState("");
  const filtered = SERVICES.filter(
    (s) => s.name.toLowerCase().includes(q.toLowerCase()) || s.slug.includes(q.toLowerCase()),
  );

  const byZone = filtered.reduce<Record<string, typeof SERVICES>>((acc, s) => {
    (acc[s.zone] ??= []).push(s);
    return acc;
  }, {});

  const zones = Object.keys(ZONE_META) as Zone[];

  return (
    <div className="flex h-full w-56 shrink-0 flex-col border-r border-border bg-surface">
      <div className="border-b border-border p-3">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">Add service</div>
        <div className="mt-2 flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-2.5">
          <Search className="h-3.5 w-3.5 text-ink-faint" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search"
            className="w-full bg-transparent py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {zones.map((z) => {
          const items = byZone[z];
          if (!items?.length) return null;
          return (
            <div key={z} className="mb-3">
              <div className="px-2 py-1 font-mono text-[9px] uppercase tracking-wider" style={{ color: ZONE_META[z].color }}>
                {ZONE_META[z].label}
              </div>
              {items.map((s) => {
                const Icon = s.icon;
                return (
                  <button
                    key={s.slug}
                    onClick={() => onAdd(s.slug)}
                    className="group flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-[13px] text-ink-muted transition-colors hover:bg-surface-2 hover:text-ink"
                  >
                    <Icon className="h-4 w-4 shrink-0 text-ink-faint group-hover:text-ink-muted" />
                    <span className="flex-1 truncate">{s.name}</span>
                    <Plus className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
