"use client";
import React from 'react';
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import Link from 'next/link';
import { ArrowRight, BarChart3, MessageSquare, PieChart, Wallet, CreditCard, TrendingUp, Activity, ListOrdered } from "lucide-react";

export default function PersonalDashboard() {
    const { data: insights, isLoading } = useQuery({
        queryKey: ["personal", "insights"],
        queryFn: () => api.personal.getInsights(),
    });

    const { data: accounts } = useQuery({
        queryKey: ["personal", "accounts"],
        queryFn: () => api.personal.listAccounts(),
    });

    const formatCurrency = (val: number) =>
        new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

    const totalBalance = accounts?.reduce((sum, acc) => sum + Number(acc.balance), 0) || 0;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Hero / Greeting */}
            <section className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-slate-800">
                <div>
                    <h1 className="text-4xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                        Hello, {isLoading ? "..." : "User"}
                    </h1>
                    <p className="text-slate-400 mt-2 text-lg">
                        Here is your financial overview.
                    </p>
                </div>
                <div className="text-right">
                    <p className="text-sm text-slate-500 uppercase tracking-wider font-medium">Total Balance</p>
                    <div className="text-4xl font-mono font-bold text-white tracking-tight">
                        {formatCurrency(totalBalance)}
                    </div>
                </div>
            </section>

            {/* Main Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

                {/* THE FLOW */}
                <Link href="/personal/flow" className="md:col-span-2 group relative overflow-hidden rounded-3xl bg-slate-900 border border-slate-800 hover:border-purple-500/50 transition-all p-8 flex flex-col justify-between min-h-[300px]">
                    <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative z-10">
                        <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400 mb-6 group-hover:scale-110 transition-transform">
                            <Activity className="w-6 h-6" />
                        </div>
                        <h2 className="text-3xl font-bold text-white mb-2">The Flow</h2>
                        <p className="text-slate-400 max-w-md text-lg">Visualize your money movement from income to categories and merchants.</p>
                    </div>
                    <div className="relative z-10 flex items-center gap-2 text-purple-400 font-medium mt-8 group-hover:translate-x-2 transition-transform">
                        Open Visualization <ArrowRight className="w-5 h-5" />
                    </div>
                </Link>

                {/* MERCHANT DNA */}
                <Link href="/personal/merchants" className="group relative overflow-hidden rounded-3xl bg-slate-900 border border-slate-800 hover:border-pink-500/50 transition-all p-8 flex flex-col justify-between">
                    <div className="absolute inset-0 bg-gradient-to-br from-pink-500/10 to-orange-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative z-10">
                        <div className="w-12 h-12 rounded-full bg-pink-500/20 flex items-center justify-center text-pink-400 mb-6 group-hover:scale-110 transition-transform">
                            <Wallet className="w-6 h-6" />
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-2">Merchant DNA</h2>
                        <p className="text-slate-400">Deep dive into your spending habits.</p>
                    </div>
                    <div className="relative z-10 flex items-center gap-2 text-pink-400 font-medium mt-8 group-hover:translate-x-2 transition-transform">
                        Analyze <ArrowRight className="w-5 h-5" />
                    </div>
                </Link>

                {/* TRANSACTIONS */}
                <Link href="/personal/transactions" className="group relative overflow-hidden rounded-3xl bg-slate-900 border border-slate-800 hover:border-cyan-500/50 transition-all p-8 flex flex-col justify-between">
                    <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative z-10">
                        <div className="w-12 h-12 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-400 mb-6 group-hover:scale-110 transition-transform">
                            <ListOrdered className="w-6 h-6" />
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-2">Transactions</h2>
                        <p className="text-slate-400">Log entries and view history.</p>
                    </div>
                    <div className="relative z-10 flex items-center gap-2 text-cyan-400 font-medium mt-8 group-hover:translate-x-2 transition-transform">
                        View History <ArrowRight className="w-5 h-5" />
                    </div>
                </Link>

                {/* BUDGETS */}
                <Link href="/personal/budgets" className="group relative overflow-hidden rounded-3xl bg-slate-900 border border-slate-800 hover:border-green-500/50 transition-all p-8 flex flex-col justify-between">
                    <div className="absolute inset-0 bg-gradient-to-br from-green-500/10 to-emerald-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative z-10">
                        <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center text-green-400 mb-6 group-hover:scale-110 transition-transform">
                            <PieChart className="w-6 h-6" />
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-2">Budgets</h2>
                        <p className="text-slate-400">Set monthly spending limits.</p>
                    </div>
                    <div className="relative z-10 flex items-center gap-2 text-green-400 font-medium mt-8 group-hover:translate-x-2 transition-transform">
                        Manage <ArrowRight className="w-5 h-5" />
                    </div>
                </Link>

                {/* AI CHAT */}
                <Link href="/personal/chat" className="group relative overflow-hidden rounded-3xl bg-slate-900 border border-slate-800 hover:border-yellow-500/50 transition-all p-8 flex flex-col justify-between">
                    <div className="absolute inset-0 bg-gradient-to-br from-yellow-500/10 to-orange-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative z-10">
                        <div className="w-12 h-12 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-400 mb-6 group-hover:scale-110 transition-transform">
                            <MessageSquare className="w-6 h-6" />
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-2">Ask AI</h2>
                        <p className="text-slate-400">Get financial advice and insights.</p>
                    </div>
                    <div className="relative z-10 flex items-center gap-2 text-yellow-400 font-medium mt-8 group-hover:translate-x-2 transition-transform">
                        Chat <ArrowRight className="w-5 h-5" />
                    </div>
                </Link>

            </div>
        </div>
    );
}
