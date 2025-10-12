// src/app/providers.tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { AuthProvider } from "@/hooks/useAuth";

export function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(() => new QueryClient());

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_USE_MSW !== "0") {
      import("@/mocks/browser").then(({ worker }) =>
        worker.start({ onUnhandledRequest: "bypass" })
      );
    }
  }, []);

  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}
