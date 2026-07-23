// Mock backend, used when the FastAPI server is unreachable (e.g. static preview).
// Mirrors the behavior of the backend's FakeProvider + MCP tools so the UI demos
// identically online or off.

import type { ChatEvent, Framework, Principal } from "./types";

export function mockPrincipal(): Principal {
  return { sub: "dev-user", name: "Dev Architect", roles: ["SecurityArchitect"], primary_role: "SecurityArchitect" };
}

export function mockFrameworks(): Framework[] {
  return [
    { framework_id: "cis-azure", name: "CIS Microsoft Azure Foundations Benchmark", version: "3.0", category: "cloud-benchmark", control_count: 21 },
    { framework_id: "mcsb", name: "Microsoft Cloud Security Benchmark", version: "v1", category: "cloud-benchmark", control_count: 16 },
    { framework_id: "nist-800-53", name: "NIST SP 800-53 Rev. 5", version: "Rev.5", category: "standard", control_count: 19 },
    { framework_id: "nist-csf", name: "NIST Cybersecurity Framework", version: "2.0", category: "standard", control_count: 10 },
    { framework_id: "iso-27001", name: "ISO/IEC 27001:2022", version: "2022", category: "standard", control_count: 11 },
    { framework_id: "soc2", name: "SOC 2 Trust Services Criteria", version: "2017", category: "regulatory", control_count: 8 },
    { framework_id: "azure-waf", name: "Azure Well-Architected — Security", version: "2024", category: "best-practice", control_count: 8 },
    { framework_id: "owasp-web-top10", name: "OWASP Top 10 Web", version: "2021", category: "best-practice", control_count: 10 },
    { framework_id: "owasp-api-top10", name: "OWASP API Security Top 10", version: "2023", category: "best-practice", control_count: 10 },
    { framework_id: "owasp-llm-top10", name: "OWASP Top 10 for LLM Apps", version: "2025", category: "ai-governance", control_count: 10 },
    { framework_id: "mitre-attack-azure", name: "MITRE ATT&CK & ATLAS — Azure", version: "v15", category: "threat-model", control_count: 14 },
  ];
}

const INTERVIEW = [
  "Will end users authenticate to this application?",
  "Will it store customer or personal data?",
  "Is it internet-facing or internal only?",
  "Are you using containers or App Service to host it?",
  "Do you have regulatory obligations (PCI-DSS, GDPR, HIPAA)?",
];

let mockTurn = 0;

async function* emitText(text: string): AsyncGenerator<ChatEvent> {
  const words = text.split(" ");
  for (let i = 0; i < words.length; i++) {
    await sleep(18);
    yield { event: "text", data: { text: words[i] + (i < words.length - 1 ? " " : "") } };
  }
}

export async function* mockChatStream(content: string): AsyncGenerator<ChatEvent> {
  const lower = content.toLowerCase();
  const wantsValidate = /validate|score|check/.test(lower);
  const wantsThreats = /threat|stride/.test(lower);
  const wantsRemediate = /remediat|fix/.test(lower);

  if (wantsValidate || wantsThreats || wantsRemediate) {
    const tool = wantsThreats ? "get_stride_threats" : wantsRemediate ? "generate_remediation" : "validate_architecture";
    yield { event: "tool_call", data: { tool, arguments: { architecture: "<demo>" } } };
    await sleep(650);
    const summary = wantsThreats ? "32 STRIDE threats" : wantsRemediate ? "22 remediation items" : "score 21/100 (F), 22 failing controls";
    yield { event: "tool_result", data: { tool, summary } };
    await sleep(200);
    const narration = wantsThreats
      ? "I generated a STRIDE threat model with 32 threats across the six categories, each linked to a mitigating control and MITRE technique. The biggest exposure is Information Disclosure from your public data services."
      : wantsRemediate
      ? "Here's a prioritized remediation plan with 22 items. Top priority: disable anonymous public blob access on the Storage Account. Work down from critical to low."
      : "Your architecture scored 21/100 (grade F). I found 22 failing controls — 1 critical and 17 high severity. The most urgent issues are exposed data services and missing encryption. Say \"remediate\" for a fix plan or \"show threats\" for a STRIDE model.";
    yield* emitText(narration);
    yield { event: "done", data: { tokens_used: 4200, tokens_remaining: 195800 } };
    return;
  }

  if (/injection|ignore (all|previous)|system prompt/.test(lower)) {
    yield { event: "guardrail", data: { stage: "input", ok: true, suspicious: true, reasons: ["Input matched prompt-injection heuristic(s)."] } };
  }

  const idx = Math.min(mockTurn, INTERVIEW.length - 1);
  mockTurn = Math.min(mockTurn + 1, INTERVIEW.length - 1);
  const lead = mockTurn === 0 ? "" : "Thanks — that helps. ";
  const greet =
    content.trim().length === 0
      ? "Hi, I'm your AI Security Architect. I'll help you design a secure Azure architecture. Tell me about the solution you're building."
      : `${lead}${INTERVIEW[idx]} When you've described the design, say "validate my architecture" and I'll check it against the frameworks.`;
  yield* emitText(greet);
  yield { event: "done", data: { tokens_used: 800, tokens_remaining: 199200 } };
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

// A compact mock of the backend scoring engine (Chunk 3) so the Designer's Validate
// button works offline in the preview. It checks a representative set of high-impact
// rules against node properties; the real engine evaluates all 137 controls.
const SEV_WEIGHT: Record<string, number> = { critical: 10, high: 6, medium: 3, low: 1 };

interface MockRule {
  service: string; prop: string; secure: boolean | string;
  framework: string; control: string; title: string; severity: string; message: string; remediation: string;
}

const RULES: MockRule[] = [
  { service: "storage-account", prop: "allow_blob_public_access", secure: false, framework: "cis-azure", control: "CIS-4.1.4", title: "Disable public blob access", severity: "critical", message: "Anonymous public blob access is permitted on the Storage Account.", remediation: "Set 'Allow Blob public access' to Disabled." },
  { service: "storage-account", prop: "public_access", secure: false, framework: "cis-azure", control: "CIS-4.1.1", title: "Prohibit public storage access", severity: "high", message: "Storage Account allows public network access.", remediation: "Disable public network access and add a Private Endpoint." },
  { service: "storage-account", prop: "https_only", secure: true, framework: "cis-azure", control: "CIS-4.2", title: "Require secure transfer", severity: "high", message: "Storage Account permits unencrypted transfer.", remediation: "Enable 'Secure transfer required'." },
  { service: "azure-sql", prop: "public_access", secure: false, framework: "cis-azure", control: "CIS-5.1.2", title: "Deny public SQL access", severity: "high", message: "Azure SQL server allows public network access.", remediation: "Set public network access to Deny; use a Private Endpoint." },
  { service: "azure-sql", prop: "auditing_enabled", secure: true, framework: "cis-azure", control: "CIS-5.1.1", title: "Enable SQL auditing", severity: "medium", message: "Azure SQL auditing is not enabled.", remediation: "Enable server-level auditing to Log Analytics." },
  { service: "key-vault", prop: "firewall_enabled", secure: true, framework: "cis-azure", control: "CIS-8.1", title: "Restrict Key Vault network", severity: "high", message: "Key Vault firewall is disabled.", remediation: "Enable the Key Vault firewall and add a Private Endpoint." },
  { service: "key-vault", prop: "purge_protection", secure: true, framework: "cis-azure", control: "CIS-8.4", title: "Enable purge protection", severity: "high", message: "Key Vault purge protection is not enabled.", remediation: "Enable soft-delete and purge protection." },
  { service: "app-service", prop: "https_only", secure: true, framework: "cis-azure", control: "CIS-9.2", title: "Enforce HTTPS only", severity: "high", message: "App Service accepts unencrypted HTTP traffic.", remediation: "Enable 'HTTPS Only' and set min TLS to 1.2." },
  { service: "app-service", prop: "managed_identity", secure: true, framework: "cis-azure", control: "CIS-9.5", title: "Use managed identity", severity: "high", message: "App Service does not use a Managed Identity.", remediation: "Assign a managed identity; remove stored credentials." },
  { service: "entra-id", prop: "mfa_enabled", secure: true, framework: "cis-azure", control: "CIS-2.1.1", title: "Require MFA for admins", severity: "critical", message: "Administrator accounts are not protected by MFA.", remediation: "Enforce MFA via Conditional Access for privileged roles." },
  { service: "azure-openai", prop: "input_filtering", secure: true, framework: "owasp-llm-top10", control: "LLM01", title: "Prompt injection defense", severity: "critical", message: "AI workload has no input filtering or prompt-injection defenses.", remediation: "Apply Azure AI Content Safety Prompt Shields and input classifiers." },
  { service: "azure-openai", prop: "tool_allowlist", secure: true, framework: "owasp-llm-top10", control: "LLM06", title: "Limit excessive agency", severity: "high", message: "AI workload's tool access is not restricted by an allow-list.", remediation: "Allow-list tools per role; require approval for destructive actions." },
];

const PRESENCE = [
  { service: "app-gateway-waf", framework: "mcsb", control: "NS-6", title: "Deploy a WAF", severity: "high", message: "No Web Application Firewall protects the public entry point.", remediation: "Front public apps with Application Gateway WAF or Front Door WAF." },
  { service: "defender-for-cloud", framework: "cis-azure", control: "CIS-3.1", title: "Enable Defender for Cloud", severity: "high", message: "Microsoft Defender for Cloud is not part of the architecture.", remediation: "Enable Defender plans across resource types." },
];

export function mockValidate(architecture: any) {
  const nodes: any[] = architecture?.nodes ?? [];
  const services = new Set(nodes.map((n) => n.service));
  const findings: any[] = [];
  let earned = 0, possible = 0;

  for (const rule of RULES) {
    const affected = nodes.filter((n) => n.service === rule.service);
    if (!affected.length) continue;
    const w = SEV_WEIGHT[rule.severity];
    possible += w;
    const failing = affected.filter((n) => (n.properties?.[rule.prop]) !== rule.secure);
    if (failing.length === 0) {
      earned += w;
      findings.push({ framework_id: rule.framework, control_id: rule.control, title: rule.title, severity: rule.severity, status: "pass", message: rule.title });
    } else {
      findings.push({ framework_id: rule.framework, control_id: rule.control, title: rule.title, severity: rule.severity, status: "fail", message: rule.message, remediation: rule.remediation, affected_nodes: failing.map((n) => n.id) });
    }
  }
  // presence checks only fire when there is at least one node
  if (nodes.length) {
    for (const p of PRESENCE) {
      const w = SEV_WEIGHT[p.severity];
      possible += w;
      if (services.has(p.service)) {
        earned += w;
        findings.push({ framework_id: p.framework, control_id: p.control, title: p.title, severity: p.severity, status: "pass", message: p.title });
      } else {
        findings.push({ framework_id: p.framework, control_id: p.control, title: p.title, severity: p.severity, status: "fail", message: p.message, remediation: p.remediation, affected_nodes: [] });
      }
    }
  }

  const score = possible ? Math.round((100 * earned) / possible) : 100;
  const grade = score >= 90 ? "A" : score >= 80 ? "B" : score >= 70 ? "C" : score >= 60 ? "D" : "F";
  const fails = findings.filter((f) => f.status === "fail");
  const byFw: Record<string, any> = {};
  for (const f of findings) {
    const k = f.framework_id;
    byFw[k] ??= { framework_id: k, name: k, status: "PASS", score: 0, passed: 0, failed: 0, _e: 0, _p: 0 };
    const w = SEV_WEIGHT[f.severity];
    byFw[k]._p += w;
    if (f.status === "pass") { byFw[k].passed++; byFw[k]._e += w; } else { byFw[k].failed++; byFw[k].status = "FAIL"; }
  }
  const frameworks = Object.values(byFw).map((f: any) => ({ framework_id: f.framework_id, name: f.name, status: f.status, score: f._p ? Math.round((100 * f._e) / f._p) : 100, passed: f.passed, failed: f.failed }));

  return {
    overall_score: score, grade,
    summary: {
      critical_failures: fails.filter((f) => f.severity === "critical").length,
      high_failures: fails.filter((f) => f.severity === "high").length,
      medium_failures: fails.filter((f) => f.severity === "medium").length,
      passed_controls: findings.filter((f) => f.status === "pass").length,
      failed_controls: fails.length,
    },
    frameworks, findings,
  };
}

// Mock STRIDE threat model. Mirrors the backend (threats.py): threats are derived
// from FAILING controls, so the model is grounded in the same corpus rather than
// invented — same design principle as the real engine.
const STRIDE_ORDER: Array<[string, string]> = [
  ["spoofing", "Spoofing"],
  ["tampering", "Tampering"],
  ["repudiation", "Repudiation"],
  ["information-disclosure", "Information Disclosure"],
  ["denial-of-service", "Denial of Service"],
  ["elevation-of-privilege", "Elevation of Privilege"],
];

// control -> STRIDE categories + ATT&CK techniques (subset mirroring framework data)
const CONTROL_STRIDE: Record<string, { stride: string[]; tech: string[]; title: string }> = {
  "CIS-4.1.4": { stride: ["information-disclosure"], tech: ["T1530"], title: "Disable public blob access" },
  "CIS-4.1.1": { stride: ["information-disclosure"], tech: ["T1530"], title: "Prohibit public storage access" },
  "CIS-4.2": { stride: ["information-disclosure", "tampering"], tech: ["T1557"], title: "Require secure transfer" },
  "CIS-5.1.2": { stride: ["information-disclosure"], tech: ["T1190"], title: "Deny public SQL access" },
  "CIS-5.1.1": { stride: ["repudiation"], tech: ["T1070"], title: "Enable SQL auditing" },
  "CIS-8.1": { stride: ["information-disclosure", "tampering"], tech: ["T1552"], title: "Restrict Key Vault network" },
  "CIS-8.4": { stride: ["tampering", "denial-of-service"], tech: ["T1485"], title: "Enable purge protection" },
  "CIS-9.2": { stride: ["information-disclosure", "tampering"], tech: ["T1557"], title: "Enforce HTTPS only" },
  "CIS-9.5": { stride: ["spoofing", "information-disclosure"], tech: ["T1552.001"], title: "Use managed identity" },
  "CIS-2.1.1": { stride: ["spoofing", "elevation-of-privilege"], tech: ["T1078"], title: "Require MFA for admins" },
  "LLM01": { stride: ["tampering", "elevation-of-privilege"], tech: ["AML.T0051"], title: "Prompt injection defense" },
  "LLM06": { stride: ["elevation-of-privilege"], tech: ["AML.T0053"], title: "Limit excessive agency" },
  "NS-6": { stride: ["tampering", "denial-of-service"], tech: ["T1190"], title: "Deploy a WAF" },
  "CIS-3.1": { stride: ["tampering"], tech: ["T1562.001"], title: "Enable Defender for Cloud" },
};

export function mockThreats(architecture: any) {
  const result = mockValidate(architecture);
  const fails = result.findings.filter((f: any) => f.status === "fail");
  const buckets: Record<string, any[]> = {};

  for (const f of fails) {
    const meta = CONTROL_STRIDE[f.control_id];
    if (!meta) continue;
    for (const cat of meta.stride) {
      (buckets[cat] ??= []).push({
        threat: meta.title,
        description: f.message,
        components: f.affected_nodes ?? [],
        mitigation: f.remediation ?? "",
        severity: f.severity,
        attack_techniques: meta.tech,
        source_control: `${f.framework_id}:${f.control_id}`,
      });
    }
  }

  const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  const stride = STRIDE_ORDER.map(([id, label]) => {
    const threats = (buckets[id] ?? []).sort(
      (a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9),
    );
    return { category: label, category_id: id, threat_count: threats.length, threats };
  });

  return {
    architecture_name: architecture?.name ?? "Architecture",
    total_threats: stride.reduce((n, c) => n + c.threat_count, 0),
    stride,
  };
}
