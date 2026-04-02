"use client";
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
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

            {/* WHATSAPP INTEGRATION SECTION */}
            <WhatsAppSection />
        </div>
    );
}


function WhatsAppSection() {
    const queryClient = useQueryClient();
    const [phone, setPhone] = useState("");
    const [isLinking, setIsLinking] = useState(false);

    const { data: waStatus, isLoading: waLoading } = useQuery({
        queryKey: ["personal", "whatsapp", "status"],
        queryFn: () => api.personal.whatsappStatus(),
    });

    const linkMutation = useMutation({
        mutationFn: () => api.personal.whatsappLink(phone),
        onSuccess: (data) => {
            toast.success(data.message || "Verification code sent!");
            setIsLinking(false);
            setPhone("");
            queryClient.invalidateQueries({ queryKey: ["personal", "whatsapp", "status"] });
        },
        onError: (err: Error) => {
            const detail = (err as ApiError)?.details
                ? ((err as ApiError).details as Record<string, string>)?.detail
                : err.message || "Failed to link WhatsApp";
            toast.error(detail);
        },
    });

    const unlinkMutation = useMutation({
        mutationFn: () => api.personal.whatsappUnlink(),
        onSuccess: () => {
            toast.success("WhatsApp unlinked");
            queryClient.invalidateQueries({ queryKey: ["personal", "whatsapp", "status"] });
        },
        onError: () => toast.error("Failed to unlink"),
    });

    const handleLink = (e: React.FormEvent) => {
        e.preventDefault();
        if (!phone) return;
        linkMutation.mutate();
    };

    const statusBadge = () => {
        if (waLoading) return null;
        if (!waStatus?.linked) return (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary text-muted-foreground">
                Not linked
            </span>
        );
        if (waStatus?.verified) return (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                ✅ Verified
            </span>
        );
        return (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 animate-pulse">
                ⏳ Pending verification
            </span>
        );
    };

    return (
        <section className="space-y-4 sm:space-y-6">
            <div className="flex items-center justify-between">
                <h2 className="text-lg sm:text-xl font-semibold">WhatsApp Integration</h2>
                {statusBadge()}
            </div>

            <div className="border bg-card rounded-2xl overflow-hidden shadow-sm">
                {waStatus?.linked ? (
                    <div className="p-4 sm:p-6 space-y-4">
                        <div className="flex items-center gap-3 sm:gap-4">
                            <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400 flex-shrink-0">
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 21l1.65-3.8a9 9 0 1 1 3.4 2.9L3 21"/><path d="M9 10a.5.5 0 0 0 1 0V9a.5.5 0 0 0-1 0v1Zm0 0a5 5 0 0 0 5 5h1a.5.5 0 0 0 0-1h-1a.5.5 0 0 0 0 1"/></svg>
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="font-semibold">{waStatus.phone}</p>
                                <p className="text-xs text-muted-foreground">
                                    {waStatus.verified
                                        ? "Connected — send transactions and ask questions via WhatsApp"
                                        : "Check your WhatsApp for the verification code"}
                                </p>
                            </div>
                        </div>

                        {!waStatus.verified && (
                            <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 text-sm text-amber-700 dark:text-amber-300">
                                📱 We sent a 6-digit code to your WhatsApp. Reply to the Hissabi bot with the code to complete verification.
                            </div>
                        )}

                        <div className="flex justify-end pt-1">
                            <button
                                onClick={() => {
                                    if (confirm("Unlink your WhatsApp number?")) {
                                        unlinkMutation.mutate();
                                    }
                                }}
                                className="text-sm text-muted-foreground hover:text-destructive transition-colors"
                            >
                                Unlink WhatsApp
                            </button>
                        </div>
                    </div>
                ) : isLinking ? (
                    <form onSubmit={handleLink} className="p-4 sm:p-6 space-y-4 animate-in slide-in-from-top-4 duration-300">
                        <h3 className="font-semibold">Link your WhatsApp</h3>
                        <p className="text-sm text-muted-foreground">
                            We&apos;ll send a verification code to this number via WhatsApp.
                        </p>
                        <div>
                            <label className="block text-xs font-medium text-muted-foreground mb-1">Phone Number</label>
                            <input
                                type="tel"
                                value={phone}
                                onChange={e => setPhone(e.target.value)}
                                placeholder="+1 234 567 8900"
                                className="w-full px-4 py-2 bg-background border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition"
                                required
                            />
                            <p className="text-xs text-muted-foreground mt-1">Include country code (e.g. +1 for US, +961 for Lebanon)</p>
                        </div>
                        <div className="flex justify-end gap-3 pt-2">
                            <button
                                type="button"
                                onClick={() => setIsLinking(false)}
                                className="px-4 py-2 text-muted-foreground hover:text-foreground transition-colors text-sm"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={linkMutation.isPending}
                                className="px-6 py-2 bg-emerald-600 text-white rounded-xl font-medium text-sm hover:bg-emerald-500 transition-all"
                            >
                                {linkMutation.isPending ? "Sending code..." : "Send Verification Code"}
                            </button>
                        </div>
                    </form>
                ) : (
                    <div className="p-6 sm:p-8 text-center space-y-4">
                        <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mx-auto">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 21l1.65-3.8a9 9 0 1 1 3.4 2.9L3 21"/><path d="M9 10a.5.5 0 0 0 1 0V9a.5.5 0 0 0-1 0v1Zm0 0a5 5 0 0 0 5 5h1a.5.5 0 0 0 0-1h-1a.5.5 0 0 0 0 1"/></svg>
                        </div>
                        <div>
                            <p className="font-medium">Log expenses via WhatsApp</p>
                            <p className="text-sm text-muted-foreground mt-1">
                                Text &quot;Paid $20 for dinner&quot; or ask &quot;How much did I spend this week?&quot;
                            </p>
                        </div>
                        <button
                            onClick={() => setIsLinking(true)}
                            className="px-6 py-2 bg-emerald-600 text-white rounded-xl font-medium text-sm hover:bg-emerald-500 transition-all"
                        >
                            Link WhatsApp Number
                        </button>
                    </div>
                )}
            </div>
        </section>
    );
}
