"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { MerchantProfile } from "@/lib/api";

export default function MerchantDNAPage() {
    const params = useParams();
    const vendor = decodeURIComponent(params.vendor as string);

    const [profile, setProfile] = useState<MerchantProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchProfile() {
            try {
                const data = await api.personal.getMerchantProfile(vendor);
                setProfile(data);
                setError(null);
            } catch (err) {
                setError("Failed to load merchant profile");
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        if (vendor) fetchProfile();
    }, [vendor]);

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            minimumFractionDigits: 2,
        }).format(amount);
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return "N/A";
        return new Date(dateStr).toLocaleDateString("en-US", {
            month: "long",
            day: "numeric",
            year: "numeric",
        });
    };

    // Get max frequency for day heatmap
    const maxDayCount = profile
        ? Math.max(...profile.frequency_by_day.map((d) => d.count))
        : 0;

    return (
        <div className="min-h-screen bg-slate-950 text-white p-6">
            <div className="max-w-4xl mx-auto">
                {/* Back Button */}
                <Link
                    href="/app/personal/merchants"
                    className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-6"
                >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                    Back to Merchants
                </Link>

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

                {/* Merchant DNA Card */}
                {!loading && profile && (
                    <>
                        {/* Header Card */}
                        <div className="rounded-2xl bg-gradient-to-br from-orange-500/20 to-red-500/10 border border-orange-500/30 p-8 mb-6">
                            <div className="flex items-start justify-between">
                                <div>
                                    <div className="text-sm text-orange-400 mb-2">Merchant DNA</div>
                                    <h1 className="text-3xl font-bold mb-2">{profile.vendor}</h1>
                                    <p className="text-slate-400">
                                        Your relationship since {formatDate(profile.first_visit)}
                                    </p>
                                </div>
                                <div className="text-right">
                                    <div className="text-sm text-slate-400">Lifetime Spend</div>
                                    <div className="text-4xl font-bold text-orange-400">
                                        {formatCurrency(profile.lifetime_spend)}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Stats Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
                                <div className="text-2xl font-bold">{profile.visit_count}</div>
                                <div className="text-sm text-slate-400">Total Visits</div>
                            </div>
                            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
                                <div className="text-2xl font-bold">{formatCurrency(profile.average_order)}</div>
                                <div className="text-sm text-slate-400">Average Order</div>
                            </div>
                            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
                                <div className="text-2xl font-bold">{profile.visits_per_week}x</div>
                                <div className="text-sm text-slate-400">Per Week</div>
                            </div>
                            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
                                <div className="text-2xl font-bold">{formatDate(profile.last_visit)?.split(",")[0]}</div>
                                <div className="text-sm text-slate-400">Last Visit</div>
                            </div>
                        </div>

                        {/* Frequency Heatmap */}
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 mb-6">
                            <h3 className="text-lg font-semibold mb-4">📅 When You Visit</h3>
                            <p className="text-slate-400 text-sm mb-4">Which days of the week you visit most</p>
                            <div className="grid grid-cols-7 gap-2">
                                {profile.frequency_by_day.map((day) => {
                                    const intensity = maxDayCount > 0 ? day.count / maxDayCount : 0;
                                    return (
                                        <div key={day.day} className="text-center">
                                            <div
                                                className="w-full aspect-square rounded-lg flex items-center justify-center text-sm font-medium transition-all"
                                                style={{
                                                    backgroundColor: `rgba(249, 115, 22, ${intensity * 0.8 + 0.1})`,
                                                }}
                                            >
                                                {day.count}
                                            </div>
                                            <div className="text-xs text-slate-500 mt-1">{day.day}</div>
                                        </div>
                                    );
                                })}
                            </div>
                            {/* Find the peak day */}
                            {maxDayCount > 0 && (
                                <p className="mt-4 text-sm text-slate-400">
                                    You visit most on{" "}
                                    <span className="text-orange-400 font-medium">
                                        {profile.frequency_by_day.reduce((max, d) => (d.count > max.count ? d : max)).day}s
                                    </span>
                                </p>
                            )}
                        </div>

                        {/* Price Trend (Inflation Tracker) */}
                        {profile.price_trend.length > 0 && (
                            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 mb-6">
                                <h3 className="text-lg font-semibold mb-4">📈 Spending Trend</h3>
                                <p className="text-slate-400 text-sm mb-4">
                                    Your average order price over time
                                </p>

                                {/* Simple Bar Chart */}
                                <div className="flex items-end gap-2 h-32">
                                    {profile.price_trend.map((month) => {
                                        const maxAvg = Math.max(...profile.price_trend.map((m) => m.avg));
                                        const height = maxAvg > 0 ? (month.avg / maxAvg) * 100 : 0;
                                        return (
                                            <div key={month.month} className="flex-1 flex flex-col items-center">
                                                <div
                                                    className="w-full bg-gradient-to-t from-orange-500 to-amber-400 rounded-t"
                                                    style={{ height: `${height}%` }}
                                                />
                                                <div className="text-xs text-slate-500 mt-2">
                                                    {month.month.split("-")[1]}
                                                </div>
                                                <div className="text-xs text-slate-400">
                                                    ${month.avg}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>

                                {/* Trend Analysis */}
                                {profile.price_trend.length >= 2 && profile.price_trend[0] && (
                                    <div className="mt-4 pt-4 border-t border-slate-800">
                                        {(() => {
                                            const first = profile.price_trend[0]?.avg ?? 0;
                                            const last = profile.price_trend[profile.price_trend.length - 1]?.avg ?? 0;
                                            const change = first > 0 ? ((last - first) / first) * 100 : 0;
                                            const isUp = change > 0;
                                            return (
                                                <p className="text-sm">
                                                    Your average order has{" "}
                                                    <span className={isUp ? "text-rose-400" : "text-emerald-400"}>
                                                        {isUp ? "increased" : "decreased"} {Math.abs(change).toFixed(1)}%
                                                    </span>{" "}
                                                    over the past {profile.price_trend.length} months
                                                </p>
                                            );
                                        })()}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* AI Insight */}
                        <div className="rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-6">
                            <h3 className="text-lg font-semibold text-cyan-400 mb-2">💡 DNA Insight</h3>
                            <p className="text-slate-300">
                                You&apos;re a{" "}
                                <span className="font-semibold">
                                    {profile.visits_per_week >= 2
                                        ? "regular"
                                        : profile.visits_per_week >= 0.5
                                            ? "occasional"
                                            : "rare"}
                                </span>{" "}
                                visitor at {profile.vendor}. Over {profile.visit_count} visits, you&apos;ve spent an average of{" "}
                                {formatCurrency(profile.average_order)} per visit. Your most frequent day to visit is{" "}
                                <span className="font-semibold">
                                    {profile.frequency_by_day.reduce((max, d) => (d.count > max.count ? d : max)).day}
                                </span>
                                .
                            </p>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
