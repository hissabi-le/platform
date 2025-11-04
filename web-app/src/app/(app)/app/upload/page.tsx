"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { api } from "@/lib/api";

const ACTIONS = [
  { value: "", label: "Choose next action" },
  { value: "analytics", label: "Go to analytics dashboard" },
  { value: "documents", label: "View generated documents" },
  { value: "inventory", label: "Review inventory" },
  { value: "balance-sheet", label: "Generate balance sheet" },
  { value: "pnl", label: "Generate profit & loss" },
];

export default function UploadPage(): JSX.Element {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [selectedAction, setSelectedAction] = useState("");
  const [result, setResult] = useState<{ id: number; status: string } | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (payload: File) => api.uploads.create(payload),
    onSuccess: (data) => {
      setResult(data);
      setSelectedAction("");
      toast.success("Upload complete.");
    },
    onError: () => toast.error("Upload failed. Please try again."),
  });

  const handleUpload = () => {
    if (!file) {
      toast.error("Please select a file first.");
      return;
    }
    uploadMutation.mutate(file);
  };

  const handleNextAction = (value: string) => {
    setSelectedAction(value);
    if (!value) return;
    switch (value) {
      case "analytics":
        router.push("/app/analytics");
        break;
      case "documents":
        router.push("/app/documents");
        break;
      case "inventory":
        router.push("/app/inventory");
        break;
      case "balance-sheet":
        toast.info("Balance sheet generation queued.");
        break;
      case "pnl":
        toast.info("Profit & loss report will refresh shortly.");
        break;
      default:
        break;
    }
  };

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Upload centre</h1>
        <p className="text-sm text-gray-500">Drop your spreadsheets or statements, then jump to the next workflow.</p>
      </header>

      <div
        onDrop={(event) => {
          event.preventDefault();
          const incoming = event.dataTransfer.files?.[0];
          if (incoming) {
            setFile(incoming);
            setResult(null);
          }
        }}
        onDragOver={(event) => event.preventDefault()}
        className="flex h-48 flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed"
      >
        {file ? (
          <>
            <div className="text-sm">
              <span className="font-medium">{file.name}</span>
              <span className="ml-2 text-xs text-gray-500">{Math.round(file.size / 1024)} KB</span>
            </div>
            <button
              className="text-xs text-slate-600 underline"
              onClick={() => {
                setFile(null);
                setResult(null);
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
                const incoming = event.target.files?.[0] ?? null;
                setFile(incoming);
                setResult(null);
              }}
              className="mt-2 text-xs"
            />
          </>
        )}
      </div>

      <button
        onClick={handleUpload}
        disabled={!file || uploadMutation.isPending}
        className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {uploadMutation.isPending ? "Uploading…" : "Upload file"}
      </button>

      {result && (
        <div className="space-y-3 rounded-lg bg-emerald-50 p-4 text-sm text-emerald-700">
          <div className="font-medium">Upload ready</div>
          <div>
            Document #{result.id} saved with status <b>{result.status}</b>.
          </div>
          <label className="block text-xs text-emerald-700">
            Next steps
            <select
              value={selectedAction}
              onChange={(event) => handleNextAction(event.target.value)}
              className="mt-1 w-full rounded border px-3 py-2 text-sm"
            >
              {ACTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
    </div>
  );
}
