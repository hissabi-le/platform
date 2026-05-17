// src/lib/api.ts
import { AUTH_TOKEN_KEY, API_ENDPOINTS, EVENTS } from "./constants";

function resolveApiBaseUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (explicit && explicit.length > 0) return explicit;
  if (
    process.env.NODE_ENV === "development" ||
    process.env.NODE_ENV === "test"
  ) {
    return "http://localhost:8000";
  }
  throw new Error(
    "NEXT_PUBLIC_API_BASE_URL is not set. " +
      "Configure it in the environment before building for production."
  );
}

export const API_BASE_URL = resolveApiBaseUrl();


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
      fetchJson<{ access_token: string; refresh_token: string; user: { id: number; email: string; org_id: number; plan?: string } }>(
        API_ENDPOINTS.AUTH.LOGIN,
        { method: "POST", body: { email, password } }
      ),
    me: () =>
      fetchJson<{ id: number; email: string; org_id: number; plan?: string }>(API_ENDPOINTS.AUTH.ME),
    register: (email: string, password: string, org_name: string) =>
      fetchJson<{ access_token: string; refresh_token: string; user: { id: number; email: string; org_id: number; plan?: string } }>(
        API_ENDPOINTS.AUTH.REGISTER,
        { method: "POST", body: { email, password, org_name } }
      ),
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

  billing: {
    createCheckoutSession: (plan: "starter" | "pro" = "pro") =>
      fetchJson<{ url: string }>(
        `${API_ENDPOINTS.BILLING.CHECKOUT_SESSION}?plan=${plan}`,
        { method: "POST" }
      ),
    createPortalSession: () =>
      fetchJson<{ url: string }>(API_ENDPOINTS.BILLING.PORTAL_SESSION, {
        method: "POST",
      }),
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

  personal: {
    // Accounts
    listAccounts: () => fetchJson<PersonalAccount[]>(API_ENDPOINTS.PERSONAL.ACCOUNTS),
    createAccount: (name: string, balance: number, type: string) =>
      fetchJson<PersonalAccount>(API_ENDPOINTS.PERSONAL.ACCOUNTS, {
        method: "POST",
        body: { name, balance, type },
      }),
    deleteAccount: (id: number) =>
      fetchJson<{ ok: boolean }>(API_ENDPOINTS.PERSONAL.ACCOUNTS_ID(id), { method: "DELETE" }),

    // Entries CRUD
    createEntry: (data: PersonalEntryInput) =>
      fetchJson<PersonalEntry>(API_ENDPOINTS.PERSONAL.ENTRIES, { method: "POST", body: data }),
    listEntries: (params?: { start_date?: string; end_date?: string; category?: string; entry_type?: string; limit?: number }) => {
      const query = new URLSearchParams();
      if (params?.start_date) query.set("start_date", params.start_date);
      if (params?.end_date) query.set("end_date", params.end_date);
      if (params?.category) query.set("category", params.category);
      if (params?.entry_type) query.set("entry_type", params.entry_type);
      if (params?.limit) query.set("limit", params.limit.toString());
      const queryStr = query.toString() ? `?${query.toString()}` : "";
      return fetchJson<PersonalEntry[]>(`${API_ENDPOINTS.PERSONAL.ENTRIES}${queryStr}`);
    },
    getEntry: (id: number) => fetchJson<PersonalEntry>(API_ENDPOINTS.PERSONAL.ENTRY(id)),
    updateEntry: (id: number, data: Partial<PersonalEntryInput>) =>
      fetchJson<PersonalEntry>(API_ENDPOINTS.PERSONAL.ENTRY(id), { method: "PUT", body: data }),
    deleteEntry: (id: number) =>
      fetchJson<{ ok: boolean }>(API_ENDPOINTS.PERSONAL.ENTRY(id), { method: "DELETE" }),

    // AI Parsing
    parseText: (text: string, default_date?: string) =>
      fetchJson<ParsedPersonalEntry[]>(API_ENDPOINTS.PERSONAL.PARSE, {
        method: "POST",
        body: { text, default_date },
      }),
    parseAndSave: (text: string, default_date?: string) =>
      fetchJson<PersonalEntry[]>(API_ENDPOINTS.PERSONAL.PARSE_SAVE, {
        method: "POST",
        body: { text, default_date },
      }),

    // Analytics
    getSummary: (start_date?: string, end_date?: string) => {
      const query = new URLSearchParams();
      if (start_date) query.set("start_date", start_date);
      if (end_date) query.set("end_date", end_date);
      const queryStr = query.toString() ? `?${query.toString()}` : "";
      return fetchJson<PersonalSummary>(`${API_ENDPOINTS.PERSONAL.SUMMARY}${queryStr}`);
    },
    getCategoryBreakdown: (start_date?: string, end_date?: string, entry_type?: string) => {
      const query = new URLSearchParams();
      if (start_date) query.set("start_date", start_date);
      if (end_date) query.set("end_date", end_date);
      if (entry_type) query.set("entry_type", entry_type);
      const queryStr = query.toString() ? `?${query.toString()}` : "";
      return fetchJson<{ breakdown: CategoryBreakdown[] }>(`${API_ENDPOINTS.PERSONAL.BY_CATEGORY}${queryStr}`);
    },
    getTrends: (months?: number) => {
      const query = months ? `?months=${months}` : "";
      return fetchJson<{ trends: MonthlyTrend[] }>(`${API_ENDPOINTS.PERSONAL.TRENDS}${query}`);
    },
    getTopSpending: (days?: number, category?: string, limit?: number) => {
      const query = new URLSearchParams();
      if (days) query.set("days", String(days));
      if (category) query.set("category", category);
      if (limit) query.set("limit", String(limit));
      const queryStr = query.toString() ? `?${query.toString()}` : "";
      return fetchJson<{ days: number; category: string | null; items: TopSpendingItem[] }>(
        `${API_ENDPOINTS.PERSONAL.TOP_SPENDING}${queryStr}`
      );
    },
    getInsights: () => fetchJson<PersonalInsights>(API_ENDPOINTS.PERSONAL.INSIGHTS),

    // Budgets
    listBudgets: () => fetchJson<PersonalBudget[]>(API_ENDPOINTS.PERSONAL.BUDGETS),
    createBudget: (category: string, monthly_limit: number) =>
      fetchJson<PersonalBudget>(API_ENDPOINTS.PERSONAL.BUDGETS, {
        method: "POST",
        body: { category, monthly_limit },
      }),
    deleteBudget: (category: string) =>
      fetchJson<{ ok: boolean }>(`${API_ENDPOINTS.PERSONAL.BUDGETS}/${category}`, { method: "DELETE" }),
    getBudgetProgress: () => fetchJson<BudgetProgress[]>(API_ENDPOINTS.PERSONAL.BUDGET_PROGRESS),

    // AI Chat
    chat: (message: string) =>
      fetchJson<{ response: string; insights: PersonalInsights | null }>(API_ENDPOINTS.PERSONAL.CHAT, {
        method: "POST",
        body: { message },
      }),

    // Categories
    getCategories: () => fetchJson<Record<string, string[]>>(API_ENDPOINTS.PERSONAL.CATEGORIES),

    // The Flow (Sankey)
    getFlowData: (startDate?: string, endDate?: string) => {
      const query = new URLSearchParams();
      if (startDate) query.set("start_date", startDate);
      if (endDate) query.set("end_date", endDate);
      const queryStr = query.toString() ? `?${query.toString()}` : "";
      return fetchJson<FlowData>(`${API_ENDPOINTS.PERSONAL.FLOW}${queryStr}`);
    },

    // Merchant DNA
    getTopMerchants: (limit?: number) => {
      const query = limit ? `?limit=${limit}` : "";
      return fetchJson<{ merchants: MerchantSummary[] }>(`${API_ENDPOINTS.PERSONAL.MERCHANTS}${query}`);
    },
    getMerchantProfile: (vendor: string) =>
      fetchJson<MerchantProfile>(API_ENDPOINTS.PERSONAL.MERCHANT(vendor)),

    // WhatsApp Integration
    whatsappLink: (phone_number: string) =>
      fetchJson<{ status: string; message: string }>(API_ENDPOINTS.PERSONAL.WHATSAPP_LINK, {
        method: "POST",
        body: { phone_number },
      }),
    whatsappUnlink: () =>
      fetchJson<{ ok: boolean }>(API_ENDPOINTS.PERSONAL.WHATSAPP_UNLINK, { method: "POST" }),
    whatsappStatus: () =>
      fetchJson<{ linked: boolean; verified: boolean; phone: string | null }>(
        API_ENDPOINTS.PERSONAL.WHATSAPP_STATUS
      ),
  },
};

// -------- Personal Finance Types --------

export type PersonalEntryInput = {
  entry_date: string;
  entry_type: "income" | "expense";
  category: string;
  amount: number;
  currency?: string;
  description?: string;
  vendor?: string;
  notes?: string;
};

export type PersonalEntry = {
  id: number;
  entry_date: string;
  entry_type: "income" | "expense";
  category: string;
  amount: number;
  currency: string;
  description?: string | null;
  vendor?: string | null;
  notes?: string | null;
  ai_categorized: boolean;
  created_at: string;
};

export type ParsedPersonalEntry = {
  entry_type: "income" | "expense";
  category: string;
  amount: number;
  description: string;
  vendor?: string | null;
  entry_date?: string | null;
};

export type PersonalSummary = {
  start_date: string;
  end_date: string;
  income: number;
  expense: number;
  net: number;
};

export type CategoryBreakdown = {
  category: string;
  total: number;
  count: number;
};

export type MonthlyTrend = {
  month: string;
  income: number;
  expense: number;
};

export type TopSpendingItem = {
  description: string;
  vendor?: string | null;
  category: string;
  total: number;
  count: number;
};

export type PersonalInsights = {
  this_week_expense: number;
  this_week_income: number;
  week_change_percent: number;
  this_month_expense: number;
  this_month_income: number;
  this_month_net: number;
  top_category: string | null;
  top_category_amount: number;
};

export type PersonalBudget = {
  id: number;
  category: string;
  monthly_limit: number;
};

export type BudgetProgress = {
  category: string;
  monthly_limit: number;
  spent: number;
  remaining: number;
  percent_used: number;
};

// -------- Flow (Sankey) Types --------

export type FlowNode = {
  id: string;
  label: string;
  value: number;
};

export type FlowLink = {
  source: string;
  target: string;
  value: number;
};

export type FlowData = {
  start_date: string;
  end_date: string;
  nodes: FlowNode[];
  links: FlowLink[];
  total_income: number;
  total_expense: number;
};

export type MerchantSummary = {
  vendor: string;
  total_spend: number;
  visit_count: number;
  first_visit: string | null;
  last_visit: string | null;
  avg_order: number;
};

export type FrequencyByDay = {
  day: string;
  count: number;
};

export type PriceTrend = {
  month: string;
  total: number;
  avg: number;
};

export type MerchantProfile = {
  vendor: string;
  lifetime_spend: number;
  visit_count: number;
  average_order: number;
  first_visit: string | null;
  last_visit: string | null;
  visits_per_week: number;
  frequency_by_day: FrequencyByDay[];
  price_trend: PriceTrend[];
};

export type PersonalAccount = {
  id: number;
  name: string;
  balance: number;
  type: string;
};
