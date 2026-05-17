"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      console.error("Route error:", error);
    }
  }, [error]);

  return (
    <main className="min-h-[60vh] flex items-center justify-center px-6">
      <div className="max-w-md text-center space-y-6">
        <div className="mx-auto h-16 w-16 rounded-2xl bg-red-50 flex items-center justify-center">
          <span className="text-3xl">!</span>
        </div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Something went wrong
        </h1>
        <p className="text-sm text-slate-600">
          We hit an unexpected error loading this page. The team has been notified
          if error tracking is enabled.
        </p>
        {error.digest && (
          <p className="text-xs text-slate-400">Reference: {error.digest}</p>
        )}
        <div className="flex justify-center gap-3 pt-2">
          <button
            type="button"
            onClick={reset}
            className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white"
          >
            Try again
          </button>
          <Link
            href="/"
            className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
          >
            Go home
          </Link>
        </div>
      </div>
    </main>
  );
}
