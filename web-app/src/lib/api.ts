// src/lib/api.ts

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
  return localStorage.getItem("hissabi_token");
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
      fetchJson<{ token: string; user: { id: number; email: string; org_id: number } }>(
        "/auth/login",
        { method: "POST", body: { email, password } }
      ),
    me: () =>
      fetchJson<{ id: number; email: string; org_id: number }>("/auth/me"),
    logout: () =>
      fetchJson<void>("/auth/logout", { method: "POST" }),
  },

  uploads: {
    // Example real upload (multipart)
    create: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return fetchJson<{ id: number; status: string }>("/uploads", {
        method: "POST",
        body: fd,
      });
    },
    list: () =>
      fetchJson<Array<{ id: number; filename: string; status: string; uploaded_at: string }>>(
        "/uploads"
      ),
  },

  documents: {
    list: () => fetchJson<DocumentListItem[]>("/documents"),
    get: (id: number) =>
      fetchJson<{
        id: number;
        filename: string;
        created_at: string;
        content_type: string;
        storage_path: string;
        url?: string | null;
      }>(`/documents/${id}`),
  },

  inventory: {
    summary: () =>
      fetchJson<Array<{ item_id: number; name: string; unit: string; on_hand: number; avg_unit_cost?: number }>>(
        "/inventory/summary"
      ),
    // optional helpers if you add them backend-side later:
    movements: (itemId: number) =>
      fetchJson<Array<{ ts: string; quantity: number; type: "in" | "out"; ref?: string | null }>>(
        `/inventory/items/${itemId}/movements`
      ),
  },

  analytics: {
    pnl: (range: "1y" | "6m" | "3m" | "1m") =>
      fetchJson<{
        revenue: number;
        expenses: number;
        profit: number;
        series: Array<{ date: string; revenue: number; expenses: number }>;
      }>(`/analytics/pnl?range=${range}`),
  },

  settings: {
    getOrg: () => fetchJson<OrganisationSettings>("/settings/org"),
    updateOrg: (payload: Partial<OrganisationSettings>) =>
      fetchJson<OrganisationSettings>("/settings/org", { method: "PUT", body: payload }),
  },

  journal: {
    saveDay: (body: { raw_text: string; date?: string; commit?: boolean }) =>
      fetchJson<JournalDayResponse>("/journal/day", { method: "POST", body }),
    getDay: async (date?: string) => {
      const query = date ? `?date_str=${encodeURIComponent(date)}` : "";
      try {
        return await fetchJson<JournalDayResponse>(`/journal/day${query}`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          return null;
        }
        throw err;
      }
    },
    resolve: (dayId: number, body: { resolutions: Array<Record<string, unknown>> }) =>
      fetchJson<JournalDayResponse>(`/journal/day/${dayId}/resolve`, { method: "PATCH", body }),
  },
};
