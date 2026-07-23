// Bridges the architecture JSON (the shared Chunk 3 schema the validator consumes)
// and React Flow's node/edge model. One source of truth: edits to the canvas update
// the JSON, and an AI-generated JSON re-renders the canvas.

import { useCallback, useState } from "react";
import {
  type Node, type Edge, type Connection,
  applyNodeChanges, applyEdgeChanges, addEdge as rfAddEdge,
  type NodeChange, type EdgeChange,
} from "reactflow";
import { SERVICE_MAP, ZONE_META, defaultProperties, type Zone } from "./azure-services";

export interface ArchNodeData {
  slug: string;
  label: string;
  zone: Zone;
  properties: Record<string, unknown>;
}

export interface ArchitectureJSON {
  name: string;
  description?: string;
  context?: Record<string, unknown>;
  nodes: Array<{ id: string; service: string; label?: string; zone?: string; properties?: Record<string, unknown>; position?: { x: number; y: number } }>;
  edges: Array<{ id?: string; source: string; target: string; label?: string }>;
}

// Zone-based auto-layout: columns by zone order, rows stacked within a zone.
const COL_W = 240;
const ROW_H = 110;
const TOP = 60;

export function layoutByZone(nodes: Node<ArchNodeData>[]): Node<ArchNodeData>[] {
  const perZone: Record<string, number> = {};
  return nodes.map((n) => {
    const zone = n.data.zone;
    const col = ZONE_META[zone]?.order ?? 2;
    const row = perZone[zone] ?? 0;
    perZone[zone] = row + 1;
    // Respect a manually-set position if present; else auto-place.
    if (n.position && (n.position.x !== 0 || n.position.y !== 0) && (n as any)._manual) {
      return n;
    }
    return { ...n, position: { x: 40 + col * COL_W, y: TOP + row * ROW_H } };
  });
}

function toFlow(arch: ArchitectureJSON): { nodes: Node<ArchNodeData>[]; edges: Edge[] } {
  const nodes: Node<ArchNodeData>[] = arch.nodes.map((n) => {
    const def = SERVICE_MAP[n.service];
    return {
      id: n.id,
      type: "azure",
      position: n.position ?? { x: 0, y: 0 },
      data: {
        slug: n.service,
        label: n.label ?? def?.name ?? n.service,
        zone: (n.zone as Zone) ?? def?.zone ?? "app",
        properties: { ...defaultProperties(n.service), ...(n.properties ?? {}) },
      },
    };
  });
  const edges: Edge[] = arch.edges.map((e, i) => ({
    id: e.id ?? `e${i}`,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: false,
  }));
  return { nodes: layoutByZone(nodes), edges };
}

export function toArchitectureJSON(
  name: string,
  nodes: Node<ArchNodeData>[],
  edges: Edge[],
  context?: Record<string, unknown>,
): ArchitectureJSON {
  return {
    name,
    context,
    nodes: nodes.map((n) => ({
      id: n.id,
      service: n.data.slug,
      label: n.data.label,
      zone: n.data.zone,
      properties: n.data.properties,
      position: n.position,
    })),
    edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target, label: e.label as string | undefined })),
  };
}

let idCounter = 1;
const nextId = (slug: string) => `${slug}-${idCounter++}`;

export function useArchitecture(initial: ArchitectureJSON) {
  const first = toFlow(initial);
  const [name, setName] = useState(initial.name);
  const [nodes, setNodes] = useState<Node<ArchNodeData>[]>(first.nodes);
  const [edges, setEdges] = useState<Edge[]>(first.edges);
  const [selected, setSelected] = useState<string | null>(null);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [],
  );
  const onConnect = useCallback(
    (c: Connection) => setEdges((eds) => rfAddEdge({ ...c, id: `e-${Date.now()}` }, eds)),
    [],
  );

  const addService = useCallback((slug: string) => {
    const def = SERVICE_MAP[slug];
    if (!def) return;
    const id = nextId(slug);
    setNodes((nds) =>
      layoutByZone([
        ...nds,
        {
          id, type: "azure", position: { x: 0, y: 0 },
          data: { slug, label: def.name, zone: def.zone, properties: defaultProperties(slug) },
        },
      ]),
    );
    setSelected(id);
  }, []);

  const removeNode = useCallback((id: string) => {
    setNodes((nds) => nds.filter((n) => n.id !== id));
    setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
    setSelected((s) => (s === id ? null : s));
  }, []);

  const updateProperty = useCallback((id: string, key: string, value: unknown) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, properties: { ...n.data.properties, [key]: value } } } : n,
      ),
    );
  }, []);

  const loadArchitecture = useCallback((arch: ArchitectureJSON) => {
    const flow = toFlow(arch);
    setName(arch.name);
    setNodes(flow.nodes);
    setEdges(flow.edges);
    setSelected(null);
  }, []);

  const relayout = useCallback(() => setNodes((nds) => layoutByZone(nds.map((n) => ({ ...n, _manual: false } as any)))), []);

  return {
    name, setName, nodes, edges, selected, setSelected,
    onNodesChange, onEdgesChange, onConnect,
    addService, removeNode, updateProperty, loadArchitecture, relayout,
    toJSON: (context?: Record<string, unknown>) => toArchitectureJSON(name, nodes, edges, context),
  };
}
