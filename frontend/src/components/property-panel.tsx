"use client";

import { Trash2, X } from "lucide-react";
import { SERVICE_MAP, ZONE_META } from "@/lib/azure-services";
import type { ArchNodeData } from "@/lib/use-architecture";
import type { Node } from "reactflow";

// Editable properties for the selected node. Toggling a security property writes
// straight into the architecture JSON the validator scores — this is the fix-and-
// re-validate loop that makes the Designer more than a drawing tool.
export function PropertyPanel({
  node, onUpdate, onRemove, onClose,
}: {
  node: Node<ArchNodeData> | null;
  onUpdate: (id: string, key: string, value: unknown) => void;
  onRemove: (id: string) => void;
  onClose: () => void;
}) {
  if (!node) return null;
  const def = SERVICE_MAP[node.data.slug];
  const zone = ZONE_META[node.data.zone];
  const Icon = def?.icon;

  return (
    <div className="flex h-full w-72 shrink-0 flex-col border-l border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border p-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ background: `${zone.color}22`, color: zone.color }}>
            {Icon ? <Icon className="h-[18px] w-[18px]" /> : null}
          </div>
          <div>
            <div className="text-sm font-medium text-ink">{node.data.label}</div>
            <div className="font-mono text-[10px] uppercase tracking-wider" style={{ color: zone.color }}>{zone.label}</div>
          </div>
        </div>
        <button onClick={onClose} className="text-ink-faint hover:text-ink"><X className="h-4 w-4" /></button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {def?.props.length ? (
          <>
            <div className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">Security properties</div>
            <div className="space-y-1">
              {def.props.map((p) => {
                const value = node.data.properties[p.key];
                const isSecure = value === p.secure;
                if (p.type === "tls") {
                  return (
                    <div key={p.key} className="flex items-center justify-between rounded-lg px-2 py-2">
                      <span className="text-sm text-ink-muted">{p.label}</span>
                      <select
                        value={String(value ?? "1.2")}
                        onChange={(e) => onUpdate(node.id, p.key, e.target.value)}
                        className="rounded-md border border-border bg-surface-2 px-2 py-1 text-xs text-ink focus:border-azure/50 focus:outline-none"
                      >
                        <option value="1.0">1.0</option>
                        <option value="1.1">1.1</option>
                        <option value="1.2">1.2</option>
                        <option value="1.3">1.3</option>
                      </select>
                    </div>
                  );
                }
                return (
                  <button
                    key={p.key}
                    onClick={() => onUpdate(node.id, p.key, !value)}
                    className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-left transition-colors hover:bg-surface-2"
                  >
                    <span className="text-sm text-ink-muted">{p.label}</span>
                    <span
                      className="relative h-5 w-9 rounded-full transition-colors"
                      style={{ background: value ? "#3b9bff" : "#243049" }}
                    >
                      <span
                        className="absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all"
                        style={{ left: value ? "18px" : "2px" }}
                      />
                    </span>
                  </button>
                );
              })}
            </div>
            <p className="mt-3 font-mono text-[10px] leading-relaxed text-ink-faint">
              A high-risk dot appears on the node when any value deviates from its secure default. Run
              Validate to see the exact controls affected.
            </p>
          </>
        ) : (
          <p className="text-sm text-ink-muted">This service has no configurable security properties in the model. Its presence alone satisfies or contributes to controls.</p>
        )}
      </div>

      <div className="border-t border-border p-4">
        <button
          onClick={() => onRemove(node.id)}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-fail/30 bg-fail/10 px-3 py-2 text-sm text-fail transition-colors hover:bg-fail/20"
        >
          <Trash2 className="h-4 w-4" /> Remove node
        </button>
      </div>
    </div>
  );
}
