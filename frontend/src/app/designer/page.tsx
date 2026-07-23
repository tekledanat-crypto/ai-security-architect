"use client";

import { useMemo, useState } from "react";
import ReactFlow, {
  Background, Controls, MiniMap, BackgroundVariant, type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { ShieldCheck, LayoutGrid, Sparkles } from "lucide-react";
import { AzureNode } from "@/components/azure-node";
import { ServicePalette } from "@/components/service-palette";
import { PropertyPanel } from "@/components/property-panel";
import { ValidationDrawer } from "@/components/validation-drawer";
import { useArchitecture, type ArchNodeData, type ArchitectureJSON } from "@/lib/use-architecture";
import { validateArchitecture, type ValidationResult } from "@/lib/api";
import { useAssessment } from "@/lib/assessment-store";

const SEED: ArchitectureJSON = {
  name: "Demo Web Application",
  context: { internet_facing: true, stores_customer_data: true },
  nodes: [
    { id: "web", service: "app-service", properties: { https_only: false, managed_identity: false, tls_min_version: "1.0" } },
    { id: "sql", service: "azure-sql", properties: { public_access: true, private_endpoint: false, auditing_enabled: false } },
    { id: "store", service: "storage-account", properties: { public_access: true, allow_blob_public_access: true, https_only: false, private_endpoint: false } },
    { id: "kv", service: "key-vault", properties: { firewall_enabled: false, purge_protection: false } },
    { id: "entra", service: "entra-id", properties: { mfa_enabled: false } },
  ],
  edges: [
    { source: "web", target: "sql" },
    { source: "web", target: "store" },
    { source: "web", target: "kv" },
  ],
};

export default function DesignerPage() {
  const arch = useArchitecture(SEED);
  const { setAssessment } = useAssessment();
  const nodeTypes = useMemo(() => ({ azure: AzureNode }), []);

  const [result, setResult] = useState<ValidationResult | null>(null);
  const [validating, setValidating] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const selectedNode = arch.nodes.find((n) => n.id === arch.selected) ?? null;

  async function runValidate() {
    setDrawerOpen(true);
    setValidating(true);
    setResult(null);
    const json = arch.toJSON({ internet_facing: true, stores_customer_data: true });
    const r = await validateArchitecture(json);
    setResult(r);
    // Share with the Compliance / Threat Model pages so "View full report" works.
    setAssessment(json, r);
    setValidating(false);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <div>
          <h1 className="font-display text-lg font-semibold text-ink">Architecture Designer</h1>
          <p className="text-sm text-ink-muted">Build or edit an Azure design, then validate it live against the frameworks.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={arch.relayout}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-ink-muted transition-colors hover:text-ink"
          >
            <LayoutGrid className="h-4 w-4" /> Auto-layout
          </button>
          <button
            onClick={runValidate}
            className="flex items-center gap-2 rounded-lg bg-azure px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-azure-bright"
          >
            <ShieldCheck className="h-4 w-4" /> Validate
          </button>
        </div>
      </div>

      <div className="relative flex flex-1 overflow-hidden">
        <ServicePalette onAdd={arch.addService} />

        <div className="relative flex-1">
          <ReactFlow
            nodes={arch.nodes}
            edges={arch.edges}
            nodeTypes={nodeTypes}
            onNodesChange={arch.onNodesChange}
            onEdgesChange={arch.onEdgesChange}
            onConnect={arch.onConnect}
            onNodeClick={(_, n: Node<ArchNodeData>) => arch.setSelected(n.id)}
            onPaneClick={() => arch.setSelected(null)}
            fitView
            proOptions={{ hideAttribution: true }}
            className="bg-base"
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#243049" />
            <Controls className="!border-border !bg-surface-2" />
            <MiniMap
              pannable zoomable
              className="!bg-surface !border !border-border"
              nodeColor="#1c2740"
              maskColor="rgba(10,14,23,0.7)"
            />
          </ReactFlow>

          {arch.nodes.length === 0 && (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-3 text-center">
                <Sparkles className="h-8 w-8 text-ink-faint" />
                <p className="max-w-xs text-sm text-ink-muted">
                  Add services from the palette, or describe your solution in the AI Assistant and it will draw the architecture here.
                </p>
              </div>
            </div>
          )}

          <ValidationDrawer result={result} loading={validating} onClose={() => setDrawerOpen(false)} />
        </div>

        {selectedNode && !drawerOpen && (
          <PropertyPanel
            node={selectedNode}
            onUpdate={arch.updateProperty}
            onRemove={arch.removeNode}
            onClose={() => arch.setSelected(null)}
          />
        )}
      </div>
    </div>
  );
}
