"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

const MAX_POLL_ATTEMPTS = 10;
const POLL_INTERVAL_MS = 1500;

export default function BillingSuccessPage() {
  const queryClient = useQueryClient();
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let attempts = 0;
    let cancelled = false;

    async function poll() {
      while (!cancelled && attempts < MAX_POLL_ATTEMPTS) {
        attempts += 1;
        try {
          const me = await api.auth.me();
          await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
          await queryClient.invalidateQueries({ queryKey: ["settings"] });
          if (me.plan && me.plan !== "starter" && me.plan !== "personal") {
            setConfirmed(true);
            return;
          }
        } catch (err) {
          if (err instanceof Error) setError(err.message);
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      }
      if (!cancelled) {
        setConfirmed(true);
      }
    }

    poll();
    return () => {
      cancelled = true;
    };
  }, [queryClient]);

  return (
    <div className="mx-auto max-w-lg space-y-6 py-16 text-center">
      <h1 className="text-2xl font-semibold text-slate-900">
        {confirmed ? "You're all set." : "Finalizing your subscription…"}
      </h1>
      <p className="text-sm text-slate-600">
        {confirmed
          ? "Thanks for upgrading. Your new plan is active and ready to use."
          : "We're confirming your payment with Stripe. This usually takes a few seconds."}
      </p>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex justify-center gap-3">
        <Link
          href="/settings/billing"
          className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
        >
          Back to billing
        </Link>
        <Link
          href="/"
          className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
