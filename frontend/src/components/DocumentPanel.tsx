import { ExternalLink, Loader2, X } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { api } from "../api/client";
import type { DocumentDetail, Version } from "../api/types";
import { useAuth } from "../auth";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

const VERSION_STYLE: Record<Version["status"], string> = {
  active: "bg-ok-soft text-ok", ready: "bg-accent-soft text-accent", pending: "bg-accent-soft text-accent",
  superseded: "bg-sunken text-ink-2", failed: "bg-danger-soft text-danger",
};

// One document: its versions (with rollback), recent ingestion jobs, and a new-version upload.
export function DocumentPanel({ documentId, onClose, onChanged }: {
  documentId: string; onClose: () => void; onChanged: () => void;
}) {
  const { can } = useAuth();
  const manage = can("documents:manage");
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.document(documentId).then(setDetail).catch((e: Error) => setError(e.message));
  }, [documentId]);
  useEffect(load, [load]);

  async function activate(version: Version) {
    setError(null);
    try {
      setDetail(await api.activateVersion(documentId, version.version_no));
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Activation failed.");
    }
  }

  return (
    <div className="fixed inset-0 z-20 flex justify-end bg-canvas/60 backdrop-blur-sm" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-labelledby="document-title" onClick={(e) => e.stopPropagation()}
             className="h-full w-full max-w-xl overflow-y-auto border-l border-line bg-surface p-6 shadow-float">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="document-title" className="text-lg font-medium">{detail?.title ?? "Document"}</h2>
            <p className="font-mono text-xs text-ink-3">{documentId}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-md p-1 text-ink-3 hover:bg-sunken"><X size={18} /></button>
        </div>
        {error && <p role="alert" className="mt-4 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
        {!detail && !error && <Loader2 className="mt-6 animate-spin text-ink-3" aria-label="Loading" />}
        {detail && (
          <>
            <p className="mt-3 text-sm text-ink-2">
              {detail.source_type === "official" ? "Official document" : "Synthetic demo data"} · {detail.status} ·{" "}
              {detail.entity_count} entities described by the active version
            </p>

            <h3 className="mt-6 text-sm font-medium">Versions</h3>
            <p className="mt-1 text-xs text-ink-3">
              A new version is ingested first and then replaces the active one; until then the active version keeps
              answering. Activating an older version rolls back to it.
            </p>
            <ol className="mt-3 space-y-2">
              {[...detail.versions].sort((a, b) => b.version_no - a.version_no).map((v) => (
                <li key={v.version_no} aria-label={`Version ${v.version_no}`} className="rounded-lg border border-line p-3 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-mono">v{v.version_no}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs ${VERSION_STYLE[v.status]}`}>{v.status}</span>
                    {v.version_label && <span className="text-ink-2">{v.version_label}</span>}
                    <span className="ml-auto flex gap-2">
                      {manage && (v.status === "ready" || v.status === "superseded") && (
                        <button type="button" onClick={() => void activate(v)}
                                className="rounded-md px-2 py-1 text-xs text-accent hover:bg-sunken">Activate</button>
                      )}
                      {manage && (
                        <a href={api.versionFileUrl(documentId, v.version_no)} target="_blank" rel="noreferrer"
                           className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-ink-2 hover:bg-sunken">
                          PDF <ExternalLink size={12} aria-hidden />
                        </a>
                      )}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-ink-3">
                    {v.original_filename} · {formatBytes(v.size_bytes)}{v.page_count !== null && ` · ${v.page_count} pages`}
                    {v.academic_year && ` · ${v.academic_year}`} · uploaded {new Date(v.created_at).toLocaleDateString()}
                  </p>
                  <p className="mt-0.5 truncate font-mono text-[11px] text-ink-3" title={v.sha256}>SHA-256 {v.sha256}</p>
                </li>
              ))}
            </ol>

            <h3 className="mt-6 text-sm font-medium">Recent ingestion</h3>
            {detail.recent_jobs.length === 0 ? <p className="mt-2 text-sm text-ink-3">No jobs.</p> : (
              <ul className="mt-2 space-y-1 text-sm">
                {detail.recent_jobs.map((job) => (
                  <li key={job.id} className="flex flex-wrap gap-x-3 text-ink-2">
                    <span className="font-mono text-xs">v{job.version_no}</span> {job.job_type} · {job.status}
                    {job.chunk_count !== null && ` · ${job.chunk_count} chunks`}
                    {job.error_message && <span className="text-danger">{job.error_message}</span>}
                  </li>
                ))}
              </ul>
            )}

            {manage && detail.status !== "deleted" && <NewVersion documentId={documentId} onUploaded={() => { load(); onChanged(); }} />}
          </>
        )}
      </aside>
    </div>
  );
}

function NewVersion({ documentId, onUploaded }: { documentId: string; onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [label, setLabel] = useState("");
  const [year, setYear] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    const formElement = event.currentTarget;  // null once the handler has awaited
    const form = new FormData();
    form.append("file", file);
    if (label.trim()) form.append("version_label", label.trim());
    if (year.trim()) form.append("academic_year", year.trim());
    setBusy(true);
    try {
      await api.uploadVersion(documentId, form);
      setMessage({ ok: true, text: "Uploaded. It will replace the active version once ingested." });
      formElement.reset();  // clears the file input (uncontrolled); the text fields are state
      setFile(null);
      setLabel("");
      setYear("");
      onUploaded();
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : "The upload failed." });
    } finally {
      setBusy(false);
    }
  }

  const field = "mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent";
  return (
    <form onSubmit={submit} className="mt-8 rounded-lg bg-sunken p-4">
      <h3 className="text-sm font-medium">Upload a new version</h3>
      <label className="mt-3 block text-sm" htmlFor="version-file">PDF file</label>
      <input id="version-file" type="file" accept="application/pdf,.pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)}
             className={field} />
      <div className="mt-3 grid grid-cols-2 gap-3">
        <label className="text-sm">Version label (optional)<input value={label} onChange={(e) => setLabel(e.target.value)} className={field} /></label>
        <label className="text-sm">Academic year (optional)
          <input value={year} onChange={(e) => setYear(e.target.value)} placeholder="2026-2027" pattern="\d{4}-\d{4}" className={field} />
        </label>
      </div>
      {message && <p role={message.ok ? "status" : "alert"} className={`mt-3 text-sm ${message.ok ? "text-ok" : "text-danger"}`}>{message.text}</p>}
      <button type="submit" disabled={!file || busy}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-40">
        {busy && <Loader2 size={15} className="animate-spin" aria-hidden />} Upload version
      </button>
    </form>
  );
}
