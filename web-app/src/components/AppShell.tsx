"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "next-themes";

const baseLinks = [
  { href: "/app", label: "Dashboard", icon: "📊", info: "Overview combining analytics and daily operations." },
  { href: "/app/upload", label: "Upload", icon: "📤", info: "Send spreadsheets or statements into Hisabi." },
  { href: "/app/documents", label: "Documents", icon: "📄", info: "Browse and download generated reports." },
  { href: "/app/journal", label: "Journal", icon: "📝", info: "Log day-to-day notes when away from spreadsheets." },
  { href: "/personal", label: "Personal", icon: "💰", info: "Track personal expenses, set budgets, and get AI insights." },
  { href: "/app/receivables", label: "Receivables", icon: "💳", info: "Track money owed to you and money you owe." },
  { href: "/app/analytics", label: "Analytics", icon: "📈", info: "Visualise revenue, expenses, margins, and trends." },
  { href: "/app/settings/billing", label: "Settings", icon: "⚙️", info: "Manage plan, invoices, and payment methods." },
];

const inventoryLink = { href: "/app/inventory", label: "Inventory", icon: "📦", info: "Monitor items, movements, and weighted costs.", insertAfter: "/app/journal" };

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [openInfo, setOpenInfo] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  // Fetch feature flags
  const { data: features } = useQuery({
    queryKey: ["features"],
    queryFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/settings/features`);
      if (!res.ok) return { inventory_enabled: false, recipes_enabled: false };
      return res.json() as Promise<{ inventory_enabled: boolean; recipes_enabled: boolean }>;
    },
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  });

  // Build links array based on feature flags
  const links = useMemo(() => {
    const result = [...baseLinks];
    // EXPLICITLY DISABLED INVENTORY FOR CEO DEMO
    // if (features?.inventory_enabled) {
    //   const insertIndex = result.findIndex(l => l.href === inventoryLink.insertAfter) + 1;
    //   result.splice(insertIndex, 0, { href: inventoryLink.href, label: inventoryLink.label, icon: inventoryLink.icon, info: inventoryLink.info });
    // }

    // Filter for Personal Plan
    if (user?.plan === "personal") {
      return result.filter((l) => l.href === "/personal" || l.href.startsWith("/app/settings"));
    }

    return result;
  }, [features?.inventory_enabled, user?.plan]);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    setOpenInfo(null);
  }, [pathname]);

  const currentPage = links.find(l => pathname === l.href || (l.href !== "/app" && pathname.startsWith(l.href)));

  return (
    <div className="min-h-screen grid grid-cols-[240px_1fr]">
      {/* Sidebar */}
      {/* Sidebar - z-index boosted to appear above header for tooltips */}
      <aside className="border-r bg-card flex flex-col z-30 relative">
        {/* Logo */}
        <div className="p-6 border-b">
          <Link href="/app" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center group-hover:scale-105 transition-transform">
              <span className="text-primary-foreground font-bold text-lg">H</span>
            </div>
            <div>
              <span className="font-semibold text-foreground">Hisabi</span>
              <span className="block text-xs text-muted-foreground">Accounting</span>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {links.map((link, index) => {
            const active = pathname === link.href || (link.href !== "/app" && pathname.startsWith(link.href));
            const infoVisible = openInfo === link.href;
            return (
              <div
                key={link.href}
                className={`relative ${mounted ? 'animate-fade-in-up' : 'opacity-0'} group`}
                style={{ animationDelay: `${index * 0.05}s`, zIndex: infoVisible ? 51 : 'auto' }}
              >
                <div className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-200 ${active
                  ? "bg-primary text-primary-foreground shadow-md"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  }`}>
                  <Link
                    href={link.href}
                    className="flex items-center gap-3 flex-1"
                    onClick={() => setOpenInfo(null)}
                  >
                    <span className="text-base">{link.icon}</span>
                    <span className="font-medium">{link.label}</span>
                  </Link>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      setOpenInfo(infoVisible ? null : link.href);
                    }}
                    className={`w-5 h-5 rounded-full text-xs flex items-center justify-center transition-all ${active
                      ? "bg-primary-foreground/20 text-primary-foreground/90 hover:bg-primary-foreground/30 hover:text-primary-foreground"
                      : "bg-muted text-muted-foreground hover:bg-muted-foreground/20 hover:text-foreground"
                      }`}
                    aria-label={`More info about ${link.label}`}
                    aria-expanded={infoVisible}
                  >
                    ?
                  </button>
                </div>

                {/* Info Tooltip */}
                {infoVisible && (
                  <div
                    className="absolute left-full top-0 ml-3 w-56 rounded-xl border bg-popover p-4 shadow-xl animate-scale-in text-popover-foreground z-[100]"
                    role="tooltip"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">{link.icon}</span>
                      <p className="font-semibold">{link.label}</p>
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">{link.info}</p>
                    <button
                      type="button"
                      onClick={() => setOpenInfo(null)}
                      className="mt-3 text-xs font-medium text-primary hover:text-primary/80 transition-colors"
                    >
                      Got it
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
              <span className="text-primary-foreground text-sm font-medium">
                {user?.email?.charAt(0).toUpperCase() || "U"}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {user?.email?.split("@")[0] || "User"}
              </p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full mt-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-secondary rounded-lg transition-colors text-left"
            aria-label="Sign out of your account"
          >
            Sign out
          </button>
          <ThemeToggle />
        </div>
      </aside>

      {/* Main Content */}
      <main className="bg-background/50 flex flex-col min-h-screen">
        {/* Header */}
        <header className="sticky top-0 z-20 flex items-center justify-between px-8 py-4 border-b bg-background/80 backdrop-blur-sm">
          <div>
            <h1 className="text-lg font-semibold text-foreground">
              {currentPage?.label || "Dashboard"}
            </h1>
            <p className="text-sm text-muted-foreground">{pathname}</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium text-foreground">{user?.email}</p>
              <p className="text-xs text-muted-foreground">Owner</p>
            </div>
            <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-medium">
                {user?.email?.charAt(0).toUpperCase() || "U"}
              </span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className={`flex-1 p-8 ${mounted ? 'animate-fade-in' : 'opacity-0'}`}>
          {children}
        </div>

        {/* Footer */}
        <footer className="px-8 py-4 border-t bg-card text-center text-xs text-muted-foreground">
          © {new Date().getFullYear()} Hisabi • SMB Accounting for Lebanon
        </footer>
      </main>
    </div>
  );
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="flex items-center gap-2 mt-2 px-3">
      <span className="text-xs text-muted-foreground flex-1">Theme</span>
      <div className="flex items-center gap-1 bg-muted rounded-lg p-0.5">
        <button
          onClick={() => setTheme("light")}
          className={`px-2 py-1 text-xs rounded-md transition-all ${theme === "light"
            ? "bg-background shadow text-foreground font-medium"
            : "text-muted-foreground hover:text-foreground"
            }`}
          aria-label="Light mode"
        >
          ☀️
        </button>
        <button
          onClick={() => setTheme("dark")}
          className={`px-2 py-1 text-xs rounded-md transition-all ${theme === "dark"
            ? "bg-background shadow text-foreground font-medium"
            : "text-muted-foreground hover:text-foreground"
            }`}
          aria-label="Dark mode"
        >
          🌙
        </button>
        <button
          onClick={() => setTheme("system")}
          className={`px-2 py-1 text-xs rounded-md transition-all ${theme === "system"
            ? "bg-background shadow text-foreground font-medium"
            : "text-muted-foreground hover:text-foreground"
            }`}
          aria-label="System theme"
        >
          🖥️
        </button>
      </div>
    </div>
  );
}
