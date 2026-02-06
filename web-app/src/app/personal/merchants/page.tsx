"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { MerchantSummary } from "@/lib/api";

export default function MerchantsPage() {
    const [merchants, setMerchants] = useState<MerchantSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchMerchants() {
            try {
                const data = await api.personal.getTopMerchants(20);
                setMerchants(data.merchants);
                setError(null);
            } catch (err) {
                setError("Failed to load merchants");
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        fetchMerchants();
    }, []);

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return "N/A";
        return new Date(dateStr).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
        });
    };

    // Calculate max spend for relative sizing
    const maxSpend = merchants.length > 0 ? Math.max(...merchants.map((m) => m.total_spend)) : 0;

    return (
        <div className="min-h-screen bg-slate-950 text-white p-6">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-400 to-red-500 bg-clip-text text-transparent">
                        Merchant DNA
                    </h1>
                    <p className="text-slate-400 mt-1">Discover your spending relationships with brands</p>
                </div>

                {/* Loading State */}
                {loading && (
                    <div className="flex items-center justify-center h-96">
                        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
                    </div>
                )}

                {/* Error State */}
                {error && (
                    <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-8 text-center">
                        <p className="text-rose-400">{error}</p>
                    </div>
                )}

                {/* No Data State */}
                {!loading && merchants.length === 0 && (
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-12 text-center">
                        <div className="text-6xl mb-4">🏪</div>
                        <h3 className="text-xl font-semibold mb-2">No merchant data yet</h3>
                        <p className="text-slate-400">
                            Add vendors to your entries to build your merchant relationships!
                        </p>
                    </div>
                )}

                {/* Merchants Grid */}
                {!loading && merchants.length > 0 && (
                    <>
                        {/* Top 3 Featured */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                            {merchants.slice(0, 3).map((merchant, index) => (
                                <Link
                                    key={merchant.vendor}
                                    href={`/personal/merchants/${encodeURIComponent(merchant.vendor)}`}
                                    className="group"
                                >
                                    <div
                                        className={`rounded-2xl p-6 transition-all hover:-translate-y-1 hover:shadow-xl ${index === 0
                                            ? "bg-gradient-to-br from-amber-500/20 to-orange-500/10 border border-amber-500/30"
                                            : index === 1
                                                ? "bg-gradient-to-br from-slate-400/20 to-slate-500/10 border border-slate-400/30"
                                                : "bg-gradient-to-br from-orange-600/20 to-orange-700/10 border border-orange-600/30"
                                            }`}
                                    >
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="text-2xl">
                                                {index === 0 ? "🥇" : index === 1 ? "🥈" : "🥉"}
                                            </div>
                                            <div className="text-xs text-slate-400">#{index + 1} Merchant</div>
                                        </div>
                                        <h3 className="text-xl font-bold mb-2 truncate group-hover:text-orange-400 transition-colors">
                                            {merchant.vendor}
                                        </h3>
                                        <div className="text-3xl font-bold text-orange-400 mb-4">
                                            {formatCurrency(merchant.total_spend)}
                                        </div>
                                        <div className="grid grid-cols-2 gap-4 text-sm">
                                            <div>
                                                <div className="text-slate-400">Visits</div>
                                                <div className="font-semibold">{merchant.visit_count}</div>
                                            </div>
                                            <div>
                                                <div className="text-slate-400">Avg Order</div>
                                                <div className="font-semibold">{formatCurrency(merchant.avg_order)}</div>
                                            </div>
                                        </div>
                                    </div>
                                </Link>
                            ))}
                        </div>

                        {/* Rest of Merchants */}
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden">
                            <div className="p-4 border-b border-slate-800">
                                <h3 className="font-semibold">All Merchants</h3>
                            </div>
                            <div className="divide-y divide-slate-800">
                                {merchants.slice(3).map((merchant, index) => (
                                    <Link
                                        key={merchant.vendor}
                                        href={`/personal/merchants/${encodeURIComponent(merchant.vendor)}`}
                                        className="flex items-center p-4 hover:bg-slate-800/50 transition-colors group"
                                    >
                                        <div className="w-8 text-center text-slate-500 font-mono text-sm">
                                            {index + 4}
                                        </div>
                                        <div className="flex-1 ml-4">
                                            <div className="font-medium group-hover:text-orange-400 transition-colors">
                                                {merchant.vendor}
                                            </div>
                                            <div className="text-sm text-slate-400">
                                                {merchant.visit_count} visits • Last: {formatDate(merchant.last_visit)}
                                            </div>
                                        </div>
                                        {/* Spend bar */}
                                        <div className="w-32 h-2 bg-slate-800 rounded-full overflow-hidden mr-4 hidden md:block">
                                            <div
                                                className="h-full bg-gradient-to-r from-orange-500 to-red-500 rounded-full"
                                                style={{ width: `${(merchant.total_spend / maxSpend) * 100}%` }}
                                            />
                                        </div>
                                        <div className="font-semibold text-right min-w-[80px]">
                                            {formatCurrency(merchant.total_spend)}
                                        </div>
                                        <svg
                                            className="w-5 h-5 ml-4 text-slate-500 group-hover:text-orange-400 transition-colors"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor"
                                        >
                                            <path
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                                strokeWidth={2}
                                                d="M9 5l7 7-7 7"
                                            />
                                        </svg>
                                    </Link>
                                ))}
                            </div>
                        </div>

                        {/* Summary Stats */}
                        <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
                                <div className="text-2xl font-bold">{merchants.length}</div>
                                <div className="text-sm text-slate-400">Unique Merchants</div>
                            </div>
                            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
                                <div className="text-2xl font-bold">
                                    {formatCurrency(merchants.reduce((sum, m) => sum + m.total_spend, 0))}
                                </div>
                                <div className="text-sm text-slate-400">Total Tracked</div>
                            </div>
                            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
                                <div className="text-2xl font-bold">
                                    {merchants.reduce((sum, m) => sum + m.visit_count, 0)}
                                </div>
                                <div className="text-sm text-slate-400">Total Visits</div>
                            </div>
                            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
                                <div className="text-2xl font-bold">
                                    {formatCurrency(
                                        merchants.reduce((sum, m) => sum + m.total_spend, 0) /
                                        merchants.reduce((sum, m) => sum + m.visit_count, 0) || 0
                                    )}
                                </div>
                                <div className="text-sm text-slate-400">Avg Transaction</div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
