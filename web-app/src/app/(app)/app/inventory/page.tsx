"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";

import { api } from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { ErrorAlert } from "@/components/Alert";
import { CardSkeleton, TableSkeleton } from "@/components/Skeleton";
import { formatCurrency, formatNumber } from "@/lib/format";

type SelectedItem = {
  id: number;
  name: string;
  unit: string;
};

export default function InventoryPage() {
  const summaryQuery = useQuery({
    queryKey: ["inventory", "summary"],
    queryFn: api.inventory.summary,
  });

  const [selected, setSelected] = useState<SelectedItem | null>(null);
  const movementsQuery = useQuery({
    queryKey: ["inventory", "movements", selected?.id],
    queryFn: () => (selected ? api.inventory.movements(selected.id) : Promise.resolve([])),
    enabled: Boolean(selected),
  });

  const totals = useMemo(() => {
    const rows = summaryQuery.data ?? [];
    const totalItems = rows.length;
    const totalQty = rows.reduce((acc, row) => acc + (row.on_hand ?? 0), 0);
    const totalValue = rows.reduce((acc, row) => acc + (row.on_hand ?? 0) * (row.avg_unit_cost ?? 0), 0);
    return { totalItems, totalQty, totalValue };
  }, [summaryQuery.data]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Inventory</h1>
        <p className="text-sm text-slate-500 mt-1">
          Monitor stock levels, movements, and weighted average costs
        </p>
      </header>

      {/* Error State */}
      {summaryQuery.error && (
        <ErrorAlert error={summaryQuery.error} onRetry={() => summaryQuery.refetch()} />
      )}

      {/* Loading State */}
      {summaryQuery.isLoading && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
          <TableSkeleton rows={5} columns={5} />
        </div>
      )}

      {/* Data Display */}
      {summaryQuery.data && (
        <>
          {/* Summary Cards */}
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard
              title="Tracked Items"
              value={totals.totalItems.toString()}
              accent="bg-blue-500"
            />
            <StatCard
              title="Units on Hand"
              value={formatNumber(totals.totalQty)}
              accent="bg-emerald-500"
            />
            <StatCard
              title="Inventory Value"
              value={formatCurrency(totals.totalValue)}
              accent="bg-amber-500"
            />
          </section>

          {/* Main Content Grid */}
          <section className="grid gap-6 lg:grid-cols-[3fr_2fr]">
            {/* Inventory Table */}
            <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b">
                <h2 className="font-semibold text-slate-900">Stock Summary</h2>
              </div>
              {summaryQuery.data.length === 0 ? (
                <div className="p-6 text-center text-slate-500">
                  No inventory items yet. Upload a spreadsheet or log purchases in your journal.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50">
                      <tr className="text-left text-xs uppercase text-slate-500">
                        <th className="px-6 py-3 font-medium">Item</th>
                        <th className="px-6 py-3 font-medium">Unit</th>
                        <th className="px-6 py-3 font-medium text-right">On Hand</th>
                        <th className="px-6 py-3 font-medium text-right">Avg Cost</th>
                        <th className="px-6 py-3 font-medium text-right">Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {summaryQuery.data.map((row) => {
                        const value = (row.on_hand ?? 0) * (row.avg_unit_cost ?? 0);
                        const isActive = selected?.id === row.item_id;
                        return (
                          <tr
                            key={row.item_id}
                            onClick={() => setSelected({ id: row.item_id, name: row.name, unit: row.unit })}
                            className={`cursor-pointer transition-colors ${isActive ? "bg-slate-100" : "hover:bg-slate-50"}`}
                          >
                            <td className="px-6 py-4 font-medium text-slate-900">{row.name}</td>
                            <td className="px-6 py-4 text-slate-600">{row.unit}</td>
                            <td className="px-6 py-4 text-right text-slate-700">
                              {formatNumber(row.on_hand ?? 0)}
                            </td>
                            <td className="px-6 py-4 text-right text-slate-600">
                              {row.avg_unit_cost != null ? formatCurrency(row.avg_unit_cost) : "—"}
                            </td>
                            <td className="px-6 py-4 text-right font-medium text-slate-900">
                              {formatCurrency(value)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Movements Panel */}
            <div className="rounded-xl border bg-white shadow-sm">
              <div className="px-6 py-4 border-b">
                <h2 className="font-semibold text-slate-900">Recent Movements</h2>
                <p className="text-sm text-slate-500 mt-1">
                  {selected ? `Movements for ${selected.name}` : "Select an item to view movements"}
                </p>
              </div>

              <div className="p-6">
                {!selected && (
                  <div className="flex items-center justify-center h-48 text-slate-400">
                    <div className="text-center">
                      <svg className="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                      </svg>
                      <p className="text-sm">Click an item to see its stock history</p>
                    </div>
                  </div>
                )}

                {selected && movementsQuery.isLoading && (
                  <div className="flex items-center justify-center h-48">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900"></div>
                  </div>
                )}

                {selected && movementsQuery.data && movementsQuery.data.length === 0 && (
                  <div className="flex items-center justify-center h-48 text-slate-500">
                    No movements recorded for {selected.name}
                  </div>
                )}

                {selected && movementsQuery.data && movementsQuery.data.length > 0 && (
                  <div className="space-y-3">
                    {movementsQuery.data.slice(0, 10).map((movement, index) => (
                      <div
                        key={`${movement.ts}-${index}`}
                        className="flex items-center justify-between py-2 border-b last:border-0"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${movement.type === "in"
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-rose-100 text-rose-800"
                              }`}>
                              {movement.type === "in" ? "IN" : "OUT"}
                            </span>
                            <span className="text-sm text-slate-600">
                              {format(new Date(movement.ts), "MMM dd, HH:mm")}
                            </span>
                          </div>
                          {movement.ref && (
                            <span className="text-xs text-slate-400 mt-0.5 block">{movement.ref}</span>
                          )}
                        </div>
                        <div className={`text-sm font-medium ${movement.type === "in" ? "text-emerald-600" : "text-rose-600"
                          }`}>
                          {movement.type === "in" ? "+" : "-"}{formatNumber(movement.quantity)} {selected.unit}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
