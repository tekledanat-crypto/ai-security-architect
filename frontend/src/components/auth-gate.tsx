"use client";

import { LogIn, ShieldCheck, AlertTriangle } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

/**
 * Renders the sign-in screen when Entra auth is configured and no account is active.
 * Under mock auth this is a passthrough, so local development never sees a login wall.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const { ready, config, account, error, signIn } = useAuth();

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-base">
        <div className="flex flex-col items-center gap-3 text-ink-muted">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-azure" />
          <span className="font-mono text-xs">Checking session…</span>
        </div>
      </div>
    );
  }

  // Mock auth (local dev): no login required.
  if (!config?.loginRequired) return <>{children}</>;

  if (account) return <>{children}</>;

  return (
    <div className="flex h-screen flex-col items-center justify-center bg-base px-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-surface p-8 text-center shadow-panel">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-azure/15 shadow-glow">
          <ShieldCheck className="h-7 w-7 text-azure" />
        </div>
        <h1 className="font-display text-xl font-semibold text-ink">AI Security Architect</h1>
        <p className="mt-2 text-sm text-ink-muted">
          Sign in with your organisational account to continue.
        </p>

        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-severity-high/30 bg-severity-high/10 p-3 text-left text-[12px] text-severity-high">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <button
          onClick={signIn}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-azure px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-azure-bright"
        >
          <LogIn className="h-4 w-4" /> Sign in with Microsoft
        </button>

        <p className="mt-4 font-mono text-[10px] leading-relaxed text-ink-faint">
          Access requires an assigned application role. Contact your administrator if
          sign-in succeeds but access is denied.
        </p>
      </div>
    </div>
  );
}
