"use client";

import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type { JournalClarification, JournalDayResponse, JournalEntry, OrganisationSettings } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorAlert, Alert } from "@/components/Alert";
import { Skeleton } from "@/components/Skeleton";
import { formatCurrency, getUTCDateString } from "@/lib/format";

const isoToday = getUTCDateString();

type EntryMode = "freetext" | "structured";

type StructuredEntry = {
  entry_type: "revenue" | "cost" | "inventory_purchase" | "inventory_use";
  item_name: string;
  quantity: string;
  unit: string;
  unit_cost: string;
  total: string;
};

type ResolutionDraft = {
  entry_id?: number | null | undefined;
  treat_as_inventory: "inventory" | "expense";
  quantity?: string;
  unit?: string;
  unit_cost?: string;
};

export default function JournalPage() {
  const qc = useQueryClient();
  const [selectedDate, setSelectedDate] = useState<string>(isoToday);
  const [notes, setNotes] = useState<string>("");
  const [entryMode, setEntryMode] = useState<EntryMode>("freetext");
  const [structuredEntry, setStructuredEntry] = useState<StructuredEntry>({
    entry_type: "revenue",
    item_name: "",
    quantity: "",
    unit: "unit",
    unit_cost: "",
    total: "",
  });
  const [resolutionDrafts, setResolutionDrafts] = useState<Record<number, ResolutionDraft>>({});

  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.settings.getOrg(),
  });

  const dayQuery = useQuery({
    queryKey: ["journal-day", selectedDate],
    queryFn: () => api.journal.getDay(selectedDate),
  });

  const updateSettings = useMutation({
    mutationFn: (payload: Partial<OrganisationSettings>) => api.settings.updateOrg(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      toast.success("Organisation settings saved");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Failed to save settings");
    },
  });

  const saveDay = useMutation({
    mutationFn: (body: { raw_text: string; date: string }) => api.journal.saveDay({ ...body, commit: true }),
    onSuccess: (data) => {
      qc.setQueryData(["journal-day", selectedDate], data);
      setNotes("");
      toast.success("Journal entry saved");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Failed to save journal");
    },
  });

  const resolveDay = useMutation({
    mutationFn: (payload: { dayId: number; resolutions: ResolutionDraft[] }) =>
      api.journal.resolve(payload.dayId, {
        resolutions: payload.resolutions.map((item) => {
          // Only include fields that have values to avoid Pydantic validation errors
          const resolution: Record<string, unknown> = {
            entry_id: item.entry_id,
          };
          if (item.treat_as_inventory) {
            resolution.treat_as_inventory = item.treat_as_inventory === "inventory";
          }
          if (item.quantity && item.quantity.trim()) {
            resolution.quantity = item.quantity;
          }
          if (item.unit && item.unit.trim()) {
            resolution.unit = item.unit;
          }
          if (item.unit_cost && item.unit_cost.trim()) {
            resolution.unit_cost = item.unit_cost;
          }
          return resolution;
        }),
      }),
    onSuccess: (data) => {
      qc.setQueryData(["journal-day", selectedDate], data);
      setResolutionDrafts({});
      toast.success("Clarifications applied");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Failed to apply clarifications");
    },
  });

  const currentDay: JournalDayResponse | null | undefined = dayQuery.data;
  const clarifications = currentDay?.clarifications ?? [];
  const entries = currentDay?.entries ?? [];
  const totals = currentDay?.totals;

  const handleSettingsSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);

    const initial = form.get("initial") as string;
    const cash = form.get("cash") as string;
    const assets = form.get("assets") as string;
    const inventoryMode = form.get("inventory_mode") as "immediate" | "on_shipment" | "manual";
    const enableRecipes = form.get("enable_recipes") === "on";

    if (isNaN(Number(initial)) || isNaN(Number(cash)) || isNaN(Number(assets))) {
      toast.error("Please enter valid numbers for all financial fields.");
      return;
    }

    updateSettings.mutate({
      total_initial_investment: initial,
      starting_cash_balance: cash,
      current_assets_value: assets,
      inventory_deduction_mode: inventoryMode,
      enable_recipes: enableRecipes,
    });
  };

  const handleSaveDay = () => {
    if (entryMode === "freetext") {
      if (!notes.trim()) {
        toast.error("Please enter at least one line");
        return;
      }
      saveDay.mutate({ raw_text: notes, date: selectedDate });
    } else {
      // Structured mode: build a line from the form
      const { entry_type, item_name, quantity, unit, total } = structuredEntry;
      if (!item_name.trim() || !total.trim()) {
        toast.error("Please fill in at least item name and total");
        return;
      }
      const verb = entry_type === "revenue" ? "sold"
        : entry_type === "inventory_purchase" ? "bought"
          : entry_type === "inventory_use" ? "used"
            : "paid";
      const qtyPart = quantity ? `${quantity} ${unit || 'unit'}` : '';
      const line = `${verb} ${qtyPart} ${item_name} for ${total}$`.trim();
      saveDay.mutate({ raw_text: line, date: selectedDate });
      // Reset form
      setStructuredEntry({
        entry_type: "revenue",
        item_name: "",
        quantity: "",
        unit: "unit",
        unit_cost: "",
        total: "",
      });
    }
  };

  const handleResolve = () => {
    if (!currentDay || !currentDay.journal_day.id) {
      toast.error("No saved journal day to resolve");
      return;
    }
    const drafts = Object.values(resolutionDrafts).filter((draft) => draft.entry_id);
    if (!drafts.length) {
      toast.error("Select at least one clarification to resolve");
      return;
    }
    resolveDay.mutate({ dayId: currentDay.journal_day.id, resolutions: drafts });
  };

  const settingsDefaults = settingsQuery.data;

  const formattedTotals = useMemo(() => {
    if (!totals) return null;
    return [
      { label: "Revenue", value: totals.revenue, accent: "text-emerald-600" },
      { label: "Cost", value: totals.cost, accent: "text-rose-600" },
      { label: "Net", value: totals.net, accent: "text-slate-900" },
      { label: "Cumulative Net", value: totals.cumulative_net, accent: "text-slate-900" },
    ];
  }, [totals]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-wrap gap-4 items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Journal</h1>
          <p className="text-sm text-slate-500 mt-1">
            Log daily activity in any language - we reconcile everything automatically
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div>
            <Label htmlFor="journal-date" className="text-sm text-slate-600">Date</Label>
            <Input
              id="journal-date"
              type="date"
              value={selectedDate}
              onChange={(e) => {
                setSelectedDate(e.target.value);
                setResolutionDrafts({});
              }}
              className="mt-1 w-40"
            />
          </div>
          <Button
            variant="outline"
            onClick={() => dayQuery.refetch()}
            disabled={dayQuery.isFetching}
          >
            {dayQuery.isFetching ? "Loading..." : "Refresh"}
          </Button>
        </div>
      </header>

      {/* Error State */}
      {dayQuery.error && <ErrorAlert error={dayQuery.error} onRetry={() => dayQuery.refetch()} />}
      {settingsQuery.error && <ErrorAlert error={settingsQuery.error} onRetry={() => settingsQuery.refetch()} />}

      {/* Baseline Settings */}
      <section className="rounded-xl border bg-white p-6 shadow-sm">
        <header className="mb-4">
          <h2 className="font-semibold text-slate-900">Baseline Setup</h2>
          <p className="text-sm text-slate-500 mt-1">Configure your organisation-level financial anchors</p>
        </header>

        {settingsQuery.isLoading && (
          <div className="grid gap-4 md:grid-cols-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        )}

        {settingsDefaults && (
          <form onSubmit={handleSettingsSubmit} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="initial">Total Initial Investment</Label>
                <Input
                  id="initial"
                  name="initial"
                  type="number"
                  step="0.01"
                  defaultValue={settingsDefaults.total_initial_investment ?? "0"}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cash">Starting Cash Balance</Label>
                <Input
                  id="cash"
                  name="cash"
                  type="number"
                  step="0.01"
                  defaultValue={settingsDefaults.starting_cash_balance ?? "0"}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="assets">Current Assets / Inventory</Label>
                <Input
                  id="assets"
                  name="assets"
                  type="number"
                  step="0.01"
                  defaultValue={settingsDefaults.current_assets_value ?? "0"}
                />
              </div>
            </div>

            {/* Inventory Settings */}
            <div className="pt-4 border-t border-slate-200">
              <h3 className="text-sm font-medium text-slate-700 mb-3">Inventory Settings</h3>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="inventory_mode">When to Deduct Inventory</Label>
                  <select
                    id="inventory_mode"
                    name="inventory_mode"
                    defaultValue={settingsDefaults.inventory_deduction_mode ?? "immediate"}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                  >
                    <option value="immediate">On Sale (Physical Retail)</option>
                    <option value="on_shipment">On Shipment (E-commerce)</option>
                    <option value="manual">Manual Only (Services/Drop-shipping)</option>
                  </select>
                  <p className="text-xs text-slate-500">
                    Choose when inventory should be automatically reduced
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="enable_recipes">Enable Recipes (F&amp;B)</Label>
                  <div className="flex items-center gap-2 mt-2">
                    <input
                      type="checkbox"
                      id="enable_recipes"
                      name="enable_recipes"
                      defaultChecked={settingsDefaults.enable_recipes ?? false}
                      className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                    />
                    <span className="text-sm text-slate-600">
                      Define recipes to auto-deduct ingredients when selling products
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <Button type="submit" disabled={updateSettings.isPending}>
              {updateSettings.isPending ? "Saving..." : "Save Settings"}
            </Button>
          </form>
        )}
      </section>

      {/* Main Content Grid */}
      <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        {/* Journal Entry Form */}
        <div className="rounded-xl border bg-white p-6 shadow-sm space-y-4">
          <header className="flex items-start justify-between">
            <div>
              <h2 className="font-semibold text-slate-900">Daily Entry</h2>
              <p className="text-sm text-slate-500 mt-1">
                Log activity using any mix of English, French, or Arabic
              </p>
            </div>
            {/* Toggle Switch */}
            <div className="flex items-center gap-2 bg-slate-100 rounded-lg p-1">
              <button
                onClick={() => setEntryMode("freetext")}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${entryMode === "freetext"
                  ? "bg-white shadow text-slate-900"
                  : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                Free Text
              </button>
              <button
                onClick={() => setEntryMode("structured")}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${entryMode === "structured"
                  ? "bg-white shadow text-slate-900"
                  : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                Form
              </button>
            </div>
          </header>

          {entryMode === "freetext" ? (
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={10}
                placeholder="sold 5 coffees for $25&#10;bought milk $6&#10;paid rent $400"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Entry Type */}
              <div className="space-y-2">
                <Label htmlFor="entry-type">Type</Label>
                <select
                  id="entry-type"
                  value={structuredEntry.entry_type}
                  onChange={(e) => setStructuredEntry(prev => ({ ...prev, entry_type: e.target.value as StructuredEntry["entry_type"] }))}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                >
                  <option value="revenue">Sale / Revenue</option>
                  <option value="inventory_purchase">Purchase (Inventory)</option>
                  <option value="cost">Expense / Cost</option>
                  <option value="inventory_use">Use Inventory</option>
                </select>
              </div>
              {/* Item Name */}
              <div className="space-y-2">
                <Label htmlFor="item-name">Item Name</Label>
                <Input
                  id="item-name"
                  value={structuredEntry.item_name}
                  onChange={(e) => setStructuredEntry(prev => ({ ...prev, item_name: e.target.value }))}
                  placeholder="e.g., Coffee, Snickers, Rent"
                />
              </div>
              {/* Quantity + Unit + Total row */}
              <div className="grid grid-cols-4 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="qty">Quantity</Label>
                  <Input
                    id="qty"
                    type="number"
                    value={structuredEntry.quantity}
                    onChange={(e) => setStructuredEntry(prev => ({ ...prev, quantity: e.target.value }))}
                    placeholder="10"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="unit">Unit</Label>
                  <select
                    id="unit"
                    value={structuredEntry.unit}
                    onChange={(e) => setStructuredEntry(prev => ({ ...prev, unit: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                  >
                    <option value="unit">unit</option>
                    <option value="kg">kg</option>
                    <option value="g">g</option>
                    <option value="l">liter</option>
                    <option value="dozen">dozen</option>
                    <option value="piece">piece</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="unit-cost">Unit Cost</Label>
                  <Input
                    id="unit-cost"
                    type="number"
                    step="0.01"
                    value={structuredEntry.unit_cost}
                    onChange={(e) => setStructuredEntry(prev => ({ ...prev, unit_cost: e.target.value }))}
                    placeholder="5.00"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="total">Total ($)</Label>
                  <Input
                    id="total"
                    type="number"
                    step="0.01"
                    value={structuredEntry.total}
                    onChange={(e) => setStructuredEntry(prev => ({ ...prev, total: e.target.value }))}
                    placeholder="50.00"
                  />
                </div>
              </div>
            </div>
          )}

          <Button
            onClick={handleSaveDay}
            disabled={saveDay.isPending || (entryMode === "freetext" ? !notes.trim() : !structuredEntry.item_name.trim())}
            className="w-full"
          >
            {saveDay.isPending ? "Saving..." : "Save Entry"}
          </Button>
        </div>

        {/* Totals Card */}
        <div className="rounded-xl border bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-900 mb-4">Today&apos;s Summary</h3>

          {dayQuery.isLoading && (
            <div className="space-y-3">
              <Skeleton className="h-8" />
              <Skeleton className="h-8" />
              <Skeleton className="h-8" />
            </div>
          )}

          {!dayQuery.isLoading && !formattedTotals && (
            <div className="text-center py-8 text-slate-500">
              <svg className="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <p className="text-sm">Save a journal entry to see totals</p>
            </div>
          )}

          {formattedTotals && (
            <div className="space-y-3">
              {formattedTotals.map((item) => (
                <div key={item.label} className="flex justify-between items-center py-2 border-b last:border-0">
                  <span className="text-sm text-slate-600">{item.label}</span>
                  <span className={`font-semibold ${item.accent}`}>{formatCurrency(item.value)}</span>
                </div>
              ))}
              <div className="flex justify-between items-center py-2 pt-3 border-t">
                <span className="text-sm text-slate-600">ROI</span>
                <span className="font-semibold text-slate-900">
                  {totals?.roi !== undefined && totals?.roi !== null ? `${totals.roi.toFixed(2)}%` : "—"}
                </span>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Clarifications Section */}
      <section className="rounded-xl border bg-white p-6 shadow-sm">
        <header className="mb-4">
          <h3 className="font-semibold text-slate-900">Clarifications</h3>
          <p className="text-sm text-slate-500 mt-1">
            Resolve classification questions to keep inventory and costs accurate
          </p>
        </header>

        {clarifications.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-emerald-100 flex items-center justify-center">
              <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-sm text-slate-500">No clarifications pending</p>
          </div>
        ) : (
          <div className="space-y-4">
            {clarifications.map((item) => {
              // Find the matching entry to pre-fill data
              const matchingEntry = entries.find(e => e.id === item.entry_id);
              return (
                <ClarificationCard
                  key={item.entry_id ?? item.question}
                  clarification={item}
                  entry={matchingEntry}
                  onChange={(draft) =>
                    setResolutionDrafts((prev) => ({
                      ...prev,
                      [draft.entry_id ?? -1]: draft,
                    }))
                  }
                />
              );
            })}
            <Button
              onClick={handleResolve}
              disabled={resolveDay.isPending || Object.keys(resolutionDrafts).length === 0}
            >
              {resolveDay.isPending ? "Applying..." : "Apply Selections"}
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}

type ClarificationCardProps = {
  clarification: JournalClarification;
  entry?: JournalEntry;
  onChange: (draft: ResolutionDraft) => void;
};

function ClarificationCard({ clarification, entry, onChange }: ClarificationCardProps) {
  // Pre-fill from entry data if available
  const [treatment, setTreatment] = useState<"inventory" | "expense">(
    entry?.entry_type === "inventory_purchase" || entry?.entry_type === "inventory_use" ? "inventory" : "expense"
  );
  const [quantity, setQuantity] = useState<string>(entry?.quantity?.toString() || "");
  const [unit, setUnit] = useState<string>(entry?.unit || "unit");
  const [unitCost, setUnitCost] = useState<string>(entry?.unit_cost?.toString() || "");

  const disabled = clarification.entry_id === undefined || clarification.entry_id === null;

  const emitChange = (
    next: Partial<Pick<ResolutionDraft, "treat_as_inventory" | "quantity" | "unit" | "unit_cost">>,
  ) => {
    onChange({
      entry_id: clarification.entry_id,
      treat_as_inventory: next.treat_as_inventory ?? treatment,
      quantity: next.quantity ?? quantity,
      unit: next.unit ?? unit,
      unit_cost: next.unit_cost ?? unitCost,
    });
  };

  return (
    <div className="rounded-lg border bg-amber-50 border-amber-200 p-4 space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
          <span className="text-amber-700 text-lg">?</span>
        </div>
        <div>
          <p className="font-medium text-amber-900">{clarification.question}</p>
          <p className="text-sm text-amber-700 mt-1">
            Category: {clarification.category || "Uncategorized"} • Type: {clarification.entry_type}
          </p>
        </div>
      </div>

      <div className="flex gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name={`clar-${clarification.entry_id}`}
            value="inventory"
            checked={treatment === "inventory"}
            disabled={disabled}
            onChange={() => {
              setTreatment("inventory");
              emitChange({ treat_as_inventory: "inventory" });
            }}
            className="text-amber-600 focus:ring-amber-500"
          />
          <span className="text-sm text-slate-700">Track as inventory</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name={`clar-${clarification.entry_id}`}
            value="expense"
            checked={treatment === "expense"}
            disabled={disabled}
            onChange={() => {
              setTreatment("expense");
              emitChange({ treat_as_inventory: "expense" });
            }}
            className="text-amber-600 focus:ring-amber-500"
          />
          <span className="text-sm text-slate-700">Expense today</span>
        </label>
      </div>

      {treatment === "inventory" && (
        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-1">
            <Label htmlFor={`qty-${clarification.entry_id}`} className="text-xs">Quantity</Label>
            <Input
              id={`qty-${clarification.entry_id}`}
              value={quantity}
              onChange={(e) => {
                setQuantity(e.target.value);
                emitChange({ quantity: e.target.value });
              }}
              disabled={disabled}
              placeholder="10"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`unit-${clarification.entry_id}`} className="text-xs">Unit</Label>
            <Input
              id={`unit-${clarification.entry_id}`}
              value={unit}
              onChange={(e) => {
                setUnit(e.target.value);
                emitChange({ unit: e.target.value });
              }}
              disabled={disabled}
              placeholder="kg"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`cost-${clarification.entry_id}`} className="text-xs">Unit Cost</Label>
            <Input
              id={`cost-${clarification.entry_id}`}
              value={unitCost}
              onChange={(e) => {
                setUnitCost(e.target.value);
                emitChange({ unit_cost: e.target.value });
              }}
              disabled={disabled}
              placeholder="5.00"
            />
          </div>
        </div>
      )}

      {disabled && (
        <Alert variant="warning">
          Save the journal entry first before resolving clarifications.
        </Alert>
      )}
    </div>
  );
}
