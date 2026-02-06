"use client";
import Protected from "@/components/Protected";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { Settings } from "lucide-react";

export default function PersonalLayout({ children }: { children: React.ReactNode }) {
    const { user } = useAuth();
    const email = user?.email;
    const initial = email ? email[0].toUpperCase() : "U";

    return (
        <Protected>
            <div className="dark min-h-screen bg-slate-950 text-slate-50 relative selection:bg-purple-500/30 font-sans">
                {/* Background Gradients */}
                <div className="fixed top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-purple-900/10 blur-[100px] rounded-full pointer-events-none" />

                {/* Header */}
                <header className="absolute top-0 left-0 right-0 z-50 p-6 flex items-center justify-between mx-auto max-w-7xl w-full">
                    <Link href="/personal" className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent hover:opacity-80 transition-opacity">
                        Hisabi Personal
                    </Link>

                    <div className="flex items-center gap-6">
                        <Link href="/personal/settings" className="p-2 rounded-full hover:bg-slate-800 transition-colors text-slate-400 hover:text-white group relative">
                            <Settings className="w-6 h-6" />
                            <span className="absolute top-full right-0 mt-2 text-xs bg-slate-800 text-slate-200 px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">Settings</span>
                        </Link>
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white text-sm font-bold border-2 border-slate-900 shadow-lg shadow-purple-900/20">
                            {initial}
                        </div>
                    </div>
                </header>

                <main className="pt-24 px-6 min-h-screen max-w-7xl mx-auto pb-12 w-full">
                    {children}
                </main>
            </div>
        </Protected>
    );
}
