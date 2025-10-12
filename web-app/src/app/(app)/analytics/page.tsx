"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useState } from "react";

export default function AnalyticsPage() {
  const [range, setRange] = useState<"1y"|"6m"|"3m"|"1m">("3m");
  const { data, isLoading } = useQuery({ queryKey: ["pnl", range], queryFn: () => api.analytics.pnl(range) });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold">Analytics</h1>
        <select value={range} onChange={e=>setRange(e.target.value as any)} className="ml-auto border p-2 rounded">
          {["1y","6m","3m","1m"].map(r=><option key={r} value={r}>{r}</option>)}
        </select>
      </div>
      {isLoading && <p>Loading…</p>}
      {data && (
        <div className="space-y-1">
          <div>Revenue: <b>${data.revenue.toFixed(2)}</b></div>
          <div>Expenses: <b>${data.expenses.toFixed(2)}</b></div>
          <div>Profit: <b>${data.profit.toFixed(2)}</b></div>
        </div>
      )}
    </div>
  );
}
