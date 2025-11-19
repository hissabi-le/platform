"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { api } from "@/lib/api";

export default function BillingSettingsPage() {
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: api.settings.getOrg });
  const [currency, setCurrency] = useState("USD");
  const [locale, setLocale] = useState("en");

  const updateMutation = useMutation({
    mutationFn: (payload: { default_currency?: string; default_locale?: string }) =>
      api.settings.updateOrg(payload),
    onSuccess: () => {
      toast.success("Settings saved.");
      settingsQuery.refetch();
    },
    onError: () => toast.error("Unable to update settings."),
  });

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Billing & plan</h1>
        <p className="text-sm text-gray-500">Manage subscription preferences and default regional settings.</p>
      </header>

      {settingsQuery.isLoading && <p className="text-sm text-gray-500">Loading organisation settings…</p>}
      {settingsQuery.data && (
        <div className="space-y-4 rounded-xl border bg-white p-6 shadow-sm">
          <div className="space-y-3 text-sm text-gray-600">
            <div>
              <span className="font-medium text-slate-700">Current plan</span>
              <p className="text-xs text-gray-500">Starter – upgrade coming soon.</p>
            </div>
            <div>
              <span className="font-medium text-slate-700">Default currency</span>
              <p className="text-xs text-gray-500">{settingsQuery.data.default_currency}</p>
            </div>
            <div>
              <span className="font-medium text-slate-700">Default locale</span>
              <p className="text-xs text-gray-500">{settingsQuery.data.default_locale}</p>
            </div>
          </div>

          <form
            className="grid gap-3 text-sm"
            onSubmit={(event) => {
              event.preventDefault();
              updateMutation.mutate({ default_currency: currency, default_locale: locale });
            }}
          >
            <label className="space-y-1">
              <span className="text-slate-600">Update currency</span>
              <input
                value={currency}
                onChange={(event) => setCurrency(event.target.value)}
                className="w-full rounded border px-3 py-2"
              />
            </label>
            <label className="space-y-1">
              <span className="text-slate-600">Update locale</span>
              <input
                value={locale}
                onChange={(event) => setLocale(event.target.value)}
                className="w-full rounded border px-3 py-2"
              />
            </label>
            <button
              type="submit"
              className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? "Saving…" : "Save changes"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
