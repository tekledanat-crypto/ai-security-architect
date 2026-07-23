"use client";

import { Handle, Position, type NodeProps } from "reactflow";
import { SERVICE_MAP, ZONE_META } from "@/lib/azure-services";
import type { ArchNodeData } from "@/lib/use-architecture";

// A custom node styled per Azure service. It surfaces an at-a-glance risk dot when
// any security property deviates from its secure default, so the diagram itself
// communicates posture before validation runs.
export function AzureNode({ data, selected }: NodeProps<ArchNodeData>) {
  const def = SERVICE_MAP[data.slug];
  const Icon = def?.icon;
  const zone = ZONE_META[data.zone];

  const risky = def?.props.some((p) => data.properties[p.key] !== p.secure) ?? false;

  return (
    <div
      className="group relative w-[168px] rounded-xl border bg-surface-2 px-3 py-2.5 transition-colors"
      style={{
        borderColor: selected ? "#3b9bff" : "#243049",
        boxShadow: selected ? "0 0 0 1px #3b9bff, 0 0 20px rgba(59,155,255,0.15)" : undefined,
      }}
    >
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-0 !bg-ink-faint" />
      <div className="flex items-center gap-2.5">
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
          style={{ background: `${zone.color}22`, color: zone.color }}
        >
          {Icon ? <Icon className="h-[18px] w-[18px]" /> : null}
        </div>
        <div className="min-w-0">
          <div className="truncate text-[13px] font-medium text-ink">{data.label}</div>
          <div className="font-mono text-[9px] uppercase tracking-wider" style={{ color: zone.color }}>
            {zone.label}
          </div>
        </div>
        {risky && (
          <span
            className="absolute right-2 top-2 h-2 w-2 rounded-full bg-severity-high"
            title="A security property deviates from its secure default"
          />
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-0 !bg-ink-faint" />
    </div>
  );
}
