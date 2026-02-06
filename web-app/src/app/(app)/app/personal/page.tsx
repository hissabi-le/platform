"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PersonalEntry, PersonalInsights, ParsedPersonalEntry } from "@/lib/api";
import { toast } from "sonner";
import Link from "next/link";

const CATEGORY_LABELS: Record<string, string> = {
    salary: "Salary",
    freelance: "Freelance",
    investment_income: "Investment Income",
    other_income: "Other Income",
    groceries: "Groceries",
    dining: "Dining Out",
    delivery: "Food Delivery",
    alcohol: "Alcohol",
    nightlife: "Nightlife",
    fitness: "Fitness",
    wellness: "Wellness",
    fashion: "Fashion",
    entertainment: "Entertainment",
    personal_care: "Personal Care",
    rent: "Rent",
    utilities: "Utilities",
    household: "Household",
    subscriptions: "Subscriptions",
    investments: "Investments",
    savings: "Savings",
    transportation: "Transportation",
    healthcare: "Healthcare",
    education: "Education",
    travel: "Travel",
    gifts: "Gifts",
    other: "Other",
};

const CATEGORY_ICONS: Record<string, string> = {
    salary: "💰",
    freelance: "💻",
    investment_income: "📈",
    other_income: "💵",
    groceries: "🛒",
    dining: "🍽️",
    delivery: "🛵",
    alcohol: "🍺",
    nightlife: "🎉",
    fitness: "💪",
    wellness: "🧘",
    fashion: "👗",
    entertainment: "🎬",
    personal_care: "💅",
    rent: "🏠",
    utilities: "💡",
    household: "🏡",
    subscriptions: "📱",
    investments: "📊",
    savings: "🏦",
    transportation: "🚗",
    healthcare: "🏥",
    education: "📚",
    travel: "✈️",
    gifts: "🎁",
    other: "📦",
};

export default function PersonalDashboardPage() {
    const queryClient = useQueryClient();
    const [entryMode, setEntryMode] = useState<"text" | "form">("text");
    const [freeText, setFreeText] = useState("");
    const [parsedEntries, setParsedEntries] = useState<ParsedPersonalEntry[]>([]);
    const [showParsed, setShowParsed] = useState(false);

    // Form state for structured entry
    const [formData, setFormData] = useState({
        entry_date: new Date().toISOString().split("T")[0] as string,
        entry_type: "expense" as "income" | "expense",
        category: "other",
        amount: "",
        description: "",
        vendor: "",
    });

    // Fetch insights for greeting
    const { data: insights } = useQuery({
        queryKey: ["personal", "insights"],
        queryFn: () => api.personal.getInsights(),
    });

    // Fetch recent entries
    const { data: entries, isLoading: entriesLoading } = useQuery({
        queryKey: ["personal", "entries"],
        queryFn: () => api.personal.listEntries({}),
    });

    // Parse text mutation
    const parseMutation = useMutation({
        mutationFn: (text: string) => api.personal.parseText(text),
        onSuccess: (data) => {
            setParsedEntries(data);
            setShowParsed(true);
        },
        onError: () => toast.error("Failed to parse text"),
    });

    // Save entries mutation
    const saveEntriesMutation = useMutation({
        mutationFn: (text: string) => api.personal.parseAndSave(text, formData.entry_date),
        onSuccess: () => {
            toast.success("Entries saved!");
            setFreeText("");
            setParsedEntries([]);
            setShowParsed(false);
            queryClient.invalidateQueries({ queryKey: ["personal"] });
        },
        onError: () => toast.error("Failed to save entries"),
    });

    // Create single entry mutation
    const createEntryMutation = useMutation({
        mutationFn: () =>
            api.personal.createEntry({
                entry_date: formData.entry_date,
                entry_type: formData.entry_type,
                category: formData.category,
                amount: parseFloat(formData.amount),
                description: formData.description,
                vendor: formData.vendor,
            }),
        onSuccess: () => {
            toast.success("Entry saved!");
            setFormData({
                ...formData,
                amount: "",
                description: "",
                vendor: "",
            });
            queryClient.invalidateQueries({ queryKey: ["personal"] });
        },
        onError: () => toast.error("Failed to save entry"),
    });

    // Delete entry mutation
    const deleteEntryMutation = useMutation({
        mutationFn: (id: number) => api.personal.deleteEntry(id),
        onSuccess: () => {
            toast.success("Entry deleted");
            queryClient.invalidateQueries({ queryKey: ["personal"] });
        },
    });

    const handleParse = () => {
        if (freeText.trim()) {
            parseMutation.mutate(freeText);
        }
    };

    const handleSaveAll = () => {
        if (freeText.trim()) {
            saveEntriesMutation.mutate(freeText);
        }
    };

    const handleFormSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (formData.amount && parseFloat(formData.amount) > 0) {
            createEntryMutation.mutate();
        }
    };

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
        }).format(amount);
    };

    return (
        <div className="space-y-8">
            {/* Personalized Greeting */}
            <div className="bg-gradient-to-r from-primary/10 via-primary/5 to-transparent rounded-2xl p-6">
                <h1 className="text-2xl font-bold text-foreground mb-2">
                    Hi there! 👋
                </h1>
                {insights ? (
                    <p className="text-muted-foreground">
                        You&apos;ve spent{" "}
                        <span className="font-semibold text-foreground">
                            {formatCurrency(insights.this_week_expense)}
                        </span>{" "}
                        this week
                        {insights.week_change_percent !== 0 && (
                            <span
                                className={
                                    insights.week_change_percent < 0
                                        ? "text-green-600"
                                        : "text-red-500"
                                }
                            >
                                {" "}
                                ({insights.week_change_percent > 0 ? "+" : ""}
                                {insights.week_change_percent}% vs last week)
                            </span>
                        )}
                        .{" "}
                        {insights.top_category && (
                            <>
                                Your top category is{" "}
                                <span className="font-semibold">
                                    {CATEGORY_ICONS[insights.top_category]}{" "}
                                    {CATEGORY_LABELS[insights.top_category] || insights.top_category}
                                </span>
                                .
                            </>
                        )}
                    </p>
                ) : (
                    <p className="text-muted-foreground">
                        Start logging your expenses to see personalized insights!
                    </p>
                )}
            </div>

            {/* Summary Cards */}
            {insights && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-card rounded-xl p-5 border shadow-sm">
                        <p className="text-sm text-muted-foreground mb-1">This Month Income</p>
                        <p className="text-2xl font-bold text-green-600">
                            {formatCurrency(insights.this_month_income)}
                        </p>
                    </div>
                    <div className="bg-card rounded-xl p-5 border shadow-sm">
                        <p className="text-sm text-muted-foreground mb-1">This Month Expenses</p>
                        <p className="text-2xl font-bold text-red-500">
                            {formatCurrency(insights.this_month_expense)}
                        </p>
                    </div>
                    <div className="bg-card rounded-xl p-5 border shadow-sm">
                        <p className="text-sm text-muted-foreground mb-1">Net Savings</p>
                        <p
                            className={`text-2xl font-bold ${insights.this_month_net >= 0 ? "text-green-600" : "text-red-500"
                                }`}
                        >
                            {formatCurrency(insights.this_month_net)}
                        </p>
                    </div>
                    <div className="bg-card rounded-xl p-5 border shadow-sm">
                        <p className="text-sm text-muted-foreground mb-1">Top Category</p>
                        <p className="text-2xl font-bold">
                            {insights.top_category
                                ? `${CATEGORY_ICONS[insights.top_category]} ${CATEGORY_LABELS[insights.top_category] || insights.top_category
                                }`
                                : "N/A"}
                        </p>
                    </div>
                </div>
            )}

            {/* Quick Links */}
            <div className="flex gap-3">
                <Link
                    href="/app/personal/analytics"
                    className="px-4 py-2 bg-card border rounded-lg text-sm font-medium hover:bg-secondary transition-colors"
                >
                    📊 Analytics
                </Link>
                <Link
                    href="/app/personal/budgets"
                    className="px-4 py-2 bg-card border rounded-lg text-sm font-medium hover:bg-secondary transition-colors"
                >
                    🎯 Budgets
                </Link>
                <Link
                    href="/app/personal/chat"
                    className="px-4 py-2 bg-card border rounded-lg text-sm font-medium hover:bg-secondary transition-colors"
                >
                    💬 Ask AI
                </Link>
            </div>

            {/* Entry Form */}
            <div className="bg-card rounded-xl border p-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">Log Entry</h2>
                    <div className="flex gap-2 bg-muted rounded-lg p-1">
                        <button
                            onClick={() => setEntryMode("text")}
                            className={`px-3 py-1.5 text-sm rounded-md transition-all ${entryMode === "text"
                                ? "bg-background shadow text-foreground font-medium"
                                : "text-muted-foreground hover:text-foreground"
                                }`}
                        >
                            Free Text
                        </button>
                        <button
                            onClick={() => setEntryMode("form")}
                            className={`px-3 py-1.5 text-sm rounded-md transition-all ${entryMode === "form"
                                ? "bg-background shadow text-foreground font-medium"
                                : "text-muted-foreground hover:text-foreground"
                                }`}
                        >
                            Structured
                        </button>
                    </div>
                </div>

                {entryMode === "text" ? (
                    <div className="space-y-4">
                        <textarea
                            value={freeText}
                            onChange={(e) => setFreeText(e.target.value)}
                            placeholder="Describe your expenses... e.g. 'Paid $45 for dinner at Olive Garden, $12 uber home, received $2000 salary'"
                            className="w-full h-32 px-4 py-3 border rounded-xl bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                        />
                        <div className="flex gap-3">
                            <button
                                onClick={handleParse}
                                disabled={parseMutation.isPending || !freeText.trim()}
                                className="px-4 py-2 bg-secondary text-foreground rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors disabled:opacity-50"
                            >
                                {parseMutation.isPending ? "Parsing..." : "Preview"}
                            </button>
                            <button
                                onClick={handleSaveAll}
                                disabled={saveEntriesMutation.isPending || !freeText.trim()}
                                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                            >
                                {saveEntriesMutation.isPending ? "Saving..." : "Save Entries"}
                            </button>
                        </div>

                        {/* Parsed Preview */}
                        {showParsed && parsedEntries.length > 0 && (
                            <div className="mt-4 p-4 bg-secondary/50 rounded-xl">
                                <p className="text-sm font-medium mb-3">Parsed Entries:</p>
                                <div className="space-y-2">
                                    {parsedEntries.map((entry, i) => (
                                        <div
                                            key={i}
                                            className="flex items-center justify-between bg-background p-3 rounded-lg"
                                        >
                                            <div className="flex items-center gap-3">
                                                <span className="text-xl">
                                                    {CATEGORY_ICONS[entry.category] || "📦"}
                                                </span>
                                                <div>
                                                    <p className="font-medium">{entry.description}</p>
                                                    <p className="text-xs text-muted-foreground">
                                                        {CATEGORY_LABELS[entry.category] || entry.category}
                                                    </p>
                                                </div>
                                            </div>
                                            <p
                                                className={`font-semibold ${entry.entry_type === "income"
                                                    ? "text-green-600"
                                                    : "text-red-500"
                                                    }`}
                                            >
                                                {entry.entry_type === "income" ? "+" : "-"}
                                                {formatCurrency(entry.amount)}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <form onSubmit={handleFormSubmit} className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">Date</label>
                                <input
                                    type="date"
                                    value={formData.entry_date}
                                    onChange={(e) =>
                                        setFormData({ ...formData, entry_date: e.target.value })
                                    }
                                    className="w-full px-3 py-2 border rounded-lg bg-background"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Type</label>
                                <select
                                    value={formData.entry_type}
                                    onChange={(e) =>
                                        setFormData({
                                            ...formData,
                                            entry_type: e.target.value as "income" | "expense",
                                        })
                                    }
                                    className="w-full px-3 py-2 border rounded-lg bg-background"
                                >
                                    <option value="expense">Expense</option>
                                    <option value="income">Income</option>
                                </select>
                            </div>
                        </div>

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
                                <label className="block text-sm font-medium mb-1">Amount</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    value={formData.amount}
                                    onChange={(e) =>
                                        setFormData({ ...formData, amount: e.target.value })
                                    }
                                    placeholder="0.00"
                                    className="w-full px-3 py-2 border rounded-lg bg-background"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">
                                    Description
                                </label>
                                <input
                                    type="text"
                                    value={formData.description}
                                    onChange={(e) =>
                                        setFormData({ ...formData, description: e.target.value })
                                    }
                                    placeholder="What was it for?"
                                    className="w-full px-3 py-2 border rounded-lg bg-background"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">
                                    Vendor (optional)
                                </label>
                                <input
                                    type="text"
                                    value={formData.vendor}
                                    onChange={(e) =>
                                        setFormData({ ...formData, vendor: e.target.value })
                                    }
                                    placeholder="e.g. Starbucks"
                                    className="w-full px-3 py-2 border rounded-lg bg-background"
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={createEntryMutation.isPending || !formData.amount}
                            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                        >
                            {createEntryMutation.isPending ? "Saving..." : "Add Entry"}
                        </button>
                    </form>
                )}
            </div>

            {/* Recent Entries */}
            <div className="bg-card rounded-xl border p-6">
                <h2 className="text-lg font-semibold mb-4">Recent Entries</h2>
                {entriesLoading ? (
                    <p className="text-muted-foreground">Loading...</p>
                ) : entries && entries.length > 0 ? (
                    <div className="space-y-3">
                        {entries.slice(0, 10).map((entry) => (
                            <div
                                key={entry.id}
                                className="flex items-center justify-between p-4 bg-secondary/30 rounded-xl group"
                            >
                                <div className="flex items-center gap-4">
                                    <span className="text-2xl">
                                        {CATEGORY_ICONS[entry.category] || "📦"}
                                    </span>
                                    <div>
                                        <p className="font-medium">
                                            {entry.description || entry.vendor || CATEGORY_LABELS[entry.category]}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {new Date(entry.entry_date).toLocaleDateString()} •{" "}
                                            {CATEGORY_LABELS[entry.category] || entry.category}
                                            {entry.ai_categorized && " • 🤖"}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <p
                                        className={`font-semibold ${entry.entry_type === "income"
                                            ? "text-green-600"
                                            : "text-red-500"
                                            }`}
                                    >
                                        {entry.entry_type === "income" ? "+" : "-"}
                                        {formatCurrency(entry.amount)}
                                    </p>
                                    <button
                                        onClick={() => deleteEntryMutation.mutate(entry.id)}
                                        className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-500 transition-all"
                                        title="Delete"
                                    >
                                        ✕
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="text-muted-foreground">
                        No entries yet. Start logging your expenses above!
                    </p>
                )}
            </div>
        </div>
    );
}
