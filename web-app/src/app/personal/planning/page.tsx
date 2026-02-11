"use client";
import React, { useState, useMemo } from 'react';
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Target, DollarSign, Calendar, TrendingDown, TrendingUp, ArrowLeft, Sparkles } from "lucide-react";
import Link from "next/link";

const formatCurrency = (val: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

export default function PlanningPage() {
    const [name, setName] = useState("");
    const [amount, setAmount] = useState("");
    const [targetDate, setTargetDate] = useState("");
    const [plans, setPlans] = useState<Array<{ name: string; amount: number; targetDate: string }>>([]);
    const [showResults, setShowResults] = useState(false);

    const { data: summaryData } = useQuery({
        queryKey: ["personal", "summary"],
        queryFn: () => api.personal.getSummary(),
    });
    const { data: trendsData } = useQuery({
        queryKey: ["personal", "trends"],
        queryFn: () => api.personal.getTrends(6),
    });

    const income = summaryData?.income ?? 0;
    const expense = summaryData?.expense ?? 0;
    const monthlySurplus = income - expense;

    // Calculate averages from trends
    const avgMonthlySurplus = useMemo(() => {
        if (!trendsData?.trends || trendsData.trends.length === 0) return monthlySurplus;
        const surpluses = trendsData.trends.map(t => t.income - t.expense);
        return surpluses.reduce((a, b) => a + b, 0) / surpluses.length;
    }, [trendsData, monthlySurplus]);

    const totalPlannedCost = plans.reduce((s, p) => s + p.amount, 0);

    function addPlan(e: React.FormEvent) {
        e.preventDefault();
        const parsed = parseFloat(amount);
        if (!name.trim() || isNaN(parsed) || parsed <= 0) return;
        setPlans(prev => [...prev, { name: name.trim(), amount: parsed, targetDate: targetDate || "" }]);
        setName("");
        setAmount("");
        setTargetDate("");
        setShowResults(true);
    }

    function removePlan(index: number) {
        setPlans(prev => prev.filter((_, i) => i !== index));
        if (plans.length <= 1) setShowResults(false);
    }

    // Impact analysis
    const monthsToSave = avgMonthlySurplus > 0 ? Math.ceil(totalPlannedCost / avgMonthlySurplus) : Infinity;
    const adjustedMonthlyRemaining = monthlySurplus - (totalPlannedCost / Math.max(monthsToSave, 1));
    const canAfford = monthlySurplus >= totalPlannedCost;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link href="/personal" className="p-2 rounded-full hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground">
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">Planning</h1>
                    <p className="text-muted-foreground mt-1">Plan trips, big purchases, or any upcoming expense and see how it impacts your finances.</p>
                </div>
            </div>

            {/* Current Financial Position */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="rounded-2xl border bg-card p-5 shadow-sm">
                    <p className="text-xs text-muted-foreground mb-1">Monthly Income</p>
                    <p className="text-2xl font-bold text-emerald-500">{formatCurrency(income)}</p>
                </div>
                <div className="rounded-2xl border bg-card p-5 shadow-sm">
                    <p className="text-xs text-muted-foreground mb-1">Monthly Expenses</p>
                    <p className="text-2xl font-bold text-rose-500">{formatCurrency(expense)}</p>
                </div>
                <div className="rounded-2xl border bg-card p-5 shadow-sm">
                    <p className="text-xs text-muted-foreground mb-1">Monthly Surplus</p>
                    <p className={`text-2xl font-bold ${monthlySurplus >= 0 ? "text-blue-500" : "text-orange-500"}`}>
                        {formatCurrency(monthlySurplus)}
                    </p>
                </div>
            </div>

            {/* Add a Plan Form */}
            <div className="rounded-2xl border bg-card p-6 shadow-sm">
                <div className="flex items-center gap-3 mb-5">
                    <div className="w-10 h-10 rounded-xl bg-amber-500/15 flex items-center justify-center">
                        <Target className="w-5 h-5 text-amber-500" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold">Add a Planned Expense</h2>
                        <p className="text-sm text-muted-foreground">Enter a trip, purchase, or any large expense to simulate its financial impact.</p>
                    </div>
                </div>
                <form onSubmit={addPlan} className="flex flex-col sm:flex-row gap-3">
                    <div className="flex-1">
                        <label className="text-xs text-muted-foreground mb-1 block">What are you planning?</label>
                        <input
                            type="text"
                            value={name}
                            onChange={e => setName(e.target.value)}
                            placeholder="e.g. Trip to Italy, New laptop"
                            className="w-full h-11 px-4 rounded-lg border bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition"
                        />
                    </div>
                    <div className="w-full sm:w-40">
                        <label className="text-xs text-muted-foreground mb-1 block">Estimated Cost</label>
                        <div className="relative">
                            <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                value={amount}
                                onChange={e => setAmount(e.target.value)}
                                placeholder="0.00"
                                className="w-full h-11 pl-9 pr-4 rounded-lg border bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition"
                            />
                        </div>
                    </div>
                    <div className="w-full sm:w-44">
                        <label className="text-xs text-muted-foreground mb-1 block">Target Date (optional)</label>
                        <div className="relative">
                            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                            <input
                                type="date"
                                value={targetDate}
                                onChange={e => setTargetDate(e.target.value)}
                                className="w-full h-11 pl-9 pr-4 rounded-lg border bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition"
                            />
                        </div>
                    </div>
                    <div className="flex items-end">
                        <button
                            type="submit"
                            className="h-11 px-6 bg-primary text-primary-foreground font-medium rounded-lg hover:opacity-90 transition"
                        >
                            Add
                        </button>
                    </div>
                </form>
            </div>

            {/* Plans List */}
            {plans.length > 0 && (
                <div className="rounded-2xl border bg-card p-6 shadow-sm">
                    <h2 className="text-lg font-semibold mb-4">Your Plans</h2>
                    <div className="space-y-3">
                        {plans.map((plan, i) => (
                            <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-secondary/50">
                                <div>
                                    <p className="font-medium">{plan.name}</p>
                                    <p className="text-sm text-muted-foreground">
                                        {formatCurrency(plan.amount)}
                                        {plan.targetDate && ` · Target: ${new Date(plan.targetDate).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`}
                                    </p>
                                </div>
                                <button onClick={() => removePlan(i)} className="text-sm text-muted-foreground hover:text-destructive transition-colors">Remove</button>
                            </div>
                        ))}
                        <div className="flex justify-between pt-3 border-t">
                            <span className="font-semibold">Total Planned</span>
                            <span className="font-bold text-lg">{formatCurrency(totalPlannedCost)}</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Impact Analysis */}
            {showResults && plans.length > 0 && (
                <div className="rounded-2xl border bg-card p-6 shadow-sm space-y-6">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center">
                            <Sparkles className="w-5 h-5 text-purple-500" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold">Financial Impact Analysis</h2>
                            <p className="text-sm text-muted-foreground">Here&apos;s how these plans would affect your finances</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {/* Can Afford? */}
                        <div className={`rounded-xl p-5 border ${canAfford ? "bg-emerald-500/5 border-emerald-500/20" : "bg-rose-500/5 border-rose-500/20"}`}>
                            <div className="flex items-center gap-2 mb-2">
                                {canAfford ? <TrendingUp className="w-5 h-5 text-emerald-500" /> : <TrendingDown className="w-5 h-5 text-rose-500" />}
                                <h3 className="font-semibold">{canAfford ? "Within Budget" : "Over Budget"}</h3>
                            </div>
                            <p className="text-sm text-muted-foreground">
                                {canAfford
                                    ? `Good news! You can cover ${formatCurrency(totalPlannedCost)} from this month's surplus alone.`
                                    : `At ${formatCurrency(totalPlannedCost)}, this exceeds your monthly surplus of ${formatCurrency(monthlySurplus)}.`}
                            </p>
                        </div>

                        {/* Months to Save */}
                        <div className="rounded-xl p-5 border bg-blue-500/5 border-blue-500/20">
                            <h3 className="font-semibold mb-2">Time to Save</h3>
                            <p className="text-3xl font-bold text-blue-500">
                                {monthsToSave === Infinity ? "∞" : `${monthsToSave} month${monthsToSave !== 1 ? "s" : ""}`}
                            </p>
                            <p className="text-sm text-muted-foreground mt-1">
                                {monthsToSave === Infinity
                                    ? "You currently have no surplus to save from — try reducing expenses first."
                                    : `Based on your average monthly surplus of ${formatCurrency(avgMonthlySurplus)}.`}
                            </p>
                        </div>

                        {/* Adjusted Monthly Remaining */}
                        <div className="rounded-xl p-5 border bg-amber-500/5 border-amber-500/20">
                            <h3 className="font-semibold mb-2">Adjusted Monthly</h3>
                            <p className={`text-3xl font-bold ${adjustedMonthlyRemaining >= 0 ? "text-amber-500" : "text-rose-500"}`}>
                                {formatCurrency(adjustedMonthlyRemaining)}
                            </p>
                            <p className="text-sm text-muted-foreground mt-1">
                                What you&apos;d have left each month while saving for this over {monthsToSave === Infinity ? "—" : `${monthsToSave} months`}.
                            </p>
                        </div>
                    </div>

                    {/* Tips */}
                    <div className="bg-secondary/50 rounded-xl p-5">
                        <h3 className="font-medium mb-2 text-sm">💡 Tips</h3>
                        <ul className="space-y-1 text-sm text-muted-foreground">
                            {!canAfford && <li>• Consider spreading this purchase over multiple months to reduce the impact.</li>}
                            {monthsToSave > 3 && <li>• Setting aside a fixed amount each month into a savings account can help stay on track.</li>}
                            <li>• Review your budgets to see if non-essential categories can be trimmed temporarily.</li>
                            <li>• Use the &ldquo;Ask AI&rdquo; feature for personalized saving strategies.</li>
                        </ul>
                    </div>
                </div>
            )}

            {/* Empty State */}
            {plans.length === 0 && (
                <div className="text-center py-16 text-muted-foreground">
                    <Target className="w-16 h-16 mx-auto mb-4 opacity-30" />
                    <p className="text-lg font-medium">No plans yet</p>
                    <p className="text-sm mt-1">Add a trip, big purchase, or any planned expense above to see how it fits into your budget.</p>
                </div>
            )}
        </div>
    );
}
