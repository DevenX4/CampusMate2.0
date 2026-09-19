import { AlertTriangle, CloudUpload, ExternalLink, FileText, Loader2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type DragEvent, type FormEvent, type ReactNode } from "react";

import { api } from "../api/client";
import { DOCUMENT_CATEGORIES, type DocumentDetail, type DocumentSummary, type Version } from "../api/types";
import { useAuth } from "../auth";
import { ErrorNote, Modal, Spinner, TrustBadge, fieldClass } from "../components/ui";
import { formatBytes, formatDate, humanize } from "../lib/format";
import { useLoad } from "../lib/useLoad";

// --- drop zone ------------------------------------------------------------------------------------

function DropZone({ file, onFile, maxMb }: { file: File | null; onFile: (file: File | null) => void; maxMb: number }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  function accept(candidate: File | undefined) {
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".pdf") && candidate.type !== "application/pdf") { setProblem("Only PDF files can be uploaded."); return; }
    if (candidate.size > maxMb * 1024 * 1024) { setProblem(`The file is ${formatBytes(candidate.size)}; the limit is ${maxMb} MB.`); return; }
    setProblem(null);
    onFile(candidate);
  }

  return (
    <div>
      <div role="button" tabIndex={0} onClick={() => input.current?.click()} onKeyDown={(e) => e.key === "Enter" && input.current?.click()}
           onDragOver={(e: DragEvent) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
           onDrop={(e: DragEvent) => { e.preventDefault(); setOver(false); accept(e.dataTransfer.files[0]); }}
           className={`cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition ${over ? "border-blue-500 bg-blue-500/5" : "border-line bg-panel-2 hover:border-blue-500"}`}>
        <FileText size={30} className="mx-auto mb-2 text-rose-500" />
        {file ? (
          <>
            <p className="text-xs font-semibold text-ink">{file.name}</p>
            <p className="mt-1 text-[11px] text-ink-4">{formatBytes(file.size)} · click to choose another</p>
          </>
        ) : (
          <>
            <p className="text-xs font-medium text-ink-2">Click to upload or drag and drop your document</p>
            <p className="mt-1 text-[11px] text-ink-4">PDF files up to {maxMb} MB</p>
          </>
        )}
      </div>
      <input ref={input} type="file" accept="application/pdf,.pdf" aria-label="PDF file" className="sr-only"
             onChange={(e) => accept(e.target.files?.[0])} />
      {problem && <p className="mt-2 text-xs text-rose-600">{problem}</p>}
    </div>
  );
}

// --- new document ---------------------------------------------------------------------------------

export function UploadModal({ onClose, onUploaded }: { onClose: () => void; onUploaded: () => void }) {
  const departments = useLoad(() => api.departments(), []);
  const info = useLoad(() => api.systemInfo(), []);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [documentType, setDocumentType] = useState("");
  const [sourceType, setSourceType] = useState<"" | "official" | "synthetic">("");
  const [departmentId, setDepartmentId] = useState("");
  const [academicYear, setAcademicYear] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const chooseFile = useCallback((f: File | null) => {
    setFile(f);
    if (f) setTitle((t) => t || f.name.replace(/\.pdf$/i, "").replaceAll(/[_-]+/g, " "));
  }, []);

  // The trust level has no default: it decides how every answer from this file is labelled.
  const ready = file !== null && title.trim().length >= 3 && documentType !== "" && sourceType !== "" && !busy;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!ready || !file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("title", title.trim());
    form.append("document_type", documentType);
    form.append("source_type", sourceType);
    if (departmentId) form.append("department_id", departmentId);
    if (academicYear.trim()) form.append("academic_year", academicYear.trim());
    setBusy(true);
    setError(null);
    try {
      await api.uploadDocument(form);
      onUploaded();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Upload New PDF to CampusMate" subtitle="Stored, then chunked and indexed by the ingestion pipeline" icon={<CloudUpload size={15} />} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4 p-6">
        <DropZone file={file} onFile={chooseFile} maxMb={info.data?.limits.max_upload_mb ?? 50} />
        <label className="block text-xs font-semibold text-ink-2">Title
          <input value={title} maxLength={300} onChange={(e) => setTitle(e.target.value)} className={`${fieldClass} mt-1`} />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block text-xs font-semibold text-ink-2">Category
            <select aria-label="Document type" value={documentType} onChange={(e) => setDocumentType(e.target.value)} className={`${fieldClass} mt-1`}>
              <option value="" disabled>Choose a type</option>
              {DOCUMENT_CATEGORIES.map((c) => (
                <optgroup key={c.label} label={c.label}>
                  {c.types.map((t) => <option key={t} value={t}>{humanize(t)}</option>)}
                </optgroup>
              ))}
            </select>
          </label>
          <label className="block text-xs font-semibold text-ink-2">Department scope
            <select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} className={`${fieldClass} mt-1`}>
              <option value="">University (all)</option>
              {(departments.data ?? []).map((d) => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
            </select>
          </label>
        </div>
        <label className="block text-xs font-semibold text-ink-2">Academic year (optional)
          <input value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} placeholder="2026-2027" pattern="\d{4}-\d{4}" className={`${fieldClass} mt-1`} />
        </label>
        <fieldset>
          <legend className="text-xs font-semibold text-ink-2">Trust level</legend>
          <div className="mt-1.5 grid grid-cols-2 gap-2">
            {([["official", "Official GUNI document"], ["synthetic", "Synthetic demo data"]] as const).map(([value, label]) => (
              <label key={value} className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium transition ${
                sourceType === value ? "border-blue-500 bg-blue-500/5 text-ink" : "border-line text-ink-2 hover:bg-panel-2"}`}>
                <input type="radio" name="source_type" value={value} checked={sourceType === value} onChange={() => setSourceType(value)} className="accent-blue-600" />
                {label}
              </label>
            ))}
          </div>
        </fieldset>
        {error && <ErrorNote>{error}</ErrorNote>}
        <div className="flex items-center justify-end gap-2.5 border-t border-line-2 pt-4">
          <button type="button" onClick={onClose} className="rounded-xl px-4 py-2 text-xs font-medium text-ink-2 hover:bg-panel-3">Cancel</button>
          <button type="submit" disabled={!ready}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm shadow-blue-500/30 transition hover:bg-blue-700 disabled:opacity-40">
            {busy && <Loader2 size={14} className="animate-spin" />} Start Ingestion Pipeline
          </button>
        </div>
      </form>
    </Modal>
  );
}

// --- new version of an existing document ------------------------------------------------------------

export function ReplaceModal({ document: doc, onClose, onDone }: { document: DocumentSummary; onClose: () => void; onDone: () => void }) {
  const info = useLoad(() => api.systemInfo(), []);
  const [file, setFile] = useState<File | null>(null);
  const [label, setLabel] = useState("");
  const [academicYear, setAcademicYear] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    if (label.trim()) form.append("version_label", label.trim());
    if (academicYear.trim()) form.append("academic_year", academicYear.trim());
    setBusy(true);
    setError(null);
    try {
      await api.uploadVersion(doc.document_id, form);
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Replace document" subtitle={doc.title} icon={<CloudUpload size={15} />} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4 p-6">
        <p className="rounded-xl bg-panel-2 p-3 text-xs leading-relaxed text-ink-2">
          The file becomes a new version. It replaces the active one automatically once ingested; until then the current
          version keeps answering, and you can always roll back.
        </p>
        <DropZone file={file} onFile={setFile} maxMb={info.data?.limits.max_upload_mb ?? 50} />
        <div className="grid grid-cols-2 gap-3">
          <label className="block text-xs font-semibold text-ink-2">Version label (optional)
            <input value={label} onChange={(e) => setLabel(e.target.value)} className={`${fieldClass} mt-1`} />
          </label>
          <label className="block text-xs font-semibold text-ink-2">Academic year (optional)
            <input value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} placeholder="2026-2027" pattern="\d{4}-\d{4}" className={`${fieldClass} mt-1`} />
          </label>
        </div>
        {error && <ErrorNote>{error}</ErrorNote>}
        <div className="flex justify-end gap-2.5 border-t border-line-2 pt-4">
          <button type="button" onClick={onClose} className="rounded-xl px-4 py-2 text-xs font-medium text-ink-2 hover:bg-panel-3">Cancel</button>
          <button type="submit" disabled={!file || busy}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-40">
            {busy && <Loader2 size={14} className="animate-spin" />} Upload new version
          </button>
        </div>
      </form>
    </Modal>
  );
}

// --- confirmation ------------------------------------------------------------------------------------

export function ConfirmDialog({ title, children, confirm, danger, onConfirm, onClose }: {
  title: string; children: ReactNode; confirm: string; danger?: boolean; onConfirm: () => Promise<void>; onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <Modal title={title} icon={<AlertTriangle size={15} />} onClose={onClose}>
      <div className="space-y-4 p-6">
        <div className="text-sm leading-relaxed text-ink-2">{children}</div>
        {error && <ErrorNote>{error}</ErrorNote>}
        <div className="flex justify-end gap-2.5">
          <button type="button" onClick={onClose} className="rounded-xl px-4 py-2 text-xs font-medium text-ink-2 hover:bg-panel-3">Cancel</button>
          <button type="button" disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    setError(null);
                    try { await onConfirm(); } catch (e) { setError(e instanceof Error ? e.message : "The action failed."); setBusy(false); }
                  }}
                  className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold text-white shadow-sm transition disabled:opacity-50 ${
                    danger ? "bg-rose-600 hover:bg-rose-700" : "bg-blue-600 hover:bg-blue-700"}`}>
            {busy && <Loader2 size={14} className="animate-spin" />} {confirm}
          </button>
        </div>
      </div>
    </Modal>
  );
}

// --- versions & details drawer ------------------------------------------------------------------------

const VERSION_STYLE: Record<Version["status"], string> = {
  active: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400", ready: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
  pending: "bg-blue-500/10 text-blue-700 dark:text-blue-400", superseded: "bg-panel-3 text-ink-3", failed: "bg-rose-500/10 text-rose-700",
};

export function DocumentPanel({ documentId, onClose, onChanged }: { documentId: string; onClose: () => void; onChanged: () => void }) {
  const { can } = useAuth();
  const manage = can("documents:manage");
  const detail = useLoad(() => api.document(documentId), [documentId]);
  const [data, setData] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { if (detail.data) setData(detail.data); }, [detail.data]);

  async function activate(v: Version) {
    setError(null);
    try {
      setData(await api.activateVersion(documentId, v.version_no));
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Activation failed.");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-sm" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-label="Document" onClick={(e) => e.stopPropagation()}
             className="h-full w-full max-w-xl animate-fade-up overflow-y-auto border-l border-line bg-panel p-6 font-admin shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-ink">{data?.title ?? "Document"}</h2>
            <p className="font-mono text-xs text-ink-4">{documentId}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="grid h-8 w-8 place-items-center rounded-lg text-ink-4 hover:bg-panel-3"><X size={16} /></button>
        </div>
        {detail.loading && !data && <Spinner className="mt-6" label="Loading…" />}
        {(detail.error || error) && <div className="mt-4"><ErrorNote>{detail.error ?? error}</ErrorNote></div>}
        {data && (
          <div className="mt-4 space-y-6">
            <div className="flex flex-wrap items-center gap-2 text-xs text-ink-3">
              <TrustBadge type={data.source_type} /><span className="capitalize">{data.status}</span><span>·</span>
              <span>{humanize(data.document_type)}</span><span>·</span><span>{data.entity_count} entities · {data.chunk_count} chunks</span>
            </div>
            <section>
              <h3 className="text-sm font-bold text-ink">Versions</h3>
              <p className="mt-1 text-xs text-ink-3">A new version is ingested first and then replaces the active one; activating an older version rolls back to it.</p>
              <ol className="mt-3 space-y-2">
                {[...data.versions].sort((a, b) => b.version_no - a.version_no).map((v) => (
                  <li key={v.version_no} aria-label={`Version ${v.version_no}`} className="rounded-xl border border-line p-3 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-ink">v{v.version_no}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${VERSION_STYLE[v.status]}`}>{v.status}</span>
                      {v.version_label && <span className="truncate text-xs text-ink-3">{v.version_label}</span>}
                      <span className="ml-auto flex gap-1.5">
                        {manage && (v.status === "ready" || v.status === "superseded") && (
                          <button type="button" onClick={() => void activate(v)} className="rounded-lg px-2 py-1 text-xs font-semibold text-blue-600 hover:bg-blue-500/10">Activate</button>
                        )}
                        {manage && (
                          <a href={api.versionFileUrl(documentId, v.version_no)} target="_blank" rel="noreferrer"
                             className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-ink-3 hover:bg-panel-3">PDF <ExternalLink size={11} /></a>
                        )}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-ink-3">
                      {v.original_filename} · {formatBytes(v.size_bytes)}{v.page_count !== null && ` · ${v.page_count} pages`}
                      {v.academic_year && ` · ${v.academic_year}`} · uploaded {formatDate(v.created_at)}
                    </p>
                    <p className="mt-0.5 truncate font-mono text-[10px] text-ink-4" title={v.sha256}>SHA-256 {v.sha256}</p>
                  </li>
                ))}
              </ol>
            </section>
            <section>
              <h3 className="text-sm font-bold text-ink">Recent ingestion</h3>
              {data.recent_jobs.length === 0 ? <p className="mt-2 text-xs text-ink-4">No jobs.</p> : (
                <ul className="mt-2 space-y-1.5">
                  {data.recent_jobs.map((job) => (
                    <li key={job.id} className="flex flex-wrap items-center gap-x-2 text-xs text-ink-2">
                      <span className="font-mono text-[11px]">v{job.version_no}</span><span>{job.job_type}</span><span>·</span>
                      <span className={job.status === "failed" ? "text-rose-600" : job.status === "completed" ? "text-emerald-600" : "text-blue-600"}>{job.status}</span>
                      {job.chunk_count !== null && <span className="text-ink-3">· {job.chunk_count} chunks</span>}
                      {job.error_message && <span className="w-full text-rose-600">{job.error_message}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </aside>
    </div>
  );
}
