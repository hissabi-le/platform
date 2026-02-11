"use client";
import Protected from "@/components/Protected";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { Settings, Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "next-themes";
import { useState, useEffect } from "react";

function ThemeToggle() {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);
    useEffect(() => { setMounted(true); }, []);
    if (!mounted) return null;

    const options = [
        { value: "light", icon: <Sun className="w-4 h-4" />, label: "Light" },
        { value: "dark", icon: <Moon className="w-4 h-4" />, label: "Dark" },
        { value: "system", icon: <Monitor className="w-4 h-4" />, label: "System" },
    ];

    return (
        <div className="flex items-center gap-1 bg-muted rounded-full p-1">
            {options.map((opt) => (
                <button
                    key={opt.value}
                    onClick={() => setTheme(opt.value)}
                    className={`p-1.5 rounded-full transition-all ${theme === opt.value
                        ? "bg-background shadow text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                        }`}
                    aria-label={opt.label}
                    title={opt.label}
                >
                    {opt.icon}
                </button>
            ))}
        </div>
    );
}

export default function PersonalLayout({ children }: { children: React.ReactNode }) {
    const { user } = useAuth();
    const email = user?.email;
    const initial = email ? email.charAt(0).toUpperCase() : "U";

    return (
        <Protected>
            <div className="min-h-screen bg-background text-foreground relative selection:bg-purple-500/30 font-sans">
                {/* Background Gradients */}
                <div className="fixed top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-purple-900/10 blur-[100px] rounded-full pointer-events-none" />

                {/* Header */}
                <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-sm">
                    <div className="flex items-center justify-between mx-auto max-w-7xl w-full px-6 py-4">
                        <Link href="/personal" className="flex items-center gap-3 group">
                            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center group-hover:scale-105 transition-transform">
                                <span className="text-primary-foreground font-bold text-lg">H</span>
                            </div>
                            <span className="text-xl font-bold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
                                Hisabi Personal
                            </span>
                        </Link>

                        <div className="flex items-center gap-4">
                            <ThemeToggle />
                            <Link href="/personal/settings" className="p-2 rounded-full hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground group relative">
                                <Settings className="w-5 h-5" />
                                <span className="absolute top-full right-0 mt-2 text-xs bg-popover text-popover-foreground px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap border shadow-sm">Settings</span>
                            </Link>
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white text-sm font-bold border-2 border-background shadow-lg shadow-purple-900/20">
                                {initial}
                            </div>
                        </div>
                    </div>
                </header>

                <main className="px-6 min-h-[calc(100vh-73px)] max-w-7xl mx-auto pb-12 pt-8 w-full">
                    {children}
                </main>
            </div>
        </Protected>
    );
}
