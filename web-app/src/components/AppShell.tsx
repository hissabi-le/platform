"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

const links = [
  { href: "/app", label: "Dashboard" },
  { href: "/app/upload", label: "Upload" },
  { href: "/app/documents", label: "Documents" },
  { href: "/app/inventory", label: "Inventory" },
  { href: "/app/analytics", label: "Analytics" },
  { href: "/app/settings/billing", label: "Billing" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen grid grid-cols-[220px_1fr]">
      <aside className="border-r p-4">
        <div className="font-semibold text-lg mb-4">Hissabi</div>
        <nav className="space-y-1">
          {links.map(l => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`block rounded px-3 py-2 text-sm ${active ? "bg-black text-white" : "hover:bg-gray-100"}`}
              >
                {l.label}
              </Link>
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
