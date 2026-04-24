"use client";

import { useRef, useState } from "react";
import { CheckCircle2, FileText, LoaderCircle, UploadCloud } from "lucide-react";

import { fetchTask, uploadDocuments } from "@/lib/api";
import { TaskSummary, UploadResponse } from "@/types/api";
import { StatusBadge } from "./status-badge";


export function UploadDropzone() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function handleFiles(fileList: FileList | null) {
    if (!fileList?.length) return;
    setLoading(true);
    setProgress(0);
    setResult(null);
    setError(null);
    try {
      const response = await uploadDocuments(Array.from(fileList), setProgress);
      setResult(response);
      setTasks([]);
      if (response.task_ids.length) {
        void pollTasks(response.task_ids);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function pollTasks(taskIds: string[]) {
    let active = true;
    for (let attempt = 0; attempt < 90 && active; attempt += 1) {
      try {
        const latest = await Promise.all(taskIds.map((taskId) => fetchTask(taskId)));
        setTasks(latest);
        active = latest.some((task) => task.status === "queued" || task.status === "processing" || task.status === "chunked");
      } catch {
        active = false;
      }
      if (active) {
        await new Promise((resolve) => globalThis.setTimeout(resolve, 1500));
      }
    }
  }

  const stageLabel =
    progress < 100 ? "Uploading files" : loading ? "Extracting, chunking, and indexing" : "Completed";

  return (
    <div className="space-y-4">
      <button
        type="button"
        className={`flex min-h-72 w-full flex-col items-center justify-center rounded-[1.75rem] border-2 border-dashed p-8 text-center transition ${
          dragging
            ? "border-primary bg-primary-soft shadow-lift"
            : "border-slate-300 bg-white/90 hover:border-primary/40 hover:bg-primary-soft/40"
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void handleFiles(event.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <div className="mb-4 rounded-2xl bg-gradient-to-br from-primary to-cyan p-4 text-white shadow-sm">
          <UploadCloud className="h-6 w-6" />
        </div>
        <h3 className="text-xl font-semibold text-slate-950">Drop documents here</h3>
        <p className="mt-2 max-w-lg text-sm leading-6 text-slate-600">
          Drop a PDF, note, or report to build your searchable workspace.
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-2 text-xs font-semibold text-slate-600">
          <span className="badge">Checks duplicates</span>
          <span className="badge">Extracts text</span>
          <span className="badge">Keeps page references</span>
        </div>
        <div className="btn-primary mt-5">
          {loading ? "Processing documents..." : "Choose files"}
        </div>
      </button>
      <input
        ref={inputRef}
        hidden
        multiple
        type="file"
        accept=".pdf,.txt,.md"
        onChange={(event) => void handleFiles(event.target.files)}
      />
      {loading ? (
        <div className="app-card p-5">
          <div className="flex items-center gap-3 text-slate-700">
            <LoaderCircle className="h-4 w-4 animate-spin" />
            <p className="text-sm font-medium">{stageLabel}</p>
          </div>
          <div className="mt-4 h-3 rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${Math.max(progress, 8)}%` }}
            />
          </div>
          <p className="mt-3 text-sm text-slate-500">{progress}% uploaded</p>
        </div>
      ) : null}
      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
      {result ? (
        <div className="app-card space-y-4 p-5">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            <p className="font-medium text-slate-950">{result.message}</p>
          </div>
          <p className="rounded-xl border border-cyan/20 bg-cyan/10 px-3 py-2 text-sm font-medium text-cyan">
            Indexing mode: {result.indexing_mode}
          </p>
          {result.warnings.map((warning) => (
            <p key={warning} className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">{warning}</p>
          ))}
          {tasks.length ? (
            <div className="grid gap-3">
              {tasks.map((task) => (
                <div key={task.task_id} className="rounded-xl border border-slate-200 bg-white p-3">
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <p className="font-semibold text-slate-900">Task {task.task_id.slice(0, 12)}</p>
                    <p className="text-slate-600">{task.status} - {task.progress}%</p>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(task.progress, 8)}%` }} />
                  </div>
                  {task.error_message ? <p className="mt-2 text-xs text-rose-700">{task.error_message}</p> : null}
                </div>
              ))}
            </div>
          ) : null}
          <div className="grid gap-3 md:grid-cols-3">
            <div className="muted-panel">
              <p className="text-sm text-slate-600">Added</p>
              <p className="mt-2 text-2xl font-semibold text-slate-950">{result.documents.length}</p>
            </div>
            <div className="muted-panel">
              <p className="text-sm text-slate-600">Duplicates skipped</p>
              <p className="mt-2 text-2xl font-semibold text-slate-950">{result.duplicates_skipped}</p>
            </div>
            <div className="muted-panel">
              <p className="text-sm text-slate-600">Failures</p>
              <p className="mt-2 text-2xl font-semibold text-slate-950">{result.failures.length}</p>
            </div>
          </div>
          {result.failures.length ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              {result.failures.map((failure) => (
                <p key={failure}>{failure}</p>
              ))}
            </div>
          ) : null}
          <div>
            <p className="mb-3 text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">
              Recently uploaded
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              {result.documents.map((document) => (
                <div key={document.id} className="interactive-card p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-primary-soft p-2 text-primary-hover">
                        <FileText className="h-4 w-4" />
                      </div>
                      <p className="font-semibold text-slate-950">{document.title}</p>
                    </div>
                    <StatusBadge status={document.status} />
                  </div>
                  <p className="mt-2 text-sm text-slate-600">
                    {document.file_name} - {document.chunk_count} chunks
                    {document.page_count ? ` - ${document.page_count} pages` : ""}
                  </p>
                  {document.authors.length || document.year ? (
                    <p className="mt-2 text-xs text-slate-500">
                      {[document.authors.slice(0, 3).join(", "), document.year].filter(Boolean).join(" - ")}
                    </p>
                  ) : null}
                  {document.keywords.length ? (
                    <p className="mt-2 text-xs text-slate-500">Keywords: {document.keywords.slice(0, 4).join(", ")}</p>
                  ) : null}
                  {document.last_indexed_at ? (
                    <p className="mt-2 text-xs text-slate-500">
                      Indexed {new Date(document.last_indexed_at).toLocaleString()}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="app-card p-5 text-sm leading-7 text-slate-600">
          After upload, open Search or Ask to use the new document.
        </div>
      )}
    </div>
  );
}
