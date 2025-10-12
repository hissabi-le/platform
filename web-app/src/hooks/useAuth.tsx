// src/hooks/useAuth.ts
"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

type User = { id: number; email: string; org_id: number };

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

  // bootstrap from token on first load
  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("hissabi_token") : null;
    if (!token) {
      setLoading(false);
      return;
    }
    api.auth
      .me()
      .then((u) => setUser(u))
      .catch(() => {
        localStorage.removeItem("hissabi_token");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback((token: string, u: User) => {
    localStorage.setItem("hissabi_token", token);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    try {
      // fire-and-forget; backend may or may not invalidate server-side
      void api.auth.logout();
    } catch {}
    localStorage.removeItem("hissabi_token");
    setUser(null);
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
