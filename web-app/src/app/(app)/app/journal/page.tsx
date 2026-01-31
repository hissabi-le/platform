"use client";

import { useMemo, useState, useEffect } from "react";
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
  const [entryMode, setEntryMode] = useState<EntryMode>("structured");
  const [structuredEntry, setStructuredEntry] = useState<StructuredEntry>({
    entry_type: "revenue",
    item_name: "",
    quantity: "",
    unit: "unit",
    unit_cost: "",
    total: "",
  });
  const [resolutionDrafts, setResolutionDrafts] = useState<Record<number, ResolutionDraft>>({});
  const [showBaselineForm, setShowBaselineForm] = useState(false);

  // Auto-calculate total when quantity or unit_cost changes
  useEffect(() => {
    const qty = parseFloat(structuredEntry.quantity);
    const cost = parseFloat(structuredEntry.unit_cost);
    if (!isNaN(qty) && !isNaN(cost) && structuredEntry.quantity && structuredEntry.unit_cost) {
      setStructuredEntry(prev => ({
        ...prev,
        total: (qty * cost).toFixed(2)
      }));
    }
  }, [structuredEntry.quantity, structuredEntry.unit_cost]);

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
      // Invalidate analytics queries so dashboard updates with new data
      qc.invalidateQueries({ queryKey: ["analytics-pnl"] });
      qc.invalidateQueries({ queryKey: ["analytics-receivables"] });
      qc.invalidateQueries({ queryKey: ["analytics-payables"] });
      toast.success("Journal entry saved");
    },
    onError: (error: unknown) => {
      // Extract detailed error message from API response
      let message = "Failed to save journal";
      if (error && typeof error === "object") {
        const apiError = error as { details?: { detail?: string | Array<{ msg: string }> } };
        const detail = apiError.details?.detail;
        if (typeof detail === "string") {
          message = detail;
        } else if (Array.isArray(detail) && detail[0]?.msg) {
          message = detail.map(e => e.msg).join("; ");
        } else if (error instanceof Error) {
          message = error.message;
        }
      }
      toast.error(message);
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
          (item.treat_as_inventory) {
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
    const enableRecipes = form.get("enable_recipes") === "on";

    if (isNaN(Number(initial)) || isNaN(Number(cash)) || isNaN(Number(assets))) {
      toast.error("Please enter valid numbers for all financial fields.");
      return;
    }

    updateSettings.mutate({
      total_initial_investment: initial,
      starting_cash_balance: cash,
      current_assets_value: assets,
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
      const verb = entry_type === "revenue" ? "sold" : "paid";
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

  // Check if baselines have been configured (any value > 0)
  const baselinesConfigured = settingsDefaults && (
    Number(settingsDefaults.total_initial_investment) > 0 ||
    Number(settingsDefaults.starting_cash_balance) > 0 ||
    Number(settingsDefaults.current_assets_value) > 0
  );

  const formattedTotals = useMemo(() => {
    if (!totals) return null;
    return [
      { label: "Revenue", value: totals.revenue, accent: "text-emerald-500" },
      { label: "Cost", value: totals.cost, accent: "text-red-500" },
      { label: "Net", value: totals.net, accent: "text-foreground" },
      { label: "Cumulative Net", value: totals.cumulative_net, accent: "text-foreground" },
    ];
  }, [totals]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-wrap gap-4 items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Journal</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Log daily activity in any language - we reconcile everything automatically
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div>
            <Label htmlFor="journal-date" className="text-sm text-muted-foreground">Date</Label>
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
      <section className="rounded-xl border bg-card text-card-foreground p-6 shadow-sm">
        <header className="flex items-start justify-between mb-4">
          <div>
            <h2 className="font-semibold text-foreground">Baseline Setup</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {baselinesConfigured
                ? "Your financial baselines are configured"
                : "Configure your organisation-level financial anchors"}
            </p>
          </div>
          {baselinesConfigured && !showBaselineForm && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowBaselineForm(true)}
            >
              Edit Settings
            </Button>
          )}
        </header>

        {settingsQuery.isLoading && (
          <div className="grid gap-4 md:grid-cols-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        )}

        {/* Collapsed summary view when configured */}
        {settingsDefaults && baselinesConfigured && !showBaselineForm && (
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg bg-muted p-4">
              <p className="text-sm text-muted-foreground">Initial Investment</p>
              <p className="text-lg font-semibold text-foreground">${settingsDefaults.total_initial_investment}</p>
            </div>
            <div className="rounded-lg bg-muted p-4">
              <p className="text-sm text-muted-foreground">Starting Cash</p>
              <p className="text-lg font-semibold text-foreground">${settingsDefaults.starting_cash_balance}</p>
            </div>
            <div className="rounded-lg bg-muted p-4">
              <p className="text-sm text-muted-foreground">Current Assets</p>
              <p className="text-lg font-semibold text-foreground">${settingsDefaults.current_assets_value}</p>
            </div>
          </div>
        )}

        {/* Expanded form view when editing or not configured */}
        {settingsDefaults && (!baselinesConfigured || showBaselineForm) && (
          <form onSubmit={(e) => {
            handleSettingsSubmit(e);
            // Collapse form after successful save
            if (baselinesConfigured) setShowBaselineForm(false);
          }} className="space-y-4">
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

            <div className="flex gap-2">
              <Button type="submit" disabled={updateSettings.isPending}>
                {updateSettings.isPending ? "Saving..." : "Save Settings"}
              </Button>
              {baselinesConfigured && showBaselineForm && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowBaselineForm(false)}
                >
                  Cancel
                </Button>
              )}
            </div>
          </form>
        )}
      </section>


      {/* Main Content Grid */}
      <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        {/* Journal Entry Form */}
        <div className="rounded-xl border bg-card text-card-foreground p-6 shadow-sm space-y-4">
          <header className="flex items-start justify-between">
            <div>
              <h2 className="font-semibold text-foreground">Daily Entry</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Log activity using any mix of English, French, or Arabic
              </p>
            </div>
            {/* Toggle Switch */}
            <div className="flex items-center gap-2 bg-muted rounded-lg p-1">
              <button
                onClick={() => setEntryMode("freetext")}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${entryMode === "freetext"
                  ? "bg-background shadow text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground"
                  }`}
              >
                Free Text
              </button>
              <button
                onClick={() => setEntryMode("structured")}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${entryMode === "structured"
                  ? "bg-background shadow text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground"
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
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
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
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="revenue">Sale / Revenue</option>
                  <option value="cost">Expense / Cost</option>
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
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
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
        <div className="rounded-xl border bg-card text-card-foreground p-6 shadow-sm">
          <h3 className="font-semibold text-foreground mb-4">Today&apos;s Summary</h3>

          {dayQuery.isLoading && (
            <div className="space-y-3">
              <Skeleton className="h-8" />
              <Skeleton className="h-8" />
              <Skeleton className="h-8" />
            </div>
          )}

          {!dayQuery.isLoading && !formattedTotals && (
            <div className="text-center py-8 text-muted-foreground">
              <svg className="w-12 h-12 mx-auto mb-3 text-muted-foreground/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <p className="text-sm">Save a journal entry to see totals</p>
            </div>
          )}

          {formattedTotals && (
            <div className="space-y-3">
              {formattedTotals.map((item) => (
                <div key={item.label} className="flex justify-between items-center py-2 border-b border-border last:border-0">
                  <span className="text-sm text-muted-foreground">{item.label}</span>
                  <span className={`font-semibold ${item.accent}`}>{formatCurrency(item.value)}</span>
                </div>
              ))}
              <div className="flex justify-between items-center py-2 pt-3 border-t border-border">
                <span className="text-sm text-muted-foreground">ROI</span>
                <span className="font-semibold text-foreground">
                  {totals?.roi !== undefined && totals?.roi !== null ? `${totals.roi.toFixed(2)}%` : "—"}
                </span>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Clarifications Section */}
      <section className="rounded-xl border bg-card text-card-foreground p-6 shadow-sm">
        <header className="mb-4">
          <h3 className="font-semibold text-foreground">Clarifications</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Resolve classification questions to keep inventory and costs accurate
          </p>
        </header>

        {clarifications.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-secondary flex items-center justify-center">
              <svg className="w-6 h-6 text-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-sm text-muted-foreground">No clarifications pending</p>
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
    <div className="rounded-lg border bg-accent/50 border-accent p-4 space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center flex-shrink-0">
          <span className="text-accent-foreground text-lg">?</span>
        </div>
        <div>
          <p className="font-medium text-foreground">{clarification.question}</p>
          <p className="text-sm text-muted-foreground mt-1">
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
            className="text-primary focus:ring-ring"
          />
          <span className="text-sm text-foreground">Track as inventory</span>
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
            className="text-primary focus:ring-ring"
          />
          <span className="text-sm text-foreground">Expense today</span>
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
