"use client";

import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/Alert";

const ACTIONS = [
  { value: "", label: "Choose next action" },
  { value: "analytics", label: "View analytics dashboard" },
  { value: "documents", label: "Browse generated documents" },
  { value: "inventory", label: "Check inventory levels" },
];

const ACCEPTED_TYPES = [
  "text/csv",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/pdf",
];

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectedAction, setSelectedAction] = useState("");
  const [result, setResult] = useState<{ id: number; status: string } | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (payload: File) => api.uploads.create(payload),
    onSuccess: (data) => {
      setResult(data);
      setFile(null);
      setSelectedAction("");
      toast.success("File uploaded successfully!");
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Upload failed";
      toast.error(message);
    },
  });

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const incoming = e.dataTransfer.files?.[0];
    if (incoming) {
      if (!ACCEPTED_TYPES.includes(incoming.type) && !incoming.name.match(/\.(csv|xlsx?|pdf)$/i)) {
        toast.error("Please upload a CSV, Excel, or PDF file.");
        return;
      }
      setFile(incoming);
      setResult(null);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const incoming = e.target.files?.[0];
    if (incoming) {
      setFile(incoming);
      setResult(null);
    }
  };

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

    const routes: Record<string, string> = {
      analytics: "/app/analytics",
      documents: "/app/documents",
      inventory: "/app/inventory",
    };

    if (routes[value]) {
      router.push(routes[value]);
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
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Upload Centre</h1>
        <p className="text-sm text-slate-500 mt-1">
          Import your spreadsheets and statements for automatic processing
        </p>
      </header>

      {/* Upload Area */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-colors ${dragActive
          ? "border-emerald-500 bg-emerald-50"
          : file
            ? "border-slate-300 bg-slate-50"
            : "border-slate-300 hover:border-slate-400"
          }`}
      >
        {file ? (
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-emerald-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="font-medium text-slate-900">{file.name}</p>
            <p className="text-sm text-slate-500 mt-1">{formatFileSize(file.size)}</p>
            <button
              onClick={() => {
                setFile(null);
                setResult(null);
              }}
              className="mt-3 text-sm text-slate-600 hover:text-slate-900 underline"
            >
              Remove file
            </button>
          </div>
        ) : (
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-slate-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="font-medium text-slate-900">Drag and drop your file here</p>
            <p className="text-sm text-slate-500 mt-1">or click to browse</p>
            <input
              type="file"
              accept=".xlsx,.xls,.csv,.pdf"
              onChange={handleFileSelect}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {["CSV", "Excel", "PDF"].map((type) => (
                <span key={type} className="px-2 py-0.5 bg-slate-100 rounded text-xs text-slate-600">
                  {type}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Upload Button */}
      <div className="flex gap-3">
        <Button
          onClick={handleUpload}
          disabled={!file || uploadMutation.isPending}
          className="bg-emerald-600 hover:bg-emerald-700"
          size="lg"
        >
          {uploadMutation.isPending ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Uploading...
            </>
          ) : (
            "Upload file"
          )}
        </Button>
        {file && !uploadMutation.isPending && (
          <Button
            variant="outline"
            size="lg"
            onClick={() => {
              setFile(null);
              setResult(null);
            }}
          >
            Cancel
          </Button>
        )}
      </div>

      {/* Success State */}
      {result && (
        <Alert variant="success" title="Upload complete">
          <div className="space-y-3">
            <p>
              Your file has been processed successfully and assigned ID <strong>#{result.id}</strong>.
              Status: <strong>{result.status}</strong>
            </p>
            <div>
              <label className="block text-sm font-medium mb-2">What would you like to do next?</label>
              <select
                value={selectedAction}
                onChange={(e) => handleNextAction(e.target.value)}
                className="w-full rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                {ACTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </Alert>
      )}

      {/* Tips Section */}
      <div className="rounded-xl bg-slate-50 p-6 border">
        <h3 className="font-medium text-slate-900 mb-3">Tips for best results</h3>
        <ul className="space-y-2 text-sm text-slate-600">
          <li className="flex items-start gap-2">
            <span className="text-emerald-500 mt-0.5">✓</span>
            Use consistent column headers in spreadsheets
          </li>
          <li className="flex items-start gap-2">
            <span className="text-emerald-500 mt-0.5">✓</span>
            Include dates in YYYY-MM-DD format when possible
          </li>
          <li className="flex items-start gap-2">
            <span className="text-emerald-500 mt-0.5">✓</span>
            PDFs work best when they contain selectable text
          </li>
        </ul>
      </div>
    </div>
  );
}
