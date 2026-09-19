import { forwardRef, useState } from "react";
import { Database, FileText, Network } from "lucide-react";

import type { Source } from "../api/types";
import { TrustBadge } from "./TrustBadge";

const KINDS = {
  structured: { label: "Structured record", Icon: Database },
  graph: { label: "Knowledge graph", Icon: Network },
  document: { label: "Document passage", Icon: FileText },
} as const;

export function pages(start: number | null, end: number | null): string {
  if (start === null) return "";
  return end !== null && end !== start ? `pp. ${start}-${end}` : `p. ${start}`;
}

export const SourceCard = forwardRef<HTMLElement, { source: Source; active: boolean }>(function SourceCard(
  { source, active }, ref,
) {
  const [expanded, setExpanded] = useState(false);
  const { Icon, label } = KINDS[source.kind];
  const c = source.citation;
  const long = source.text.length > 280;
  return (
    <article ref={ref} aria-label={`Source ${source.ref}`}
             className={`rounded-lg border bg-surface p-4 transition-shadow
                         ${active ? "border-accent/40 shadow-float" : "border-line"}`}>
      <header className="flex items-start gap-3">
        <span className="mt-0.5 inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-accent-soft px-1.5
                         font-mono text-xs text-accent">{source.ref}</span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium" title={c.title}>{c.title}</p>
          <p className="mt-0.5 text-xs text-ink-3">
            {c.document_id} · v{c.version_no}{pages(c.page_start, c.page_end) && ` · ${pages(c.page_start, c.page_end)}`}
          </p>
        </div>
      </header>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-ink-2">
        <TrustBadge type={source.source_type} />
        <span className="inline-flex items-center gap-1"><Icon size={13} aria-hidden /> {label}</span>
        <span className={source.cited ? "font-medium text-ink" : "text-ink-3"}>
          {source.cited ? "Cited in the answer" : "Consulted, not cited"}
        </span>
      </div>
      <p className={`mt-3 whitespace-pre-line rounded-md bg-sunken p-3 font-mono text-[12.5px] leading-5 text-ink-2
                     ${expanded || !long ? "" : "line-clamp-5"}`}>
        {source.text}
      </p>
      {long && (
        <button type="button" onClick={() => setExpanded(!expanded)}
                className="mt-2 text-xs font-medium text-accent hover:underline">
          {expanded ? "Show less" : "Show the whole source"}
        </button>
      )}
    </article>
  );
});
