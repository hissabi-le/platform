"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { MerchantSummary } from "@/lib/api";
import { ArrowLeft } from "lucide-react";

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

    const formatCurrency = (amount: number) =>
        new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(amount);

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return "N/A";
        return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    };

    const maxSpend = merchants.length > 0 ? Math.max(...merchants.map((m) => m.total_spend)) : 0;

    return (
        <div className="space-y-6 sm:space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex items-center gap-3 sm:gap-4">
                <Link href="/personal" className="p-2 rounded-full hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground">
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                    <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-orange-400 to-red-500 bg-clip-text text-transparent">
                        Merchant DNA
                    </h1>
                    <p className="text-muted-foreground text-sm sm:text-base mt-1">Discover your spending relationships with brands</p>
                </div>
            </div>

            {/* Loading State */}
            {loading && (
                <div className="flex items-center justify-center h-48 sm:h-96">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
                </div>
            )}

            {/* Error State */}
            {error && (
                <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-6 sm:p-8 text-center">
                    <p className="text-destructive">{error}</p>
                </div>
            )}

            {/* No Data State */}
            {!loading && merchants.length === 0 && (
                <div className="rounded-2xl border bg-card p-8 sm:p-12 text-center">
                    <div className="text-5xl sm:text-6xl mb-4">🏪</div>
                    <h3 className="text-xl font-semibold mb-2">No merchant data yet</h3>
                    <p className="text-muted-foreground">
                        Add vendors to your entries to build your merchant relationships!
                    </p>
                </div>
            )}

            {/* Merchants Grid */}
            {!loading && merchants.length > 0 && (
                <>
                    {/* Top 3 Featured */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                        {merchants.slice(0, 3).map((merchant, index) => (
                            <Link
                                key={merchant.vendor}
                                href={`/personal/merchants/${encodeURIComponent(merchant.vendor)}`}
                                className="group"
                            >
                                <div
                                    className={`rounded-2xl p-5 sm:p-6 transition-all hover:-translate-y-1 hover:shadow-xl ${index === 0
                                        ? "bg-gradient-to-br from-amber-500/20 to-orange-500/10 border border-amber-500/30"
                                        : index === 1
                                            ? "bg-gradient-to-br from-secondary to-secondary/50 border"
                                            : "bg-gradient-to-br from-orange-600/20 to-orange-700/10 border border-orange-600/30"
                                        }`}
                                >
                                    <div className="flex items-center justify-between mb-3 sm:mb-4">
                                        <div className="text-2xl">
                                            {index === 0 ? "🥇" : index === 1 ? "🥈" : "🥉"}
                                        </div>
                                        <div className="text-xs text-muted-foreground">#{index + 1} Merchant</div>
                                    </div>
                                    <h3 className="text-lg sm:text-xl font-bold mb-2 truncate group-hover:text-orange-400 transition-colors">
                                        {merchant.vendor}
                                    </h3>
                                    <div className="text-2xl sm:text-3xl font-bold text-orange-400 mb-3 sm:mb-4">
                                        {formatCurrency(merchant.total_spend)}
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div>
                                            <div className="text-muted-foreground">Visits</div>
                                            <div className="font-semibold">{merchant.visit_count}</div>
                                        </div>
                                        <div>
                                            <div className="text-muted-foreground">Avg Order</div>
                                            <div className="font-semibold">{formatCurrency(merchant.avg_order)}</div>
                                        </div>
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>

                    {/* Rest of Merchants */}
                    <div className="rounded-2xl border bg-card overflow-hidden shadow-sm">
                        <div className="p-4 border-b">
                            <h3 className="font-semibold">All Merchants</h3>
                        </div>
                        <div className="divide-y">
                            {merchants.slice(3).map((merchant, index) => (
                                <Link
                                    key={merchant.vendor}
                                    href={`/personal/merchants/${encodeURIComponent(merchant.vendor)}`}
                                    className="flex items-center p-3 sm:p-4 hover:bg-secondary/50 transition-colors group"
                                >
                                    <div className="w-6 sm:w-8 text-center text-muted-foreground font-mono text-sm flex-shrink-0">
                                        {index + 4}
                                    </div>
                                    <div className="flex-1 ml-3 sm:ml-4 min-w-0">
                                        <div className="font-medium group-hover:text-orange-400 transition-colors truncate">
                                            {merchant.vendor}
                                        </div>
                                        <div className="text-xs sm:text-sm text-muted-foreground truncate">
                                            {merchant.visit_count} visits • Last: {formatDate(merchant.last_visit)}
                                        </div>
                                    </div>
                                    {/* Spend bar — hidden on mobile */}
                                    <div className="w-32 h-2 bg-secondary rounded-full overflow-hidden mr-4 hidden lg:block">
                                        <div
                                            className="h-full bg-gradient-to-r from-orange-500 to-red-500 rounded-full"
                                            style={{ width: `${(merchant.total_spend / maxSpend) * 100}%` }}
                                        />
                                    </div>
                                    <div className="font-semibold text-right min-w-[70px] sm:min-w-[80px] text-sm sm:text-base">
                                        {formatCurrency(merchant.total_spend)}
                                    </div>
                                    <svg
                                        className="w-4 h-4 sm:w-5 sm:h-5 ml-2 sm:ml-4 text-muted-foreground group-hover:text-orange-400 transition-colors flex-shrink-0"
                                        fill="none" viewBox="0 0 24 24" stroke="currentColor"
                                    >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                    </svg>
                                </Link>
                            ))}
                        </div>
                    </div>

                    {/* Summary Stats */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
                        <div className="rounded-xl border bg-card p-3 sm:p-4 text-center shadow-sm">
                            <div className="text-xl sm:text-2xl font-bold">{merchants.length}</div>
                            <div className="text-xs sm:text-sm text-muted-foreground">Unique Merchants</div>
                        </div>
                        <div className="rounded-xl border bg-card p-3 sm:p-4 text-center shadow-sm">
                            <div className="text-xl sm:text-2xl font-bold">
                                {formatCurrency(merchants.reduce((sum, m) => sum + m.total_spend, 0))}
                            </div>
                            <div className="text-xs sm:text-sm text-muted-foreground">Total Tracked</div>
                        </div>
                        <div className="rounded-xl border bg-card p-3 sm:p-4 text-center shadow-sm">
                            <div className="text-xl sm:text-2xl font-bold">
                                {merchants.reduce((sum, m) => sum + m.visit_count, 0)}
                            </div>
                            <div className="text-xs sm:text-sm text-muted-foreground">Total Visits</div>
                        </div>
                        <div className="rounded-xl border bg-card p-3 sm:p-4 text-center shadow-sm">
                            <div className="text-xl sm:text-2xl font-bold">
                                {formatCurrency(
                                    merchants.reduce((sum, m) => sum + m.total_spend, 0) /
                                    merchants.reduce((sum, m) => sum + m.visit_count, 0) || 0
                                )}
                            </div>
                            <div className="text-xs sm:text-sm text-muted-foreground">Avg Transaction</div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
