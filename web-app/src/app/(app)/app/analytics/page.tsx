"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";

import { api } from "@/lib/api";

const RANGE_OPTIONS = ["1y", "6m", "3m", "1m"] as const;
type RangeOption = (typeof RANGE_OPTIONS)[number];

export default function AnalyticsPage(): JSX.Element {
  const [range, setRange] = useState<RangeOption>("3m");
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-detail", range],
    queryFn: () => api.analytics.pnl(range),
  });

  const formattedSeries = useMemo(() => {
    const series = data?.series ?? [];
    return series.map((row) => ({
      ...row,
      label: format(parseISO(row.date), "dd/MM/yy"),
      profit: row.revenue - row.expenses,
    }));
  }, [data?.series]);

  const maxLineValue = useMemo(() => {
    if (!formattedSeries.length) return 1;
    return Math.max(
      ...formattedSeries.map((row) => Math.max(row.revenue, row.expenses, 1))
    );
  }, [formattedSeries]);

  const maxProfit = useMemo(() => {
    if (!formattedSeries.length) return 1;
    return Math.max(...formattedSeries.map((row) => Math.abs(row.profit)), 1);
  }, [formattedSeries]);

  const margin = data?.revenue ? ((data.profit / data.revenue) * 100).toFixed(2) : "0.00";

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Analytics</h1>
          <p className="text-sm text-gray-500">
            Deep dive into revenue, expenses, profit, and margin trends.
          </p>
        </div>
        <select
          value={range}
          onChange={(event) => setRange(event.target.value as RangeOption)}
          className="ml-auto rounded border px-3 py-2 text-sm"
        >
          {RANGE_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option.toUpperCase()}
            </option>
          ))}
        </select>
      </header>

  {isLoading && <p className="text-sm text-gray-500">Loading analytics…</p>}

      {data && (
        <>
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <AnalyticsCard title="Revenue" value={`$${data.revenue.toFixed(2)}`} accent="bg-emerald-500" />
            <AnalyticsCard title="Expenses" value={`$${data.expenses.toFixed(2)}`} accent="bg-rose-500" />
            <AnalyticsCard title="Net profit" value={`$${data.profit.toFixed(2)}`} accent="bg-slate-900" />
            <AnalyticsCard title="Margin" value={`${margin}%`} accent="bg-amber-500" />
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between text-sm text-gray-500">
                <span>Revenue vs expenses</span>
              </div>
              <div className="mt-4 flex items-end gap-4">
                {formattedSeries.length === 0 ? (
                  <p className="text-sm text-gray-500">Upload data to visualise trends across periods.</p>
                ) : (
                  formattedSeries.map((period) => {
                    const revenueHeight = Math.round((period.revenue / maxLineValue) * 100);
                    const expenseHeight = Math.round((period.expenses / maxLineValue) * 100);
                    return (
                      <div key={`line-${period.label}`} className="flex flex-1 flex-col items-center">
                        <div className="flex h-40 w-full items-end justify-between overflow-hidden rounded bg-gray-100">
                          <div
                            className="ml-1 w-1/2 rounded-t bg-emerald-500"
                            style={{ height: `${revenueHeight}%` }}
                            title={`Revenue $${period.revenue.toFixed(2)}`}
                          ></div>
                          <div
                            className="mr-1 w-1/2 rounded-t bg-rose-500"
                            style={{ height: `${expenseHeight}%` }}
                            title={`Expenses $${period.expenses.toFixed(2)}`}
                          ></div>
                        </div>
                        <div className="mt-2 text-xs text-gray-500">{period.label}</div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            <div className="rounded-xl border bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between text-sm text-gray-500">
                <span>Net profit vs margin</span>
              </div>
              <div className="mt-4 space-y-3">
                {formattedSeries.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    Once you log revenue/costs you will see period-by-period profit bars.
                  </p>
                ) : (
                  formattedSeries.map((period) => {
                    const profit = period.profit;
                    const height = Math.round((Math.abs(profit) / maxProfit) * 100);
                    const periodMargin = period.revenue
                      ? ((profit / period.revenue) * 100).toFixed(1)
                      : "0.0";
                    return (
                      <div key={`profit-${period.label}`} className="space-y-1">
                        <div className="flex justify-between text-xs text-gray-500">
                          <span>{period.label}</span>
                          <span>{profit >= 0 ? "Profit" : "Loss"} ${profit.toFixed(2)}</span>
                        </div>
                        <div className="flex h-16 items-end overflow-hidden rounded bg-gray-100">
                          <div
                            className={`${profit >= 0 ? "bg-emerald-500" : "bg-rose-500"} w-full`}
                            style={{ height: `${height}%` }}
                          ></div>
                        </div>
                        <div className="text-xs text-gray-500">Margin: {periodMargin}%</div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </section>

          <section className="rounded-xl border bg-white p-6 shadow-sm">
            <header className="mb-3 text-sm font-medium text-gray-600">Period details</header>
            {formattedSeries.length === 0 ? (
              <p className="text-sm text-gray-500">No periods available yet.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-gray-500">
                    <th className="pb-2">Period</th>
                    <th className="pb-2 text-right">Revenue</th>
                    <th className="pb-2 text-right">Expenses</th>
                    <th className="pb-2 text-right">Profit</th>
                    <th className="pb-2 text-right">Margin</th>
                  </tr>
                </thead>
                <tbody>
                  {formattedSeries.map((row) => {
                    const profit = row.profit;
                    const periodMargin = row.revenue
                      ? `${((profit / row.revenue) * 100).toFixed(2)}%`
                      : "0.00%";
                    return (
                      <tr key={`table-${row.label}`} className="border-t text-sm">
                        <td className="py-2">{row.label}</td>
                        <td className="py-2 text-right">${row.revenue.toFixed(2)}</td>
                        <td className="py-2 text-right">${row.expenses.toFixed(2)}</td>
                        <td className="py-2 text-right">${profit.toFixed(2)}</td>
                        <td className="py-2 text-right">{periodMargin}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  );
}

type AnalyticsCardProps = {
  title: string;
  value: string;
  accent: string;
};

function AnalyticsCard({ title, value, accent }: AnalyticsCardProps): JSX.Element {
  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>{title}</span>
        <span className={`h-2 w-2 rounded-full ${accent}`}></span>
      </div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  );
}
