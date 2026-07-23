"use client";

// Authentication for the SPA.
//
// Two modes, chosen by the backend's /api/auth/config response rather than a build
// flag — so the same container image runs locally without a tenant and in Azure with
// Entra, which is what keeps the "clone and run" story true (ADR-0003).
//
//   mock  → no login; the backend issues a dev identity. Local development only.
//   entra → MSAL authorization-code flow with PKCE; access token attached to API calls.
//
// The access token is held in memory and refreshed silently. It is deliberately NOT
// written to localStorage: a token in localStorage is readable by any XSS payload,
// and MSAL's in-memory cache plus silent refresh gives the same UX without that.

import {
  createContext, useCallback, useContext, useEffect, useMemo, useRef, useState,
} from "react";
import type {
  AccountInfo, IPublicClientApplication, RedirectRequest,
} from "@azure/msal-browser";

export interface AuthConfig {
  provider: "mock" | "entra";
  loginRequired: boolean;
  clientId?: string;
  authority?: string;
  scopes?: string[];
}

interface AuthState {
  ready: boolean;
  config: AuthConfig | null;
  account: AccountInfo | null;
  error: string | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const msalRef = useRef<IPublicClientApplication | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch("/api/auth/config");
        const cfg: AuthConfig = res.ok
          ? await res.json()
          : { provider: "mock", loginRequired: false };
        if (cancelled) return;
        setConfig(cfg);

        if (cfg.provider !== "entra") {
          setReady(true);
          return;
        }

        // Imported dynamically so the MSAL bundle isn't shipped to dev users who
        // never authenticate.
        const { PublicClientApplication, InteractionRequiredAuthError } = await import(
          "@azure/msal-browser"
        );

        const msal = new PublicClientApplication({
          auth: {
            clientId: cfg.clientId!,
            authority: cfg.authority!,
            redirectUri: typeof window !== "undefined" ? window.location.origin : undefined,
            navigateToLoginRequestUrl: true,
          },
          cache: {
            // In-memory: no token in localStorage where XSS could read it.
            cacheLocation: "memoryStorage",
            storeAuthStateInCookie: false,
          },
        });

        await msal.initialize();
        const result = await msal.handleRedirectPromise();
        if (cancelled) return;

        if (result?.account) {
          msal.setActiveAccount(result.account);
          setAccount(result.account);
        } else {
          const existing = msal.getAllAccounts()[0] ?? null;
          if (existing) {
            msal.setActiveAccount(existing);
            setAccount(existing);
          }
        }

        msalRef.current = msal;
        void InteractionRequiredAuthError; // referenced for type-loading side effect
        setReady(true);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Authentication failed to initialise");
        setReady(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async () => {
    const msal = msalRef.current;
    if (!msal || !config?.scopes) return;
    const request: RedirectRequest = { scopes: config.scopes };
    await msal.loginRedirect(request);
  }, [config]);

  const signOut = useCallback(async () => {
    const msal = msalRef.current;
    if (!msal) return;
    await msal.logoutRedirect({ account: msal.getActiveAccount() ?? undefined });
  }, []);

  const getAccessToken = useCallback(async (): Promise<string | null> => {
    const msal = msalRef.current;
    if (!msal || !config?.scopes) return null;

    const active = msal.getActiveAccount();
    if (!active) return null;

    try {
      const result = await msal.acquireTokenSilent({ scopes: config.scopes, account: active });
      return result.accessToken;
    } catch {
      // Silent refresh failed (consent revoked, session expired). Interactive
      // sign-in is the correct recovery — surfaced rather than swallowed.
      await msal.acquireTokenRedirect({ scopes: config.scopes });
      return null;
    }
  }, [config]);

  // Register the token getter so the API client can attach bearer tokens.
  // Without this, getAuthHeader() would silently return no header and every
  // authenticated request would 401 — a failure mode worth wiring explicitly.
  useEffect(() => {
    registerTokenGetter(getAccessToken);
  }, [getAccessToken]);

  const value = useMemo<AuthState>(
    () => ({ ready, config, account, error, signIn, signOut, getAccessToken }),
    [ready, config, account, error, signIn, signOut, getAccessToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

// Registered by AuthProvider so the API client can attach tokens without importing
// React context (api.ts is not a component and may run outside the tree).
let tokenGetter: (() => Promise<string | null>) | null = null;

export function registerTokenGetter(fn: () => Promise<string | null>) {
  tokenGetter = fn;
}

export async function getAuthHeader(): Promise<Record<string, string>> {
  if (!tokenGetter) return {};
  const token = await tokenGetter();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
