"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  CalendarDays,
  Clapperboard,
  Gauge,
  LayoutDashboard,
  Settings,
  Sparkles,
  Users,
} from "lucide-react";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/home", label: "Command Center", icon: Gauge },
  { href: "/dashboard", label: "Analytics", icon: LayoutDashboard },
  { href: "/crm", label: "CRM", icon: Users },
  { href: "/calendar", label: "Content Calendar", icon: CalendarDays },
  { href: "/content", label: "AI Content Studio", icon: Sparkles },
  { href: "/video", label: "AI Video Studio", icon: Clapperboard },
  { href: "/agents", label: "AI Agents", icon: Bot },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col gap-6 border-r border-border/60 bg-card/40 p-4 md:flex">
      <Link href="/home" className="flex items-center gap-2 px-2 py-1">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-primary-foreground">
          <Sparkles className="h-4 w-4" />
        </div>
        <span className="text-sm font-semibold tracking-tight">Social OS</span>
      </Link>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="rounded-lg border border-border/60 bg-secondary/30 p-3 text-xs text-muted-foreground">
        Built on the Social Media AI OS foundation. New feature areas plug into this
        same shell — see the roadmap in the repo docs.
      </div>
    </aside>
  );
}
