"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";

const links = [
  { href: "/app", label: "Dashboard", info: "Overview combining analytics and daily operations." },
  { href: "/app/upload", label: "Upload", info: "Send spreadsheets or statements into Hissabi." },
  { href: "/app/documents", label: "Documents", info: "Browse and download generated reports." },
  { href: "/app/journal", label: "Journal", info: "Log day-to-day notes when away from spreadsheets." },
  { href: "/app/inventory", label: "Inventory", info: "Monitor items, movements, and weighted costs." },
  { href: "/app/analytics", label: "Analytics", info: "Visualise revenue, expenses, margins, and trends." },
  { href: "/app/settings/billing", label: "Billing", info: "Manage plan, invoices, and payment methods." },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [openInfo, setOpenInfo] = useState<string | null>(null);

  useEffect(() => {
    setOpenInfo(null);
  }, [pathname]);

  return (
    <div className="min-h-screen grid grid-cols-[220px_1fr]">
      <aside className="border-r p-4">
        <div className="font-semibold text-lg mb-4">Hissabi</div>
        <nav className="space-y-1">
          {links.map((link) => {
            const active = pathname === link.href;
            const infoVisible = openInfo === link.href;
            return (
              <div key={link.href} className="relative">
                <Link
                  href={link.href}
                  className={`flex items-center justify-between gap-2 rounded px-3 py-2 text-sm ${active ? "bg-black text-white" : "hover:bg-gray-100"}`}
                >
                  <span>{link.label}</span>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      setOpenInfo(infoVisible ? null : link.href);
                    }}
                    className={`h-4 w-4 rounded-full border text-[10px] leading-4 ${active ? "border-white text-white" : "border-gray-400 text-gray-500"}`}
                    aria-label={`About ${link.label}`}
                  >
                    i
                  </button>
                </Link>
                {infoVisible && (
                  <div className="absolute left-full top-1/2 z-10 w-48 -translate-y-1/2 rounded-md border bg-white p-3 text-xs text-gray-600 shadow-lg">
                    <p className="mb-2 font-medium text-gray-700">{link.label}</p>
                    <p>{link.info}</p>
                    <button
                      type="button"
                      onClick={() => setOpenInfo(null)}
                      className="mt-2 text-[11px] font-medium text-slate-600 underline"
                    >
                      Close
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </aside>
      <main>
        <header className="flex items-center justify-between px-6 py-3 border-b">
          <div className="text-sm text-gray-500">{pathname}</div>
          <div className="flex items-center gap-3">
            <span className="text-sm">{user?.email}</span>
            <button onClick={logout} className="text-sm underline">Logout</button>
          </div>
        </header>
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
