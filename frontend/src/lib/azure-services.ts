// Azure service catalog. Drives node rendering (icon, color, zone) and the default
// security properties each service exposes in the property panel. Service slugs match
// the architecture schema (Chunk 3) and the framework check_hints, so a toggle here
// maps directly to a control the validator evaluates.

import type { LucideIcon } from "lucide-react";
import {
  Globe, ShieldCheck, Server, Database, KeyRound, Lock, Container,
  Boxes, Network, Flame, Waypoints, Cpu, HardDrive, Radio, Activity,
  UserCheck, Cloud, GitBranch,
} from "lucide-react";

export type Zone = "internet" | "edge" | "app" | "data" | "security" | "identity";

export const ZONE_META: Record<Zone, { label: string; color: string; order: number }> = {
  internet: { label: "Internet", color: "#5f6f8f", order: 0 },
  edge: { label: "Edge", color: "#3b9bff", order: 1 },
  app: { label: "Application", color: "#7c8cff", order: 2 },
  data: { label: "Data", color: "#4fd1a5", order: 3 },
  security: { label: "Security & Ops", color: "#ff8f3f", order: 4 },
  identity: { label: "Identity", color: "#c88bff", order: 5 },
};

export interface PropSpec {
  key: string;
  label: string;
  // "secure" is the value that satisfies controls; the panel highlights deviations.
  secure: boolean | string;
  type: "bool" | "tls";
}

export interface ServiceDef {
  slug: string;
  name: string;
  icon: LucideIcon;
  zone: Zone;
  props: PropSpec[];
}

const TLS: PropSpec = { key: "tls_min_version", label: "Min TLS version", secure: "1.2", type: "tls" };

export const SERVICES: ServiceDef[] = [
  { slug: "front-door", name: "Front Door", icon: Globe, zone: "edge", props: [] },
  { slug: "app-gateway-waf", name: "App Gateway + WAF", icon: ShieldCheck, zone: "edge", props: [] },
  { slug: "apim", name: "API Management", icon: Waypoints, zone: "edge",
    props: [{ key: "rate_limited", label: "Rate limiting", secure: true, type: "bool" }] },
  { slug: "firewall", name: "Azure Firewall", icon: Flame, zone: "edge", props: [] },
  {
    slug: "app-service", name: "App Service", icon: Server, zone: "app",
    props: [
      { key: "https_only", label: "HTTPS only", secure: true, type: "bool" },
      { key: "managed_identity", label: "Managed identity", secure: true, type: "bool" },
      TLS,
    ],
  },
  {
    slug: "container-apps", name: "Container Apps", icon: Container, zone: "app",
    props: [{ key: "managed_identity", label: "Managed identity", secure: true, type: "bool" }],
  },
  { slug: "aks", name: "AKS", icon: Boxes, zone: "app",
    props: [{ key: "managed_identity", label: "Managed identity", secure: true, type: "bool" }] },
  {
    slug: "azure-openai", name: "Azure OpenAI", icon: Cpu, zone: "app",
    props: [
      { key: "input_filtering", label: "Input filtering", secure: true, type: "bool" },
      { key: "tool_allowlist", label: "Tool allow-list", secure: true, type: "bool" },
      { key: "rate_limited", label: "Rate limiting", secure: true, type: "bool" },
    ],
  },
  {
    slug: "azure-sql", name: "Azure SQL", icon: Database, zone: "data",
    props: [
      { key: "public_access", label: "Public network access", secure: false, type: "bool" },
      { key: "private_endpoint", label: "Private endpoint", secure: true, type: "bool" },
      { key: "auditing_enabled", label: "Auditing enabled", secure: true, type: "bool" },
      { key: "tde_enabled", label: "TDE at rest", secure: true, type: "bool" },
    ],
  },
  {
    slug: "cosmos-db", name: "Cosmos DB", icon: Database, zone: "data",
    props: [
      { key: "public_access", label: "Public network access", secure: false, type: "bool" },
      { key: "private_endpoint", label: "Private endpoint", secure: true, type: "bool" },
    ],
  },
  {
    slug: "storage-account", name: "Storage Account", icon: HardDrive, zone: "data",
    props: [
      { key: "public_access", label: "Public network access", secure: false, type: "bool" },
      { key: "allow_blob_public_access", label: "Anonymous blob access", secure: false, type: "bool" },
      { key: "https_only", label: "Secure transfer only", secure: true, type: "bool" },
      { key: "private_endpoint", label: "Private endpoint", secure: true, type: "bool" },
    ],
  },
  {
    slug: "key-vault", name: "Key Vault", icon: KeyRound, zone: "data",
    props: [
      { key: "firewall_enabled", label: "Firewall enabled", secure: true, type: "bool" },
      { key: "purge_protection", label: "Purge protection", secure: true, type: "bool" },
    ],
  },
  { slug: "service-bus", name: "Service Bus", icon: Radio, zone: "app", props: [] },
  {
    slug: "entra-id", name: "Microsoft Entra ID", icon: UserCheck, zone: "identity",
    props: [
      { key: "mfa_enabled", label: "MFA (privileged)", secure: true, type: "bool" },
      { key: "mfa_all_users", label: "MFA (all users)", secure: true, type: "bool" },
      { key: "legacy_auth_blocked", label: "Legacy auth blocked", secure: true, type: "bool" },
      { key: "pim_enabled", label: "PIM enabled", secure: true, type: "bool" },
    ],
  },
  { slug: "defender-for-cloud", name: "Defender for Cloud", icon: ShieldCheck, zone: "security", props: [] },
  { slug: "log-analytics", name: "Log Analytics", icon: Activity, zone: "security", props: [] },
  { slug: "private-endpoint", name: "Private Endpoint", icon: Lock, zone: "data", props: [] },
  { slug: "vnet", name: "Virtual Network", icon: Network, zone: "app", props: [] },
  { slug: "virtual-machine", name: "Virtual Machine", icon: Cloud, zone: "app",
    props: [{ key: "jit_access", label: "Just-in-time access", secure: true, type: "bool" }] },
];

export const SERVICE_MAP: Record<string, ServiceDef> = Object.fromEntries(
  SERVICES.map((s) => [s.slug, s]),
);

export function defaultProperties(slug: string): Record<string, unknown> {
  const def = SERVICE_MAP[slug];
  if (!def) return {};
  const out: Record<string, unknown> = {};
  for (const p of def.props) out[p.key] = p.secure;
  return out;
}
