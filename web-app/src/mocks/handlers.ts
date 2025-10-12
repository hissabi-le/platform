// src/mocks/handlers.ts
import { http, HttpResponse } from "msw";

// JSON type that TS can verify is serializable
type JsonPrimitive = string | number | boolean | null;
type Json = JsonPrimitive | { [k: string]: Json } | Json[];

const ok = <T extends Json>(json: T) => HttpResponse.json(json);

export const handlers = [
  // auth
  http.post("http://localhost:8000/auth/login", async ({ request }) => {
    const body = (await request.json()) as any;
    if (body.email && body.password) {
      return ok({ token: "dev-token", user: { id: 1, email: body.email, org_id: 1 } });
    }
    return new HttpResponse("Unauthorized", { status: 401 });
  }),

  http.get("http://localhost:8000/auth/me", () =>
    ok({ id: 1, email: "owner@demo.local", org_id: 1 })
  ),

  // documents
  http.get("http://localhost:8000/documents", () =>
    ok([
      {
        id: 21,
        filename: "balance_sheet_2025-09-01.pdf",
        created_at: new Date().toISOString(),
        content_type: "application/pdf",
      },
    ])
  ),

  // inventory
  http.get("http://localhost:8000/inventory/summary", () =>
    ok([
      { item_id: 101, name: "Chicken", unit: "kg", qty: 10, avg_cost: 4.2 },
      { item_id: 102, name: "Eggs", unit: "dozen", qty: 3, avg_cost: 2.1 },
    ])
  ),

  // analytics
  http.get("http://localhost:8000/analytics/pnl", ({ request }) => {
    const url = new URL(request.url);
    const range = url.searchParams.get("range") ?? "1m";
    const series = Array.from({ length: 6 }).map((_, i) => ({
      date: new Date(Date.now() - (5 - i) * 7 * 864e5).toISOString(),
      revenue: 1000 + i * 200,
      expenses: 500 + i * 120,
    }));
    const revenue = series.reduce((s, r) => s + r.revenue, 0);
    const expenses = series.reduce((s, r) => s + r.expenses, 0);
    return ok({ range, revenue, expenses, profit: revenue - expenses, series });
  }),
];
