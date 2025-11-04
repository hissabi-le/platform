"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import type { JournalDayResponse } from "@/lib/api";
import { api } from "@/lib/api";

const RANGE_OPTIONS = ["1m", "3m", "6m", "1y"] as const;
type RangeOption = (typeof RANGE_OPTIONS)[number];

type NavAction = {
  value: string;
  label: string;
  href?: string;
  message?: string;
};

const NAV_ACTIONS: NavAction[] = [
  { value: "", label: "Choose next action" },
  { value: "analytics", label: "Go to analytics dashboard", href: "/app/analytics" },
  { value: "documents", label: "View generated documents", href: "/app/documents" },
  { value: "inventory", label: "Review inventory snapshot", href: "/app/inventory" },
  { value: "balance-sheet", label: "Generate balance sheet snapshot", message: "Queued balance sheet generation for your latest data." },
  { value: "pnl", label: "Generate profit & loss report", message: "Profit & loss report will refresh shortly." },
];

const todayIso = format(new Date(), "yyyy-MM-dd");

export default function AppDashboard(): JSX.Element {
  const router = useRouter();
  const [range, setRange] = useState<RangeOption>("3m");
  const [journalText, setJournalText] = useState("");
  const [journalDate, setJournalDate] = useState(todayIso);
  const [journalResult, setJournalResult] = useState<JournalDayResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<{ id: number; status: string } | null>(null);
  const [selectedAction, setSelectedAction] = useState("");

  const pnlQuery = useQuery({
    queryKey: ["analytics-pnl", range],
    queryFn: () => api.analytics.pnl(range),
  });

  const saveJournal = useMutation({
    mutationFn: () => api.journal.saveDay({ raw_text: journalText, date: journalDate, commit: true }),
    onSuccess: (data) => {
      setJournalResult(data);
      setJournalText("");
      toast.success("Journal saved. Totals refreshed.");
    },
    onError: () => {
      toast.error("Unable to save journal entry. Please try again.");
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploads.create(file),
    onSuccess: (data) => {
      setUploadResult(data);
      setSelectedAction("");
      toast.success("Upload complete.");
    },
    onError: () => {
      toast.error("Upload failed. Please verify the file and try again.");
    },
  });

  const analyticsCards = useMemo(() => {
    if (!pnlQuery.data) return [];
    const revenue = pnlQuery.data.revenue;
    const expenses = pnlQuery.data.expenses;
    const profit = pnlQuery.data.profit;
    const margin = revenue ? ((profit / revenue) * 100).toFixed(1) : "0";
    return [
      { title: "Revenue", value: revenue.toFixed(2), accent: "bg-emerald-500" },
      { title: "Expenses", value: expenses.toFixed(2), accent: "bg-rose-500" },
      { title: "Net Profit", value: profit.toFixed(2), accent: "bg-slate-900" },
      { title: "Margin", value: `${margin}%`, accent: "bg-amber-500" },
    ];
  }, [pnlQuery.data]);

  const pnlSeries = useMemo(() => pnlQuery.data?.series ?? [], [pnlQuery.data?.series]);
  const formattedSeries = useMemo(
    () =>
      pnlSeries.map((period) => ({
        ...period,
        label: format(parseISO(period.date), "dd/MM/yy"),
      })),
    [pnlSeries]
  );
  const pnlMax = useMemo(() => {
    if (!pnlSeries.length) return 1;
    return Math.max(
      ...pnlSeries.map((item) => Math.max(item.revenue, item.expenses, 1))
    );
  }, [pnlSeries]);
  const profitMax = useMemo(() => {
    if (!pnlSeries.length) return 1;
    return Math.max(...pnlSeries.map((item) => Math.abs(item.revenue - item.expenses)), 1);
  }, [pnlSeries]);

  const journalTotals = journalResult?.totals;
  const journalClarifications = journalResult?.clarifications ?? [];

  const handleUpload = () => {
    if (!selectedFile) {
      toast.error("Please choose a file first.");
      return;
    }
    uploadMutation.mutate(selectedFile);
  };

  const handleActionSelect = (value: string) => {
    setSelectedAction(value);
    const target = NAV_ACTIONS.find((item) => item.value === value);
    if (!target) return;
    if (target.href) {
      router.push(target.href);
    } else if (target.message) {
      toast.info(target.message);
    }
  };

  const handleJournalSubmit = () => {
    if (!journalText.trim()) {
      toast.error("Write a quick summary before saving.");
      return;
    }
    saveJournal.mutate();
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Business overview</h1>
          <p className="text-sm text-gray-500">Track revenue, expenses, and daily activity at a glance.</p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">Analytics range</span>
          <select
            value={range}
            onChange={(event) => setRange(event.target.value as RangeOption)}
            className="rounded border px-3 py-2"
          >
            {RANGE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <section className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-2">
            {analyticsCards.map((card) => (
              <div key={card.title} className="rounded-xl border bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between text-sm text-gray-500">
                  <span>{card.title}</span>
                  <span className={`h-2 w-2 rounded-full ${card.accent}`}></span>
                </div>
                <div className="mt-2 text-2xl font-semibold">${card.value}</div>
              </div>
            ))}
            {!pnlQuery.data && (
              <div className="rounded-xl border bg-white p-6 text-sm text-gray-500 shadow-sm">
                Analytics will appear here once transactions are processed.
              </div>
            )}
          </div>

          <div className="rounded-xl border bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>Revenue vs expenses</span>
              {pnlQuery.isLoading && <span>Loading…</span>}
            </div>
            <div className="mt-4 flex items-end gap-4">
              {formattedSeries.length === 0 && (
                <p className="text-sm text-gray-500">Upload a spreadsheet or add a journal entry to see trends.</p>
              )}
              {formattedSeries.map((period) => {
                const revenueHeight = Math.round((period.revenue / pnlMax) * 100);
                const expenseHeight = Math.round((period.expenses / pnlMax) * 100);
                const label = period.label;
                return (
                  <div key={`${label}-chart`} className="flex flex-1 flex-col items-center">
                    <div className="relative flex h-32 w-full items-end justify-between overflow-hidden rounded bg-gray-100">
                      <div
                        className="ml-1 h-full w-1/2 self-end rounded-t bg-emerald-500"
                        style={{ height: `${revenueHeight}%` }}
                        title={`Revenue ${period.revenue.toFixed(2)}`}
                      ></div>
                      <div
                        className="mr-1 h-full w-1/2 self-end rounded-t bg-rose-500"
                        style={{ height: `${expenseHeight}%` }}
                        title={`Expenses ${period.expenses.toFixed(2)}`}
                      ></div>
                    </div>
                  <div className="mt-2 text-xs text-gray-500">{label}</div>
                </div>
              );
              })}
            </div>
          </div>

          {formattedSeries.length > 0 && (
            <div className="rounded-xl border bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between text-sm text-gray-500">
                <span>Net profit by period</span>
              </div>
              <div className="mt-4 flex items-end gap-4">
                {formattedSeries.map((period) => {
                  const profit = period.revenue - period.expenses;
                  const height = Math.round((Math.abs(profit) / profitMax) * 100);
                  const positive = profit >= 0;
                  return (
                    <div key={`${period.label}-profit`} className="flex flex-1 flex-col items-center">
                      <div className="flex h-28 w-full items-end justify-center overflow-hidden rounded bg-gray-100">
                        <div
                          className={`w-3/5 rounded-t ${positive ? "bg-emerald-500" : "bg-rose-500"}`}
                          style={{ height: `${height}%` }}
                          title={`Net ${profit.toFixed(2)}`}
                        ></div>
                      </div>
                      <div className="mt-2 text-xs text-gray-500">{period.label}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        <section className="space-y-6">
          <div className="space-y-4 rounded-xl border bg-white p-6 shadow-sm">
            <header className="space-y-1">
              <h2 className="text-lg font-semibold">Daily accounting journal</h2>
              <p className="text-sm text-gray-500">Log today’s activity; we reconcile inventory and analytics automatically.</p>
            </header>
            <div className="grid gap-3 sm:grid-cols-[140px_1fr]">
              <label className="text-sm text-gray-600">
                Date
                <input
                  type="date"
                  value={journalDate}
                  onChange={(event) => setJournalDate(event.target.value)}
                  className="mt-1 w-full rounded border px-3 py-2 text-sm"
                />
              </label>
              <label className="text-sm text-gray-600">
                Notes
                <textarea
                  rows={4}
                  value={journalText}
                  onChange={(event) => setJournalText(event.target.value)}
                  placeholder="sold 5 coffees for $25\nbought milk $6\npaid rent $400"
                  className="mt-1 w-full rounded border px-3 py-2 font-mono text-sm"
                />
              </label>
            </div>
            <button
              onClick={handleJournalSubmit}
              disabled={saveJournal.isPending}
              className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saveJournal.isPending ? "Saving…" : "Save journal"}
            </button>

            {journalTotals && (
              <div className="grid gap-2 rounded-lg bg-slate-50 p-4 text-sm">
                <div className="font-medium text-slate-700">Today&apos;s totals</div>
                <div className="flex justify-between"><span>Revenue</span><span>${journalTotals.revenue}</span></div>
                <div className="flex justify-between"><span>Cost</span><span>${journalTotals.cost}</span></div>
                <div className="flex justify-between"><span>Net</span><span>${journalTotals.net}</span></div>
                <div className="flex justify-between"><span>Cumulative net</span><span>${journalTotals.cumulative_net}</span></div>
                <div className="flex justify-between"><span>ROI</span><span>{journalTotals.roi != null ? `${journalTotals.roi.toFixed(2)}%` : "—"}</span></div>
              </div>
            )}

            {journalClarifications.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                <div className="font-medium">Clarifications needed</div>
                <ul className="mt-1 list-disc space-y-1 pl-5">
                  {journalClarifications.map((item) => (
                    <li key={item.question}>{item.question}</li>
                  ))}
                </ul>
                <p className="mt-2 text-xs text-amber-700">
                  Resolve open questions from the journal detail page after reviewing with your team.
                </p>
              </div>
            )}
          </div>

          <div className="space-y-4 rounded-xl border bg-white p-6 shadow-sm">
            <header className="space-y-1">
              <h2 className="text-lg font-semibold">Upload dashboard</h2>
              <p className="text-sm text-gray-500">Send us spreadsheets or statements and route straight to the next workflow.</p>
            </header>

            <div
              onDrop={(event) => {
                event.preventDefault();
                const file = event.dataTransfer.files?.[0];
                if (file) {
                  setSelectedFile(file);
                  setUploadResult(null);
                }
              }}
              onDragOver={(event) => event.preventDefault()}
              className="flex h-36 flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 text-sm"
            >
              {selectedFile ? (
                <>
                  <div>
                    <span className="font-medium">{selectedFile.name}</span>
                    <span className="ml-2 text-xs text-gray-500">{Math.round(selectedFile.size / 1024)} KB</span>
                  </div>
                  <button
                    className="text-xs text-slate-600 underline"
                    onClick={() => {
                      setSelectedFile(null);
                      setUploadResult(null);
                    }}
                  >
                    Remove
                  </button>
                </>
              ) : (
                <>
                  <div className="text-sm font-medium">Drag & drop files here</div>
                  <div className="text-xs text-gray-500">Supported: CSV, Excel, PDF</div>
                  <input
                    type="file"
                    accept=".xlsx,.xls,.csv,application/pdf"
                    onChange={(event) => {
                      const file = event.target.files?.[0] ?? null;
                      setSelectedFile(file);
                      setUploadResult(null);
                    }}
                    className="mt-2 text-xs"
                  />
                </>
              )}
            </div>

            <button
              onClick={handleUpload}
              disabled={!selectedFile || uploadMutation.isPending}
              className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {uploadMutation.isPending ? "Uploading…" : "Upload file"}
            </button>

            {uploadResult && (
              <div className="space-y-2 rounded-lg bg-emerald-50 p-4 text-sm text-emerald-700">
                <div className="font-medium">Upload ready</div>
                <div>Document #{uploadResult.id} saved with status <b>{uploadResult.status}</b>.</div>
                <label className="block text-xs text-emerald-700">
                  Next steps
                  <select
                    value={selectedAction}
                    onChange={(event) => handleActionSelect(event.target.value)}
                    className="mt-1 w-full rounded border px-3 py-2 text-sm"
                  >
                    {NAV_ACTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
