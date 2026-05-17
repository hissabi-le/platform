// src/hooks/useAuth.ts
"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { AUTH_TOKEN_KEY, EVENTS } from "@/lib/constants";

type User = { id: number; email: string; org_id: number; plan?: string };

type AuthContextType = {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const logout = useCallback(() => {
    // Prevent re-entrant logout calls (e.g., from 401 handler)
    if (isLoggingOut) return;
    setIsLoggingOut(true);

    // Best-effort server-side revocation so the JWT can't be reused if leaked.
    // Fire-and-forget — we still clear local state regardless.
    api.auth.logout().catch(() => {
      /* ignore: token may already be invalid */
    });

    localStorage.removeItem(AUTH_TOKEN_KEY);
    setUser(null);

    setTimeout(() => setIsLoggingOut(false), 100);
  }, [isLoggingOut]);

  // bootstrap from token on first load
  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem(AUTH_TOKEN_KEY) : null;
    if (!token) {
      setLoading(false);
      return;
    }
    api.auth
      .me()
      .then((u) => setUser(u))
      .catch(() => {
        localStorage.removeItem(AUTH_TOKEN_KEY);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  // Listen for global 401 events
  useEffect(() => {
    const handleUnauthorized = () => {
      logout();
    };

    if (typeof window !== "undefined") {
      window.addEventListener(EVENTS.AUTH_UNAUTHORIZED, handleUnauthorized);
      return () => {
        window.removeEventListener(EVENTS.AUTH_UNAUTHORIZED, handleUnauthorized);
      };
    }
  }, [logout]);

  const login = useCallback((token: string, u: User) => {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    setUser(u);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const u = await api.auth.me();
      setUser(u);
    } finally {
      setLoading(false);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: !!user,
      login,
      logout,
      refresh,
    }),
    [user, loading, login, logout, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
