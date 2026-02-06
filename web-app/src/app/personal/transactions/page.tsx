"use client";
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { ArrowLeft, Trash2, DollarSign } from "lucide-react";
import Link from 'next/link';

const CATEGORY_ICONS: Record<string, string> = {
    salary: "💰", freelance: "💻", investment: "📈", groceries: "🛒", dining: "🍽️",
    transportation: "🚗", housing: "🏠", utilities: "💡", entertainment: "🎬",
    shopping: "🛍️", healthcare: "🏥", other: "📦"
};

export default function TransactionsPage() {
    const queryClient = useQueryClient();
    const [isAdding, setIsAdding] = useState(false);
    const [formData, setFormData] = useState({
        entry_date: new Date().toISOString().split("T")[0],
        entry_type: "expense" as "income" | "expense",
        category: "other",
        amount: "",
        description: "",
        vendor: "",
    });

    const { data: entries, isLoading } = useQuery({
        queryKey: ["personal", "entries"],
        queryFn: () => api.personal.listEntries({}),
    });

    const { data: categories } = useQuery({
        queryKey: ["personal", "categories"],
        queryFn: () => api.personal.getCategories(),
    });

    const createMutation = useMutation({
        mutationFn: () => api.personal.createEntry({
            ...formData,
            entry_date: (formData.entry_date || new Date().toISOString().split("T")[0]) as string,
            amount: parseFloat(formData.amount),
        }),
        onSuccess: () => {
            toast.success("Entry added");
            setFormData({ ...formData, amount: "", description: "", vendor: "" });
            setIsAdding(false);
            queryClient.invalidateQueries({ queryKey: ["personal", "entries"] });
        },
        onError: () => toast.error("Failed to add entry"),
    });

    const deleteMutation = useMutation({
        mutationFn: (id: number) => api.personal.deleteEntry(id),
        onSuccess: () => {
            toast.success("Entry deleted");
            queryClient.invalidateQueries({ queryKey: ["personal", "entries"] });
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        createMutation.mutate();
    };

    return (
        <div className="space-y-8 max-w-4xl mx-auto animate-in fade-in duration-500">
            <div className="flex items-center gap-4">
                <Link href="/personal" className="p-2 -ml-2 text-slate-400 hover:text-white transition-colors">
                    <ArrowLeft className="w-6 h-6" />
                </Link>
                <div>
                    <h1 className="text-3xl font-bold text-white">Transactions</h1>
                    <p className="text-slate-400">Log and review your financial activity.</p>
                </div>
                <div className="ml-auto">
                    <button
                        onClick={() => setIsAdding(!isAdding)}
                        className="px-6 py-2 bg-slate-100 text-slate-900 rounded-full font-bold hover:bg-white transition-colors shadow-lg shadow-white/10"
                    >
                        + New Entry
                    </button>
                </div>
            </div>

            {/* Add Entry Form */}
            {isAdding && (
                <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 animate-in slide-in-from-top-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">Date</label>
                            <input
                                type="date"
                                value={formData.entry_date}
                                onChange={e => setFormData({ ...formData, entry_date: e.target.value })}
                                className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-cyan-500"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">Type</label>
                            <div className="flex bg-slate-950 rounded-xl p-1 border border-slate-800">
                                <button
                                    type="button"
                                    onClick={() => setFormData({ ...formData, entry_type: "expense" })}
                                    className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-colors ${formData.entry_type === "expense" ? "bg-slate-800 text-white" : "text-slate-500 hover:text-slate-300"}`}
                                >
                                    Expense
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setFormData({ ...formData, entry_type: "income" })}
                                    className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-colors ${formData.entry_type === "income" ? "bg-slate-800 text-white" : "text-slate-500 hover:text-slate-300"}`}
                                >
                                    Income
                                </button>
                            </div>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">Description</label>
                            <input
                                type="text"
                                value={formData.description}
                                onChange={e => setFormData({ ...formData, description: e.target.value })}
                                placeholder="What was it?"
                                className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-cyan-500"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">Amount</label>
                            <div className="relative">
                                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input
                                    type="number"
                                    value={formData.amount}
                                    onChange={e => setFormData({ ...formData, amount: e.target.value })}
                                    placeholder="0.00"
                                    step="0.01"
                                    className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-cyan-500"
                                    required
                                />
                            </div>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">Category</label>
                            <select
                                value={formData.category}
                                onChange={e => setFormData({ ...formData, category: e.target.value })}
                                className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-cyan-500"
                            >
                                {categories ? Object.keys(categories).flatMap(group => (categories[group] || [])).map((cat: string) => (
                                    <option key={cat} value={cat}>{cat}</option>
                                )) : <option value="other">Other</option>}
                                <option value="salary">Salary</option>
                                <option value="groceries">Groceries</option>
                                <option value="dining">Dining</option>
                                <option value="transportation">Transportation</option>
                                <option value="utilities">Utilities</option>
                                <option value="entertainment">Entertainment</option>
                                <option value="shopping">Shopping</option>
                                <option value="healthcare">Healthcare</option>
                                <option value="investment">Investment</option>
                                <option value="other">Other</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">Vendor (Optional)</label>
                            <input
                                type="text"
                                value={formData.vendor}
                                onChange={e => setFormData({ ...formData, vendor: e.target.value })}
                                placeholder="e.g. Starbucks"
                                className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-cyan-500"
                            />
                        </div>
                    </div>
                    <div className="flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={() => setIsAdding(false)}
                            className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-8 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl font-medium transition-colors"
                        >
                            Save Entry
                        </button>
                    </div>
                </form>
            )}

            {/* List */}
            <div className="space-y-4">
                {isLoading ? (
                    <div className="text-center text-slate-500 py-12">Loading transactions...</div>
                ) : entries && entries.length > 0 ? (
                    <div className="grid gap-3">
                        {entries.map((entry) => (
                            <div key={entry.id} className="p-4 bg-slate-900 border border-slate-800 rounded-2xl flex items-center justify-between group hover:border-cyan-500/30 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-xl">
                                        {CATEGORY_ICONS[entry.category] || "📦"}
                                    </div>
                                    <div>
                                        <p className="font-medium text-white">{entry.description || entry.vendor || "No description"}</p>
                                        <div className="flex items-center gap-2 text-xs text-slate-500">
                                            <span>{new Date(entry.entry_date).toLocaleDateString()}</span>
                                            <span>•</span>
                                            <span className="capitalize">{entry.category}</span>
                                            {entry.vendor && <span>• {entry.vendor}</span>}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4">
                                    <span className={`font-mono font-medium ${entry.entry_type === 'income' ? 'text-green-400' : 'text-slate-200'}`}>
                                        {entry.entry_type === 'income' ? '+' : '-'}
                                        {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(entry.amount)}
                                    </span>
                                    <button
                                        onClick={() => deleteMutation.mutate(entry.id)}
                                        className="p-2 text-slate-600 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-12 text-slate-500">
                        <p>No transactions found.</p>
                        <button onClick={() => setIsAdding(true)} className="text-cyan-400 hover:underline mt-2">Log your first entry</button>
                    </div>
                )}
            </div>
        </div>
    );
}
