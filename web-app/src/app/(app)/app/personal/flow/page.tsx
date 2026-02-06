"use client";

import { useState, useEffect, useMemo } from "react";
import { api } from "@/lib/api";
import type { FlowData } from "@/lib/api";

// Category colors for visualization
const CATEGORY_COLORS: Record<string, string> = {
    salary: "#10b981",
    freelance: "#34d399",
    investment_income: "#6ee7b7",
    other_income: "#a7f3d0",
    groceries: "#f59e0b",
    dining: "#fbbf24",
    delivery: "#fcd34d",
    alcohol: "#fde68a",
    nightlife: "#fef3c7",
    fitness: "#ec4899",
    wellness: "#f472b6",
    fashion: "#f9a8d4",
    entertainment: "#fbcfe8",
    personal_care: "#fce7f3",
    rent: "#8b5cf6",
    utilities: "#a78bfa",
    household: "#c4b5fd",
    subscriptions: "#ddd6fe",
    investments: "#06b6d4",
    savings: "#22d3ee",
    transportation: "#3b82f6",
    healthcare: "#60a5fa",
    education: "#93c5fd",
    travel: "#bfdbfe",
    gifts: "#f43f5e",
    other: "#94a3b8",
};

function getColor(category: string): string {
    return CATEGORY_COLORS[category.toLowerCase()] || "#94a3b8";
}

export default function FlowPage() {
    const [flowData, setFlowData] = useState<FlowData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [timeRange, setTimeRange] = useState<"week" | "month" | "quarter">("month");
    const [hoveredLink, setHoveredLink] = useState<string | null>(null);

    // Calculate date range based on selection
    const dateRange = useMemo(() => {
        const end = new Date();
        const start = new Date();
        if (timeRange === "week") {
            start.setDate(end.getDate() - 7);
        } else if (timeRange === "month") {
            start.setMonth(end.getMonth() - 1);
        } else {
            start.setMonth(end.getMonth() - 3);
        }
        return {
            start: start.toISOString().split("T")[0],
            end: end.toISOString().split("T")[0],
        };
    }, [timeRange]);

    useEffect(() => {
        async function fetchFlow() {
            setLoading(true);
            try {
                const data = await api.personal.getFlowData(dateRange.start, dateRange.end);
                setFlowData(data);
                setError(null);
            } catch (err) {
                setError("Failed to load flow data");
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        fetchFlow();
    }, [dateRange]);

    // Prepare visualization data
    const visualData = useMemo(() => {
        if (!flowData || flowData.nodes.length === 0) return null;

        const incomeNode = flowData.nodes.find((n) => n.id === "income");
        const categoryNodes = flowData.nodes.filter((n) => n.id.startsWith("cat_"));
        const vendorNodes = flowData.nodes.filter((n) => n.id.startsWith("vendor_"));

        // Filter links for income → category
        const incomeToCategory = flowData.links.filter((l) => l.source === "income");
        // Category → vendor links
        const categoryToVendor = flowData.links.filter((l) => l.source.startsWith("cat_"));

        return { incomeNode, categoryNodes, vendorNodes, incomeToCategory, categoryToVendor };
    }, [flowData]);

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    return (
        <div className="min-h-screen bg-slate-950 text-white p-6">
            {/* Header */}
            <div className="max-w-7xl mx-auto">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                            The Flow
                        </h1>
                        <p className="text-slate-400 mt-1">See where your money goes</p>
                    </div>
                    <div className="flex gap-2">
                        {(["week", "month", "quarter"] as const).map((range) => (
                            <button
                                key={range}
                                onClick={() => setTimeRange(range)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${timeRange === range
                                    ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-white"
                                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                                    }`}
                            >
                                {range === "week" ? "7 Days" : range === "month" ? "30 Days" : "90 Days"}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Summary Cards */}
                {flowData && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
                            <div className="text-slate-400 text-sm">Total Income</div>
                            <div className="text-2xl font-bold text-emerald-400 mt-1">
                                {formatCurrency(flowData.total_income)}
                            </div>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
                            <div className="text-slate-400 text-sm">Total Expenses</div>
                            <div className="text-2xl font-bold text-rose-400 mt-1">
                                {formatCurrency(flowData.total_expense)}
                            </div>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
                            <div className="text-slate-400 text-sm">Net</div>
                            <div
                                className={`text-2xl font-bold mt-1 ${flowData.total_income - flowData.total_expense >= 0
                                    ? "text-emerald-400"
                                    : "text-rose-400"
                                    }`}
                            >
                                {formatCurrency(flowData.total_income - flowData.total_expense)}
                            </div>
                        </div>
                    </div>
                )}

                {/* Loading State */}
                {loading && (
                    <div className="flex items-center justify-center h-96">
                        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-500"></div>
                    </div>
                )}

                {/* Error State */}
                {error && (
                    <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-8 text-center">
                        <p className="text-rose-400">{error}</p>
                    </div>
                )}

                {/* No Data State */}
                {!loading && flowData && flowData.nodes.length <= 1 && (
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-12 text-center">
                        <div className="text-6xl mb-4">🌊</div>
                        <h3 className="text-xl font-semibold mb-2">No flow data yet</h3>
                        <p className="text-slate-400">
                            Start logging your income and expenses to see your money flow!
                        </p>
                    </div>
                )}

                {/* Sankey Visualization */}
                {!loading && visualData && (
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
                        <h3 className="text-lg font-semibold mb-6">Money Flow Visualization</h3>

                        {/* Simple Flow Diagram */}
                        <div className="flex items-start justify-between gap-8 min-h-[400px]">
                            {/* Income Column */}
                            <div className="flex-1">
                                <div className="text-sm text-slate-400 mb-4 text-center">Income</div>
                                <div className="space-y-3">
                                    {visualData.incomeNode && (
                                        <div className="rounded-xl bg-gradient-to-r from-emerald-500/20 to-emerald-500/5 border border-emerald-500/30 p-4">
                                            <div className="text-emerald-400 font-semibold text-lg">
                                                {formatCurrency(visualData.incomeNode.value)}
                                            </div>
                                            <div className="text-sm text-slate-400">Total Income</div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Flow Arrows */}
                            <div className="flex items-center justify-center w-16 h-full">
                                <svg className="w-full h-32" viewBox="0 0 50 100">
                                    <path
                                        d="M0,50 Q25,30 50,20 M0,50 Q25,50 50,50 M0,50 Q25,70 50,80"
                                        stroke="url(#flowGradient)"
                                        strokeWidth="2"
                                        fill="none"
                                        opacity="0.5"
                                    />
                                    <defs>
                                        <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                            <stop offset="0%" stopColor="#10b981" />
                                            <stop offset="100%" stopColor="#3b82f6" />
                                        </linearGradient>
                                    </defs>
                                </svg>
                            </div>

                            {/* Categories Column */}
                            <div className="flex-1">
                                <div className="text-sm text-slate-400 mb-4 text-center">Categories</div>
                                <div className="space-y-2">
                                    {visualData.categoryNodes.slice(0, 8).map((cat) => {
                                        const categoryName = cat.id.replace("cat_", "");
                                        const isHovered = hoveredLink === cat.id;
                                        return (
                                            <div
                                                key={cat.id}
                                                onMouseEnter={() => setHoveredLink(cat.id)}
                                                onMouseLeave={() => setHoveredLink(null)}
                                                className={`rounded-xl p-3 transition-all cursor-pointer ${isHovered
                                                    ? "border-2 border-cyan-500 bg-cyan-500/10"
                                                    : "border border-slate-700 bg-slate-800/50"
                                                    }`}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-2">
                                                        <div
                                                            className="w-3 h-3 rounded-full"
                                                            style={{ backgroundColor: getColor(categoryName) }}
                                                        />
                                                        <span className="capitalize text-sm">{categoryName.replace("_", " ")}</span>
                                                    </div>
                                                    <span className="font-semibold">{formatCurrency(cat.value)}</span>
                                                </div>
                                                {/* Percentage bar */}
                                                <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full"
                                                        style={{
                                                            width: `${Math.min((cat.value / (flowData?.total_expense || 1)) * 100, 100)}%`,
                                                            backgroundColor: getColor(categoryName),
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Flow Arrows 2 */}
                            <div className="flex items-center justify-center w-16 h-full">
                                <svg className="w-full h-32" viewBox="0 0 50 100">
                                    <path
                                        d="M0,20 Q25,30 50,20 M0,50 Q25,50 50,50 M0,80 Q25,70 50,80"
                                        stroke="#3b82f6"
                                        strokeWidth="2"
                                        fill="none"
                                        opacity="0.3"
                                    />
                                </svg>
                            </div>

                            {/* Vendors Column */}
                            <div className="flex-1">
                                <div className="text-sm text-slate-400 mb-4 text-center">Top Merchants</div>
                                <div className="space-y-2">
                                    {visualData.vendorNodes.slice(0, 8).map((vendor) => {
                                        const vendorName = vendor.id.replace("vendor_", "");
                                        return (
                                            <div
                                                key={vendor.id}
                                                className="rounded-xl border border-slate-700 bg-slate-800/50 p-3 hover:border-slate-600 transition-all"
                                            >
                                                <div className="flex items-center justify-between">
                                                    <span className="text-sm truncate max-w-[120px]">{vendorName}</span>
                                                    <span className="font-semibold text-sm">{formatCurrency(vendor.value)}</span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                    {visualData.vendorNodes.length === 0 && (
                                        <div className="text-center text-slate-500 py-8">
                                            <p className="text-sm">No merchant data</p>
                                            <p className="text-xs mt-1">Add vendors to your entries to see them here</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Legend */}
                        <div className="mt-8 pt-6 border-t border-slate-800">
                            <div className="flex flex-wrap gap-4 justify-center">
                                {visualData.categoryNodes.slice(0, 6).map((cat) => {
                                    const categoryName = cat.id.replace("cat_", "");
                                    return (
                                        <div key={cat.id} className="flex items-center gap-2 text-sm">
                                            <div
                                                className="w-3 h-3 rounded-full"
                                                style={{ backgroundColor: getColor(categoryName) }}
                                            />
                                            <span className="text-slate-400 capitalize">{categoryName.replace("_", " ")}</span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                )}

                {/* Insight Card */}
                {flowData && flowData.total_expense > 0 && visualData && visualData.categoryNodes[0] && (
                    <div className="mt-8 rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-6">
                        <h3 className="text-lg font-semibold text-cyan-400 mb-2">💡 AI Insight</h3>
                        <p className="text-slate-300">
                            Your top spending category is{" "}
                            <span className="font-semibold capitalize">
                                {visualData.categoryNodes[0]?.label.replace("_", " ")}
                            </span>{" "}
                            at {formatCurrency(visualData.categoryNodes[0]?.value ?? 0)}, which is{" "}
                            <span className="font-semibold">
                                {Math.round(((visualData.categoryNodes[0]?.value ?? 0) / flowData.total_expense) * 100)}%
                            </span>{" "}
                            of your total expenses. Consider setting a budget for this category to optimize your spending.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
