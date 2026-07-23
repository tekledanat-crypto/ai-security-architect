import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { AssessmentProvider } from "@/lib/assessment-store";
import { AuthProvider } from "@/lib/auth-context";
import { AuthGate } from "@/components/auth-gate";

// Fonts are loaded via <link> in globals/CSS with robust system fallbacks rather
// than next/font's build-time fetch, so the app builds in network-restricted CI
// and still upgrades to the web fonts when available at runtime.

export const metadata: Metadata = {
  title: "AI Security Architect",
  description: "Design, validate, and harden secure Azure architectures with AI and MCP.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AuthProvider>
          <AuthGate>
            <AssessmentProvider>
              <div className="flex h-screen overflow-hidden">
                <Sidebar />
                <div className="flex flex-1 flex-col overflow-hidden">
                  <Topbar />
                  <main className="flex-1 overflow-y-auto">{children}</main>
                </div>
              </div>
            </AssessmentProvider>
          </AuthGate>
        </AuthProvider>
      </body>
    </html>
  );
}
