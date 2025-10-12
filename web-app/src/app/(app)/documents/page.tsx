"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function DocumentsPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["docs"], queryFn: api.documents.list });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Documents</h1>
      {isLoading && <p>Loading…</p>}
      {error && <p className="text-red-600">Failed to load documents.</p>}
      {data && (
        <table className="w-full text-sm border">
          <thead><tr><th className="p-2 text-left">Filename</th><th className="p-2">Created</th><th className="p-2">Type</th></tr></thead>
          <tbody>
          {data.map((d) => (
            <tr key={d.id} className="border-t">
              <td className="p-2">{d.filename}</td>
              <td className="p-2">{new Date(d.created_at).toLocaleString()}</td>
              <td className="p-2">{d.content_type}</td>
            </tr>
          ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
