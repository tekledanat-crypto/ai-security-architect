"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, MessagesSquare, Network, ShieldCheck,
  Bug, FileText, Settings, ShieldHalf,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, ready: true },
  { href: "/assistant", label: "AI Assistant", icon: MessagesSquare, ready: true },
  { href: "/designer", label: "Architecture Designer", icon: Network, ready: true },
  { href: "/compliance", label: "Compliance", icon: ShieldCheck, ready: true },
  { href: "/threats", label: "Threat Model", icon: Bug, ready: true },
  { href: "/reports", label: "Reports", icon: FileText, ready: true },
  { href: "/settings", label: "Settings", icon: Settings, ready: false, chunk: 11 },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-surface">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-azure/15 shadow-glow">
          <ShieldHalf className="h-5 w-5 text-azure" />
        </div>
        <div className="leading-tight">
          <div className="font-display text-[15px] font-semibold text-ink">Security Architect</div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">AI · MCP · Azure</div>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-2">
        {NAV.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                active ? "bg-surface-3 text-ink" : "text-ink-muted hover:bg-surface-2 hover:text-ink",
              )}
            >
              {active && <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-azure" />}
              <Icon className={cn("h-[18px] w-[18px]", active ? "text-azure" : "text-ink-faint group-hover:text-ink-muted")} />
              <span className="flex-1">{item.label}</span>
              {!item.ready && (
                <span className="font-mono text-[9px] uppercase tracking-wider text-ink-faint">C{item.chunk}</span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border px-5 py-4">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-pass" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-pass" />
          </span>
          <span className="font-mono text-[11px] text-ink-muted">MCP server online</span>
        </div>
        <div className="mt-1 font-mono text-[10px] text-ink-faint">11 frameworks · 137 controls</div>
      </div>
    </aside>
  );
}
