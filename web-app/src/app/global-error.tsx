"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      console.error("Global error:", error);
    }
  }, [error]);

  return (
    <html lang="en">
      <body>
        <main style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "1.5rem",
          fontFamily: "system-ui, sans-serif",
          backgroundColor: "#f8fafc",
        }}>
          <div style={{ maxWidth: "28rem", textAlign: "center" }}>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 600, color: "#0f172a", marginBottom: "0.75rem" }}>
              Something went very wrong
            </h1>
            <p style={{ color: "#475569", marginBottom: "1.5rem", fontSize: "0.9rem" }}>
              The application encountered a critical error. Please try reloading.
            </p>
            <button
              type="button"
              onClick={reset}
              style={{
                background: "#0f172a",
                color: "white",
                padding: "0.5rem 1rem",
                borderRadius: "0.375rem",
                fontWeight: 500,
                border: "none",
                cursor: "pointer",
              }}
            >
              Reload
            </button>
          </div>
        </main>
      </body>
    </html>
  );
}
