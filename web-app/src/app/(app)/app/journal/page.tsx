"use client";

import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type { JournalClarification, JournalDayResponse, OrganisationSettings } from "@/lib/api";

const isoToday = format(new Date(), "yyyy-MM-dd");

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
      qc.invalidateQueries({ queryKey: ["settings"] }).catch(() => undefined);
      toast.success("saved organisation settings");
    },
  });

  const saveDay = useMutation({
    mutationFn: (body: { raw_text: string; date: string }) => api.journal.saveDay({ ...body, commit: true }),
    onSuccess: (data) => {
      qc.setQueryData(["journal-day", selectedDate], data);
      toast.success("journal saved");
    },
  });

  const resolveDay = useMutation({
    mutationFn: (payload: { dayId: number; resolutions: ResolutionDraft[] }) =>
      api.journal.resolve(payload.dayId, {
        resolutions: payload.resolutions.map((item) => ({
          entry_id: item.entry_id,
          treat_as_inventory: item.treat_as_inventory === "inventory",
          quantity: item.quantity,
          unit: item.unit,
          unit_cost: item.unit_cost,
        })),
      }),
    onSuccess: (data) => {
      qc.setQueryData(["journal-day", selectedDate], data);
      toast.success("clarifications applied");
    },
  });

  const currentDay: JournalDayResponse | null | undefined = dayQuery.data;
  const clarifications = currentDay?.clarifications ?? [];
  const totals = currentDay?.totals;

  const handleSettingsSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    updateSettings.mutate({
      total_initial_investment: form.get("initial") as string,
      starting_cash_balance: form.get("cash") as string,
      current_assets_value: form.get("assets") as string,
    });
  };

  const handleSaveDay = () => {
    if (!notes.trim()) {
      toast.error("please enter at least one line");
      return;
    }
    saveDay.mutate({ raw_text: notes, date: selectedDate });
  };

  const handleResolve = () => {
    if (!currentDay || !currentDay.journal_day.id) {
      toast.error("no saved journal day to resolve");
      return;
    }
    const drafts = Object.values(resolutionDrafts).filter((draft) => draft.entry_id);
    if (!drafts.length) {
      toast.error("select at least one clarification to resolve");
      return;
    }
    resolveDay.mutate({ dayId: currentDay.journal_day.id, resolutions: drafts });
  };

  const settingsDefaults = settingsQuery.data;

  const formattedTotals = useMemo(() => {
    if (!totals) {
      return null;
    }
    return [
      { label: "Revenue", value: totals.revenue },
      { label: "Cost", value: totals.cost },
      { label: "Net", value: totals.net },
      { label: "Cumulative Net", value: totals.cumulative_net },
    ];
  }, [totals]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-gray-600">Journal date</label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => {
              setSelectedDate(e.target.value);
              setResolutionDrafts({});
            }}
            className="border rounded px-3 py-2 text-sm"
          />
        </div>
        <button
          onClick={() => dayQuery.refetch()}
          className="px-4 py-2 text-sm bg-black text-white rounded"
        >
          Refresh
        </button>
      </div>

      <section className="border rounded-lg p-4 space-y-4">
        <header>
          <h2 className="text-lg font-semibold">Baseline setup</h2>
          <p className="text-sm text-gray-500">configure your org level financial anchors.</p>
        </header>
        <form onSubmit={handleSettingsSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <label className="text-sm space-y-1">
            <span className="block text-gray-600">Total initial investment</span>
            <input
              name="initial"
              defaultValue={settingsDefaults?.total_initial_investment ?? "0"}
              className="border rounded px-3 py-2 text-sm w-full"
            />
          </label>
          <label className="text-sm space-y-1">
            <span className="block text-gray-600">Starting cash balance</span>
            <input
              name="cash"
              defaultValue={settingsDefaults?.starting_cash_balance ?? "0"}
              className="border rounded px-3 py-2 text-sm w-full"
            />
          </label>
          <label className="text-sm space-y-1">
            <span className="block text-gray-600">Current assets / inventory</span>
            <input
              name="assets"
              defaultValue={settingsDefaults?.current_assets_value ?? "0"}
              className="border rounded px-3 py-2 text-sm w-full"
            />
          </label>
          <div className="md:col-span-3">
            <button
              type="submit"
              className="px-4 py-2 bg-black text-white rounded text-sm"
              disabled={updateSettings.isPending}
            >
              {updateSettings.isPending ? "Saving..." : "Save settings"}
            </button>
          </div>
        </form>
      </section>

      <section className="grid md:grid-cols-[2fr_1fr] gap-6">
        <div className="space-y-3">
          <header>
            <h2 className="text-lg font-semibold">Information sheet</h2>
            <p className="text-sm text-gray-500">log daily activity using any mix of english, french, or arabic.</p>
          </header>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={10}
            placeholder="sold 5 coffees for $25\nbought milk $6\npaid rent $400"
            className="w-full border rounded px-3 py-2 text-sm font-mono"
          />
          <button
            onClick={handleSaveDay}
            className="px-4 py-2 bg-black text-white rounded text-sm"
            disabled={saveDay.isPending}
          >
            {saveDay.isPending ? "Saving..." : "Save day"}
          </button>
        </div>

        <div className="border rounded-lg p-4 space-y-3">
          <h3 className="text-sm font-medium text-gray-600">Totals</h3>
          {formattedTotals ? (
            <ul className="space-y-2 text-sm">
              {formattedTotals.map((item) => (
                <li key={item.label} className="flex justify-between">
                  <span>{item.label}</span>
                  <span className="font-semibold">{item.value}</span>
                </li>
              ))}
              <li className="flex justify-between">
                <span>ROI</span>
                <span className="font-semibold">
                  {totals?.roi !== undefined && totals?.roi !== null ? `${totals.roi.toFixed(2)} %` : "—"}
                </span>
              </li>
            </ul>
          ) : (
            <p className="text-sm text-gray-500">save a journal day to compute totals.</p>
          )}
        </div>
      </section>

      <section className="border rounded-lg p-4 space-y-4">
        <header>
          <h3 className="text-lg font-semibold">Clarifications</h3>
          <p className="text-sm text-gray-500">
            resolve classification questions so inventory and costs stay accurate.
          </p>
        </header>
        {clarifications.length === 0 ? (
          <p className="text-sm text-gray-500">no clarifications pending.</p>
        ) : (
          <div className="space-y-4">
            {clarifications.map((item) => (
              <ClarificationCard
                key={item.entry_id ?? item.question}
                clarification={item}
                onChange={(draft) =>
                  setResolutionDrafts((prev) => ({
                    ...prev,
                    [draft.entry_id ?? -1]: draft,
                  }))
                }
              />
            ))}
            <button
              onClick={handleResolve}
              className="px-4 py-2 bg-black text-white rounded text-sm"
              disabled={resolveDay.isPending}
            >
              {resolveDay.isPending ? "Submitting..." : "Apply selections"}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}

type ClarificationCardProps = {
  clarification: JournalClarification;
  onChange: (draft: ResolutionDraft) => void;
};

function ClarificationCard({ clarification, onChange }: ClarificationCardProps) {
  const [treatment, setTreatment] = useState<"inventory" | "expense">("inventory");
  const [quantity, setQuantity] = useState<string>("");
  const [unit, setUnit] = useState<string>("unit");
  const [unitCost, setUnitCost] = useState<string>("");

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
    <div className="border rounded-lg p-4 space-y-3">
      ******EOF
      <div className="flex gap-4 text-sm">
        <label className="flex items-center gap-2">
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
          />
          <span>Track as inventory</span>
        </label>
        <label className="flex items-center gap-2">
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
          />
          <span>Expense today</span>
        </label>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
        <label className="space-y-1">
          <span className="block text-gray-500">Quantity</span>
          <input
            value={quantity}
            onChange={(e) => {
              setQuantity(e.target.value);
              emitChange({ quantity: e.target.value });
            }}
            disabled={disabled}
            className="border rounded px-2 py-1 w-full"
          />
        </label>
        <label className="space-y-1">
          <span className="block text-gray-500">Unit</span>
          <input
            value={unit}
            onChange={(e) => {
              setUnit(e.target.value);
              emitChange({ unit: e.target.value });
            }}
            disabled={disabled}
            className="border rounded px-2 py-1 w-full"
          />
        </label>
        <label className="space-y-1">
          <span className="block text-gray-500">Unit cost</span>
          <input
            value={unitCost}
            onChange={(e) => {
              setUnitCost(e.target.value);
              emitChange({ unit_cost: e.target.value });
            }}
            disabled={disabled}
            className="border rounded px-2 py-1 w-full"
          />
        </label>
      </div>
      {disabled && (
        <p className="text-xs text-gray-500">
          save this day first before resolving clarifications.
        </p>
      )}
    </div>
  );
}
