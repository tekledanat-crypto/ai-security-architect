"use client";

import { useEffect, useState } from "react";
import { ShieldCheck, Check, X, KeyRound, UserCircle2 } from "lucide-react";
import { getPrincipal } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Principal, Role } from "@/lib/types";
import { Panel, Eyebrow } from "@/components/ui";

// The permission matrix mirrors backend/app/auth/provider.py:ROLE_PERMISSIONS.
// Shown here so the authorization model is legible to an auditor rather than
// buried in code — which is the point of documenting RBAC at all.
const PERMISSIONS = ["read", "chat", "design", "validate", "threat-model", "remediate", "report", "manage-settings"] as const;

const ROLE_PERMISSIONS: Record<Role, readonly string[]> = {
  Administrator: ["read", "chat", "design", "validate", "threat-model", "remediate", "report", "manage-settings"],
  SecurityArchitect: ["read", "chat", "design", "validate", "threat-model", "remediate", "report"],
  Auditor: ["read", "validate", "threat-model", "report"],
  ReadOnly: ["read"],
};

const ROLES: Role[] = ["Administrator", "SecurityArchitect", "Auditor", "ReadOnly"];
const LABEL: Record<Role, string> = {
  Administrator: "Administrator",
  SecurityArchitect: "Security Architect",
  Auditor: "Auditor",
  ReadOnly: "Read Only",
};

export default function SettingsPage() {
  const { config, account } = useAuth();
  const [principal, setPrincipal] = useState<Principal | null>(null);

  useEffect(() => {
    getPrincipal().then(setPrincipal).catch(() => setPrincipal(null));
  }, []);

  const isEntra = config?.provider === "entra";

  return (
    <div className="px-6 py-6">
      <h1 className="font-display text-lg font-semibold text-ink">Identity &amp; Access</h1>
      <p className="text-sm text-ink-muted">
        How this application authenticates you and what your role permits.
      </p>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel>
          <Eyebrow>Signed in as</Eyebrow>
          <div className="mt-3 flex items-start gap-3">
            <UserCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-azure" />
            <div className="min-w-0">
              <div className="truncate text-sm text-ink">{account?.name ?? principal?.name ?? "—"}</div>
              <div className="truncate font-mono text-[11px] text-ink-faint">
                {account?.username ?? principal?.sub ?? "—"}
              </div>
            </div>
          </div>
          <div className="mt-4 space-y-1.5">
            {(principal?.roles ?? []).map((r) => (
              <div key={r} className="flex items-center gap-2 rounded-md bg-surface-2 px-2.5 py-1.5 text-[13px] text-ink">
                <ShieldCheck className="h-3.5 w-3.5 text-pass" /> {LABEL[r]}
              </div>
            ))}
          </div>
        </Panel>

        <Panel className="lg:col-span-2">
          <Eyebrow>Authentication</Eyebrow>
          <div className="mt-3 flex items-start gap-3">
            <KeyRound className="mt-0.5 h-5 w-5 shrink-0 text-azure" />
            <div>
              <div className="text-sm text-ink">
                {isEntra ? "Microsoft Entra ID" : "Mock authentication (local development)"}
              </div>
              <p className="mt-1 text-[13px] leading-relaxed text-ink-muted">
                {isEntra ? (
                  <>
                    Access tokens are validated against the tenant JWKS on every request —
                    signature, issuer, audience, and expiry. Roles come from app role
                    assignments in Entra, so access is managed by your administrator, not
                    stored in this application.
                  </>
                ) : (
                  <>
                    A signed dev cookie supplies your identity so the app runs with no tenant
                    configured. This provider refuses to start when <code className="font-mono text-ink">APP_ENV=production</code>,
                    so a forgeable identity can never be issued in a deployed environment.
                  </>
                )}
              </p>
            </div>
          </div>
        </Panel>
      </div>

      <Panel className="mt-4">
        <Eyebrow>Permission matrix</Eyebrow>
        <p className="mt-1 text-[13px] text-ink-muted">
          Enforced server-side on every route. The client never decides authorization.
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 pr-4 text-left font-mono text-[10px] uppercase tracking-wider text-ink-faint">
                  Permission
                </th>
                {ROLES.map((r) => (
                  <th key={r} className="px-2 py-2 text-center font-mono text-[10px] uppercase tracking-wider text-ink-faint">
                    {LABEL[r].split(" ")[0]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {PERMISSIONS.map((perm) => (
                <tr key={perm} className="border-b border-border/50">
                  <td className="py-2 pr-4 font-mono text-[12px] text-ink-muted">{perm}</td>
                  {ROLES.map((r) => {
                    const allowed = ROLE_PERMISSIONS[r].includes(perm);
                    const isMine = principal?.roles.includes(r);
                    return (
                      <td key={r} className={`px-2 py-2 text-center ${isMine ? "bg-azure/5" : ""}`}>
                        {allowed ? (
                          <Check className="mx-auto h-3.5 w-3.5 text-pass" />
                        ) : (
                          <X className="mx-auto h-3.5 w-3.5 text-ink-faint/40" />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 font-mono text-[10px] text-ink-faint">
          Highlighted columns are roles assigned to you.
        </p>
      </Panel>
    </div>
  );
}
