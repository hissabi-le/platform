"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function InventoryPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["inventory","summary"], queryFn: api.inventory.summary });
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Inventory</h1>
      {isLoading && <p>Loading…</p>}
      {error && <p className="text-red-600">Failed to load.</p>}
      {data && (
        <table className="w-full text-sm border">
          <thead><tr><th className="p-2 text-left">Item</th><th className="p-2 text-right">Qty</th><th className="p-2">Unit</th><th className="p-2 text-right">Avg Cost</th></tr></thead>
          <tbody>
          {data.map(row=>(
            <tr key={row.item_id} className="border-t">
              <td className="p-2">{row.name}</td>
              <td className="p-2 text-right">{row.qty}</td>
              <td className="p-2">{row.unit}</td>
              <td className="p-2 text-right">{row.avg_cost?.toFixed(2) ?? "-"}</td>
            </tr>
          ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
