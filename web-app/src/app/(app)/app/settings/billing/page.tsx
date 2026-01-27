"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ErrorAlert } from "@/components/Alert";
import { CardSkeleton } from "@/components/Skeleton";

const CURRENCIES = [
  { code: "USD", name: "US Dollar" },
  { code: "EUR", name: "Euro" },
  { code: "GBP", name: "British Pound" },
  { code: "LBP", name: "Lebanese Pound" },
  { code: "AED", name: "UAE Dirham" },
];

const LOCALES = [
  { code: "en-US", name: "English (US)" },
  { code: "en-GB", name: "English (UK)" },
  { code: "fr-FR", name: "French" },
  { code: "ar-LB", name: "Arabic (Lebanon)" },
];

export default function BillingSettingsPage() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: api.settings.getOrg
  });

  const [currency, setCurrency] = useState("");
  const [locale, setLocale] = useState("");

  // Sync form state with fetched data
  useEffect(() => {
    if (settingsQuery.data) {
      setCurrency(settingsQuery.data.default_currency || "USD");
      setLocale(settingsQuery.data.default_locale || "en-US");
    }
  }, [settingsQuery.data]);

  const updateMutation = useMutation({
    mutationFn: (payload: { default_currency?: string; default_locale?: string }) =>
      api.settings.updateOrg(payload),
    onSuccess: () => {
      toast.success("Settings saved successfully.");
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Unable to update settings";
      toast.error(message);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate({
      default_currency: currency,
      default_locale: locale
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Billing & Settings</h1>
        <p className="text-sm text-slate-500 mt-1">
          Manage your subscription and regional preferences
        </p>
      </header>

      {/* Error State */}
      {settingsQuery.error && (
        <ErrorAlert error={settingsQuery.error} onRetry={() => settingsQuery.refetch()} />
      )}

      {/* Loading State */}
      {settingsQuery.isLoading && (
        <div className="grid gap-6 lg:grid-cols-2">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      )}

      {/* Settings Content */}
      {settingsQuery.data && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Current Plan Card */}
          <div className="rounded-xl border bg-white p-6 shadow-sm">
            <h2 className="font-semibold text-slate-900 mb-4">Current Plan</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-lg bg-slate-50">
                <div>
                  <p className="font-medium text-slate-900">Starter Plan</p>
                  <p className="text-sm text-slate-500">Free during beta</p>
                </div>
                <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-sm font-medium rounded-full">
                  Active
                </span>
              </div>
              <div className="text-sm text-slate-600 space-y-2">
                <p className="flex items-center gap-2">
                  <span className="text-emerald-500">✓</span>
                  Unlimited uploads
                </p>
                <p className="flex items-center gap-2">
                  <span className="text-emerald-500">✓</span>
                  Basic analytics
                </p>
                <p className="flex items-center gap-2">
                  <span className="text-emerald-500">✓</span>
                  Inventory tracking
                </p>
              </div>
              <Button variant="outline" className="w-full" disabled>
                Upgrade coming soon
              </Button>
            </div>
          </div>

          {/* Regional Settings Card */}
          <div className="rounded-xl border bg-white p-6 shadow-sm">
            <h2 className="font-semibold text-slate-900 mb-4">Regional Settings</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="currency">Default Currency</Label>
                <select
                  id="currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                >
                  {CURRENCIES.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.code} - {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="locale">Display Locale</Label>
                <select
                  id="locale"
                  value={locale}
                  onChange={(e) => setLocale(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                >
                  {LOCALES.map((l) => (
                    <option key={l.code} value={l.code}>
                      {l.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="w-full"
                >
                  {updateMutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Current Settings Display */}
      {settingsQuery.data && (
        <div className="rounded-xl border bg-slate-50 p-6">
          <h3 className="font-medium text-slate-900 mb-3">Current Configuration</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 text-sm">
            <div>
              <span className="text-slate-500">Currency</span>
              <p className="font-medium text-slate-900">{settingsQuery.data.default_currency}</p>
            </div>
            <div>
              <span className="text-slate-500">Locale</span>
              <p className="font-medium text-slate-900">{settingsQuery.data.default_locale}</p>
            </div>
            <div>
              <span className="text-slate-500">Initial Investment</span>
              <p className="font-medium text-slate-900">${settingsQuery.data.total_initial_investment}</p>
            </div>
            <div>
              <span className="text-slate-500">Starting Cash</span>
              <p className="font-medium text-slate-900">${settingsQuery.data.starting_cash_balance}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
