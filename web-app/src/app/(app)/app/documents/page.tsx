"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type { DocumentListItem } from "@/lib/api";

type DocumentWithLink = DocumentListItem & { url?: string | null; storage_path?: string };

export default function DocumentsPage() {
  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: api.documents.list,
  });

  const [downloading, setDownloading] = useState<number | null>(null);
  const downloadMutation = useMutation({
    mutationFn: (id: number) => api.documents.get(id),
    onMutate: (id) => {
      setDownloading(id);
    },
    onSettled: () => setDownloading(null),
  });

  const handleDownload = async (doc: DocumentListItem) => {
    try {
      const full = (await downloadMutation.mutateAsync(doc.id)) as DocumentWithLink;
      const destination = full.url ?? full.storage_path;
      if (!destination) {
        toast.error("No download URL is available yet.");
        return;
      }
      window.open(destination, "_blank", "noopener,noreferrer");
    } catch {
      toast.error("Unable to fetch document. Please retry in a moment.");
    }
  };

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">Documents</h1>
        <p className="text-sm text-gray-500">Browse every balance sheet, P&L, and export Hissabi has produced for your organisation.</p>
      </header>

      {documentsQuery.isLoading && <p className="text-sm text-gray-500">Loading documents…</p>}
      {documentsQuery.error && (
        <p className="text-sm text-red-600">Failed to load documents. Refresh to try again.</p>
      )}

      {documentsQuery.data && documentsQuery.data.length === 0 && (
        <p className="text-sm text-gray-500">No documents generated yet. Upload a spreadsheet or save a journal day to get started.</p>
      )}

      {documentsQuery.data && documentsQuery.data.length > 0 && (
        <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-gray-500">
                <th className="px-4 py-3">Filename</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3 text-right">Size</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documentsQuery.data.map((doc) => {
                const created = format(new Date(doc.created_at), "dd/MM/yy HH:mm");
                const sizeKb = `${Math.max(1, Math.round(doc.size_bytes / 1024))} KB`;
                return (
                  <tr key={doc.id} className="border-t">
                    <td className="px-4 py-3 font-medium text-slate-700">{doc.filename}</td>
                    <td className="px-4 py-3 text-gray-500">{doc.doc_type ?? "generated"}</td>
                    <td className="px-4 py-3 text-gray-500">{created}</td>
                    <td className="px-4 py-3 text-right text-gray-500">{sizeKb}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDownload(doc)}
                        disabled={downloading === doc.id}
                        className="rounded border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                      >
                        {downloading === doc.id ? "Preparing…" : "Download"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
