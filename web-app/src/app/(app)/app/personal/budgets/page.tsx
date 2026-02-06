"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { BudgetProgress } from "@/lib/api";
import { toast } from "sonner";
import Link from "next/link";

const CATEGORY_LABELS: Record<string, string> = {
    groceries: "Groceries", dining: "Dining Out", delivery: "Food Delivery",
    alcohol: "Alcohol", nightlife: "Nightlife", fitness: "Fitness",
    wellness: "Wellness", fashion: "Fashion", entertainment: "Entertainment",
    personal_care: "Personal Care", rent: "Rent", utilities: "Utilities",
    household: "Household", subscriptions: "Subscriptions", investments: "Investments",
    savings: "Savings", transportation: "Transportation", healthcare: "Healthcare",
    education: "Education", travel: "Travel", gifts: "Gifts", other: "Other",
};

const CATEGORY_ICONS: Record<string, string> = {
    groceries: "🛒", dining: "🍽️", delivery: "🛵", alcohol: "🍺", nightlife: "🎉",
    fitness: "💪", wellness: "🧘", fashion: "👗", entertainment: "🎬",
    personal_care: "💅", rent: "🏠", utilities: "💡", household: "🏡",
    subscriptions: "📱", investments: "📊", savings: "🏦", transportation: "🚗",
    healthcare: "🏥", education: "📚", travel: "✈️", gifts: "🎁", other: "📦",
};

export default function PersonalBudgetsPage() {
    const queryClient = useQueryClient();
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({
        category: "groceries",
        monthly_limit: "",
    });

    // Fetch budget progress
    const { data: budgetProgress, isLoading } = useQuery({
        queryKey: ["personal", "budget-progress"],
        queryFn: () => api.personal.getBudgetProgress(),
    });

    // Create budget mutation
    const createBudgetMutation = useMutation({
        mutationFn: () =>
            api.personal.createBudget(
                formData.category,
                parseFloat(formData.monthly_limit)
            ),
        onSuccess: () => {
            toast.success("Budget created!");
            setFormData({ category: "groceries", monthly_limit: "" });
            setShowForm(false);
            queryClient.invalidateQueries({ queryKey: ["personal"] });
        },
        onError: () => toast.error("Failed to create budget"),
    });

    // Delete budget mutation
    const deleteBudgetMutation = useMutation({
        mutationFn: (category: string) => api.personal.deleteBudget(category),
        onSuccess: () => {
            toast.success("Budget deleted");
            queryClient.invalidateQueries({ queryKey: ["personal"] });
        },
    });

    const formatCurrency = (amount: number) =>
        new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);

    const getProgressColor = (percent: number) => {
        if (percent >= 100) return "bg-red-500";
        if (percent >= 80) return "bg-orange-500";
        if (percent >= 60) return "bg-yellow-500";
        return "bg-green-500";
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (formData.monthly_limit && parseFloat(formData.monthly_limit) > 0) {
            createBudgetMutation.mutate();
        }
    };

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Budget Goals</h1>
                    <p className="text-muted-foreground">
                        Set monthly spending limits and track your progress
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => setShowForm(!showForm)}
                        className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                    >
                        {showForm ? "Cancel" : "+ Add Budget"}
                    </button>
                    <Link
                        href="/app/personal"
                        className="px-4 py-2 bg-secondary rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors"
                    >
                        ← Back
                    </Link>
                </div>
            </div>

            {/* New Budget Form */}
            {showForm && (
                <div className="bg-card rounded-xl border p-6">
                    <h2 className="text-lg font-semibold mb-4">Create New Budget</h2>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">Category</label>
                                <select
                                    value={formData.category}
                                    onChange={(e) =>
                                        setFormData({ ...formData, category: e.target.value })
                                    }
                                    className="w-full px-3 py-2 border rounded-lg bg-background"
                                >
                                    {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                                        <option key={value} value={value}>
                                            {CATEGORY_ICONS[value]} {label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">
                                    Monthly Limit ($)
                                </label>
                                <input
                                    type="number"
                                    step="1"
                                    min="1"
                                    value={formData.monthly_limit}
                                    onChange={(e) =>
                                        setFormData({ ...formData, monthly_limit: e.target.value })
                                    }
                                    placeholder="e.g. 500"
                                    className="w-full px-3 py-2 border rounded-lg bg-background"
                                />
                            </div>
                        </div>
                        <button
                            type="submit"
                            disabled={
                                createBudgetMutation.isPending ||
                                !formData.monthly_limit ||
                                parseFloat(formData.monthly_limit) <= 0
                            }
                            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                        >
                            {createBudgetMutation.isPending ? "Creating..." : "Create Budget"}
                        </button>
                    </form>
                </div>
            )}

            {/* Budget Cards */}
            {isLoading ? (
                <div className="bg-card rounded-xl border p-6">
                    <p className="text-muted-foreground">Loading budgets...</p>
                </div>
            ) : budgetProgress && budgetProgress.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {budgetProgress.map((budget) => (
                        <div
                            key={budget.category}
                            className="bg-card rounded-xl border p-5 group"
                        >
                            <div className="flex items-start justify-between mb-3">
                                <div className="flex items-center gap-3">
                                    <span className="text-3xl">
                                        {CATEGORY_ICONS[budget.category] || "📦"}
                                    </span>
                                    <div>
                                        <h3 className="font-semibold">
                                            {CATEGORY_LABELS[budget.category] || budget.category}
                                        </h3>
                                        <p className="text-sm text-muted-foreground">
                                            {formatCurrency(budget.spent)} / {formatCurrency(budget.monthly_limit)}
                                        </p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => deleteBudgetMutation.mutate(budget.category)}
                                    className="opacity-0 group-hover:opacity-100 p-1 text-muted-foreground hover:text-red-500 transition-all"
                                    title="Delete budget"
                                >
                                    ✕
                                </button>
                            </div>

                            {/* Progress bar */}
                            <div className="h-3 bg-secondary rounded-full overflow-hidden mb-2">
                                <div
                                    className={`h-full rounded-full transition-all ${getProgressColor(budget.percent_used)}`}
                                    style={{ width: `${Math.min(budget.percent_used, 100)}%` }}
                                />
                            </div>

                            <div className="flex justify-between text-sm">
                                <span
                                    className={
                                        budget.percent_used >= 100
                                            ? "text-red-500 font-medium"
                                            : budget.percent_used >= 80
                                                ? "text-orange-500 font-medium"
                                                : "text-muted-foreground"
                                    }
                                >
                                    {budget.percent_used >= 100 ? (
                                        <>⚠️ Over budget by {formatCurrency(Math.abs(budget.remaining))}</>
                                    ) : budget.percent_used >= 80 ? (
                                        <>⚠️ {Math.round(budget.percent_used)}% used</>
                                    ) : (
                                        <>{Math.round(budget.percent_used)}% used</>
                                    )}
                                </span>
                                <span className="text-muted-foreground">
                                    {budget.remaining > 0
                                        ? `${formatCurrency(budget.remaining)} left`
                                        : ""}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="bg-card rounded-xl border p-8 text-center">
                    <p className="text-4xl mb-3">🎯</p>
                    <h3 className="text-lg font-semibold mb-2">No Budgets Yet</h3>
                    <p className="text-muted-foreground mb-4">
                        Create spending limits to track your budget and stay on target.
                    </p>
                    <button
                        onClick={() => setShowForm(true)}
                        className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                    >
                        Create Your First Budget
                    </button>
                </div>
            )}

            {/* Tips */}
            <div className="bg-secondary/30 rounded-xl p-6">
                <h3 className="font-semibold mb-2">💡 Budget Tips</h3>
                <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Start with categories where you tend to overspend</li>
                    <li>• Use the 50/30/20 rule: 50% needs, 30% wants, 20% savings</li>
                    <li>• Review and adjust your budgets monthly based on actual spending</li>
                    <li>• The progress bar turns orange at 80% and red when over budget</li>
                </ul>
            </div>
        </div>
    );
}
