// src/mocks/handlers.ts
import { http, HttpResponse } from "msw";

// JSON type that TS can verify is serializable
type JsonPrimitive = string | number | boolean | null;
type Json = JsonPrimitive | { [k: string]: Json } | Json[];

const ok = <T extends Json>(json: T) => HttpResponse.json(json);

let settingsState = {
  id: 1,
  org_id: 1,
  total_initial_investment: "5000",
  starting_cash_balance: "1500",
  current_assets_value: "2000",
  default_currency: "USD",
  default_locale: "en",
  vat_rate: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

type JournalState = {
  journal_day: {
    id: number;
    org_id: number;
    user_id: number;
    journal_date: string;
    language: string;
    parse_status: "pending" | "parsed" | "needs_review" | "error";
    total_revenue: string;
    total_cost: string;
    net_profit: string;
    clarification_count: number;
    created_at: string;
    updated_at: string;
  };
  entries: Array<{
    id?: number;
    entry_type: string;
    item_name?: string | null;
    quantity?: string | null;
    unit?: string | null;
    unit_cost?: string | null;
    total: string;
    category?: string | null;
    vat_percent?: string | null;
    vat_included?: boolean | null;
    notes?: string | null;
    ambiguous: boolean;
    clarification_question?: string | null;
    resolved: boolean;
    created_at?: string;
  }>;
  clarifications: Array<{ entry_id?: number | null; question: string; entry_type: string; category?: string | null }>;
  totals: {
    revenue: string;
    cost: string;
    net: string;
    cumulative_net: string;
    roi: number | null;
  };
};

const journalStore: Record<string, JournalState> = {};

const buildMockJournal = (raw: string, date: string): JournalState => {
  const lower = raw.toLowerCase();
  const baseRevenue = lower.includes("sold") ? 50 : 0;
  const baseCost = lower.includes("rent") ? 40 : 0;
  const inventoryCost = lower.includes("bought") ? 20 : 0;
  const clarifications =
    lower.includes("bought")
      ? [
        {
          entry_id: 2,
          question: "should the milk purchase be tracked as inventory or expensed today?",
          entry_type: "inventory_purchase",
          category: "Ingredients",
        },
      ]
      : [];
  const entries = [
    {
      id: 1,
      entry_type: "revenue",
      item_name: "coffee sales",
      quantity: "5",
      unit: "unit",
      unit_cost: "10",
      total: baseRevenue.toFixed(2),
      category: "Sales",
      ambiguous: false,
      resolved: true,
      created_at: new Date().toISOString(),
    },
    {
      id: 2,
      entry_type: "inventory_purchase",
      item_name: "milk",
      quantity: "3",
      unit: "kg",
      unit_cost: "6.67",
      total: inventoryCost.toFixed(2),
      category: "Ingredients",
      ambiguous: clarifications.length > 0,
      clarification_question: clarifications.length ? clarifications[0]?.question : null,
      resolved: clarifications.length === 0,
      created_at: new Date().toISOString(),
    },
    {
      id: 3,
      entry_type: "cost",
      item_name: "rent",
      quantity: null,
      unit: null,
      unit_cost: null,
      total: baseCost.toFixed(2),
      category: "Fixed Expense",
      ambiguous: false,
      resolved: true,
      created_at: new Date().toISOString(),
    },
  ];
  const revenue = baseRevenue.toFixed(2);
  const totalCost = (baseCost + (clarifications.length ? 0 : inventoryCost)).toFixed(2);
  const net = (baseRevenue - parseFloat(totalCost)).toFixed(2);
  const cumulative = net;
  return {
    journal_day: {
      id: 10,
      org_id: 1,
      user_id: 1,
      journal_date: date,
      language: "en",
      parse_status: clarifications.length ? "needs_review" : "parsed",
      total_revenue: revenue,
      total_cost: totalCost,
      net_profit: net,
      clarification_count: clarifications.length,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    entries,
    clarifications,
    totals: {
      revenue,
      cost: totalCost,
      net,
      cumulative_net: cumulative,
      roi: baseRevenue ? (parseFloat(net) / 5000) * 100 : null,
    },
  };
};

export const handlers = [
  // auth
  http.post("http://localhost:8000/auth/login", async ({ request }) => {
    const body = (await request.json()) as { email?: string; password?: string };
    if (body.email && body.password) {
      return ok({ token: "dev-token", user: { id: 1, email: body.email, org_id: 1 } });
    }
    return new HttpResponse("Unauthorized", { status: 401 });
  }),

  http.get("http://localhost:8000/auth/me", () =>
    ok({ id: 1, email: "owner@demo.local", org_id: 1 })
  ),

  // settings
  http.get("http://localhost:8000/settings/org", () => ok(settingsState)),
  http.put("http://localhost:8000/settings/org", async ({ request }) => {
    const body = (await request.json()) as Record<string, string>;
    settingsState = {
      ...settingsState,
      ...body,
      updated_at: new Date().toISOString(),
    };
    return ok(settingsState);
  }),

  // uploads
  http.post("http://localhost:8000/uploads", async ({ request }) => {
    const formData = await request.formData();
    const file = formData.get("file");
    if (!file) {
      return new HttpResponse("Bad Request", { status: 400 });
    }
    return HttpResponse.json(
      { id: 1001, status: "done", document_id: 21 },
      { status: 201 }
    );
  }),

  http.get("http://localhost:8000/uploads", () =>
    ok([
      {
        id: 1001,
        filename: "inventory.xlsx",
        status: "done",
        uploaded_at: new Date().toISOString(),
      },
    ])
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

  http.get("http://localhost:8000/documents/:id", ({ params }) =>
    ok({
      id: Number(params.id),
      org_id: 1,
      upload_id: 1001,
      doc_type: "generic",
      filename: "balance_sheet_2025-09-01.pdf",
      content_type: "application/pdf",
      storage_path: "/mock/path",
      size_bytes: 12345,
      created_at: new Date().toISOString(),
      metadata_json: {},
      url: null,
    })
  ),

  // inventory
  http.get("http://localhost:8000/inventory/summary", () =>
    ok([
      { item_id: 101, name: "Chicken", unit: "kg", qty: 10, avg_cost: 4.2 },
      { item_id: 102, name: "Eggs", unit: "dozen", qty: 3, avg_cost: 2.1 },
    ])
  ),

  http.get("http://localhost:8000/inventory/items/:id/movements", () =>
    ok([
      {
        ts: new Date().toISOString(),
        quantity: 10,
        type: "in",
        ref: "Initial stock",
      },
      {
        ts: new Date().toISOString(),
        quantity: -2,
        type: "out",
        ref: "Sale #123",
      },
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

  // journal save
  http.post("http://localhost:8000/journal/day", async ({ request }) => {
    const body = (await request.json()) as { raw_text: string; date?: string };
    const targetDate = body.date ?? formatDate(new Date());
    const payload = buildMockJournal(body.raw_text, targetDate);
    journalStore[targetDate] = payload;
    return ok(payload);
  }),

  http.get("http://localhost:8000/journal/day", ({ request }) => {
    const url = new URL(request.url);
    const targetDate = url.searchParams.get("date_str") ?? formatDate(new Date());
    const payload = journalStore[targetDate];
    if (!payload) {
      return new HttpResponse("Not Found", { status: 404 });
    }
    return ok(payload);
  }),

  http.patch("http://localhost:8000/journal/day/:id/resolve", async ({ request, params: _params }) => {
    const body = (await request.json()) as { resolutions: Array<{ entry_id?: number | null }> };
    const target = Object.entries(journalStore).find(([, value]) => value.journal_day.id === Number(_params.id));
    if (!target) {
      return new HttpResponse("Not Found", { status: 404 });
    }
    const [key, state] = target;
    const entryIds = new Set(body.resolutions.map((item) => item.entry_id).filter(Boolean) as number[]);
    const updatedEntries = state.entries.map((entry) =>
      entryIds.has(entry.id ?? -1)
        ? { ...entry, ambiguous: false, clarification_question: null, resolved: true }
        : entry,
    );
    const updated: JournalState = {
      ...state,
      entries: updatedEntries,
      clarifications: [],
      totals: {
        ...state.totals,
        cost: (parseFloat(state.totals.cost) + 0).toFixed(2),
        net: (parseFloat(state.totals.revenue) - parseFloat(state.totals.cost)).toFixed(2),
      },
      journal_day: {
        ...state.journal_day,
        parse_status: "parsed",
        clarification_count: 0,
      },
    };
    journalStore[key] = updated;
    return ok(updated);
  }),
];

function formatDate(value: Date): string {
  return value.toISOString().slice(0, 10);
}
