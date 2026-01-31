// src/app/providers.tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, Component } from "react";
import type { ReactNode } from "react";
import { AuthProvider } from "@/hooks/useAuth";
import { ThemeProvider } from "next-themes";

// Error Boundary Component
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log to error reporting service (e.g., Sentry)
    console.error("React Error Boundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md p-8 bg-white rounded-xl shadow-sm border text-center">
            <h1 className="text-xl font-semibold text-gray-900 mb-4">
              Something went wrong
            </h1>
            <p className="text-gray-600 mb-6">
              We encountered an unexpected error. Please refresh the page to try again.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-slate-900 text-white rounded-lg font-medium"
            >
              Refresh page
            </button>
            {process.env.NODE_ENV === "development" && this.state.error && (
              <pre className="mt-4 p-4 bg-red-50 text-red-700 text-xs text-left overflow-auto rounded">
                {this.state.error.message}
              </pre>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Create QueryClient with production-ready configuration
function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Don't retry on 4xx errors (client errors)
        retry: (failureCount, error) => {
          if (error instanceof Error && "status" in error) {
            const status = (error as { status: number }).status;
            if (status >= 400 && status < 500) return false;
          }
          return failureCount < 2;
        },
        // Data considered fresh for 30 seconds
        staleTime: 30 * 1000,
        // Keep unused data in cache for 5 minutes
        gcTime: 5 * 60 * 1000,
        // Don't refetch on window focus in production (too aggressive)
        refetchOnWindowFocus: process.env.NODE_ENV === "development",
      },
      mutations: {
        // Don't retry mutations by default
        retry: false,
      },
    },
  });
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(() => createQueryClient());

  useEffect(() => {
    // Only enable MSW when explicitly opted in (development/testing)
    if (process.env.NEXT_PUBLIC_USE_MSW === "1") {
      import("@/mocks/browser").then(({ worker }) =>
        worker.start({ onUnhandledRequest: "bypass" })
      );
    }
  }, []);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={qc}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
