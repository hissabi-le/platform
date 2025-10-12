"use client";
import { useState, type DragEvent } from "react";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  }

  async function onUpload() {
    if (!file) return;
    setStatus("uploading");
    try {
      // TODO: switch to real POST /uploads with FormData
      await new Promise(res => setTimeout(res, 800));
      setStatus("done");
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Upload data</h1>

      <div
        onDrop={onDrop}
        onDragOver={e=>e.preventDefault()}
        className="border-2 border-dashed rounded p-8 text-center"
      >
        {file ? (
          <div className="space-y-2">
            <div className="text-sm">Selected: <b>{file.name}</b> ({Math.round(file.size/1024)} KB)</div>
            <button onClick={()=>setFile(null)} className="text-sm underline">Remove</button>
          </div>
        ) : (
          <>
            <p>Drag & drop Excel/PDF here</p>
            <p className="text-xs text-gray-500">or click to choose</p>
            <input
              type="file"
              accept=".xlsx,.xls,.csv,application/pdf"
              onChange={(e)=>setFile(e.target.files?.[0] ?? null)}
              className="mt-3 block w-full"
            />
          </>
        )}
      </div>

      <div className="flex gap-2">
        <button
          disabled={!file || status === "uploading"}
          onClick={onUpload}
          className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
        >
          {status === "uploading" ? "Uploading…" : "Upload"}
        </button>
        {status === "done" && <span className="text-green-600">Uploaded ✔</span>}
        {status === "error" && <span className="text-red-600">Failed ✖</span>}
      </div>
    </div>
  );
}
