import type { Config } from "tailwindcss";

/**
 * Design system — "Azure SOC Console".
 * Deep slate-blue surfaces (not pure black), Azure blue primary, and a functional
 * severity spectrum where color IS information (critical→informational).
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Surfaces — layered slate, darkest at the base.
        base: "#0a0e17",
        surface: "#0f1524",
        "surface-2": "#151c2e",
        "surface-3": "#1c2740",
        border: "#243049",
        "border-bright": "#2f3d5c",

        // Text
        ink: "#e8edf7",
        "ink-muted": "#9aa8c4",
        "ink-faint": "#5f6f8f",

        // Azure primary
        azure: {
          DEFAULT: "#3b9bff",
          bright: "#5eb0ff",
          dim: "#1f6fd6",
          glow: "rgba(59,155,255,0.15)",
        },

        // Severity spectrum — the functional color language.
        severity: {
          critical: "#ff4d6d",
          high: "#ff8f3f",
          medium: "#ffcf3f",
          low: "#4fd1a5",
          info: "#6b7fa8",
        },
        pass: "#4fd1a5",
        fail: "#ff4d6d",
      },
      fontFamily: {
        // Display: geometric, technical. Body: clean sans. Mono: telemetry/data.
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(59,155,255,0.3), 0 0 24px rgba(59,155,255,0.12)",
        panel: "0 1px 3px rgba(0,0,0,0.4), 0 8px 24px rgba(0,0,0,0.3)",
      },
      keyframes: {
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(59,155,255,0.4)" },
          "70%": { boxShadow: "0 0 0 6px rgba(59,155,255,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(59,155,255,0)" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-ring": "pulse-ring 1.6s ease-out infinite",
        "fade-up": "fade-up 0.25s ease-out",
      },
    },
  },
  plugins: [],
};
export default config;
