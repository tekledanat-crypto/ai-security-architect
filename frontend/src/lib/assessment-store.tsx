"use client";

// Shared assessment state. The Designer writes the architecture + validation result
// here; the Compliance and Threat Model pages read it. Persisted to sessionStorage so
// a page navigation (or refresh) doesn't lose the assessment — without this, the
// Designer's "View full report" handoff would land on an empty page.

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ValidationResult } from "./api";
import type { ArchitectureJSON } from "./use-architecture";
import type { ThreatModel } from "./types";

const KEY = "asa.assessment.v1";

interface AssessmentState {
  architecture: ArchitectureJSON | null;
  result: ValidationResult | null;
  threats: ThreatModel | null;
  updatedAt: string | null;
}

interface Ctx extends AssessmentState {
  setAssessment: (architecture: ArchitectureJSON, result: ValidationResult) => void;
  setThreats: (threats: ThreatModel) => void;
  clear: () => void;
}

const EMPTY: AssessmentState = { architecture: null, result: null, threats: null, updatedAt: null };
const AssessmentContext = createContext<Ctx | null>(null);

export function AssessmentProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AssessmentState>(EMPTY);

  // Rehydrate on mount (client-only; avoids SSR mismatch).
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(KEY);
      if (raw) setState(JSON.parse(raw));
    } catch {
      /* ignore corrupt state */
    }
  }, []);

  const persist = useCallback((next: AssessmentState) => {
    setState(next);
    try {
      sessionStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      /* storage unavailable — in-memory only */
    }
  }, []);

  const setAssessment = useCallback(
    (architecture: ArchitectureJSON, result: ValidationResult) =>
      persist({ architecture, result, threats: null, updatedAt: new Date().toISOString() }),
    [persist],
  );

  const setThreats = useCallback(
    (threats: ThreatModel) => persist({ ...state, threats, updatedAt: new Date().toISOString() }),
    [persist, state],
  );

  const clear = useCallback(() => {
    setState(EMPTY);
    try {
      sessionStorage.removeItem(KEY);
    } catch {
      /* noop */
    }
  }, []);

  return (
    <AssessmentContext.Provider value={{ ...state, setAssessment, setThreats, clear }}>
      {children}
    </AssessmentContext.Provider>
  );
}

export function useAssessment(): Ctx {
  const ctx = useContext(AssessmentContext);
  if (!ctx) throw new Error("useAssessment must be used within AssessmentProvider");
  return ctx;
}
