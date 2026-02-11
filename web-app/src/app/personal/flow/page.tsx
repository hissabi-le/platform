"use client";

import { useState, useEffect, useMemo } from "react";
import { api } from "@/lib/api";
import type { FlowData } from "@/lib/api";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

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

const formatCurrency = (amount: number) =>
    new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(amount);

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

    return (
        <div className="space-y-6 sm:space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
                <div className="flex items-center gap-3 sm:gap-4">
                    <Link href="/personal" className="p-2 -ml-2 rounded-full hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground flex-shrink-0">
                        <ArrowLeft className="w-5 h-5 sm:w-6 sm:h-6" />
                    </Link>
                    <div>
                        <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                            The Flow
                        </h1>
                        <p className="text-muted-foreground text-sm mt-1">See where your money goes</p>
                    </div>
                </div>
                <div className="flex gap-2 self-start sm:self-auto">
                    {(["week", "month", "quarter"] as const).map((range) => (
                        <button
                            key={range}
                            onClick={() => setTimeRange(range)}
                            className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-all ${timeRange === range
                                ? "bg-primary text-primary-foreground shadow"
                                : "bg-secondary text-muted-foreground hover:text-foreground hover:bg-secondary/80"
                                }`}
                        >
                            {range === "week" ? "7 Days" : range === "month" ? "30 Days" : "90 Days"}
                        </button>
                    ))}
                </div>
            </div>

            {/* Summary Cards */}
            {flowData && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm">
                        <div className="text-muted-foreground text-sm">Total Income</div>
                        <div className="text-2xl font-bold text-emerald-500 mt-1">
                            {formatCurrency(flowData.total_income)}
                        </div>
                    </div>
                    <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm">
                        <div className="text-muted-foreground text-sm">Total Expenses</div>
                        <div className="text-2xl font-bold text-rose-500 mt-1">
                            {formatCurrency(flowData.total_expense)}
                        </div>
                    </div>
                    <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm">
                        <div className="text-muted-foreground text-sm">Net</div>
                        <div
                            className={`text-2xl font-bold mt-1 ${flowData.total_income - flowData.total_expense >= 0
                                ? "text-emerald-500"
                                : "text-rose-500"
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
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
                </div>
            )}

            {/* Error State */}
            {error && (
                <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-8 text-center">
                    <p className="text-destructive">{error}</p>
                </div>
            )}

            {/* No Data State */}
            {!loading && flowData && flowData.nodes.length <= 1 && (
                <div className="rounded-2xl border bg-card p-12 text-center shadow-sm">
                    <div className="text-6xl mb-4">🌊</div>
                    <h3 className="text-xl font-semibold mb-2">No flow data yet</h3>
                    <p className="text-muted-foreground">
                        Start logging your income and expenses to see your money flow!
                    </p>
                </div>
            )}

            {/* Sankey Visualization */}
            {!loading && visualData && (
                <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm">
                    <h3 className="text-lg font-semibold mb-6">Money Flow Visualization</h3>

                    {/* Simple Flow Diagram */}
                    <div className="flex flex-col lg:flex-row items-start justify-between gap-6 lg:gap-8 min-h-[300px] lg:min-h-[400px]">
                        {/* Income Column */}
                        <div className="w-full lg:flex-1">
                            <div className="text-sm text-muted-foreground mb-4 text-center">Income</div>
                            <div className="space-y-3">
                                {visualData.incomeNode && (
                                    <div className="rounded-xl bg-gradient-to-r from-emerald-500/20 to-emerald-500/5 border border-emerald-500/30 p-4">
                                        <div className="text-emerald-500 font-semibold text-lg">
                                            {formatCurrency(visualData.incomeNode.value)}
                                        </div>
                                        <div className="text-sm text-muted-foreground">Total Income</div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Flow Arrows (hidden on mobile, shown on lg) */}
                        <div className="hidden lg:flex items-center justify-center w-16 h-full">
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
                        <div className="w-full lg:flex-1">
                            <div className="text-sm text-muted-foreground mb-4 text-center">Categories</div>
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
                                                ? "border-2 border-primary bg-primary/10"
                                                : "border bg-secondary/50 hover:bg-secondary"
                                                }`}
                                        >
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <div
                                                        className="w-3 h-3 rounded-full flex-shrink-0"
                                                        style={{ backgroundColor: getColor(categoryName) }}
                                                    />
                                                    <span className="capitalize text-sm">{categoryName.replace("_", " ")}</span>
                                                </div>
                                                <span className="font-semibold">{formatCurrency(cat.value)}</span>
                                            </div>
                                            {/* Percentage bar */}
                                            <div className="mt-2 h-1 bg-secondary rounded-full overflow-hidden">
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

                        {/* Flow Arrows 2 (hidden on mobile) */}
                        <div className="hidden lg:flex items-center justify-center w-16 h-full">
                            <svg className="w-full h-32" viewBox="0 0 50 100">
                                <path
                                    d="M0,20 Q25,30 50,20 M0,50 Q25,50 50,50 M0,80 Q25,70 50,80"
                                    stroke="currentColor"
                                    className="text-primary/30"
                                    strokeWidth="2"
                                    fill="none"
                                />
                            </svg>
                        </div>

                        {/* Vendors Column */}
                        <div className="w-full lg:flex-1">
                            <div className="text-sm text-muted-foreground mb-4 text-center">Top Merchants</div>
                            <div className="space-y-2">
                                {visualData.vendorNodes.slice(0, 8).map((vendor) => {
                                    const vendorName = vendor.id.replace("vendor_", "");
                                    return (
                                        <div
                                            key={vendor.id}
                                            className="rounded-xl border bg-secondary/50 p-3 hover:bg-secondary transition-all"
                                        >
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm truncate max-w-[120px]">{vendorName}</span>
                                                <span className="font-semibold text-sm">{formatCurrency(vendor.value)}</span>
                                            </div>
                                        </div>
                                    );
                                })}
                                {visualData.vendorNodes.length === 0 && (
                                    <div className="text-center text-muted-foreground py-8">
                                        <p className="text-sm">No merchant data</p>
                                        <p className="text-xs mt-1">Add vendors to your entries to see them here</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Legend */}
                    <div className="mt-8 pt-6 border-t">
                        <div className="flex flex-wrap gap-4 justify-center">
                            {visualData.categoryNodes.slice(0, 6).map((cat) => {
                                const categoryName = cat.id.replace("cat_", "");
                                return (
                                    <div key={cat.id} className="flex items-center gap-2 text-sm">
                                        <div
                                            className="w-3 h-3 rounded-full"
                                            style={{ backgroundColor: getColor(categoryName) }}
                                        />
                                        <span className="text-muted-foreground capitalize">{categoryName.replace("_", " ")}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}

            {/* Insight Card */}
            {flowData && flowData.total_expense > 0 && visualData && visualData.categoryNodes[0] && (
                <div className="rounded-2xl border border-primary/30 bg-primary/5 p-5 sm:p-6 shadow-sm">
                    <h3 className="text-lg font-semibold text-primary mb-2">💡 AI Insight</h3>
                    <p className="text-muted-foreground">
                        Your top spending category is{" "}
                        <span className="font-semibold capitalize text-foreground">
                            {visualData.categoryNodes[0]?.label.replace("_", " ")}
                        </span>{" "}
                        at {formatCurrency(visualData.categoryNodes[0]?.value ?? 0)}, which is{" "}
                        <span className="font-semibold text-foreground">
                            {Math.round(((visualData.categoryNodes[0]?.value ?? 0) / flowData.total_expense) * 100)}%
                        </span>{" "}
                        of your total expenses. Consider setting a budget for this category to optimize your spending.
                    </p>
                </div>
            )}
        </div>
    );
}
