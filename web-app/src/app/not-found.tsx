"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function NotFound() {
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    return (
        <main className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-white relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute top-0 right-0 w-96 h-96 bg-slate-100 rounded-full blur-3xl" />
            <div className="absolute bottom-0 left-0 w-96 h-96 bg-slate-100/50 rounded-full blur-3xl" />

            <div className={`text-center px-6 relative z-10 ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}>
                {/* 404 Number */}
                <div className="relative mb-8">
                    <div className="text-[180px] font-bold text-slate-100 leading-none select-none">404</div>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-24 h-24 rounded-2xl bg-slate-900 flex items-center justify-center shadow-2xl shadow-slate-900/30">
                            <span className="text-white text-4xl font-bold">?</span>
                        </div>
                    </div>
                </div>

                <h1 className="text-3xl font-bold text-slate-900 mb-3">Page not found</h1>
                <p className="text-lg text-slate-600 mb-8 max-w-md mx-auto">
                    The page you&apos;re looking for doesn&apos;t exist or has been moved to a new location.
                </p>

                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                    <Link
                        href="/app"
                        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-slate-900 text-white rounded-xl font-medium hover:bg-slate-800 transition-all shadow-lg shadow-slate-900/20 hover:-translate-y-0.5"
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                        </svg>
                        Go to Dashboard
                    </Link>
                    <Link
                        href="/"
                        className="inline-flex items-center justify-center gap-2 px-6 py-3 border-2 border-slate-200 text-slate-700 rounded-xl font-medium hover:bg-slate-50 hover:border-slate-300 transition-all"
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                        Back to Home
                    </Link>
                </div>

                {/* Help links */}
                <div className="mt-12 pt-8 border-t border-slate-200">
                    <p className="text-sm text-slate-500 mb-4">Maybe you were looking for:</p>
                    <div className="flex flex-wrap gap-3 justify-center">
                        {[
                            { href: "/app/analytics", label: "Analytics" },
                            { href: "/app/journal", label: "Journal" },
                            { href: "/app/documents", label: "Documents" },
                            { href: "/app/inventory", label: "Inventory" },
                        ].map((link) => (
                            <Link
                                key={link.href}
                                href={link.href}
                                className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm hover:bg-slate-200 transition-colors"
                            >
                                {link.label}
                            </Link>
                        ))}
                    </div>
                </div>
            </div>
        </main>
    );
}
