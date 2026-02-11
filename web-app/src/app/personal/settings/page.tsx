"use client";
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Trash2, Plus, CreditCard, Banknote, Landmark, ArrowLeft } from "lucide-react";
import Link from "next/link";

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
        <div className="max-w-2xl mx-auto space-y-8 sm:space-y-12 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex items-center gap-3 sm:gap-4">
                <Link href="/personal" className="p-2 rounded-full hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground">
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                    <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">Settings</h1>
                    <p className="text-muted-foreground text-sm sm:text-base">Manage your accounts and preferences.</p>
                </div>
            </div>

            {/* ACCOUNTS SECTION */}
            <section className="space-y-4 sm:space-y-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-lg sm:text-xl font-semibold">Accounts & Assets</h2>
                    <button
                        onClick={() => setIsAdding(!isAdding)}
                        className="flex items-center gap-2 text-primary hover:text-primary/80 font-medium transition-colors text-sm"
                    >
                        <Plus className="w-4 h-4" /> Add Account
                    </button>
                </div>

                <div className="border bg-card rounded-2xl overflow-hidden shadow-sm">
                    {isLoading ? (
                        <div className="p-6 text-muted-foreground">Loading accounts...</div>
                    ) : accounts && accounts.length > 0 ? (
                        <div className="divide-y">
                            {accounts.map((acc) => (
                                <div key={acc.id} className="p-3 sm:p-4 flex items-center justify-between group">
                                    <div className="flex items-center gap-3 sm:gap-4 min-w-0">
                                        <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-secondary flex items-center justify-center text-muted-foreground flex-shrink-0">
                                            {getIcon(acc.type)}
                                        </div>
                                        <div className="min-w-0">
                                            <p className="font-semibold truncate">{acc.name}</p>
                                            <p className="text-xs text-muted-foreground capitalize">{acc.type}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3 sm:gap-6 flex-shrink-0">
                                        <div className="text-right">
                                            <span className="block font-mono font-medium text-sm sm:text-base">
                                                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(acc.balance)}
                                            </span>
                                        </div>
                                        <button
                                            onClick={() => deleteMutation.mutate(acc.id)}
                                            className="text-muted-foreground hover:text-destructive transition-colors sm:opacity-0 sm:group-hover:opacity-100"
                                            title="Delete Account"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="p-6 sm:p-8 text-center text-muted-foreground text-sm sm:text-base">
                            No accounts added yet. Add your bank accounts, cash, or savings to track your net worth.
                        </div>
                    )}
                </div>

                {isAdding && (
                    <form onSubmit={handleSubmit} className="border bg-card rounded-2xl p-4 sm:p-6 space-y-4 animate-in slide-in-from-top-4 duration-300 shadow-sm">
                        <h3 className="font-semibold">Add New Account</h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1">Account Name</label>
                                <input
                                    type="text"
                                    value={newAccount.name}
                                    onChange={e => setNewAccount({ ...newAccount, name: e.target.value })}
                                    placeholder="e.g. Chase Checking"
                                    className="w-full px-4 py-2 bg-background border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1">Current Balance</label>
                                <input
                                    type="number"
                                    value={newAccount.balance}
                                    onChange={e => setNewAccount({ ...newAccount, balance: e.target.value })}
                                    placeholder="0.00"
                                    step="0.01"
                                    className="w-full px-4 py-2 bg-background border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-1">Type</label>
                                <select
                                    value={newAccount.type}
                                    onChange={e => setNewAccount({ ...newAccount, type: e.target.value })}
                                    className="w-full px-4 py-2 bg-background border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
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
                                className="px-4 py-2 text-muted-foreground hover:text-foreground transition-colors text-sm"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={createMutation.isPending}
                                className="px-6 py-2 bg-primary text-primary-foreground rounded-xl font-medium text-sm hover:opacity-90 transition-all"
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
