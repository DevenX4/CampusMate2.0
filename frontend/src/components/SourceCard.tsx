import { useState } from "react";

import type { Source } from "../api/types";
import { pages } from "../lib/format";
import { TrustBadge } from "./ui";

// What kind of source it is, as a small badge in the corner (PDF / SQL / KG), like the Stitch design.
const KIND = {
  document: { badge: "PDF", label: "Document passage", className: "bg-rose-500/10 text-rose-600 ring-rose-500/20 dark:text-rose-400" },
  structured: { badge: "SQL", label: "Structured record", className: "bg-blue-500/10 text-blue-600 ring-blue-500/20 dark:text-blue-400" },
  graph: { badge: "KG", label: "Knowledge graph", className: "bg-indigo-500/10 text-indigo-600 ring-indigo-500/20 dark:text-indigo-400" },
} as const;

export function SourceCard({ source, active, onSelect }: { source: Source; active: boolean; onSelect?: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const kind = KIND[source.kind];
  const c = source.citation;
  const long = source.text.length > 260;
  return (
    <article aria-label={`Source ${source.ref}`} onClick={onSelect}
             className={`space-y-2.5 rounded-xl border p-3 transition ${onSelect ? "cursor-pointer" : ""}
                         ${active ? "border-blue-500/50 bg-blue-500/[0.03] shadow-[0_0_0_3px_rgba(37,99,235,0.08)]"
                                  : "border-line bg-panel hover:border-ink-4/50"}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-start gap-2.5">
          <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-lg font-mono text-[9px] font-bold ring-1 ring-inset ${kind.className}`}>
            {kind.badge}
          </span>
          <div className="min-w-0">
            <h4 className="truncate text-xs font-bold leading-tight text-ink" title={c.title}>{c.title}</h4>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-[10px] font-medium text-ink-3">
              {pages(c.page_start, c.page_end) && <span>{pages(c.page_start, c.page_end)}</span>}
              <span aria-hidden>•</span>
              <span className="font-mono">{c.document_id} v{c.version_no}</span>
            </div>
          </div>
        </div>
        <span className="grid h-5 min-w-5 place-items-center rounded-full bg-panel-3 px-1 font-mono text-[10px] font-bold text-ink-2">
          {source.ref}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        <TrustBadge type={source.source_type} compact />
        <span className="text-[10px] text-ink-3">{kind.label}</span>
        <span className={`ml-auto text-[10px] font-semibold ${source.cited ? "text-blue-600 dark:text-blue-400" : "text-ink-4"}`}>
          {source.cited ? "Cited" : "Consulted"}
        </span>
      </div>
      <p className={`whitespace-pre-line rounded-lg border border-line-2 bg-panel-2 p-2.5 font-mono text-[10.5px] leading-relaxed text-ink-2
                     ${expanded || !long ? "" : "line-clamp-6"}`}>
        {source.text}
      </p>
      {long && (
        <button type="button" onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
                className="text-[11px] font-semibold text-blue-600 hover:underline dark:text-blue-400">
          {expanded ? "Show less" : "Show the whole source"}
        </button>
      )}
    </article>
  );
}
