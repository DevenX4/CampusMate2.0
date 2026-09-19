import { AlertTriangle, CheckCircle2, Clock, Database, FileText, RefreshCw, Search, Upload } from "lucide-react";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { api, type DocumentAction } from "../api/client";
import type { DocumentStats, DocumentStatus, DocumentSummary, IngestionJob, Page } from "../api/types";
import { useAuth } from "../auth";
import { DocumentPanel } from "../components/DocumentPanel";
import { TopBar } from "../components/TopBar";
import { UploadDialog } from "../components/UploadDialog";

const PAGE_SIZE = 20;
// Which actions each status allows (the same rules the server enforces: TRANSITIONS in
// backend/app/services/documents.py). Offering only valid actions saves a round trip.
const ACTIONS: Record<DocumentStatus, (DocumentAction | "delete")[]> = {
  active: ["deactivate", "archive", "reindex", "delete"],
  inactive: ["activate", "archive", "delete"],
  archived: ["activate", "delete"],
  deleted: [],
};
const ACTION_LABELS: Record<DocumentAction | "delete", string> = {
  activate: "Activate", deactivate: "Deactivate", archive: "Archive", reindex: "Re-index", delete: "Delete",
};

export function relativeTime(iso: string | null, now = Date.now()): string {
  if (!iso) return "never";
  const minutes = Math.round((now - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  return hours < 48 ? `${hours} h ago` : new Date(iso).toLocaleDateString();
}

export function AdminPage() {
  const { can } = useAuth();
  const [tab, setTab] = useState<"documents" | "jobs">("documents");
  const [stats, setStats] = useState<DocumentStats | null>(null);
  const [uploading, setUploading] = useState(false);
  const [openDocument, setOpenDocument] = useState<string | null>(null);
  const [version, setVersion] = useState(0);  // bumped after any change, to reload
  const reload = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    api.documentStats().then(setStats).catch(() => setStats(null));
  }, [version]);

  return (
    <div className="min-h-screen">
      <TopBar />
      <main className="mx-auto max-w-[1280px] px-4 py-8 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-[32px] font-medium tracking-tight">Knowledge base</h1>
            <p className="mt-1 text-ink-2">The documents CampusMate answers from, and their ingestion.</p>
          </div>
          {can("documents:manage") && (
            <button type="button" onClick={() => setUploading(true)}
                    className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white">
              <Upload size={16} aria-hidden /> Upload document
            </button>
          )}
        </div>

        <section aria-label="Statistics" className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Stat label="Active documents" value={stats?.active_documents} note={stats && `${stats.total_documents} in total`} Icon={FileText} />
          <Stat label="Indexed chunks" value={stats?.total_chunks} note="of active versions" Icon={Database} />
          <Stat label="Ingestion in progress" value={stats?.pending_jobs} Icon={Clock} />
          <Stat label="Failed ingestion" value={stats?.failed_jobs} Icon={AlertTriangle} warn={!!stats?.failed_jobs} />
          <Stat label="Last change" value={stats ? relativeTime(stats.last_updated) : undefined} Icon={RefreshCw} />
        </section>

        <div className="mt-10 flex gap-1 border-b border-line" role="tablist">
          <TabButton active={tab === "documents"} onClick={() => setTab("documents")}>Documents</TabButton>
          {can("ingestion:manage") && <TabButton active={tab === "jobs"} onClick={() => setTab("jobs")}>Ingestion jobs</TabButton>}
        </div>
        {tab === "documents"
          ? <DocumentsTable version={version} onChanged={reload} onOpen={setOpenDocument} />
          : <JobsTable version={version} onChanged={reload} />}
        <Pipeline />
      </main>
      {openDocument && <DocumentPanel documentId={openDocument} onClose={() => setOpenDocument(null)} onChanged={reload} />}
      {uploading && <UploadDialog onClose={() => setUploading(false)} onUploaded={() => { setUploading(false); reload(); }} />}
    </div>
  );
}

function Stat({ label, value, note, Icon, warn }: {
  label: string; value: number | string | undefined; note?: string | null; Icon: typeof FileText; warn?: boolean;
}) {
  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <div className="flex items-center justify-between text-xs font-medium uppercase tracking-wider text-ink-3">
        {label}<Icon size={16} className={warn ? "text-danger" : "text-ink-3"} aria-hidden />
      </div>
      <p className={`mt-3 text-2xl font-medium tracking-tight ${warn ? "text-danger" : ""}`}>{value ?? "–"}</p>
      {note && <p className="mt-1 text-xs text-ink-3">{note}</p>}
    </div>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" role="tab" aria-selected={active} onClick={onClick}
            className={`-mb-px border-b-2 px-4 py-2.5 text-sm ${active ? "border-accent font-medium text-ink" : "border-transparent text-ink-2 hover:text-ink"}`}>
      {children}
    </button>
  );
}

function StatusPill({ status }: { status: string }) {
  const style: Record<string, string> = {
    active: "bg-ok-soft text-ok", completed: "bg-ok-soft text-ok", failed: "bg-danger-soft text-danger",
    pending: "bg-accent-soft text-accent", processing: "bg-accent-soft text-accent",
  };
  return <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs capitalize ${style[status] ?? "bg-sunken text-ink-2"}`}>{status}</span>;
}

function DocumentsTable({ version, onChanged, onOpen }: {
  version: number; onChanged: () => void; onOpen: (documentId: string) => void;
}) {
  const { can } = useAuth();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<Page<DocumentSummary> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      api.documents({ q: q.trim() || undefined, status: status || undefined, limit: PAGE_SIZE, offset })
        .then((result) => { setPage(result); setError(null); })
        .catch((e: Error) => setError(e.message));
    }, 250);  // wait until typing pauses
    return () => clearTimeout(timer);
  }, [q, status, offset, version]);

  async function act(document: DocumentSummary, action: DocumentAction | "delete") {
    if (action === "delete" && !window.confirm(`Delete "${document.title}"? It will no longer be used for answers.`)) return;
    try {
      if (action === "delete") await api.deleteDocument(document.document_id);
      else await api.documentAction(document.document_id, action);
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The action failed.");
    }
  }

  return (
    <section className="mt-4 rounded-xl border border-line bg-surface">
      <div className="flex flex-wrap items-center gap-3 border-b border-line p-4">
        <label className="flex flex-1 items-center gap-2 rounded-lg border border-line px-3 py-2 focus-within:border-accent">
          <Search size={15} className="text-ink-3" aria-hidden />
          <span className="sr-only">Search documents</span>
          <input value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} placeholder="Search by title or ID"
                 className="w-full bg-transparent text-sm outline-none" />
        </label>
        <label className="text-sm text-ink-2">
          <span className="sr-only">Status</span>
          <select value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }}
                  className="rounded-lg border border-line bg-surface px-3 py-2 text-sm">
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="archived">Archived</option>
            <option value="deleted">Deleted</option>
          </select>
        </label>
      </div>
      {error && <p role="alert" className="border-b border-line bg-danger-soft px-4 py-2 text-sm text-danger">{error}</p>}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-ink-3">
            <tr>{["Document", "Type", "Trust", "Version", "Status", "Updated", ""].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {page?.items.map((d) => (
              <tr key={d.document_id} className="border-t border-line">
                <td className="px-4 py-3">
                  <button type="button" onClick={() => onOpen(d.document_id)} className="text-left font-medium hover:text-accent hover:underline">{d.title}</button>
                  <p className="font-mono text-xs text-ink-3">{d.document_id}</p>
                </td>
                <td className="px-4 py-3 text-ink-2">{d.document_type.replaceAll("_", " ")}</td>
                <td className="px-4 py-3">
                  <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs ${d.source_type === "official" ? "bg-accent-soft text-accent" : "bg-demo-soft text-demo"}`}>
                    {d.source_type === "official" ? "Official" : "Synthetic demo"}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-xs">
                  {d.active_version ? `v${d.active_version.version_no}` : "none active"}
                  {d.latest_version_no && d.latest_version_no !== d.active_version?.version_no ? ` (latest v${d.latest_version_no})` : ""}
                </td>
                <td className="px-4 py-3"><StatusPill status={d.status} /></td>
                <td className="px-4 py-3 text-ink-2">{relativeTime(d.updated_at)}</td>
                <td className="px-4 py-3 text-right">
                  {can("documents:manage") && ACTIONS[d.status].map((action) => (
                    <button key={action} type="button" onClick={() => void act(d, action)}
                            className={`ml-1 rounded-md px-2 py-1 text-xs hover:bg-sunken ${action === "delete" ? "text-danger" : "text-ink-2"}`}>
                      {ACTION_LABELS[action]}
                    </button>
                  ))}
                </td>
              </tr>
            ))}
            {page && page.items.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-ink-3">No documents match.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {page && (
        <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm text-ink-2">
          <span>{page.total === 0 ? "0 documents" : `${offset + 1}–${offset + page.items.length} of ${page.total}`}</span>
          <span className="flex gap-2">
            <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                    className="rounded-md border border-line px-3 py-1 disabled:opacity-40">Previous</button>
            <button type="button" disabled={offset + PAGE_SIZE >= page.total} onClick={() => setOffset(offset + PAGE_SIZE)}
                    className="rounded-md border border-line px-3 py-1 disabled:opacity-40">Next</button>
          </span>
        </div>
      )}
    </section>
  );
}

function JobsTable({ version, onChanged }: { version: number; onChanged: () => void }) {
  const [page, setPage] = useState<Page<IngestionJob> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.jobs({ limit: 50 }).then(setPage).catch((e: Error) => setError(e.message));
  }, [version]);

  async function retry(job: IngestionJob) {
    try {
      await api.retryJob(job.id);
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retry failed.");
    }
  }

  return (
    <section className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface">
      {error && <p role="alert" className="bg-danger-soft px-4 py-2 text-sm text-danger">{error}</p>}
      <table className="w-full text-left text-sm">
        <thead className="text-xs uppercase tracking-wider text-ink-3">
          <tr>{["Document", "Job", "Status", "Stage", "Chunks", "Attempts", "Queued", ""].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr>
        </thead>
        <tbody>
          {page?.items.map((job) => (
            <tr key={job.id} className="border-t border-line align-top">
              <td className="px-4 py-3 font-mono text-xs">{job.document_id} v{job.version_no}</td>
              <td className="px-4 py-3 text-ink-2">{job.job_type}</td>
              <td className="px-4 py-3"><StatusPill status={job.status} />
                {job.error_message && <p className="mt-1 max-w-xs text-xs text-danger">{job.error_message}</p>}</td>
              <td className="px-4 py-3 text-ink-2">{job.current_stage ?? "–"}</td>
              <td className="px-4 py-3">{job.chunk_count ?? "–"}</td>
              <td className="px-4 py-3">{job.attempts}</td>
              <td className="px-4 py-3 text-ink-2">{relativeTime(job.created_at)}</td>
              <td className="px-4 py-3 text-right">
                {job.status === "failed" && (
                  <button type="button" onClick={() => void retry(job)} className="rounded-md px-2 py-1 text-xs text-accent hover:bg-sunken">Retry</button>
                )}
              </td>
            </tr>
          ))}
          {page && page.items.length === 0 && <tr><td colSpan={8} className="px-4 py-10 text-center text-ink-3">No ingestion jobs yet.</td></tr>}
        </tbody>
      </table>
    </section>
  );
}

// What actually happens to an uploaded PDF (backend/app/ingestion), stated plainly.
const STEPS = [
  ["Upload", "SHA-256 fingerprint, PDF signature check, size limit; stored once by content"],
  ["Extract", "Text per page with pypdf, within the document's page scope (e.g. only the IT pages of the full syllabus)"],
  ["Clean", "Broken characters repaired; headers and footers repeated on most pages removed"],
  ["Chunk", "Split along the document's structure, up to 1,200 characters; table lines are never cut"],
  ["Index", "Embedded with BGE-small into Chroma, and in BM25; searchable once the version is active"],
];

function Pipeline() {
  return (
    <section className="mt-10 rounded-xl border border-line bg-surface p-6">
      <h2 className="flex items-center gap-2 font-medium"><CheckCircle2 size={16} className="text-ok" aria-hidden /> Ingestion pipeline</h2>
      <ol className="mt-4 grid gap-3 md:grid-cols-5">
        {STEPS.map(([title, text], i) => (
          <li key={title} className="rounded-lg bg-sunken p-4">
            <p className="text-xs font-medium text-accent">Step {i + 1}</p>
            <p className="mt-1 text-sm font-medium">{title}</p>
            <p className="mt-1 text-xs leading-5 text-ink-2">{text}</p>
          </li>
        ))}
      </ol>
      <p className="mt-4 text-xs text-ink-3">
        Replacing or deactivating a document never rebuilds the whole index: PostgreSQL decides which versions are
        active, and only those are searched.
      </p>
    </section>
  );
}
