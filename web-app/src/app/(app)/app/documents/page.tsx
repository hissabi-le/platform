"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type { DocumentListItem } from "@/lib/api";
import { ErrorAlert } from "@/components/Alert";
import { TableSkeleton } from "@/components/Skeleton";
import { Button } from "@/components/ui/button";

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

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Documents</h1>
        <p className="text-sm text-slate-500 mt-1">
          Browse all balance sheets, P&L reports, and exports generated for your organisation
        </p>
      </header>

      {/* Error State */}
      {documentsQuery.error && (
        <ErrorAlert error={documentsQuery.error} onRetry={() => documentsQuery.refetch()} />
      )}

      {/* Loading State */}
      {documentsQuery.isLoading && <TableSkeleton rows={5} columns={5} />}

      {/* Empty State */}
      {documentsQuery.data && documentsQuery.data.length === 0 && (
        <div className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-12 text-center">
          <svg className="w-12 h-12 mx-auto text-slate-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 className="text-lg font-medium text-slate-900 mb-1">No documents yet</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            Upload a spreadsheet or save a journal entry to generate your first reports.
          </p>
        </div>
      )}

      {/* Documents Table */}
      {documentsQuery.data && documentsQuery.data.length > 0 && (
        <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="px-6 py-3 font-medium">Filename</th>
                  <th className="px-6 py-3 font-medium">Type</th>
                  <th className="px-6 py-3 font-medium">Created</th>
                  <th className="px-6 py-3 font-medium text-right">Size</th>
                  <th className="px-6 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documentsQuery.data.map((doc) => {
                  const created = format(new Date(doc.created_at), "MMM dd, yyyy HH:mm");
                  return (
                    <tr key={doc.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                            <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                          </div>
                          <span className="font-medium text-slate-900">{doc.filename}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                          {doc.doc_type ?? "Report"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-600">{created}</td>
                      <td className="px-6 py-4 text-right text-slate-600">{formatFileSize(doc.size_bytes)}</td>
                      <td className="px-6 py-4 text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDownload(doc)}
                          disabled={downloading === doc.id}
                        >
                          {downloading === doc.id ? "Preparing..." : "Download"}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
