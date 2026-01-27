export const AUTH_TOKEN_KEY = "hissabi_token";

export const API_ENDPOINTS = {
    AUTH: {
        LOGIN: "/auth/login",
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
} as const;

export const EVENTS = {
    AUTH_UNAUTHORIZED: "auth:unauthorized",
} as const;
