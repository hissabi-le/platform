"use client";
import React, { useMemo, useState } from 'react';
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import Link from 'next/link';
import {
    ArrowRight, TrendingUp, TrendingDown, Wallet, CreditCard,
    MessageSquare, PieChart as PieChartIcon, Target, Zap,
    Activity, ArrowUpRight, ArrowDownRight, Flame, Percent, Sparkles,
    ChevronDown, Trophy, BarChart3
} from "lucide-react";

// ─── Varied Phrases ───────────────────────────────────────────────────────
const GREETINGS = [
    "Welcome back 👋", "Let's check on your finances 📊", "Here's your money snapshot 💰",
    "Your financial pulse 🩺", "Hey there, money maestro 🎹", "Time for a financial check-in ✅",
    "Your wallet report is ready 📋", "Let's see how you're doing 🔍",
    "Here's what's happening with your money 💵", "Financial update incoming 📡",
    "Quick look at your finances 👀", "Your money, at a glance ✨",
];
const POSITIVE_NET = [
    "You're saving well! Keep it up 🎉", "Nice work — more money in than out 💪",
    "Your finances are looking healthy 🌿", "Solid month — you're in the green ✅",
    "Great discipline! Your savings are growing 📈", "You're on track — nice balance 🏆",
];
const NEGATIVE_NET = [
    "Heads up — spending exceeded income this period 📉",
    "You're in the red this period — consider adjusting 🔴",
    "Expenses are outpacing income — let's review 🧐",
    "Time to tighten the belt a little 🤏",
    "Spending spike detected — worth a look 🔍",
];
const INSIGHT_TEMPLATES = [
    "Your top category this week: {category} at {amount}",
    "Most of your spending went to {category} ({amount})",
    "{category} is your biggest expense — {amount} this period",
];

function pickRandom<T>(arr: T[]): T {
    return arr[Math.floor(Math.random() * arr.length)]!;
}

// ─── Colors & Labels ───────────────────────────────────────────────────────
const CATEGORY_COLORS: Record<string, string> = {
    groceries: "#10b981", dining: "#f59e0b", delivery: "#ef4444", alcohol: "#8b5cf6",
    nightlife: "#ec4899", fitness: "#06b6d4", wellness: "#14b8a6", fashion: "#f97316",
    entertainment: "#6366f1", personal_care: "#d946ef", rent: "#64748b",
    utilities: "#eab308", household: "#84cc16", subscriptions: "#3b82f6",
    investments: "#22c55e", savings: "#0ea5e9", transportation: "#a855f7",
    healthcare: "#f43f5e", education: "#0891b2", travel: "#2563eb",
    gifts: "#c026d3", other: "#737373", salary: "#10b981", freelance: "#06b6d4",
    investment_income: "#22c55e", other_income: "#737373",
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

const CATEGORY_EMOJIS: Record<string, string> = {
    groceries: "🛒", dining: "🍽️", delivery: "🚚", alcohol: "🍺",
    nightlife: "🌙", fitness: "💪", wellness: "🧘", fashion: "👗",
    entertainment: "🎬", personal_care: "💅", rent: "🏠",
    utilities: "💡", household: "🏡", subscriptions: "📱",
    investments: "📈", savings: "🏦", transportation: "🚗",
    healthcare: "🏥", education: "📚", travel: "✈️",
    gifts: "🎁", other: "📦", salary: "💰", freelance: "💻",
    investment_income: "📊", other_income: "💵",
};

const formatCurrency = (val: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

// ─── Time Range Helpers ────────────────────────────────────────────────────
type TimeRange = "week" | "month" | "3months" | "year";

function getDateRange(range: TimeRange): { start: string; end: string; label: string } {
    const today = new Date();
    const end = today.toISOString().split("T")[0]!;
    const d = new Date(today);
    switch (range) {
        case "week":
            d.setDate(d.getDate() - 7);
            return { start: d.toISOString().split("T")[0]!, end, label: "This Week" };
        case "month":
            d.setDate(1);
            return { start: d.toISOString().split("T")[0]!, end, label: "This Month" };
        case "3months":
            d.setMonth(d.getMonth() - 3);
            return { start: d.toISOString().split("T")[0]!, end, label: "3 Months" };
        case "year":
            d.setFullYear(d.getFullYear() - 1);
            return { start: d.toISOString().split("T")[0]!, end, label: "1 Year" };
    }
}

function TimeRangeSelector({ value, onChange }: { value: TimeRange; onChange: (v: TimeRange) => void }) {
    const options: { value: TimeRange; label: string }[] = [
        { value: "week", label: "Week" },
        { value: "month", label: "Month" },
        { value: "3months", label: "3M" },
        { value: "year", label: "Year" },
    ];
    return (
        <div className="flex bg-secondary/60 rounded-lg p-0.5 gap-0.5">
            {options.map(o => (
                <button
                    key={o.value}
                    onClick={() => onChange(o.value)}
                    className={`px-2.5 py-1 text-xs font-medium rounded-md transition-all ${value === o.value
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                        }`}
                >
                    {o.label}
                </button>
            ))}
        </div>
    );
}

// ─── SVG Pie Chart ─────────────────────────────────────────────────────────
function DonutChart({ data }: { data: { category: string; total: number }[] }) {
    const [hovered, setHovered] = useState<number | null>(null);
    const total = data.reduce((s, d) => s + d.total, 0);
    if (total === 0) return <p className="text-muted-foreground text-sm">No spending data yet.</p>;

    const slices: { category: string; total: number; startAngle: number; endAngle: number; color: string }[] = [];
    let currentAngle = -90;
    data.forEach(d => {
        const angle = (d.total / total) * 360;
        slices.push({
            ...d,
            startAngle: currentAngle,
            endAngle: currentAngle + angle,
            color: CATEGORY_COLORS[d.category] || "#737373",
        });
        currentAngle += angle;
    });

    const toRad = (deg: number) => (deg * Math.PI) / 180;
    const arcPath = (cx: number, cy: number, r: number, start: number, end: number) => {
        const s = { x: cx + r * Math.cos(toRad(start)), y: cy + r * Math.sin(toRad(start)) };
        const e = { x: cx + r * Math.cos(toRad(end)), y: cy + r * Math.sin(toRad(end)) };
        const large = end - start > 180 ? 1 : 0;
        return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
    };

    const hoveredSlice = hovered !== null ? slices[hovered] : null;

    return (
        <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6">
            <div className="relative flex-shrink-0">
                <svg viewBox="0 0 200 200" className="w-36 h-36 sm:w-48 sm:h-48">
                    {slices.map((sl, i) => (
                        <path
                            key={i}
                            d={arcPath(100, 100, 80, sl.startAngle, sl.endAngle - 0.5)}
                            fill="none"
                            stroke={sl.color}
                            strokeWidth={hovered === i ? "34" : "28"}
                            strokeLinecap="round"
                            className="transition-all duration-200 cursor-pointer"
                            style={{ opacity: hovered !== null && hovered !== i ? 0.4 : 1 }}
                            onMouseEnter={() => setHovered(i)}
                            onMouseLeave={() => setHovered(null)}
                        />
                    ))}
                    <text x="100" y="95" textAnchor="middle" className="fill-foreground text-lg font-bold" fontSize="18">
                        {hoveredSlice ? formatCurrency(hoveredSlice.total) : formatCurrency(total)}
                    </text>
                    <text x="100" y="115" textAnchor="middle" className="fill-muted-foreground" fontSize="11">
                        {hoveredSlice ? (CATEGORY_LABELS[hoveredSlice.category] || hoveredSlice.category) : "Total Spent"}
                    </text>
                </svg>
                {/* Tooltip */}
                {hoveredSlice && (
                    <div className="absolute -top-2 left-1/2 -translate-x-1/2 -translate-y-full bg-popover text-popover-foreground border rounded-lg px-3 py-2 shadow-lg text-sm whitespace-nowrap z-20 pointer-events-none">
                        <p className="font-semibold">{CATEGORY_LABELS[hoveredSlice.category] || hoveredSlice.category}</p>
                        <p>{formatCurrency(hoveredSlice.total)} · {Math.round((hoveredSlice.total / total) * 100)}%</p>
                    </div>
                )}
            </div>
            <div className="grid grid-cols-2 gap-x-4 sm:gap-x-6 gap-y-2 text-sm w-full sm:w-auto">
                {data.slice(0, 8).map((d, i) => (
                    <Link
                        key={d.category}
                        href={`/personal/transactions?category=${d.category}`}
                        className={`flex items-center gap-2 cursor-pointer rounded-md px-1 py-0.5 transition-colors hover:bg-secondary ${hovered === i ? 'bg-secondary' : ''}`}
                        onMouseEnter={() => setHovered(i)}
                        onMouseLeave={() => setHovered(null)}
                    >
                        <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: CATEGORY_COLORS[d.category] || "#737373" }} />
                        <span className="text-muted-foreground truncate">{CATEGORY_LABELS[d.category] || d.category}</span>
                        <span className="font-medium ml-auto">{Math.round((d.total / total) * 100)}%</span>
                    </Link>
                ))}
            </div>
        </div>
    );
}

// ─── Bar Chart ──────────────────────────────────────────────────────────────
function MonthlyBarChart({ data }: { data: { month: string; income: number; expense: number }[] }) {
    const maxVal = Math.max(...data.map(m => Math.max(m.income, m.expense)), 1);
    return (
        <div className="space-y-4">
            <div className="flex items-end gap-3 h-48">
                {data.slice(-6).map(month => {
                    const incH = (month.income / maxVal) * 100;
                    const expH = (month.expense / maxVal) * 100;
                    return (
                        <div key={month.month} className="flex-1 flex flex-col items-center gap-1">
                            <div className="flex gap-1 h-40 items-end w-full justify-center">
                                <div
                                    className="w-[40%] max-w-5 bg-emerald-500 rounded-t-md transition-all duration-700"
                                    style={{ height: `${incH}%` }}
                                    title={`Income: ${formatCurrency(month.income)}`}
                                />
                                <div
                                    className="w-[40%] max-w-5 bg-rose-500 rounded-t-md transition-all duration-700"
                                    style={{ height: `${expH}%` }}
                                    title={`Expense: ${formatCurrency(month.expense)}`}
                                />
                            </div>
                            <span className="text-xs text-muted-foreground">
                                {new Date(month.month + "-01").toLocaleDateString("en-US", { month: "short" })}
                            </span>
                        </div>
                    );
                })}
            </div>
            <div className="flex justify-center gap-6 text-sm">
                <div className="flex items-center gap-2"><div className="w-3 h-3 bg-emerald-500 rounded" /><span className="text-muted-foreground">Income</span></div>
                <div className="flex items-center gap-2"><div className="w-3 h-3 bg-rose-500 rounded" /><span className="text-muted-foreground">Expenses</span></div>
            </div>
        </div>
    );
}

// ─── Circular Gauge ─────────────────────────────────────────────────────────
function SavingsGauge({ rate }: { rate: number }) {
    const clamped = Math.max(0, Math.min(100, rate));
    const circumference = 2 * Math.PI * 40;
    const offset = circumference - (clamped / 100) * circumference;
    const color = clamped >= 20 ? "#10b981" : clamped >= 10 ? "#f59e0b" : "#ef4444";

    return (
        <div className="flex flex-col items-center">
            <svg viewBox="0 0 100 100" className="w-28 h-28">
                <circle cx="50" cy="50" r="40" fill="none" stroke="currentColor" strokeWidth="8" className="text-muted/30" />
                <circle cx="50" cy="50" r="40" fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
                    strokeDasharray={circumference} strokeDashoffset={offset}
                    className="transition-all duration-1000" transform="rotate(-90 50 50)" />
                <text x="50" y="48" textAnchor="middle" className="fill-foreground font-bold" fontSize="16">{Math.round(clamped)}%</text>
                <text x="50" y="62" textAnchor="middle" className="fill-muted-foreground" fontSize="8">saved</text>
            </svg>
        </div>
    );
}

// ─── Top Spending Categories ────────────────────────────────────────────────
function TopSpendingWidget({ data, range }: { data: { category: string; total: number }[]; range: string }) {
    const [showAll, setShowAll] = useState(false);
    const total = data.reduce((s, d) => s + d.total, 0);
    if (!data.length) return <p className="text-muted-foreground text-sm py-4 text-center">No spending data for this period.</p>;

    const display = showAll ? data : data.slice(0, 5);
    const maxSpend = data[0]?.total ?? 1;

    return (
        <div className="space-y-3">
            {display.map((d, i) => {
                const pct = total > 0 ? Math.round((d.total / total) * 100) : 0;
                const barW = (d.total / maxSpend) * 100;
                return (
                    <Link
                        key={d.category}
                        href={`/personal/transactions?category=${d.category}`}
                        className="group flex items-center gap-3 p-2 rounded-xl hover:bg-secondary/60 transition-colors"
                    >
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-base flex-shrink-0"
                            style={{ backgroundColor: `${CATEGORY_COLORS[d.category] || "#737373"}20` }}>
                            <span role="img">{CATEGORY_EMOJIS[d.category] || "📦"}</span>
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-baseline mb-1">
                                <span className="text-sm font-medium truncate">{CATEGORY_LABELS[d.category] || d.category}</span>
                                <span className="text-sm font-semibold ml-2 flex-shrink-0">{formatCurrency(d.total)}</span>
                            </div>
                            <div className="h-1.5 bg-secondary/80 rounded-full overflow-hidden">
                                <div
                                    className="h-full rounded-full transition-all duration-700"
                                    style={{
                                        width: `${barW}%`,
                                        backgroundColor: CATEGORY_COLORS[d.category] || "#737373",
                                    }}
                                />
                            </div>
                        </div>
                        <span className="text-xs text-muted-foreground w-10 text-right flex-shrink-0">{pct}%</span>
                    </Link>
                );
            })}
            {data.length > 5 && (
                <button
                    onClick={() => setShowAll(!showAll)}
                    className="w-full text-center text-sm text-primary hover:underline flex items-center justify-center gap-1 py-2"
                >
                    {showAll ? "Show Less" : `See All ${data.length} Categories`}
                    <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showAll ? "rotate-180" : ""}`} />
                </button>
            )}
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════════════════════════════
export default function PersonalDashboard() {
    // ── State ──
    const [chartRange, setChartRange] = useState<TimeRange>("month");
    const chartDates = getDateRange(chartRange);

    // ── Data fetching ──
    const { data: summaryData } = useQuery({ queryKey: ["personal", "summary"], queryFn: () => api.personal.getSummary() });
    const { data: insights, isLoading } = useQuery({ queryKey: ["personal", "insights"], queryFn: () => api.personal.getInsights() });
    const { data: breakdownData } = useQuery({
        queryKey: ["personal", "breakdown", chartRange],
        queryFn: () => api.personal.getCategoryBreakdown(chartDates.start, chartDates.end),
    });
    const { data: trendsData } = useQuery({ queryKey: ["personal", "trends"], queryFn: () => api.personal.getTrends(12) });
    const { data: topSpendingData } = useQuery({
        queryKey: ["personal", "top-spending", chartRange],
        queryFn: () => api.personal.getCategoryBreakdown(chartDates.start, chartDates.end),
    });
    const { data: incomeBreakdown } = useQuery({
        queryKey: ["personal", "income-breakdown"],
        queryFn: () => api.personal.getCategoryBreakdown(undefined, undefined, "income"),
    });
    const { data: recentEntries } = useQuery({
        queryKey: ["personal", "recent-entries"],
        queryFn: () => api.personal.listEntries({ limit: 50 }),
    });

    // ── Derived values ──
    const income = summaryData?.income ?? 0;
    const expense = summaryData?.expense ?? 0;
    const remaining = summaryData?.net ?? 0;
    const savingsRate = income > 0 ? (remaining / income) * 100 : 0;
    const today = new Date();
    const daysPassed = today.getDate();
    const dailyBurn = daysPassed > 0 ? expense / daysPassed : 0;

    // Expense velocity: projected vs. last month
    const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
    const projectedMonthly = dailyBurn * daysInMonth;

    // Largest single expense this month
    const largestExpense = useMemo(() => {
        if (!recentEntries) return null;
        const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
        const expenses = recentEntries.filter(
            e => e.entry_type === "expense" && new Date(e.entry_date) >= monthStart
        );
        if (!expenses.length) return null;
        return expenses.reduce((max, e) => e.amount > max.amount ? e : max, expenses[0]!);
    }, [recentEntries]);

    // Streak: days since last expense
    const streakDays = useMemo(() => {
        if (!recentEntries) return 0;
        const lastExpense = recentEntries.find(e => e.entry_type === "expense");
        if (!lastExpense) return 0;
        const diff = Math.floor((today.getTime() - new Date(lastExpense.entry_date).getTime()) / (1000 * 60 * 60 * 24));
        return diff;
    }, [recentEntries]);

    // ── Phrases (memoized per mount) ──
    const greeting = useMemo(() => pickRandom(GREETINGS), []);
    const netMessage = useMemo(() => remaining >= 0 ? pickRandom(POSITIVE_NET) : pickRandom(NEGATIVE_NET), [remaining]);
    const insightMessage = useMemo(() => {
        if (!insights?.top_category) return null;
        const tmpl = pickRandom(INSIGHT_TEMPLATES);
        return tmpl
            .replace("{category}", CATEGORY_LABELS[insights.top_category] || insights.top_category)
            .replace("{amount}", formatCurrency(insights.top_category_amount));
    }, [insights]);

    // ── Bucket cards config ──
    const buckets = [
        { href: "/personal/transactions", label: "Transactions", desc: "Log entries and view history", icon: <CreditCard className="w-6 h-6" />, color: "cyan" },
        { href: "/personal/flow", label: "The Flow", desc: "Visualize where your money goes", icon: <Activity className="w-6 h-6" />, color: "blue" },
        { href: "/personal/planning", label: "Planning", desc: "Plan trips & big purchases", icon: <Target className="w-6 h-6" />, color: "amber" },
        { href: "/personal/budgets", label: "Budgeting", desc: "Set monthly spending limits", icon: <PieChartIcon className="w-6 h-6" />, color: "green" },
        { href: "/personal/chat", label: "Ask AI", desc: "Get financial advice & insights", icon: <MessageSquare className="w-6 h-6" />, color: "yellow" },
        { href: "/personal/merchants", label: "Merchant DNA", desc: "Deep dive into spending habits", icon: <Sparkles className="w-6 h-6" />, color: "pink" },
    ];

    const bucketColors: Record<string, { border: string; bg: string; text: string; iconBg: string }> = {
        cyan: { border: "hover:border-cyan-500/50", bg: "from-cyan-500/10 to-blue-500/5", text: "text-cyan-400", iconBg: "bg-cyan-500/20" },
        blue: { border: "hover:border-blue-500/50", bg: "from-blue-500/10 to-indigo-500/5", text: "text-blue-400", iconBg: "bg-blue-500/20" },
        amber: { border: "hover:border-amber-500/50", bg: "from-amber-500/10 to-orange-500/5", text: "text-amber-400", iconBg: "bg-amber-500/20" },
        green: { border: "hover:border-green-500/50", bg: "from-green-500/10 to-emerald-500/5", text: "text-green-400", iconBg: "bg-green-500/20" },
        yellow: { border: "hover:border-yellow-500/50", bg: "from-yellow-500/10 to-orange-500/5", text: "text-yellow-400", iconBg: "bg-yellow-500/20" },
        pink: { border: "hover:border-pink-500/50", bg: "from-pink-500/10 to-rose-500/5", text: "text-pink-400", iconBg: "bg-pink-500/20" },
    };

    return (
        <div className="space-y-10 animate-in fade-in duration-500">
            {/* ───── GREETING ───── */}
            <section className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div>
                    <h1 className="text-2xl sm:text-4xl font-bold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
                        {isLoading ? "Loading..." : greeting}
                    </h1>
                    <p className="text-muted-foreground mt-1.5 sm:mt-2 text-base sm:text-lg">{netMessage}</p>
                </div>
            </section>

            {/* ───── 3 STAT CARDS ───── */}
            <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* Income */}
                <div className="rounded-2xl border bg-card p-4 sm:p-6 flex items-center gap-3 sm:gap-4 shadow-sm hover:shadow-md transition-shadow">
                    <div className="w-11 h-11 sm:w-14 sm:h-14 rounded-2xl bg-emerald-500/15 flex items-center justify-center flex-shrink-0">
                        <ArrowUpRight className="w-5 h-5 sm:w-7 sm:h-7 text-emerald-500" />
                    </div>
                    <div>
                        <p className="text-xs sm:text-sm text-muted-foreground font-medium">Income</p>
                        <p className="text-xl sm:text-2xl font-bold text-emerald-500">{formatCurrency(income)}</p>
                        <p className="text-xs text-muted-foreground mt-0.5 hidden sm:block">This month&apos;s total earnings</p>
                    </div>
                </div>
                {/* Expense */}
                <div className="rounded-2xl border bg-card p-4 sm:p-6 flex items-center gap-3 sm:gap-4 shadow-sm hover:shadow-md transition-shadow">
                    <div className="w-11 h-11 sm:w-14 sm:h-14 rounded-2xl bg-rose-500/15 flex items-center justify-center flex-shrink-0">
                        <ArrowDownRight className="w-5 h-5 sm:w-7 sm:h-7 text-rose-500" />
                    </div>
                    <div>
                        <p className="text-xs sm:text-sm text-muted-foreground font-medium">Expenses</p>
                        <p className="text-xl sm:text-2xl font-bold text-rose-500">{formatCurrency(expense)}</p>
                        <p className="text-xs text-muted-foreground mt-0.5 hidden sm:block">Total spent this month</p>
                    </div>
                </div>
                {/* Remaining */}
                <div className="rounded-2xl border bg-card p-4 sm:p-6 flex items-center gap-3 sm:gap-4 shadow-sm hover:shadow-md transition-shadow">
                    <div className={`w-11 h-11 sm:w-14 sm:h-14 rounded-2xl flex items-center justify-center flex-shrink-0 ${remaining >= 0 ? "bg-blue-500/15" : "bg-orange-500/15"}`}>
                        <Wallet className={`w-5 h-5 sm:w-7 sm:h-7 ${remaining >= 0 ? "text-blue-500" : "text-orange-500"}`} />
                    </div>
                    <div>
                        <p className="text-xs sm:text-sm text-muted-foreground font-medium">Remaining</p>
                        <p className={`text-xl sm:text-2xl font-bold ${remaining >= 0 ? "text-blue-500" : "text-orange-500"}`}>{formatCurrency(remaining)}</p>
                        <p className="text-xs text-muted-foreground mt-0.5 hidden sm:block">{remaining >= 0 ? "Available balance" : "Over budget"}</p>
                    </div>
                </div>
            </section>

            {/* ───── CHARTS ROW ───── */}
            <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Pie Chart with Time Range */}
                <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm">
                    <div className="flex items-center justify-between mb-1">
                        <h2 className="text-lg font-semibold">Where Your Money Goes</h2>
                        <TimeRangeSelector value={chartRange} onChange={setChartRange} />
                    </div>
                    <p className="text-sm text-muted-foreground mb-5">Expense breakdown · {chartDates.label}</p>
                    {breakdownData?.breakdown && breakdownData.breakdown.length > 0 ? (
                        <DonutChart data={breakdownData.breakdown} />
                    ) : (
                        <p className="text-muted-foreground text-sm py-8 text-center">No spending data yet — log some transactions to see your breakdown.</p>
                    )}
                </div>

                {/* Top Spending Categories */}
                <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm">
                    <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                            <Trophy className="w-5 h-5 text-amber-500" />
                            <h2 className="text-lg font-semibold">Top Spending</h2>
                        </div>
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">Your biggest spending categories · {chartDates.label}. Tap a category to see its transactions.</p>
                    <TopSpendingWidget
                        data={topSpendingData?.breakdown ?? []}
                        range={chartDates.label}
                    />
                </div>
            </section>

            {/* ───── MONTHLY TRENDS ───── */}
            <section className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm">
                <h2 className="text-lg font-semibold mb-1">Monthly Income vs. Expenses</h2>
                <p className="text-sm text-muted-foreground mb-5">Compare your earning and spending patterns month-over-month.</p>
                {trendsData?.trends && trendsData.trends.length > 0 ? (
                    <MonthlyBarChart data={trendsData.trends} />
                ) : (
                    <p className="text-muted-foreground text-sm py-8 text-center">Keep logging entries to see your monthly trends appear here.</p>
                )}
            </section>

            {/* ───── WEEKLY INSIGHTS ───── */}
            <section className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center">
                        <Zap className="w-5 h-5 text-purple-500" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold">Weekly Insights</h2>
                        <p className="text-sm text-muted-foreground">A quick pulse on how your week went financially.</p>
                    </div>
                </div>
                {insights ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        {/* Week expense */}
                        <div className="rounded-xl bg-secondary/50 p-4">
                            <p className="text-xs text-muted-foreground mb-1">This Week&apos;s Spending</p>
                            <p className="text-xl font-bold">{formatCurrency(insights.this_week_expense)}</p>
                            <div className={`flex items-center gap-1 text-sm mt-1 ${insights.week_change_percent <= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                                {insights.week_change_percent <= 0 ? <TrendingDown className="w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
                                <span>{Math.abs(insights.week_change_percent).toFixed(0)}% vs last week</span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-2">
                                {insights.week_change_percent <= 0
                                    ? "You spent less than last week — great discipline! 👏"
                                    : "Spending ticked up compared to last week — worth keeping an eye on."}
                            </p>
                        </div>
                        {/* Week income */}
                        <div className="rounded-xl bg-secondary/50 p-4">
                            <p className="text-xs text-muted-foreground mb-1">This Week&apos;s Income</p>
                            <p className="text-xl font-bold text-emerald-500">{formatCurrency(insights.this_week_income)}</p>
                            <p className="text-xs text-muted-foreground mt-2">All income received in the current week.</p>
                        </div>
                        {/* Top category */}
                        <div className="rounded-xl bg-secondary/50 p-4">
                            <p className="text-xs text-muted-foreground mb-1">Top Category</p>
                            <p className="text-xl font-bold">{CATEGORY_LABELS[insights.top_category || ""] || insights.top_category || "—"}</p>
                            <p className="text-sm text-muted-foreground">{formatCurrency(insights.top_category_amount)}</p>
                            {insightMessage && <p className="text-xs text-muted-foreground mt-2">{insightMessage}</p>}
                        </div>
                        {/* Month net */}
                        <div className="rounded-xl bg-secondary/50 p-4">
                            <p className="text-xs text-muted-foreground mb-1">Month Net</p>
                            <p className={`text-xl font-bold ${insights.this_month_net >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                                {formatCurrency(insights.this_month_net)}
                            </p>
                            <p className="text-xs text-muted-foreground mt-2">
                                {insights.this_month_net >= 0
                                    ? "Positive net — you're saving money this month! 🎯"
                                    : "Negative net — expenses are outweighing income. 📉"}
                            </p>
                        </div>
                    </div>
                ) : (
                    <p className="text-muted-foreground text-sm">Loading insights...</p>
                )}
            </section>

            {/* ───── ADVANCED ANALYTICS ───── */}
            <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
                {/* Savings Rate */}
                <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm text-center">
                    <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center justify-center gap-2">
                        <Percent className="w-4 h-4" /> Savings Rate
                    </h3>
                    <SavingsGauge rate={savingsRate} />
                    <p className="text-xs text-muted-foreground mt-3">
                        {savingsRate >= 20
                            ? "Excellent! Saving more than 20% 🎯"
                            : savingsRate >= 10
                                ? "Decent — try to push above 20%"
                                : "Low savings — reduce non-essentials"}
                    </p>
                </div>
                {/* Daily Burn Rate */}
                <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm text-center">
                    <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center justify-center gap-2">
                        <Flame className="w-4 h-4" /> Daily Burn
                    </h3>
                    <p className="text-3xl font-bold mt-4 mb-1">{formatCurrency(dailyBurn)}</p>
                    <p className="text-sm text-muted-foreground">per day</p>
                    <p className="text-xs text-muted-foreground mt-2">
                        Projected: {formatCurrency(projectedMonthly)}/mo
                    </p>
                </div>
                {/* Largest Transaction */}
                <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm text-center">
                    <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center justify-center gap-2">
                        <BarChart3 className="w-4 h-4" /> Biggest Expense
                    </h3>
                    {largestExpense ? (
                        <>
                            <p className="text-3xl font-bold mt-4 mb-1 text-rose-500">{formatCurrency(largestExpense.amount)}</p>
                            <p className="text-sm font-medium truncate">{largestExpense.vendor || largestExpense.description || largestExpense.category}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                                <span role="img">{CATEGORY_EMOJIS[largestExpense.category] || "📦"}</span>{" "}
                                {CATEGORY_LABELS[largestExpense.category] || largestExpense.category}
                            </p>
                        </>
                    ) : (
                        <p className="text-muted-foreground text-sm mt-6">No expenses yet</p>
                    )}
                </div>
                {/* Spending Streak */}
                <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm text-center">
                    <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center justify-center gap-2">
                        <Zap className="w-4 h-4" /> No-Spend Streak
                    </h3>
                    <p className="text-3xl font-bold mt-4 mb-1">
                        {streakDays} <span className="text-lg font-normal text-muted-foreground">day{streakDays !== 1 ? "s" : ""}</span>
                    </p>
                    <p className="text-xs text-muted-foreground mt-2">
                        {streakDays >= 3
                            ? "Impressive self-control! 🔥"
                            : streakDays >= 1
                                ? "Keep going! Every day counts 💪"
                                : "Start a streak — skip spending today!"}
                    </p>
                </div>
            </section>

            {/* ───── INCOME SOURCES ───── */}
            {incomeBreakdown?.breakdown && incomeBreakdown.breakdown.length > 0 && (
                <section className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm">
                    <h2 className="text-lg font-semibold mb-1">Income Sources</h2>
                    <p className="text-sm text-muted-foreground mb-4">Where your money comes from this month.</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {incomeBreakdown.breakdown.map(d => {
                            const total = incomeBreakdown.breakdown.reduce((s, x) => s + x.total, 0);
                            const pct = total > 0 ? Math.round((d.total / total) * 100) : 0;
                            return (
                                <div key={d.category} className="flex items-center gap-3 p-3 rounded-xl bg-secondary/40">
                                    <div className="w-10 h-10 rounded-lg flex items-center justify-center text-lg"
                                        style={{ backgroundColor: `${CATEGORY_COLORS[d.category] || "#737373"}20` }}>
                                        <span role="img">{CATEGORY_EMOJIS[d.category] || "💵"}</span>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium truncate">{CATEGORY_LABELS[d.category] || d.category}</p>
                                        <p className="text-lg font-bold text-emerald-500">{formatCurrency(d.total)}</p>
                                    </div>
                                    <span className="text-sm font-semibold text-muted-foreground">{pct}%</span>
                                </div>
                            );
                        })}
                    </div>
                </section>
            )}

            {/* ───── MONTHLY TREND (compact) ───── */}
            <section className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
                {/* Monthly Trend */}
                <div className="rounded-2xl border bg-card p-4 sm:p-6 shadow-sm text-center sm:col-span-3">
                    <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center justify-center gap-2">
                        <Activity className="w-4 h-4" /> Monthly Trend (Compact)
                    </h3>
                    {trendsData?.trends && trendsData.trends.length >= 2 ? (() => {
                        const recent = trendsData.trends.slice(-6);
                        const maxV = Math.max(...recent.map(m => Math.max(m.income, m.expense)), 1);
                        return (
                            <div className="mt-4 space-y-2 max-w-xl mx-auto">
                                {recent.map(m => (
                                    <div key={m.month} className="flex items-center gap-2 text-xs">
                                        <span className="w-12 text-muted-foreground text-right">
                                            {new Date(m.month + "-01").toLocaleDateString("en-US", { month: "short" })}
                                        </span>
                                        <div className="flex-1 flex gap-0.5 h-3">
                                            <div className="bg-emerald-500 rounded-l" style={{ width: `${(m.income / maxV) * 100}%` }} />
                                            <div className="bg-rose-500 rounded-r" style={{ width: `${(m.expense / maxV) * 100}%` }} />
                                        </div>
                                        <span className="w-20 text-muted-foreground text-right">
                                            {formatCurrency(m.income - m.expense)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        );
                    })() : (
                        <p className="text-muted-foreground text-sm mt-6">Need at least 2 months of data.</p>
                    )}
                </div>
            </section>

            {/* ───── NAVIGATION BUCKETS ───── */}
            <section>
                <h2 className="text-2xl font-bold mb-6">Explore</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {buckets.map(bucket => {
                        const c = bucketColors[bucket.color] ?? { border: "", bg: "", text: "", iconBg: "" };
                        return (
                            <Link
                                key={bucket.href}
                                href={bucket.href}
                                className={`group relative overflow-hidden rounded-2xl border bg-card ${c.border} transition-all p-5 sm:p-6 flex flex-col justify-between min-h-[160px] sm:min-h-[180px] shadow-sm hover:shadow-lg`}
                            >
                                <div className={`absolute inset-0 bg-gradient-to-br ${c.bg} opacity-0 group-hover:opacity-100 transition-opacity`} />
                                <div className="relative z-10">
                                    <div className={`w-11 h-11 rounded-xl ${c.iconBg} flex items-center justify-center ${c.text} mb-4 group-hover:scale-110 transition-transform`}>
                                        {bucket.icon}
                                    </div>
                                    <h3 className="text-xl font-bold mb-1">{bucket.label}</h3>
                                    <p className="text-muted-foreground text-sm">{bucket.desc}</p>
                                </div>
                                <div className={`relative z-10 flex items-center gap-2 ${c.text} font-medium mt-4 text-sm group-hover:translate-x-2 transition-transform`}>
                                    Open <ArrowRight className="w-4 h-4" />
                                </div>
                            </Link>
                        );
                    })}
                </div>
            </section>
        </div>
    );
}
