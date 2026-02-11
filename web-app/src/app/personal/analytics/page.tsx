"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CategoryBreakdown, MonthlyTrend, TopSpendingItem } from "@/lib/api";
import Link from "next/link";

const CATEGORY_LABELS: Record<string, string> = {
    salary: "Salary", freelance: "Freelance", investment_income: "Investment Income",
    other_income: "Other Income", groceries: "Groceries", dining: "Dining Out",
    delivery: "Food Delivery", alcohol: "Alcohol", nightlife: "Nightlife",
    fitness: "Fitness", wellness: "Wellness", fashion: "Fashion",
    entertainment: "Entertainment", personal_care: "Personal Care", rent: "Rent",
    utilities: "Utilities", household: "Household", subscriptions: "Subscriptions",
    investments: "Investments", savings: "Savings", transportation: "Transportation",
    healthcare: "Healthcare", education: "Education", travel: "Travel",
    gifts: "Gifts", other: "Other",
};

const CATEGORY_COLORS: Record<string, string> = {
    groceries: "#10b981", dining: "#f59e0b", delivery: "#ef4444", alcohol: "#8b5cf6",
    nightlife: "#ec4899", fitness: "#06b6d4", wellness: "#14b8a6", fashion: "#f97316",
    entertainment: "#6366f1", personal_care: "#d946ef", rent: "#64748b",
    utilities: "#eab308", household: "#84cc16", subscriptions: "#3b82f6",
    investments: "#22c55e", savings: "#0ea5e9", transportation: "#a855f7",
    healthcare: "#f43f5e", education: "#0891b2", travel: "#2563eb",
    gifts: "#c026d3", other: "#737373",
};

const TIME_RANGES = [
    { label: "7 days", value: 7 },
    { label: "30 days", value: 30 },
    { label: "90 days", value: 90 },
];

export default function PersonalAnalyticsPage() {
    const [timeRange, setTimeRange] = useState(30);
    const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

    // Category breakdown for pie chart
    const { data: breakdownData } = useQuery({
        queryKey: ["personal", "breakdown"],
        queryFn: () => api.personal.getCategoryBreakdown(),
    });

    // Monthly trends for bar chart
    const { data: trendsData } = useQuery({
        queryKey: ["personal", "trends"],
        queryFn: () => api.personal.getTrends(12),
    });

    // Top spending with filters
    const { data: topSpendingData, isLoading: topLoading } = useQuery({
        queryKey: ["personal", "top-spending", timeRange, categoryFilter],
        queryFn: () => api.personal.getTopSpending(timeRange, categoryFilter || undefined, 5),
    });

    // Get summary
    const { data: summaryData } = useQuery({
        queryKey: ["personal", "summary"],
        queryFn: () => api.personal.getSummary(),
    });

    const formatCurrency = (amount: number) =>
        new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);

    const totalSpending = breakdownData?.breakdown.reduce((acc, item) => acc + item.total, 0) || 0;

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-bold">Analytics</h1>
                    <p className="text-muted-foreground text-sm sm:text-base">
                        {summaryData
                            ? `Showing data from ${new Date(summaryData.start_date).toLocaleDateString()} to ${new Date(summaryData.end_date).toLocaleDateString()}`
                            : "Your spending insights"}
                    </p>
                </div>
                <Link
                    href="/personal"
                    className="px-4 py-2 bg-secondary rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors self-start sm:self-auto"
                >
                    ← Back
                </Link>
            </div>

            {/* Summary Cards */}
            {summaryData && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-card rounded-xl p-5 border shadow-sm">
                        <p className="text-sm text-muted-foreground mb-1">Total Income</p>
                        <p className="text-2xl font-bold text-green-600">
                            {formatCurrency(summaryData.income)}
                        </p>
                    </div>
                    <div className="bg-card rounded-xl p-5 border shadow-sm">
                        <p className="text-sm text-muted-foreground mb-1">Total Expenses</p>
                        <p className="text-2xl font-bold text-red-500">
                            {formatCurrency(summaryData.expense)}
                        </p>
                    </div>
                    <div className="bg-card rounded-xl p-5 border shadow-sm">
                        <p className="text-sm text-muted-foreground mb-1">Net Savings</p>
                        <p className={`text-2xl font-bold ${summaryData.net >= 0 ? "text-green-600" : "text-red-500"}`}>
                            {formatCurrency(summaryData.net)}
                        </p>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Pie Chart - Category Breakdown */}
                <div className="bg-card rounded-xl border p-6">
                    <h2 className="text-lg font-semibold mb-4">Spending by Category</h2>
                    {breakdownData && breakdownData.breakdown.length > 0 ? (
                        <div className="space-y-4">
                            {/* Simple visual breakdown */}
                            <div className="flex flex-wrap gap-2 mb-4">
                                {breakdownData.breakdown.slice(0, 8).map((item) => (
                                    <div
                                        key={item.category}
                                        className="flex items-center gap-1 text-xs"
                                    >
                                        <div
                                            className="w-3 h-3 rounded-full"
                                            style={{ backgroundColor: CATEGORY_COLORS[item.category] || "#737373" }}
                                        />
                                        <span>{CATEGORY_LABELS[item.category] || item.category}</span>
                                    </div>
                                ))}
                            </div>

                            {/* Bar breakdown */}
                            <div className="space-y-3">
                                {breakdownData.breakdown.map((item) => (
                                    <div key={item.category}>
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="font-medium">
                                                {CATEGORY_LABELS[item.category] || item.category}
                                            </span>
                                            <span className="text-muted-foreground">
                                                {formatCurrency(item.total)} ({Math.round((item.total / totalSpending) * 100)}%)
                                            </span>
                                        </div>
                                        <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                            <div
                                                className="h-full rounded-full transition-all"
                                                style={{
                                                    width: `${(item.total / totalSpending) * 100}%`,
                                                    backgroundColor: CATEGORY_COLORS[item.category] || "#737373",
                                                }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <p className="text-muted-foreground">No spending data yet</p>
                    )}
                </div>

                {/* Top Spending Widget */}
                <div className="bg-card rounded-xl border p-6">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                        <h2 className="text-lg font-semibold">Top Spending</h2>
                        <div className="flex gap-2 bg-muted rounded-lg p-1 self-start sm:self-auto">
                            {TIME_RANGES.map((range) => (
                                <button
                                    key={range.value}
                                    onClick={() => setTimeRange(range.value)}
                                    className={`px-3 py-1 text-xs rounded-md transition-all ${timeRange === range.value
                                        ? "bg-background shadow text-foreground font-medium"
                                        : "text-muted-foreground hover:text-foreground"
                                        }`}
                                >
                                    {range.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Category Filter */}
                    <div className="mb-4">
                        <select
                            value={categoryFilter || ""}
                            onChange={(e) => setCategoryFilter(e.target.value || null)}
                            className="px-3 py-2 text-sm border rounded-lg bg-background w-full"
                        >
                            <option value="">All Categories</option>
                            {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                                <option key={value} value={value}>
                                    {label}
                                </option>
                            ))}
                        </select>
                    </div>

                    {topLoading ? (
                        <p className="text-muted-foreground">Loading...</p>
                    ) : topSpendingData && topSpendingData.items.length > 0 ? (
                        <div className="space-y-3">
                            {topSpendingData.items.map((item, i) => (
                                <div
                                    key={i}
                                    className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg"
                                >
                                    <div className="flex items-center gap-3">
                                        <span className="text-lg font-bold text-muted-foreground">
                                            #{i + 1}
                                        </span>
                                        <div>
                                            <p className="font-medium">{item.description}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {CATEGORY_LABELS[item.category] || item.category}
                                                {item.vendor && ` • ${item.vendor}`}
                                                {item.count > 1 && ` • ${item.count}x`}
                                            </p>
                                        </div>
                                    </div>
                                    <p className="font-semibold text-red-500">
                                        {formatCurrency(item.total)}
                                    </p>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-muted-foreground">
                            No spending data for this period
                        </p>
                    )}
                </div>
            </div>

            {/* Monthly Trends */}
            <div className="bg-card rounded-xl border p-6">
                <h2 className="text-lg font-semibold mb-4">Monthly Trends</h2>
                {trendsData && trendsData.trends.length > 0 ? (
                    <div className="space-y-4">
                        {/* Bar chart representation */}
                        <div className="flex items-end gap-2 h-48">
                            {trendsData.trends.slice(-6).map((month) => {
                                const maxValue = Math.max(
                                    ...trendsData.trends.map((m) => Math.max(m.income, m.expense))
                                );
                                const incomeHeight = maxValue > 0 ? (month.income / maxValue) * 100 : 0;
                                const expenseHeight = maxValue > 0 ? (month.expense / maxValue) * 100 : 0;

                                return (
                                    <div key={month.month} className="flex-1 flex flex-col items-center gap-1">
                                        <div className="flex gap-1 h-40 items-end">
                                            <div
                                                className="w-4 bg-green-500 rounded-t"
                                                style={{ height: `${incomeHeight}%` }}
                                                title={`Income: ${formatCurrency(month.income)}`}
                                            />
                                            <div
                                                className="w-4 bg-red-400 rounded-t"
                                                style={{ height: `${expenseHeight}%` }}
                                                title={`Expense: ${formatCurrency(month.expense)}`}
                                            />
                                        </div>
                                        <span className="text-xs text-muted-foreground">
                                            {month.month.slice(5)}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>

                        {/* Legend */}
                        <div className="flex justify-center gap-6">
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 bg-green-500 rounded" />
                                <span className="text-sm text-muted-foreground">Income</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 bg-red-400 rounded" />
                                <span className="text-sm text-muted-foreground">Expenses</span>
                            </div>
                        </div>

                        {/* Monthly breakdown */}
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-4">
                            {trendsData.trends.slice(-6).map((month) => (
                                <div key={month.month} className="p-3 bg-secondary/30 rounded-lg text-center">
                                    <p className="text-xs text-muted-foreground mb-1">
                                        {new Date(month.month + "-01").toLocaleDateString("en-US", {
                                            month: "short",
                                            year: "2-digit",
                                        })}
                                    </p>
                                    <p className="text-sm font-medium text-green-600">
                                        +{formatCurrency(month.income)}
                                    </p>
                                    <p className="text-sm font-medium text-red-500">
                                        -{formatCurrency(month.expense)}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>
                ) : (
                    <p className="text-muted-foreground">
                        No trend data yet. Keep logging entries to see your monthly patterns!
                    </p>
                )}
            </div>
        </div>
    );
}
