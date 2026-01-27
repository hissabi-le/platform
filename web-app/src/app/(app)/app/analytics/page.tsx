"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

import { api } from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { ErrorAlert } from "@/components/Alert";
import { ChartSkeleton, CardSkeleton } from "@/components/Skeleton";
import { formatCurrency, formatPercent } from "@/lib/format";

const RANGE_OPTIONS = ["1y", "6m", "3m", "1m"] as const;
type RangeOption = (typeof RANGE_OPTIONS)[number];

const RANGE_LABELS: Record<RangeOption, string> = {
  "1y": "Last 12 months",
  "6m": "Last 6 months",
  "3m": "Last 3 months",
  "1m": "Last 30 days",
};

export default function AnalyticsPage() {
  const [range, setRange] = useState<RangeOption>("3m");
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["analytics-detail", range],
    queryFn: () => api.analytics.pnl(range),
  });

  const formattedSeries = useMemo(() => {
    const series = data?.series ?? [];
    return series.map((row) => ({
      ...row,
      label: format(parseISO(row.date), "MMM dd"),
      profit: row.revenue - row.expenses,
    }));
  }, [data?.series]);

  const margin = data?.revenue ? (data.profit / data.revenue) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Analytics</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track your financial performance over time
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="range" className="text-sm text-slate-600">
            Time period:
          </label>
          <select
            id="range"
            value={range}
            onChange={(e) => setRange(e.target.value as RangeOption)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
          >
            {RANGE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {RANGE_LABELS[option]}
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* Error State */}
      {error && <ErrorAlert error={error} onRetry={() => refetch()} />}

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
          <ChartSkeleton />
        </div>
      )}

      {/* Data Display */}
      {data && (
        <>
          {/* KPI Cards */}
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Total Revenue"
              value={formatCurrency(data.revenue)}
              accent="bg-emerald-500"
            />
            <StatCard
              title="Total Expenses"
              value={formatCurrency(data.expenses)}
              accent="bg-rose-500"
            />
            <StatCard
              title="Net Profit"
              value={formatCurrency(data.profit)}
              accent="bg-slate-900"
            />
            <StatCard
              title="Profit Margin"
              value={formatPercent(margin)}
              accent="bg-amber-500"
            />
          </section>

          {/* Revenue vs Expenses Chart */}
          <section className="rounded-xl border bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="font-semibold text-slate-900">Revenue vs Expenses</h2>
                <p className="text-sm text-slate-500">Trend over {RANGE_LABELS[range].toLowerCase()}</p>
              </div>
            </div>
            {formattedSeries.length === 0 ? (
              <div className="flex items-center justify-center h-64 text-slate-500">
                <p>Upload data to visualize trends</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={formattedSeries} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
                    </linearGradient>
                    <linearGradient id="colorExpenses" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 12, fill: "#64748b" }}
                    tickLine={false}
                    axisLine={{ stroke: "#e2e8f0" }}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: "#64748b" }}
                    tickLine={false}
                    axisLine={{ stroke: "#e2e8f0" }}
                    tickFormatter={(v) => `$${v}`}
                  />
                  <Tooltip
                    formatter={(value) => [formatCurrency(Number(value))]}
                    contentStyle={{
                      borderRadius: 8,
                      border: "1px solid #e2e8f0",
                      boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                    }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#10b981"
                    strokeWidth={2}
                    fill="url(#colorRevenue)"
                    name="Revenue"
                  />
                  <Area
                    type="monotone"
                    dataKey="expenses"
                    stroke="#f43f5e"
                    strokeWidth={2}
                    fill="url(#colorExpenses)"
                    name="Expenses"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </section>

          {/* Profit Bar Chart */}
          <section className="rounded-xl border bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="font-semibold text-slate-900">Net Profit by Period</h2>
                <p className="text-sm text-slate-500">Monthly profit/loss breakdown</p>
              </div>
            </div>
            {formattedSeries.length === 0 ? (
              <div className="flex items-center justify-center h-48 text-slate-500">
                <p>No data available</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={formattedSeries} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 12, fill: "#64748b" }}
                    tickLine={false}
                    axisLine={{ stroke: "#e2e8f0" }}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: "#64748b" }}
                    tickLine={false}
                    axisLine={{ stroke: "#e2e8f0" }}
                    tickFormatter={(v) => `$${v}`}
                  />
                  <Tooltip
                    formatter={(value) => [formatCurrency(Number(value)), "Net Profit"]}
                    contentStyle={{
                      borderRadius: 8,
                      border: "1px solid #e2e8f0",
                      boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)"
                    }}
                  />
                  <Bar
                    dataKey="profit"
                    fill="#0f172a"
                    radius={[4, 4, 0, 0]}
                    name="Net Profit"
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </section>

          {/* Period Details Table */}
          <section className="rounded-xl border bg-white shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b">
              <h2 className="font-semibold text-slate-900">Period Details</h2>
            </div>
            {formattedSeries.length === 0 ? (
              <div className="p-6 text-center text-slate-500">
                No periods available yet
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr className="text-left text-xs uppercase text-slate-500">
                      <th className="px-6 py-3 font-medium">Period</th>
                      <th className="px-6 py-3 font-medium text-right">Revenue</th>
                      <th className="px-6 py-3 font-medium text-right">Expenses</th>
                      <th className="px-6 py-3 font-medium text-right">Profit</th>
                      <th className="px-6 py-3 font-medium text-right">Margin</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {formattedSeries.map((row) => {
                      const periodMargin = row.revenue ? (row.profit / row.revenue) * 100 : 0;
                      return (
                        <tr key={row.label} className="hover:bg-slate-50 transition-colors">
                          <td className="px-6 py-4 font-medium text-slate-900">{row.label}</td>
                          <td className="px-6 py-4 text-right text-emerald-600">
                            {formatCurrency(row.revenue)}
                          </td>
                          <td className="px-6 py-4 text-right text-rose-600">
                            {formatCurrency(row.expenses)}
                          </td>
                          <td className={`px-6 py-4 text-right font-medium ${row.profit >= 0 ? "text-slate-900" : "text-rose-600"}`}>
                            {formatCurrency(row.profit)}
                          </td>
                          <td className="px-6 py-4 text-right text-slate-600">
                            {formatPercent(periodMargin)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
