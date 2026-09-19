import {
  ArrowLeftRight, CircleAlert, Clock, CloudUpload, Database, EyeOff, FileText, Plus, RefreshCw, Search, ShieldCheck, SlidersHorizontal,
  Trash2, Eye,
} from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { api } from "../api/client";
import type { DocumentSummary } from "../api/types";
import { useAuth } from "../auth";
import { relativeTime } from "../lib/format";
import { useLoad } from "../lib/useLoad";
import { card, PageHeader } from "./AdminLayout";
import { DocumentsCard, useDocumentActions } from "./documentsWorkbench";

function useDocuments() {
  const documents = useLoad(() => api.documents({ limit: 100 }), []);
  const departments = useLoad(() => api.departments(), []);
  return { documents, departments };
}

export function DashboardPage() {
  const { can } = useAuth();
  const manage = can("documents:manage");
  const { documents, departments } = useDocuments();
  const stats = useLoad(() => api.documentStats(), []);
  const reload = () => { documents.reload(); stats.reload(); };
  const actions = useDocumentActions(reload);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({ status: "", trust: "" });

  const monthAgo = Date.now() - 30 * 86400000;
  const addedThisMonth = (documents.data?.items ?? []).filter((d) => new Date(d.created_at).getTime() > monthAgo).length;

  return (
    <>
      <PageHeader title="Knowledge Control Center" subtitle="Manage the documents that CampusMate uses to answer questions.">
        <SearchBox value={search} onChange={setSearch} />
        <FilterButton value={filters} onChange={setFilters} />
        {manage && (
          <button type="button" onClick={() => void actions.run(null, "upload")}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm shadow-blue-500/30 transition hover:bg-blue-700 active:bg-blue-800">
            <Plus size={14} /> Upload Document
          </button>
        )}
      </PageHeader>

      <section aria-label="Statistics" className="grid grid-cols-2 gap-3.5 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard label="Active documents" value={stats.data?.active_documents} tone="emerald" icon={<FileText size={17} />}
                  chip={addedThisMonth ? `+${addedThisMonth} this month` : undefined} />
        <StatCard label="Total chunks" value={stats.data?.total_chunks.toLocaleString()} tone="blue" icon={<Database size={17} />} />
        <StatCard label="Pending indexing" value={stats.data?.pending_jobs} tone="amber" icon={<Clock size={17} />} />
        <StatCard label="Failed ingestion" value={stats.data?.failed_jobs} tone="rose" icon={<CircleAlert size={17} />} />
        <StatCard label="Last updated" value={stats.data ? relativeTime(stats.data.last_updated) : undefined} tone="teal" icon={<RefreshCw size={17} />} small />
      </section>

      {actions.notice && <p role="status" className="rounded-xl border border-blue-500/20 bg-blue-500/10 px-4 py-2.5 text-xs font-medium text-blue-800 dark:text-blue-300">{actions.notice}</p>}

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        <div className="lg:col-span-9">
          <DocumentsCard documents={documents.data?.items ?? []} departments={departments.data ?? []} search={search}
                         status={filters.status} trust={filters.trust} pageSize={8} manage={manage}
                         selectedId={actions.selected?.document_id ?? null} onSelect={actions.setSelected}
                         onAction={(d, a) => void actions.run(d, a)} />
        </div>
        {manage && <QuickActions selected={actions.selected} run={(a) => void actions.run(actions.selected, a)} />}
      </div>

      <PipelineCard />
      {actions.dialogs}
    </>
  );
}

export function DocumentsPage() {
  const { can } = useAuth();
  const manage = can("documents:manage");
  const { documents, departments } = useDocuments();
  const actions = useDocumentActions(documents.reload);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({ status: "", trust: "" });
  return (
    <>
      <PageHeader title="Documents" subtitle="Every document CampusMate knows, its versions and its trust level.">
        <SearchBox value={search} onChange={setSearch} />
        <FilterButton value={filters} onChange={setFilters} />
        {manage && (
          <button type="button" onClick={() => void actions.run(null, "upload")}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm shadow-blue-500/30 hover:bg-blue-700">
            <Plus size={14} /> Upload Document
          </button>
        )}
      </PageHeader>
      {actions.notice && <p role="status" className="rounded-xl border border-blue-500/20 bg-blue-500/10 px-4 py-2.5 text-xs font-medium text-blue-800 dark:text-blue-300">{actions.notice}</p>}
      <DocumentsCard documents={documents.data?.items ?? []} departments={departments.data ?? []} search={search}
                     status={filters.status} trust={filters.trust} pageSize={20} manage={manage}
                     selectedId={actions.selected?.document_id ?? null} onSelect={(d) => void actions.run(d, "open")}
                     onAction={(d, a) => void actions.run(d, a)} />
      {actions.dialogs}
    </>
  );
}

function SearchBox({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <label className="relative block w-64 md:w-72">
      <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-4" />
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder="Search documents..." aria-label="Search documents"
             className="w-full rounded-xl border border-line bg-panel py-2 pl-9 pr-3.5 text-sm text-ink shadow-sm outline-none placeholder:text-ink-4 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20" />
    </label>
  );
}

function FilterButton({ value, onChange }: { value: { status: string; trust: string }; onChange: (v: { status: string; trust: string }) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);
  const active = value.status || value.trust;
  const select = "mt-1 w-full rounded-lg border border-line bg-panel px-2.5 py-1.5 text-xs text-ink";
  return (
    <div ref={ref} className="relative">
      <button type="button" aria-label="Filter" onClick={() => setOpen(!open)}
              className={`grid h-9 w-9 place-items-center rounded-xl border bg-panel shadow-sm transition hover:bg-panel-2 ${active ? "border-blue-500 text-blue-600" : "border-line text-ink-3"}`}>
        <SlidersHorizontal size={14} />
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-30 w-56 animate-fade-up space-y-3 rounded-2xl border border-line bg-panel p-4 shadow-float">
          <label className="block text-[11px] font-semibold text-ink-3">Status
            <select aria-label="Status" value={value.status} onChange={(e) => onChange({ ...value, status: e.target.value })} className={select}>
              <option value="">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="archived">Archived</option>
            </select>
          </label>
          <label className="block text-[11px] font-semibold text-ink-3">Trust level
            <select aria-label="Trust level" value={value.trust} onChange={(e) => onChange({ ...value, trust: e.target.value })} className={select}>
              <option value="">Official and synthetic</option><option value="official">Official</option><option value="synthetic">Synthetic demo</option>
            </select>
          </label>
          {active && <button type="button" onClick={() => onChange({ status: "", trust: "" })} className="text-xs font-semibold text-blue-600">Clear filters</button>}
        </div>
      )}
    </div>
  );
}

const TONE = {
  emerald: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400", blue: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  amber: "bg-amber-500/10 text-amber-500", rose: "bg-rose-500/10 text-rose-500", teal: "bg-teal-500/10 text-teal-600 dark:text-teal-400",
};

function StatCard({ label, value, tone, icon, chip, small }: {
  label: string; value: ReactNode; tone: keyof typeof TONE; icon: ReactNode; chip?: string; small?: boolean;
}) {
  return (
    <div className={`${card} flex items-center justify-between p-4`}>
      <div className="min-w-0">
        <span className="block text-xs font-medium uppercase tracking-wider text-ink-4">{label}</span>
        <div className="mt-1 flex flex-wrap items-baseline gap-2">
          <span className={`${small ? "text-base" : "text-2xl"} font-bold text-ink`}>{value ?? "–"}</span>
          {chip && <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">{chip}</span>}
        </div>
      </div>
      <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${TONE[tone]}`}>{icon}</span>
    </div>
  );
}

const ACTIONS = [
  { action: "upload", title: "Upload Document", text: "Add new PDF to knowledge base", Icon: CloudUpload, tone: "emerald", needsSelection: false },
  { action: "replace", title: "Replace Document", text: "Upload a new version of the selected one", Icon: ArrowLeftRight, tone: "purple", needsSelection: true },
  { action: "reindex", title: "Re-Index Document", text: "Process and update embeddings", Icon: RefreshCw, tone: "blue", needsSelection: true },
  { action: "toggle", title: "Deactivate Document", text: "Hide document without deleting", Icon: EyeOff, tone: "amber", needsSelection: true },
  { action: "delete", title: "Delete Document", text: "Remove it from the knowledge base", Icon: Trash2, tone: "rose", needsSelection: true },
] as const;

const ACTION_TONE = {
  emerald: ["bg-emerald-500/10 text-emerald-600", "hover:border-emerald-300 hover:bg-emerald-500/5"],
  purple: ["bg-purple-500/10 text-purple-600", "hover:border-purple-300 hover:bg-purple-500/5"],
  blue: ["bg-blue-500/10 text-blue-600", "hover:border-blue-300 hover:bg-blue-500/5"],
  amber: ["bg-amber-500/10 text-amber-600", "hover:border-amber-300 hover:bg-amber-500/5"],
  rose: ["bg-rose-500/10 text-rose-600", "hover:border-rose-300 hover:bg-rose-500/5"],
};

function QuickActions({ selected, run }: { selected: DocumentSummary | null; run: (a: "upload" | "replace" | "reindex" | "deactivate" | "activate" | "delete") => void }) {
  return (
    <section aria-label="Quick Actions" className={`${card} flex flex-col space-y-3 p-5 lg:col-span-3`}>
      <div>
        <h3 className="text-sm font-bold text-ink">Quick Actions</h3>
        <p className="mt-0.5 truncate text-[11px] text-ink-4" title={selected?.title}>
          {selected ? <>Selected: <span className="font-semibold text-ink-2">{selected.title}</span></> : "Select a document in the table"}
        </p>
      </div>
      {ACTIONS.map(({ action, title, text, Icon, tone, needsSelection }) => {
        const reactivate = action === "toggle" && selected && selected.status !== "active";
        const blocked = (needsSelection && !selected) || (action === "reindex" && selected?.status !== "active")
          || (selected?.status === "deleted" && action !== "upload");
        const [iconTone, hoverTone] = ACTION_TONE[reactivate ? "emerald" : tone];
        return (
          <button key={action} type="button" disabled={blocked}
                  onClick={() => run(action === "toggle" ? (reactivate ? "activate" : "deactivate") : action)}
                  className={`group flex items-center gap-3 rounded-xl border border-line-2 p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-45 ${blocked ? "" : hoverTone}`}>
            <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg transition-transform group-hover:scale-105 ${iconTone}`}>
              {reactivate ? <Eye size={15} /> : <Icon size={15} />}
            </span>
            <span>
              <span className={`block text-xs font-semibold ${action === "delete" ? "text-rose-600" : "text-ink"}`}>
                {reactivate ? "Activate Document" : title}
              </span>
              <span className="block text-[11px] text-ink-4">{reactivate ? "Answer from it again" : text}</span>
            </span>
          </button>
        );
      })}
    </section>
  );
}

// What actually happens to an uploaded PDF (backend/app/ingestion), stated plainly.
function PipelineCard() {
  const info = useLoad(() => api.systemInfo(), []);
  const steps = [
    ["Upload PDF", "SHA-256 fingerprint, PDF signature and size checks"],
    ["Validate & Extract", "Text per page with pypdf, within the document’s page scope"],
    ["Structure-aware Chunking", "Up to 1,200 characters; table lines are never cut"],
    ["Embeddings & BM25", info.data ? `${info.data.embedding_model} → ${info.data.vector_store}` : "Embedding model → vector store"],
    ["Active in KB", "Ready for grounded, cited answers"],
  ];
  return (
    <section aria-label="Ingestion pipeline" className={`${card} p-5`}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-line-2 pb-4">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-500" />
          <h3 className="text-sm font-bold text-ink">Document Ingestion Pipeline (5-Step Engine)</h3>
        </div>
        {info.data && (
          <span className="rounded-md bg-panel-3 px-2.5 py-1 text-xs font-medium text-ink-3">
            {info.data.vector_store} v{info.data.vector_store_version} · {info.data.ingestion_in_api ? "ingestion inside the API" : "separate worker"}
          </span>
        )}
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
        {steps.map(([title, text], i) => (
          <div key={title} className={`rounded-xl border p-3 ${i === 4 ? "border-blue-200 bg-blue-50/70 dark:border-blue-500/25 dark:bg-blue-500/10" : "border-line-2 bg-panel-2"}`}>
            <span className={`text-[10px] font-bold uppercase ${i === 4 ? "text-emerald-600" : "text-blue-600 dark:text-blue-400"}`}>Step 0{i + 1}</span>
            <div className="mt-1 text-xs font-semibold text-ink">{title}</div>
            <p className="mt-0.5 text-[11px] text-ink-3">{text}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-blue-500/15 bg-panel-2 p-3 text-xs text-ink-2">
        <ShieldCheck size={15} className="mt-px shrink-0 text-blue-500" />
        <p>
          <span className="font-semibold text-ink">Document-level isolated scope:</span> replacing or deactivating a document never
          wipes or rebuilds the global index. PostgreSQL decides which versions are active, and only those are searched.
        </p>
      </div>
    </section>
  );
}
