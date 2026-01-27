"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/hooks/useAuth";

const baseLinks = [
  { href: "/app", label: "Dashboard", icon: "📊", info: "Overview combining analytics and daily operations." },
  { href: "/app/upload", label: "Upload", icon: "📤", info: "Send spreadsheets or statements into Hissabi." },
  { href: "/app/documents", label: "Documents", icon: "📄", info: "Browse and download generated reports." },
  { href: "/app/journal", label: "Journal", icon: "📝", info: "Log day-to-day notes when away from spreadsheets." },
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
    if (features?.inventory_enabled) {
      const insertIndex = result.findIndex(l => l.href === inventoryLink.insertAfter) + 1;
      result.splice(insertIndex, 0, { href: inventoryLink.href, label: inventoryLink.label, icon: inventoryLink.icon, info: inventoryLink.info });
    }
    return result;
  }, [features?.inventory_enabled]);

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
      <aside className="border-r bg-white flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b">
          <Link href="/app" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center group-hover:scale-105 transition-transform">
              <span className="text-white font-bold text-lg">H</span>
            </div>
            <div>
              <span className="font-semibold text-slate-900">Hissabi</span>
              <span className="block text-xs text-slate-500">Accounting</span>
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
                className={`relative ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <div className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-200 ${active
                  ? "bg-slate-900 text-white shadow-md"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
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
                      ? "bg-white/20 text-white/70 hover:bg-white/30 hover:text-white"
                      : "bg-slate-200 text-slate-400 hover:bg-slate-300 hover:text-slate-600"
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
                    className="absolute left-full top-0 z-50 w-56 ml-3 rounded-xl border bg-white p-4 shadow-xl animate-scale-in"
                    role="tooltip"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">{link.icon}</span>
                      <p className="font-semibold text-slate-900">{link.label}</p>
                    </div>
                    <p className="text-sm text-slate-600 leading-relaxed">{link.info}</p>
                    <button
                      type="button"
                      onClick={() => setOpenInfo(null)}
                      className="mt-3 text-xs font-medium text-slate-500 hover:text-slate-700 transition-colors"
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
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center">
              <span className="text-white text-sm font-medium">
                {user?.email?.charAt(0).toUpperCase() || "U"}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900 truncate">
                {user?.email?.split("@")[0] || "User"}
              </p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full mt-2 px-3 py-2 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors text-left"
            aria-label="Sign out of your account"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="bg-slate-50 flex flex-col min-h-screen">
        {/* Header */}
        <header className="sticky top-0 z-20 flex items-center justify-between px-8 py-4 border-b bg-white/80 backdrop-blur-sm">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">
              {currentPage?.label || "Dashboard"}
            </h1>
            <p className="text-sm text-slate-500">{pathname}</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium text-slate-700">{user?.email}</p>
              <p className="text-xs text-slate-500">Owner</p>
            </div>
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center">
              <span className="text-white font-medium">
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
        <footer className="px-8 py-4 border-t bg-white text-center text-xs text-slate-500">
          © {new Date().getFullYear()} Hissabi • SMB Accounting for Lebanon
        </footer>
      </main>
    </div>
  );
}
