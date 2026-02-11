export const AUTH_TOKEN_KEY = "hissabi_token";

export const API_ENDPOINTS = {
    AUTH: {
        LOGIN: "/auth/login",
        REGISTER: "/auth/register",
        ME: "/auth/me",
        LOGOUT: "/auth/logout",
    },
    UPLOADS: "/uploads",
    DOCUMENTS: "/documents",
    INVENTORY: {
        SUMMARY: "/inventory/summary",
        MOVEMENTS: (id: number) => `/inventory/items/${id}/movements`,
    },
    ANALYTICS: {
        BASE: "/analytics",
        PNL: "/analytics/pnl",
        RECEIVABLES: "/analytics/receivables",
        PAYABLES: "/analytics/payables",
    },
    SETTINGS: {
        ORG: "/settings/org",
    },
    JOURNAL: {
        DAY: "/journal/day",
        RESOLVE: (id: number) => `/journal/day/${id}/resolve`,
    },
    PERSONAL: {
        ENTRIES: "/personal/entries",
        ACCOUNTS: "/personal/accounts",
        ACCOUNTS_ID: (id: number) => `/personal/accounts/${id}`,
        ENTRY: (id: number) => `/personal/entries/${id}`,
        PARSE: "/personal/parse",
        PARSE_SAVE: "/personal/parse/save",
        SUMMARY: "/personal/analytics/summary",
        BY_CATEGORY: "/personal/analytics/by-category",
        TRENDS: "/personal/analytics/trends",
        TOP_SPENDING: "/personal/analytics/top-spending",
        FLOW: "/personal/analytics/flow",
        INSIGHTS: "/personal/insights",
        BUDGETS: "/personal/budgets",
        BUDGET_PROGRESS: "/personal/budgets/progress",
        CHAT: "/personal/chat",
        CATEGORIES: "/personal/categories",
        MERCHANTS: "/personal/merchants",
        MERCHANT: (vendor: string) => `/personal/merchants/${encodeURIComponent(vendor)}`,
    },
} as const;

export const EVENTS = {
    AUTH_UNAUTHORIZED: "auth:unauthorized",
} as const;
