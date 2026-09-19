import { Fragment, type ReactNode } from "react";

const CITATION = /\[(\d+(?:\s*,\s*\d+)*)\]/g;

// The answer as text, with each [n] turned into a small button that shows source n. The text
// is rendered as plain React text (never as HTML), so an answer cannot inject markup.
export function AnswerText({ text, onCite, activeRef }: {
  text: string;
  onCite: (ref: number) => void;
  activeRef?: number | null;
}) {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(CITATION)) {
    parts.push(text.slice(last, match.index));
    const refs = match[1].split(",").map((n) => Number(n.trim()));
    parts.push(
      <span key={match.index} className="whitespace-nowrap">
        {refs.map((ref) => (
          <button key={ref} type="button" onClick={() => onCite(ref)}
                  aria-label={`Show source ${ref}`}
                  className={`mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 align-text-top
                              font-mono text-[11px] transition-colors
                              ${activeRef === ref ? "bg-accent text-white" : "bg-accent-soft text-accent hover:bg-accent/15"}`}>
            {ref}
          </button>
        ))}
      </span>,
    );
    last = (match.index ?? 0) + match[0].length;
  }
  parts.push(text.slice(last));
  return <p className="whitespace-pre-line leading-7">{parts.map((part, i) => <Fragment key={i}>{part}</Fragment>)}</p>;
}
