"use client";
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Trash2, Plus, CreditCard, Banknote, Landmark } from "lucide-react";

export default function PersonalSettings() {
    const queryClient = useQueryClient();
    const [isAdding, setIsAdding] = useState(false);
    const [newAccount, setNewAccount] = useState({ name: "", balance: "", type: "checking" });

    const { data: accounts, isLoading } = useQuery({
        queryKey: ["personal", "accounts"],
        queryFn: () => api.personal.listAccounts(),
    });

    const createMutation = useMutation({
        mutationFn: () => api.personal.createAccount(
            newAccount.name,
            parseFloat(newAccount.balance) || 0,
            newAccount.type
        ),
        onSuccess: () => {
            toast.success("Account created");
            setIsAdding(false);
            setNewAccount({ name: "", balance: "", type: "checking" });
            queryClient.invalidateQueries({ queryKey: ["personal", "accounts"] });
        },
        onError: () => toast.error("Failed to create account"),
    });

    const deleteMutation = useMutation({
        mutationFn: (id: number) => api.personal.deleteAccount(id),
        onSuccess: () => {
            toast.success("Account removed");
            queryClient.invalidateQueries({ queryKey: ["personal", "accounts"] });
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!newAccount.name) return;
        createMutation.mutate();
    };

    const getIcon = (type: string) => {
        if (type === "cash") return <Banknote className="w-5 h-5" />;
        if (type === "investment") return <Landmark className="w-5 h-5" />;
        return <CreditCard className="w-5 h-5" />;
    };

    return (
        <div className="max-w-2xl mx-auto space-y-12 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
                <p className="text-slate-400">Manage your accounts and preferences.</p>
            </div>

            {/* ACCOUNTS SECTION */}
            <section className="space-y-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold text-white">Accounts & Assets</h2>
                    <button
                        onClick={() => setIsAdding(!isAdding)}
                        className="flex items-center gap-2 text-purple-400 hover:text-purple-300 font-medium transition-colors"
                    >
                        <Plus className="w-4 h-4" /> Add Account
                    </button>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
                    {isLoading ? (
                        <div className="p-6 text-slate-500">Loading accounts...</div>
                    ) : accounts && accounts.length > 0 ? (
                        <div className="divide-y divide-slate-800">
                            {accounts.map((acc) => (
                                <div key={acc.id} className="p-4 flex items-center justify-between group">
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-slate-400">
                                            {getIcon(acc.type)}
                                        </div>
                                        <div>
                                            <p className="font-semibold text-white">{acc.name}</p>
                                            <p className="text-xs text-slate-500 capitalize">{acc.type}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-6">
                                        <div className="text-right">
                                            <span className="block font-mono font-medium text-slate-200">
                                                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(acc.balance)}
                                            </span>
                                            {/* Note: Balance editing not implemented yet, just display */}
                                        </div>
                                        <button
                                            onClick={() => deleteMutation.mutate(acc.id)}
                                            className="text-slate-600 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                                            title="Delete Account"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="p-8 text-center text-slate-500">
                            No accounts added yet. Add your bank accounts, cash, or savings to track your net worth.
                        </div>
                    )}
                </div>

                {isAdding && (
                    <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 animate-in slide-in-from-top-4 duration-300">
                        <h3 className="font-semibold text-white">Add New Account</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-medium text-slate-400 mb-1">Account Name</label>
                                <input
                                    type="text"
                                    value={newAccount.name}
                                    onChange={e => setNewAccount({ ...newAccount, name: e.target.value })}
                                    placeholder="e.g. Chase Checking"
                                    className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-purple-500"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-400 mb-1">Current Balance</label>
                                <input
                                    type="number"
                                    value={newAccount.balance}
                                    onChange={e => setNewAccount({ ...newAccount, balance: e.target.value })}
                                    placeholder="0.00"
                                    step="0.01"
                                    className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-purple-500"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-400 mb-1">Type</label>
                                <select
                                    value={newAccount.type}
                                    onChange={e => setNewAccount({ ...newAccount, type: e.target.value })}
                                    className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-purple-500"
                                >
                                    <option value="checking">Checking</option>
                                    <option value="savings">Savings</option>
                                    <option value="credit">Credit Card</option>
                                    <option value="investment">Investment</option>
                                    <option value="cash">Cash</option>
                                    <option value="other">Other</option>
                                </select>
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 pt-2">
                            <button
                                type="button"
                                onClick={() => setIsAdding(false)}
                                className="px-4 py-2 text-slate-400 hover:text-white transition-colors text-sm"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={createMutation.isPending}
                                className="px-6 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl font-medium text-sm transition-colors"
                            >
                                {createMutation.isPending ? "Adding..." : "Add Account"}
                            </button>
                        </div>
                    </form>
                )}
            </section>
        </div>
    );
}
