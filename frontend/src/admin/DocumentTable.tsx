import { Ellipsis, FileText } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { DocumentAction } from "../api/client";
import { categoryOf, DOCUMENT_CATEGORIES, type Department, type DocumentStatus, type DocumentSummary } from "../api/types";
import { TrustBadge } from "../components/ui";
import { formatDate, relativeTime } from "../lib/format";

export type RowAction = DocumentAction | "delete" | "open" | "replace";

// Which lifecycle actions each status allows (the same rules the server enforces: TRANSITIONS in
// backend/app/services/documents.py). Offering only valid actions saves a round trip.
export const ALLOWED: Record<DocumentStatus, (DocumentAction | "delete")[]> = {
  active: ["deactivate", "archive", "reindex", "delete"],
  inactive: ["activate", "archive", "delete"],
  archived: ["activate", "delete"],
  deleted: [],
};
const LABELS: Record<RowAction, string> = {
  open: "Versions & details", replace: "Upload new version", activate: "Activate", deactivate: "Deactivate",
  archive: "Archive", reindex: "Re-index", delete: "Delete",
};

const STATUS_PILL: Record<DocumentStatus, string> = {
  active: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  inactive: "bg-amber-500/15 text-amber-800 dark:text-amber-400",
  archived: "bg-panel-3 text-ink-3",
  deleted: "bg-rose-500/10 text-rose-700",
};
const STATUS_DOT: Record<DocumentStatus, string> = { active: "bg-emerald-500", inactive: "bg-amber-500", archived: "bg-slate-400", deleted: "bg-rose-500" };

export function CategoryPills({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div className="flex items-center gap-1.5 overflow-x-auto border-b border-line-2 px-5 pb-3 pt-4">
      {["All Documents", ...DOCUMENT_CATEGORIES.map((c) => c.label)].map((label) => {
        const key = label === "All Documents" ? "" : label;
        return (
          <button key={label} type="button" onClick={() => onChange(key)}
                  className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium transition ${
                    value === key ? "bg-blue-600 text-white shadow-sm" : "text-ink-2 hover:bg-panel-3"}`}>
            {label}
          </button>
        );
      })}
    </div>
  );
}

export function DocumentTable({ documents, departments, selectedId, onSelect, onAction, manage }: {
  documents: DocumentSummary[];
  departments: Department[];
  selectedId: string | null;
  onSelect: (document: DocumentSummary) => void;
  onAction: (document: DocumentSummary, action: RowAction) => void;
  manage: boolean;
}) {
  const departmentName = (id: string | null) =>
    departments.find((d) => d.department_id === id)?.department_name.replace(/^Department of /, "") ?? (id ? id : "University");
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-xs">
        <thead>
          <tr className="border-b border-line-2 bg-panel-2/60 font-semibold uppercase tracking-wider text-ink-4">
            <th className="px-4 py-3">Document</th>
            <th className="px-3 py-3">Category</th>
            <th className="hidden px-3 py-3 xl:table-cell">Department</th>
            <th className="hidden px-3 py-3 md:table-cell">Academic year</th>
            <th className="px-2 py-3 text-center">Version</th>
            <th className="px-3 py-3">Status</th>
            <th className="px-3 py-3 text-right">Chunks</th>
            <th className="hidden px-3 py-3 min-[1800px]:table-cell">Updated</th>
            <th className="px-3 py-3 text-center">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line-2 text-ink-2">
          {documents.map((d) => {
            const selected = d.document_id === selectedId;
            const icon = d.status === "active" ? "bg-blue-500/10 text-blue-600 dark:text-blue-400" : "bg-amber-500/10 text-amber-600";
            return (
              <tr key={d.document_id} onClick={() => onSelect(d)} aria-selected={selected}
                  className={`cursor-pointer transition-colors ${selected ? "bg-blue-500/[0.06] shadow-[inset_3px_0_0_#2563eb]"
                                                                 : d.status !== "active" ? "bg-amber-500/[0.03] hover:bg-panel-2" : "hover:bg-panel-2"}`}>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2.5">
                    <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg ${icon}`}><FileText size={15} /></span>
                    <div className="min-w-0">
                      <button type="button" onClick={(e) => { e.stopPropagation(); onAction(d, "open"); }}
                              className="block max-w-[240px] truncate text-left font-semibold text-ink hover:text-blue-600" title={d.title}>{d.title}</button>
                      <div className="mt-0.5 flex items-center gap-1.5">
                        <span className="font-mono text-[10px] text-ink-4">{d.document_id}</span>
                        <TrustBadge type={d.source_type} compact />
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-3 py-3">{categoryOf(d.document_type)}</td>
                <td className="hidden px-3 py-3 text-ink-3 xl:table-cell">{departmentName(d.department_id)}</td>
                <td className="hidden px-3 py-3 text-ink-3 md:table-cell">{d.active_version?.academic_year ?? "–"}</td>
                <td className={`px-2 py-3 text-center font-semibold ${d.status === "active" ? "text-blue-600 dark:text-blue-400" : "text-amber-600"}`}>
                  {d.active_version ? `v${d.active_version.version_no}` : "–"}
                  {d.latest_version_no && d.latest_version_no !== d.active_version?.version_no && (
                    <span className="block text-[10px] font-normal text-ink-4">latest v{d.latest_version_no}</span>
                  )}
                </td>
                <td className="px-3 py-3">
                  <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${STATUS_PILL[d.status]}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[d.status]}`} />{d.status}
                  </span>
                </td>
                <td className={`px-3 py-3 text-right font-semibold ${d.chunk_count ? "text-ink-2" : "text-ink-4"}`}>{d.chunk_count}</td>
                <td className="hidden whitespace-nowrap px-3 py-3 text-ink-3 min-[1800px]:table-cell" title={formatDate(d.updated_at)}>
                  {relativeTime(d.updated_at)}
                </td>
                <td className="px-3 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                  <RowMenu doc={d} manage={manage} onAction={(a) => onAction(d, a)} />
                </td>
              </tr>
            );
          })}
          {documents.length === 0 && (
            <tr><td colSpan={9} className="px-4 py-12 text-center text-ink-4">No documents match.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function RowMenu({ doc, manage, onAction }: { doc: DocumentSummary; manage: boolean; onAction: (a: RowAction) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);
  const actions: RowAction[] = ["open", ...(manage && doc.status !== "deleted" ? ["replace" as const] : []),
                                ...(manage ? ALLOWED[doc.status] : [])];
  return (
    <div ref={ref} className="relative inline-block">
      <button type="button" onClick={() => setOpen(!open)} aria-label={`Actions for ${doc.title}`}
              className="inline-grid h-7 w-7 place-items-center rounded-lg text-ink-4 transition hover:bg-panel-3 hover:text-ink-2">
        <Ellipsis size={16} />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-8 z-30 w-48 animate-fade-up rounded-xl border border-line bg-panel p-1.5 text-left shadow-float">
          {actions.map((a) => (
            <button key={a} type="button" role="menuitem" onClick={() => { setOpen(false); onAction(a); }}
                    className={`block w-full rounded-lg px-3 py-2 text-left text-xs font-medium transition hover:bg-panel-3 ${a === "delete" ? "text-rose-600" : "text-ink-2"}`}>
              {LABELS[a]}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

