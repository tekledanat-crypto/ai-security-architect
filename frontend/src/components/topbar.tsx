"use client";

import { useEffect, useState } from "react";
import { ChevronDown, LogOut, UserCircle2 } from "lucide-react";
import { getPrincipal, switchRole } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Principal, Role } from "@/lib/types";

const ROLES: Role[] = ["Administrator", "SecurityArchitect", "Auditor", "ReadOnly"];
const ROLE_LABEL: Record<Role, string> = {
  Administrator: "Administrator",
  SecurityArchitect: "Security Architect",
  Auditor: "Auditor",
  ReadOnly: "Read Only",
};

export function Topbar() {
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const { config, account, signOut } = useAuth();
  // Under Entra, roles come from app role assignments in the tenant — switching them
  // from the browser would be nonsense (and a privilege-escalation smell).
  const canSwitchRole = config?.provider !== "entra";
  const [open, setOpen] = useState(false);

  useEffect(() => {
    getPrincipal().then(setPrincipal);
  }, []);

  async function pick(role: Role) {
    setOpen(false);
    await switchRole(role);
    const p = await getPrincipal();
    // In mock mode the server won't change; reflect the choice locally.
    setPrincipal(p.primary_role === role ? p : { ...p, primary_role: role, roles: [role] });
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface/60 px-6 backdrop-blur">
      <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink-faint">
        Azure Security Design Console
      </div>

      <div className="relative">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-2.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-sm text-ink-muted transition-colors hover:border-border-bright hover:text-ink"
        >
          <UserCircle2 className="h-[18px] w-[18px] text-azure" />
          <span className="text-ink">{principal ? ROLE_LABEL[principal.primary_role] : "…"}</span>
          <ChevronDown className="h-3.5 w-3.5" />
        </button>

        {open && (
          <div className="absolute right-0 top-full z-20 mt-2 w-56 animate-fade-up rounded-lg border border-border bg-surface-2 p-1 shadow-panel">
            {canSwitchRole ? (
              <>
                <div className="px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-ink-faint">
                  Switch role (dev)
                </div>
                {ROLES.map((r) => (
                  <button
                    key={r}
                    onClick={() => pick(r)}
                    className="flex w-full items-center justify-between rounded-md px-3 py-2 text-sm text-ink-muted transition-colors hover:bg-surface-3 hover:text-ink"
                  >
                    {ROLE_LABEL[r]}
                    {principal?.primary_role === r && <span className="h-1.5 w-1.5 rounded-full bg-azure" />}
                  </button>
                ))}
              </>
            ) : (
              <>
                <div className="border-b border-border px-3 py-2">
                  <div className="truncate text-sm text-ink" title={account?.name ?? principal?.name}>
                    {account?.name ?? principal?.name ?? "Signed in"}
                  </div>
                  <div className="truncate font-mono text-[10px] text-ink-faint" title={account?.username}>
                    {account?.username}
                  </div>
                </div>
                <div className="px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-ink-faint">
                  Roles assigned in Entra ID
                </div>
                {(principal?.roles ?? []).map((r) => (
                  <div key={r} className="flex items-center justify-between px-3 py-1.5 text-sm text-ink-muted">
                    {ROLE_LABEL[r]}
                    <span className="h-1.5 w-1.5 rounded-full bg-azure" />
                  </div>
                ))}
                <button
                  onClick={signOut}
                  className="mt-1 flex w-full items-center gap-2 rounded-md border-t border-border px-3 py-2 text-sm text-ink-muted transition-colors hover:bg-surface-3 hover:text-ink"
                >
                  <LogOut className="h-3.5 w-3.5" /> Sign out
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
