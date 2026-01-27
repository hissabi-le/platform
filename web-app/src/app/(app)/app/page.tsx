"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import type { JournalDayResponse } from "@/lib/api";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatCard } from "@/components/StatCard";
import { ErrorAlert, Alert } from "@/components/Alert";
import { CardSkeleton, ChartSkeleton } from "@/components/Skeleton";
import { formatCurrency, formatPercent, getUTCDateString } from "@/lib/format";

const RANGE_OPTIONS = ["1m", "3m", "6m", "1y"] as const;
type RangeOption = (typeof RANGE_OPTIONS)[number];

const RANGE_LABELS: Record<RangeOption, string> = {
  "1m": "Last month",
  "3m": "Last 3 months",
  "6m": "Last 6 months",
  "1y": "Last year",
};

const NAV_ACTIONS = [
  { value: "", label: "Choose next action" },
  { value: "analytics", label: "View detailed analytics", href: "/app/analytics" },
  { value: "documents", label: "Browse documents", href: "/app/documents" },
  { value: "inventory", label: "Check inventory", href: "/app/inventory" },
];

const todayIso = getUTCDateString();

export default function AppDashboard() {
  const router = useRouter();
  const [range, setRange] = useState<RangeOption>("3m");
  const [journalText, setJournalText] = useState("");
  const [journalDate, setJournalDate] = useState(todayIso);
  const [journalResult, setJournalResult] = useState<JournalDayResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<{ id: number; status: string } | null>(null);
  const [selectedAction, setSelectedAction] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const pnlQuery = useQuery({
    queryKey: ["analytics-pnl", range],
    queryFn: () => api.analytics.pnl(range),
  });

  const receivablesQuery = useQuery({
    queryKey: ["analytics-receivables"],
    queryFn: () => api.analytics.receivables(),
  });

  const payablesQuery = useQuery({
    queryKey: ["analytics-payables"],
    queryFn: () => api.analytics.payables(),
  });

  const saveJournal = useMutation({
    mutationFn: () => api.journal.saveDay({ raw_text: journalText, date: journalDate, commit: true }),
    onSuccess: (data) => {
      setJournalResult(data);
      setJournalText("");
      toast.success("Journal saved. Totals refreshed.");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Unable to save journal entry.");
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploads.create(file),
    onSuccess: (data) => {
      setUploadResult(data);
      setSelectedFile(null);
      setSelectedAction("");
      toast.success("Upload complete!");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Upload failed.");
    },
  });

  const margin = pnlQuery.data?.revenue
    ? (pnlQuery.data.profit / pnlQuery.data.revenue) * 100
    : 0;

  const formattedSeries = useMemo(() => {
    return (pnlQuery.data?.series ?? []).map((row) => ({
      ...row,
      label: format(parseISO(row.date), "MMM dd"),
      profit: row.revenue - row.expenses,
    }));
  }, [pnlQuery.data?.series]);

  const handleJournalSubmit = () => {
    if (!journalText.trim()) {
      toast.error("Please enter at least one line.");
      return;
    }
    saveJournal.mutate();
  };

  const handleUpload = () => {
    if (!selectedFile) {
      toast.error("Please select a file first.");
      return;
    }
    uploadMutation.mutate(selectedFile);
  };

  const handleActionSelect = (value: string) => {
    setSelectedAction(value);
    const action = NAV_ACTIONS.find((a) => a.value === value);
    if (action?.href) {
      router.push(action.href);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track revenue, expenses, and daily activity at a glance
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Label htmlFor="range" className="text-sm text-slate-600">Period:</Label>
          <select
            id="range"
            value={range}
            onChange={(e) => setRange(e.target.value as RangeOption)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
          >
            {RANGE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{RANGE_LABELS[opt]}</option>
            ))}
          </select>
        </div>
      </header>

      {/* Error State */}
      {pnlQuery.error && <ErrorAlert error={pnlQuery.error} onRetry={() => pnlQuery.refetch()} />}

      {/* Analytics Section */}
      {pnlQuery.isLoading && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
          <ChartSkeleton />
        </div>
      )}

      {pnlQuery.data && (
        <div className="space-y-6">
          {/* KPI Cards */}
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Revenue" value={formatCurrency(pnlQuery.data.revenue)} accent="bg-emerald-500" />
            <StatCard title="Expenses" value={formatCurrency(pnlQuery.data.expenses)} accent="bg-rose-500" />
            <StatCard title="Net Profit" value={formatCurrency(pnlQuery.data.profit)} accent="bg-slate-900" />
            <StatCard title="Margin" value={formatPercent(margin)} accent="bg-amber-500" />
          </section>

          {/* Receivables & Payables */}
          <section className="grid gap-4 sm:grid-cols-2">
            <Link
              href="/app/receivables"
              className="rounded-xl border bg-white p-6 shadow-sm hover:border-blue-300 hover:shadow-md transition-all cursor-pointer block"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-900">Accounts Receivable</h3>
                <span className="text-xs text-slate-500">Money owed to you →</span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold text-blue-600">
                  {formatCurrency(receivablesQuery.data?.total ?? 0)}
                </span>
                {(receivablesQuery.data?.count ?? 0) > 0 && (
                  <span className="text-sm text-slate-500 mb-1">
                    ({receivablesQuery.data?.count} unpaid)
                  </span>
                )}
              </div>
              {receivablesQuery.data?.breakdown?.slice(0, 3).map((row) => (
                <div key={row.category} className="mt-2 flex justify-between text-sm">
                  <span className="text-slate-600">{row.category}</span>
                  <span className="font-medium text-slate-900">{formatCurrency(row.amount)}</span>
                </div>
              ))}
            </Link>

            <Link
              href="/app/receivables"
              className="rounded-xl border bg-white p-6 shadow-sm hover:border-orange-300 hover:shadow-md transition-all cursor-pointer block"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-900">Accounts Payable</h3>
                <span className="text-xs text-slate-500">Money you owe →</span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold text-orange-600">
                  {formatCurrency(payablesQuery.data?.total ?? 0)}
                </span>
                {(payablesQuery.data?.count ?? 0) > 0 && (
                  <span className="text-sm text-slate-500 mb-1">
                    ({payablesQuery.data?.count} unpaid)
                  </span>
                )}
              </div>
              {payablesQuery.data?.breakdown?.slice(0, 3).map((row) => (
                <div key={row.category} className="mt-2 flex justify-between text-sm">
                  <span className="text-slate-600">{row.category}</span>
                  <span className="font-medium text-slate-900">{formatCurrency(row.amount)}</span>
                </div>
              ))}
            </Link>
          </section>

          {/* Charts Row */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Revenue vs Expenses Chart */}
            <div className="rounded-xl border bg-white p-6 shadow-sm">
              <h3 className="font-semibold text-slate-900 mb-4">Revenue vs Expenses</h3>
              {formattedSeries.length === 0 ? (
                <div className="flex items-center justify-center h-48 text-slate-500">
                  <p className="text-sm">Upload data to see trends</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={formattedSeries} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
                      </linearGradient>
                      <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} tickFormatter={(v) => `$${v}`} />
                    <Tooltip formatter={(v) => [formatCurrency(Number(v))]} />
                    <Area type="monotone" dataKey="revenue" stroke="#10b981" fill="url(#revGrad)" />
                    <Area type="monotone" dataKey="expenses" stroke="#f43f5e" fill="url(#expGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Net Profit Chart */}
            <div className="rounded-xl border bg-white p-6 shadow-sm">
              <h3 className="font-semibold text-slate-900 mb-4">Net Profit by Period</h3>
              {formattedSeries.length === 0 ? (
                <div className="flex items-center justify-center h-48 text-slate-500">
                  <p className="text-sm">No data available</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={formattedSeries} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} tickFormatter={(v) => `$${v}`} />
                    <Tooltip formatter={(v) => [formatCurrency(Number(v)), "Profit"]} />
                    <Bar dataKey="profit" fill="#0f172a" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Action Cards */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Quick Journal Entry */}
        <div className="rounded-xl border bg-white p-6 shadow-sm space-y-4">
          <header>
            <h2 className="font-semibold text-slate-900">Quick Journal Entry</h2>
            <p className="text-sm text-slate-500 mt-1">Log today&apos;s activity in seconds</p>
          </header>

          <div className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="journal-date">Date</Label>
              <Input
                id="journal-date"
                type="date"
                value={journalDate}
                onChange={(e) => setJournalDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="journal-text">Notes</Label>
              <textarea
                id="journal-text"
                rows={4}
                value={journalText}
                onChange={(e) => setJournalText(e.target.value)}
                placeholder="sold 5 coffees for $25&#10;bought milk $6"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>
            <Button
              onClick={handleJournalSubmit}
              disabled={saveJournal.isPending || !journalText.trim()}
              className="w-full"
            >
              {saveJournal.isPending ? "Saving..." : "Save Journal"}
            </Button>
          </div>

          {journalResult?.totals && (
            <div className="rounded-lg bg-slate-50 p-4 space-y-2">
              <p className="font-medium text-slate-700 text-sm">Today&apos;s Totals</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">Revenue</span>
                  <span className="text-emerald-600">{formatCurrency(journalResult.totals.revenue)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Cost</span>
                  <span className="text-rose-600">{formatCurrency(journalResult.totals.cost)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Net</span>
                  <span className="font-medium">{formatCurrency(journalResult.totals.net)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">ROI</span>
                  <span>{journalResult.totals.roi != null ? `${journalResult.totals.roi.toFixed(1)}%` : "—"}</span>
                </div>
              </div>
            </div>
          )}

          {journalResult?.clarifications && journalResult.clarifications.length > 0 && (
            <Alert variant="warning" title="Clarifications needed">
              <ul className="list-disc pl-5 space-y-1">
                {journalResult.clarifications.map((c) => (
                  <li key={c.question}>{c.question}</li>
                ))}
              </ul>
              <p className="mt-2 text-xs">Visit the Journal page to resolve these.</p>
            </Alert>
          )}
        </div>

        {/* Quick Upload */}
        <div className="rounded-xl border bg-white p-6 shadow-sm space-y-4">
          <header>
            <h2 className="font-semibold text-slate-900">Quick Upload</h2>
            <p className="text-sm text-slate-500 mt-1">Drop a spreadsheet or statement</p>
          </header>

          <div
            onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              const file = e.dataTransfer.files?.[0];
              if (file) {
                setSelectedFile(file);
                setUploadResult(null);
              }
            }}
            className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${dragActive ? "border-emerald-500 bg-emerald-50" : selectedFile ? "border-slate-300 bg-slate-50" : "border-slate-300"
              }`}
          >
            {selectedFile ? (
              <div className="text-center">
                <svg className="w-10 h-10 mx-auto text-emerald-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="font-medium text-slate-900">{selectedFile.name}</p>
                <p className="text-sm text-slate-500">{formatFileSize(selectedFile.size)}</p>
                <button
                  onClick={() => { setSelectedFile(null); setUploadResult(null); }}
                  className="mt-2 text-sm text-slate-600 underline hover:text-slate-900"
                >
                  Remove
                </button>
              </div>
            ) : (
              <div className="text-center">
                <svg className="w-10 h-10 mx-auto text-slate-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p className="font-medium text-slate-900">Drop files here</p>
                <p className="text-sm text-slate-500">CSV, Excel, PDF</p>
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv,.pdf"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setSelectedFile(file);
                      setUploadResult(null);
                    }
                  }}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
              </div>
            )}
          </div>

          <Button
            onClick={handleUpload}
            disabled={!selectedFile || uploadMutation.isPending}
            className="w-full bg-emerald-600 hover:bg-emerald-700"
          >
            {uploadMutation.isPending ? "Uploading..." : "Upload File"}
          </Button>

          {uploadResult && (
            <Alert variant="success" title="Upload complete">
              <p>Document #{uploadResult.id} saved. Status: <strong>{uploadResult.status}</strong></p>
              <div className="mt-3">
                <Label htmlFor="next-action" className="text-sm">What&apos;s next?</Label>
                <select
                  id="next-action"
                  value={selectedAction}
                  onChange={(e) => handleActionSelect(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm"
                >
                  {NAV_ACTIONS.map((a) => (
                    <option key={a.value} value={a.value}>{a.label}</option>
                  ))}
                </select>
              </div>
            </Alert>
          )}
        </div>
      </div>
    </div>
  );
}
