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
    list: () =>
      fetchJson<Array<{ id: number; filename: string; created_at: string; content_type: string }>>(
        "/documents"
      ),
    get: (id: number) =>
      fetchJson<{ id: number; filename: string; created_at: string; content_type: string; url?: string }>(
        `/documents/${id}`
      ),
  },

  inventory: {
    summary: () =>
      fetchJson<Array<{ item_id: number; name: string; unit: string; qty: number; avg_cost?: number }>>(
        "/inventory/summary"
      ),
    // optional helpers if you add them backend-side later:
    movements: (itemId: number) =>
      fetchJson<Array<{ date: string; type: "in" | "out"; qty: number; ref?: string }>>(
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
};
