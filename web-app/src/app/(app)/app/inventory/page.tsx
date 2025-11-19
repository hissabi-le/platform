"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";

import { api } from "@/lib/api";

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
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Inventory</h1>
        <p className="text-sm text-gray-500">Monitor stock on hand, recent movements, and weighted average costs.</p>
      </header>

      {summaryQuery.isLoading && <p className="text-sm text-gray-500">Loading inventory summary…</p>}
      {summaryQuery.error && <p className="text-sm text-red-600">Unable to load inventory. Refresh to retry.</p>}

      {summaryQuery.data && (
        <>
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <InventoryCard title="Tracked items" value={totals.totalItems.toString()} />
            <InventoryCard title="Units on hand" value={totals.totalQty.toFixed(2)} />
            <InventoryCard title="Inventory value" value={`$${totals.totalValue.toFixed(2)}`} />
          </section>

          <section className="grid gap-6 lg:grid-cols-[3fr_2fr]">
            <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-gray-500">
                    <th className="px-4 py-3">Item</th>
                    <th className="px-4 py-3">Unit</th>
                    <th className="px-4 py-3 text-right">On hand</th>
                    <th className="px-4 py-3 text-right">Avg cost</th>
                    <th className="px-4 py-3 text-right">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {summaryQuery.data.map((row) => {
                    const value = (row.on_hand ?? 0) * (row.avg_unit_cost ?? 0);
                    const isActive = selected?.id === row.item_id;
                    return (
                      <tr
                        key={row.item_id}
                        className={`border-t text-sm ${isActive ? "bg-slate-50" : ""}`}
                        onClick={() =>
                          setSelected({ id: row.item_id, name: row.name, unit: row.unit })
                        }
                      >
                        <td className="cursor-pointer px-4 py-3 font-medium text-slate-700">{row.name}</td>
                        <td className="px-4 py-3 text-gray-500">{row.unit}</td>
                        <td className="px-4 py-3 text-right text-gray-600">{(row.on_hand ?? 0).toFixed(2)}</td>
                        <td className="px-4 py-3 text-right text-gray-600">
                          {row.avg_unit_cost != null ? `$${row.avg_unit_cost.toFixed(2)}` : "-"}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-600">${value.toFixed(2)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="space-y-4 rounded-xl border bg-white p-6 shadow-sm">
              <header className="space-y-1">
                <h2 className="text-lg font-semibold">Recent movements</h2>
                <p className="text-sm text-gray-500">
                  Select an item to review stock inflows and outflows. Weighted average cost is applied automatically.
                </p>
              </header>

              {!selected && <p className="text-sm text-gray-500">Pick an item in the table to inspect individual movements.</p>}

              {selected && movementsQuery.isLoading && <p className="text-sm text-gray-500">Loading movements…</p>}

              {selected && movementsQuery.data && movementsQuery.data.length === 0 && (
                <p className="text-sm text-gray-500">No movements recorded for {selected.name} yet.</p>
              )}

              {selected && movementsQuery.data && movementsQuery.data.length > 0 && (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase text-gray-500">
                      <th className="pb-2">Date</th>
                      <th className="pb-2">Type</th>
                      <th className="pb-2 text-right">Quantity</th>
                      <th className="pb-2">Reference</th>
                    </tr>
                  </thead>
                  <tbody>
                    {movementsQuery.data.map((movement, index) => (
                      <tr key={`${movement.ts}-${index}`} className="border-t">
                        <td className="py-2 text-gray-600">{format(new Date(movement.ts), "dd/MM/yy HH:mm")}</td>
                        <td className="py-2 text-gray-600">{movement.type === "in" ? "Stock in" : "Stock out"}</td>
                        <td className="py-2 text-right text-gray-600">{movement.quantity.toFixed(2)}</td>
                        <td className="py-2 text-gray-500">{movement.ref ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

type InventoryCardProps = {
  title: string;
  value: string;
};

function InventoryCard({ title, value }: InventoryCardProps) {
  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="text-xs uppercase text-gray-500">{title}</div>
      <div className="mt-2 text-2xl font-semibold text-slate-800">{value}</div>
    </div>
  );
}
