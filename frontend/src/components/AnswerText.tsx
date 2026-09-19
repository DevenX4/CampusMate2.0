import { useState, type ReactNode } from "react";

const CITATION = /\[(\d+(?:\s*,\s*\d+)*)\]/g;
// What the extractive provider puts before a statement from synthetic data, and after the answer.
const SYNTHETIC_PREFIX = "(Synthetic demo data) ";
export const SYNTHETIC_NOTE = "Synthetic demo data is not official GUNI information.";
// A statement cited only to tabulated sources and longer than this is shown as its lead, since
// the table under the answer lists the same evidence ("Semester VI (23 credits): <30 courses>").
const LONG_STATEMENT = 160;

// The answer's paragraphs. A model's own line breaks are kept; the extractive answer has none, so
// it is split after each cited statement ("... [1]. (Synthetic demo data) ... [3].").
export function paragraphs(text: string): string[] {
  const parts = text.includes("\n") ? text.split(/\n\s*/) : text.split(/(?<=\]\.)\s+/);
  return parts.map((p) => p.trim()).filter(Boolean);
}

const refsOf = (text: string) => [...text.matchAll(CITATION)].flatMap((m) => m[1].split(",").map((n) => Number(n.trim())));

// The answer as text, with each [n] turned into a small button that shows source n. The text
// is rendered as plain React text (never as HTML), so an answer cannot inject markup.
export function AnswerText({ text, onCite, activeRef, tabled = [], omit }: {
  text: string;
  onCite: (ref: number) => void;
  activeRef?: number | null;
  tabled?: number[];    // sources whose evidence is shown as a table under the answer
  omit?: string;        // a paragraph shown elsewhere (the synthetic-data note)
}) {
  return (
    <div className="space-y-2.5 leading-relaxed">
      {paragraphs(text).filter((p) => p !== omit).map((p, i) => (
        <Paragraph key={i} text={p} onCite={onCite} activeRef={activeRef} tabled={tabled} />
      ))}
    </div>
  );
}

function Paragraph({ text, onCite, activeRef, tabled }: {
  text: string; onCite: (ref: number) => void; activeRef?: number | null; tabled: number[];
}) {
  const [full, setFull] = useState(false);
  const synthetic = text.startsWith(SYNTHETIC_PREFIX);
  const body = synthetic ? text.slice(SYNTHETIC_PREFIX.length) : text;
  const refs = refsOf(body);
  const lead = body.split(/:\s/)[0];
  const summarised = !full && body.length > LONG_STATEMENT && refs.length > 0 && refs.every((r) => tabled.includes(r))
                     && lead.length < body.length && lead.length <= 120;
  const cite = (t: string) => <Cited text={t} onCite={onCite} activeRef={activeRef} />;

  return (
    <div>
      {synthetic && (
        <span className="mr-1.5 inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-1.5 py-px align-[1px] text-[10px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-500/25 dark:text-amber-400">
          <span className="h-1 w-1 rounded-full bg-amber-500" />Synthetic demo
        </span>
      )}
      {summarised ? (
        <>
          <span className="font-semibold text-ink">{lead}</span>
          <span className="text-ink-3">, listed in the table below</span>
          {cite(` [${[...new Set(refs)].join(", ")}]. `)}
          <button type="button" onClick={() => setFull(true)} className="text-[11px] font-semibold text-blue-600 hover:underline dark:text-blue-400">
            Show as text
          </button>
        </>
      ) : (
        // " | " separates the parts of a computed statement (regular courses | each elective slot).
        body.split(" | ").map((part, i) => <span key={i} className={i ? "mt-1 block" : ""}>{cite(part)}</span>)
      )}
    </div>
  );
}

function Cited({ text, onCite, activeRef }: { text: string; onCite: (ref: number) => void; activeRef?: number | null }) {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(CITATION)) {
    parts.push(text.slice(last, match.index));
    const refs = match[1].split(",").map((n) => Number(n.trim()));
    parts.push(
      <span key={match.index} className="whitespace-nowrap">
        {refs.map((ref) => (
          <button key={ref} type="button" onClick={() => onCite(ref)} aria-label={`Show source ${ref}`}
                  className={`mx-0.5 inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-md px-1 align-[1px]
                              font-mono text-[10px] font-semibold transition
                              ${activeRef === ref
                                ? "bg-blue-600 text-white shadow-[0_0_12px_rgba(37,99,235,0.35)]"
                                : "bg-blue-500/10 text-blue-700 ring-1 ring-inset ring-blue-500/20 hover:bg-blue-500/20 dark:text-blue-400"}`}>
            {ref}
          </button>
        ))}
      </span>,
    );
    last = (match.index ?? 0) + match[0].length;
  }
  parts.push(text.slice(last));
  return <>{parts}</>;
}
