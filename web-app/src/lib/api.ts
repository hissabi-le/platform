// src/lib/api.ts
import { AUTH_TOKEN_KEY, API_ENDPOINTS, EVENTS } from "./constants";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export class ApiError extends Error {
  status: number;
  details?: unknown;
  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

function authToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

type FetchJsonInit = {
  method?: HttpMethod;
  body?: unknown | FormData;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

export async function fetchJson<T>(path: string, options: FetchJsonInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  // start with provided headers
  const headers: Record<string, string> = { ...(options.headers ?? {}) };

  // auth header if token present
  const token = authToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  // build RequestInit without undefined fields
  const init: RequestInit = {
    method: options.method ?? "GET",
    headers,
    credentials: "include",
    ...(options.signal ? { signal: options.signal } : {}),
  };

  // attach body only when present; handle JSON vs FormData
  if (options.body !== undefined && options.body !== null) {
    if (typeof FormData !== "undefined" && options.body instanceof FormData) {
      // Do not set Content-Type; browser will set multipart boundary
      init.body = options.body;
    } else {
      headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
      init.body = JSON.stringify(options.body);
    }
  }

  const res = await fetch(url, init);

  if (!res.ok) {
    let details: unknown;
    try {
      // response might not be JSON; ignore errors
      details = await res.json();
    } catch {
      /* noop */
    }

    // Global 401 handling
    if (res.status === 401) {
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event(EVENTS.AUTH_UNAUTHORIZED));
      }
    }

    throw new ApiError(`Request failed: ${res.status}`, res.status, details);
  }

  // 204 No Content => typed undefined
  if (res.status === 204) return undefined as unknown as T;

  return (await res.json()) as T;
}

// -------- Feature endpoints (keep shapes aligned with backend) --------

export type OrganisationSettings = {
  id?: number;
  org_id?: number;
  total_initial_investment: string;
  starting_cash_balance: string;
  current_assets_value: string;
  default_currency: string;
  default_locale: string;
  vat_rate?: string | null;
  // Inventory settings
  inventory_deduction_mode: "immediate" | "on_shipment" | "manual";
  enable_recipes: boolean;
  created_at?: string;
  updated_at?: string;
};

export type JournalEntry = {
  id?: number;
  entry_type: "revenue" | "cost" | "inventory_purchase" | "inventory_use" | "transfer";
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
  created_at?: string | null;
};

export type JournalClarification = {
  entry_id?: number | null;
  question: string;
  entry_type: string;
  category?: string | null;
};

export type JournalTotals = {
  revenue: string;
  cost: string;
  net: string;
  cumulative_net: string;
  roi?: number | null;
};

export type JournalDay = {
  id?: number | null;
  org_id: number;
  user_id?: number | null;
  journal_date: string;
  language?: string | null;
  parse_status: "pending" | "parsed" | "needs_review" | "error";
  total_revenue: string;
  total_cost: string;
  net_profit: string;
  clarification_count: number;
  created_at: string;
  updated_at: string;
};

export type JournalDayResponse = {
  journal_day: JournalDay;
  entries: JournalEntry[];
  clarifications: JournalClarification[];
  totals: JournalTotals;
};

export type DocumentListItem = {
  id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  doc_type?: string;
};

export const api = {
  auth: {
    login: (email: string, password: string) =>
      fetchJson<{ access_token: string; refresh_token: string; user: { id: number; email: string; org_id: number } }>(
        API_ENDPOINTS.AUTH.LOGIN,
        { method: "POST", body: { email, password } }
      ),
    me: () =>
      fetchJson<{ id: number; email: string; org_id: number }>(API_ENDPOINTS.AUTH.ME),
    logout: () =>
      fetchJson<void>(API_ENDPOINTS.AUTH.LOGOUT, { method: "POST" }),
  },

  uploads: {
    create: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return fetchJson<{ id: number; status: string }>(API_ENDPOINTS.UPLOADS, {
        method: "POST",
        body: fd,
      });
    },
    list: () =>
      fetchJson<Array<{ id: number; filename: string; status: string; uploaded_at: string }>>(
        API_ENDPOINTS.UPLOADS
      ),
  },

  documents: {
    list: () => fetchJson<DocumentListItem[]>(API_ENDPOINTS.DOCUMENTS),
    get: (id: number) =>
      fetchJson<{
        id: number;
        filename: string;
        created_at: string;
        content_type: string;
        storage_path: string;
        url?: string | null;
      }>(`${API_ENDPOINTS.DOCUMENTS}/${id}`),
  },

  inventory: {
    summary: () =>
      fetchJson<Array<{ item_id: number; name: string; unit: string; on_hand: number; avg_unit_cost?: number }>>(
        API_ENDPOINTS.INVENTORY.SUMMARY
      ),
    movements: (itemId: number) =>
      fetchJson<Array<{ ts: string; quantity: number; type: "in" | "out"; ref?: string | null }>>(
        API_ENDPOINTS.INVENTORY.MOVEMENTS(itemId)
      ),
  },

  analytics: {
    pnl: (range: "1y" | "6m" | "3m" | "1m") =>
      fetchJson<{
        revenue: number;
        expenses: number;
        profit: number;
        series: Array<{ date: string; revenue: number; expenses: number }>;
      }>(`${API_ENDPOINTS.ANALYTICS.PNL}?range=${range}`),
    receivables: () =>
      fetchJson<{
        total: number;
        count: number;
        breakdown: Array<{ category: string; amount: number; count: number }>;
      }>(`${API_ENDPOINTS.ANALYTICS.BASE}/receivables`),
    payables: () =>
      fetchJson<{
        total: number;
        count: number;
        breakdown: Array<{ category: string; amount: number; count: number }>;
      }>(`${API_ENDPOINTS.ANALYTICS.BASE}/payables`),
    receivablesList: () =>
      fetchJson<Array<{
        id: number;
        type: "journal" | "transaction";
        description: string;
        amount: number;
        category: string;
        date: string | null;
      }>>(`${API_ENDPOINTS.ANALYTICS.BASE}/receivables/list`),
    payablesList: () =>
      fetchJson<Array<{
        id: number;
        type: "journal" | "transaction";
        description: string;
        amount: number;
        category: string;
        date: string | null;
      }>>(`${API_ENDPOINTS.ANALYTICS.BASE}/payables/list`),
    toggleTransactionPayment: (txnId: number, status: "paid" | "unpaid") =>
      fetchJson<{ id: number; payment_status: string; payment_date: string | null }>(
        `${API_ENDPOINTS.ANALYTICS.BASE}/transaction/${txnId}/payment-status?status=${status}`,
        { method: "PATCH" }
      ),
    toggleJournalPayment: (entryId: number, status: "paid" | "unpaid") =>
      fetchJson<{ id: number; payment_status: string; payment_date: string | null }>(
        `/journal/entry/${entryId}/payment-status?status=${status}`,
        { method: "PATCH" }
      ),
  },

  settings: {
    getOrg: () => fetchJson<OrganisationSettings>(API_ENDPOINTS.SETTINGS.ORG),
    updateOrg: (payload: Partial<OrganisationSettings>) =>
      fetchJson<OrganisationSettings>(API_ENDPOINTS.SETTINGS.ORG, { method: "PUT", body: payload }),
  },

  journal: {
    saveDay: (body: { raw_text: string; date?: string; commit?: boolean }) =>
      fetchJson<JournalDayResponse>(API_ENDPOINTS.JOURNAL.DAY, { method: "POST", body }),
    getDay: async (date?: string) => {
      const query = date ? `?date_str=${encodeURIComponent(date)}` : "";
      try {
        return await fetchJson<JournalDayResponse>(`${API_ENDPOINTS.JOURNAL.DAY}${query}`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          return null;
        }
        throw err;
      }
    },
    resolve: (dayId: number, body: { resolutions: Array<Record<string, unknown>> }) =>
      fetchJson<JournalDayResponse>(API_ENDPOINTS.JOURNAL.RESOLVE(dayId), { method: "PATCH", body }),
  },
};
