"use client";
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { ArrowLeft, Trash2, DollarSign, Filter, X } from "lucide-react";
import Link from 'next/link';
import { useSearchParams } from "next/navigation";

const CATEGORY_ICONS: Record<string, string> = {
    salary: "💰", freelance: "💻", investment_income: "📊", other_income: "💵",
    groceries: "🛒", dining: "🍽️", delivery: "🚚", alcohol: "🍺",
    nightlife: "🌙", fitness: "💪", wellness: "🧘", fashion: "👗",
    entertainment: "🎬", personal_care: "💅", rent: "🏠",
    utilities: "💡", household: "🏡", subscriptions: "📱",
    investments: "📈", savings: "🏦", transportation: "🚗",
    healthcare: "🏥", education: "📚", travel: "✈️",
    gifts: "🎁", other: "📦",
};

const CATEGORY_LABELS: Record<string, string> = {
    salary: "Salary", freelance: "Freelance", investment_income: "Investment",
    other_income: "Other Income", groceries: "Groceries", dining: "Dining Out",
    delivery: "Delivery", alcohol: "Alcohol", nightlife: "Nightlife",
    fitness: "Fitness", wellness: "Wellness", fashion: "Fashion",
    entertainment: "Entertainment", personal_care: "Personal Care", rent: "Rent",
    utilities: "Utilities", household: "Household", subscriptions: "Subscriptions",
    investments: "Investments", savings: "Savings", transportation: "Transport",
    healthcare: "Healthcare", education: "Education", travel: "Travel",
    gifts: "Gifts", other: "Other",
};

export default function TransactionsPage() {
    const queryClient = useQueryClient();
    const searchParams = useSearchParams();
    const categoryFilter = searchParams.get("category") || "";

    const [isAdding, setIsAdding] = useState(false);
    const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
    const [formData, setFormData] = useState({
        entry_date: new Date().toISOString().split("T")[0],
        entry_type: "expense" as "income" | "expense",
        category: "",
        amount: "",
        vendor: "",
    });

    const { data: entries, isLoading } = useQuery({
        queryKey: ["personal", "entries", categoryFilter],
        queryFn: () => api.personal.listEntries(categoryFilter ? { category: categoryFilter } : {}),
    });

    const createMutation = useMutation({
        mutationFn: () => {
            const amt = parseFloat(formData.amount);
            if (isNaN(amt) || amt <= 0) throw new Error("Amount is required");
            return api.personal.createEntry({
                entry_date: formData.entry_date || new Date().toISOString().split("T")[0]!,
                entry_type: formData.entry_type,
                category: formData.category || "other",
                amount: amt,
                vendor: formData.vendor || undefined,
            });
        },
        onSuccess: () => {
            toast.success("Entry added");
            setFormData({ ...formData, amount: "", category: "", vendor: "" });
            setIsAdding(false);
            queryClient.invalidateQueries({ queryKey: ["personal", "entries"] });
            queryClient.invalidateQueries({ queryKey: ["personal"] });
        },
        onError: () => toast.error("Failed to add entry"),
    });

    const deleteMutation = useMutation({
        mutationFn: (id: number) => api.personal.deleteEntry(id),
        onSuccess: () => {
            toast.success("Entry deleted");
            setDeleteConfirmId(null);
            queryClient.invalidateQueries({ queryKey: ["personal", "entries"] });
            queryClient.invalidateQueries({ queryKey: ["personal"] });
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        createMutation.mutate();
    };

    const isExpense = formData.entry_type === "expense";

    return (
        <div className="space-y-6 sm:space-y-8 max-w-4xl mx-auto animate-in fade-in duration-500">
            <div className="flex items-center gap-3 sm:gap-4">
                <Link href="/personal" className="p-2 -ml-2 rounded-full hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground flex-shrink-0">
                    <ArrowLeft className="w-5 h-5 sm:w-6 sm:h-6" />
                </Link>
                <div className="min-w-0">
                    <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">Transactions</h1>
                    <p className="text-muted-foreground text-sm">Log and review your financial activity.</p>
                </div>
                <div className="ml-auto flex-shrink-0">
                    <button
                        onClick={() => setIsAdding(!isAdding)}
                        className="px-4 sm:px-6 py-2 bg-primary text-primary-foreground rounded-full font-bold text-sm hover:opacity-90 transition-opacity shadow-lg"
                    >
                        + New
                    </button>
                </div>
            </div>

            {/* Active Category Filter Banner */}
            {categoryFilter && (
                <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-primary/10 border border-primary/20">
                    <Filter className="w-4 h-4 text-primary flex-shrink-0" />
                    <span className="text-sm font-medium">
                        Showing: <span className="text-primary">{CATEGORY_LABELS[categoryFilter] || categoryFilter}</span>
                    </span>
                    <span role="img" className="text-xs ml-1">
                        {CATEGORY_ICONS[categoryFilter] || "📦"}
                    </span>
                    <Link
                        href="/personal/transactions"
                        className="ml-auto p-1 rounded-full hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
                    >
                        <X className="w-4 h-4" />
                    </Link>
                </div>
            )}

            {/* Add Entry Form */}
            {isAdding && (
                <form onSubmit={handleSubmit} className="border bg-card rounded-2xl p-4 sm:p-6 space-y-4 sm:space-y-6 animate-in slide-in-from-top-4 shadow-sm">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Type Toggle */}
                        <div>
                            <label className="block text-xs font-medium text-muted-foreground mb-1">Type</label>
                            <div className="flex bg-secondary rounded-xl p-1">
                                <button
                                    type="button"
                                    onClick={() => setFormData({ ...formData, entry_type: "expense", category: "" })}
                                    className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-colors ${formData.entry_type === "expense" ? "bg-background text-foreground shadow" : "text-muted-foreground hover:text-foreground"}`}
                                >
                                    Expense
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setFormData({ ...formData, entry_type: "income", category: "" })}
                                    className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-colors ${formData.entry_type === "income" ? "bg-background text-foreground shadow" : "text-muted-foreground hover:text-foreground"}`}
                                >
                                    Income
                                </button>
                            </div>
                        </div>

                        {/* Amount — always required */}
                        <div>
                            <label className="block text-xs font-medium text-muted-foreground mb-1">Amount *</label>
                            <div className="relative">
                                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                <input
                                    type="number"
                                    value={formData.amount}
                                    onChange={e => setFormData({ ...formData, amount: e.target.value })}
                                    placeholder="0.00"
                                    step="0.01"
                                    className="w-full pl-10 pr-4 py-2 bg-background border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
                                    required
                                />
                            </div>
                        </div>

                        {/* Date — optional for income, shown for both */}
                        <div>
                            <label className="block text-xs font-medium text-muted-foreground mb-1">
                                Date {!isExpense && <span className="text-muted-foreground/70">(optional)</span>}
                            </label>
                            <input
                                type="date"
                                value={formData.entry_date}
                                onChange={e => setFormData({ ...formData, entry_date: e.target.value })}
                                className="w-full px-4 py-2 bg-background border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
                            />
                        </div>

                        {/* Category — free text input */}
                        <div>
                            <label className="block text-xs font-medium text-muted-foreground mb-1">
                                {isExpense ? "Category" : "Source"}{" "}
                                {!isExpense && <span className="text-muted-foreground/70">(optional)</span>}
                            </label>
                            <input
                                type="text"
                                value={formData.category}
                                onChange={e => setFormData({ ...formData, category: e.target.value })}
                                placeholder={isExpense ? "e.g. Groceries, Rent, Dining" : "e.g. Salary, Freelance"}
                                className="w-full px-4 py-2 bg-background border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
                            />
                        </div>

                        {/* Vendor / Shop Name — optional, only for expenses */}
                        {isExpense && (
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1">Shop Name <span className="text-muted-foreground/70">(optional)</span></label>
                                <input
                                    type="text"
                                    value={formData.vendor}
                                    onChange={e => setFormData({ ...formData, vendor: e.target.value })}
                                    placeholder="e.g. Starbucks, Amazon"
                                    className="w-full px-4 py-2 bg-background border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
                                />
                            </div>
                        )}
                    </div>
                    <div className="flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={() => setIsAdding(false)}
                            className="px-4 py-2 text-muted-foreground hover:text-foreground transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-8 py-2 bg-primary text-primary-foreground rounded-xl font-medium hover:opacity-90 transition-all"
                        >
                            Save Entry
                        </button>
                    </div>
                </form>
            )}

            {/* List */}
            <div className="space-y-4">
                {isLoading ? (
                    <div className="text-center text-muted-foreground py-12">Loading transactions...</div>
                ) : entries && entries.length > 0 ? (
                    <div className="grid gap-3">
                        {entries.map((entry) => (
                            <div key={entry.id} className="p-3 sm:p-4 bg-card border rounded-2xl flex items-center justify-between group hover:border-primary/30 transition-colors shadow-sm">
                                <div className="flex items-center gap-3 sm:gap-4 min-w-0">
                                    <div role="img" className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-secondary flex items-center justify-center text-lg sm:text-xl flex-shrink-0">
                                        {CATEGORY_ICONS[entry.category] || "📦"}
                                    </div>
                                    <div className="min-w-0">
                                        <p className="font-medium text-sm sm:text-base truncate">{entry.vendor || entry.category || "Entry"}</p>
                                        <div className="flex items-center gap-1.5 sm:gap-2 text-xs text-muted-foreground flex-wrap">
                                            <span>{new Date(entry.entry_date).toLocaleDateString()}</span>
                                            <span>•</span>
                                            <span className="capitalize truncate">{CATEGORY_LABELS[entry.category] || entry.category}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0">
                                    <span className={`font-mono font-medium text-sm sm:text-base ${entry.entry_type === 'income' ? 'text-emerald-500' : 'text-foreground'}`}>
                                        {entry.entry_type === 'income' ? '+' : '-'}
                                        {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(entry.amount)}
                                    </span>
                                    {deleteConfirmId === entry.id ? (
                                        <div className="flex items-center gap-1 animate-in fade-in duration-200">
                                            <button
                                                onClick={() => deleteMutation.mutate(entry.id)}
                                                className="px-2 py-1 text-xs bg-destructive text-destructive-foreground rounded-md hover:opacity-90 transition-opacity font-medium"
                                            >
                                                Delete
                                            </button>
                                            <button
                                                onClick={() => setDeleteConfirmId(null)}
                                                className="px-2 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    ) : (
                                        <button
                                            onClick={() => setDeleteConfirmId(entry.id)}
                                            className="p-2 text-muted-foreground hover:text-destructive transition-colors sm:opacity-0 sm:group-hover:opacity-100"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-12 text-muted-foreground">
                        <p>{categoryFilter ? `No transactions found in "${CATEGORY_LABELS[categoryFilter] || categoryFilter}".` : "No transactions found."}</p>
                        {categoryFilter ? (
                            <Link href="/personal/transactions" className="text-primary hover:underline mt-2 inline-block">Clear filter</Link>
                        ) : (
                            <button onClick={() => setIsAdding(true)} className="text-primary hover:underline mt-2">Log your first entry</button>
                        )}
                    </div>
                )}
            </div>
        </div >
    );
}
