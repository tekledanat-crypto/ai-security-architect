// Types mirroring the backend API contracts (Chunk 4).

export type Role = "Administrator" | "SecurityArchitect" | "Auditor" | "ReadOnly";

export interface Principal {
  sub: string;
  name: string;
  roles: Role[];
  primary_role: Role;
}

export type Severity = "critical" | "high" | "medium" | "low" | "informational";

export interface Framework {
  framework_id: string;
  name: string;
  version: string;
  category: string;
  control_count: number;
}

// Streaming orchestrator events (SSE) from POST /api/chat/:id/message
export type ChatEvent =
  | { event: "text"; data: { text: string } }
  | { event: "tool_call"; data: { tool: string; arguments: Record<string, unknown> } }
  | { event: "tool_result"; data: { tool: string; summary: string } }
  | { event: "guardrail"; data: { stage: string; ok: boolean; reasons?: string[]; suspicious?: boolean } }
  | { event: "error"; data: { message: string } }
  | { event: "done"; data: { assistant_text?: string; tokens_used?: number; tokens_remaining?: number } };

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolActivity: ToolActivity[];
}

export interface ToolActivity {
  tool: string;
  status: "running" | "done" | "denied";
  summary?: string;
  reason?: string;
}

// STRIDE threat model (from POST /api/architecture/threats — MCP get_stride_threats)
export interface Threat {
  threat: string;
  description: string;
  components: string[];
  mitigation: string;
  severity: Severity;
  attack_techniques: string[];
  source_control: string;
}

export interface StrideCategory {
  category: string;
  category_id: string;
  threat_count: number;
  threats: Threat[];
}

export interface ThreatModel {
  architecture_name: string;
  total_threats: number;
  stride: StrideCategory[];
}
