import { ArrowLeft, CheckCircle2, ChevronRight, CircleAlert, GitBranch, Route, ThumbsDown, ThumbsUp, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import type { ChatResponse, KnowledgeItem, Rating } from "../api/types";
import { SourceCard } from "../components/SourceCard";
import { EmptyState, ErrorNote, Spinner, TrustBadge, trustDot } from "../components/ui";
import { humanize } from "../lib/format";
import { useLoad } from "../lib/useLoad";
import { useWorkspace, type PanelTab } from "./workspace";

const TABS: { id: PanelTab; label: string }[] = [
  { id: "sources", label: "Sources" }, { id: "tree", label: "Tree" }, { id: "trace", label: "Trace" },
];

export function InsightPanel() {
  const { turns, selected, select, tab, setTab, setPanelOpen } = useWorkspace();
  const turn = turns.find((t) => t.id === selected?.turn);
  const response = turn?.response ?? null;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-line pb-2.5">
        <div role="tablist" className="flex items-center gap-1 rounded-lg bg-panel-3 p-0.5 text-xs font-semibold text-ink-3">
          {TABS.map((t) => (
            <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}
                    className={`rounded-md px-3 py-1 transition ${tab === t.id ? "bg-panel text-ink shadow-sm" : "hover:text-ink"}`}>
              {t.label}
            </button>
          ))}
        </div>
        <button type="button" onClick={() => setPanelOpen(false)} aria-label="Close the sources panel"
                className="rounded-md p-1 text-ink-4 transition hover:bg-panel-3 hover:text-ink-2">
          <X size={16} />
        </button>
      </div>

      <div className="-mx-1 flex-1 overflow-y-auto px-1 pt-4">
        {!response ? (
          <EmptyState icon={<GitBranch size={18} />} title="Sources appear here">
            Ask a question: every answer lists the exact documents and pages it comes from, how it was found,
            and how far each source can be trusted.
          </EmptyState>
        ) : tab === "sources" ? (
          <SourcesTab response={response} activeRef={selected?.ref ?? null} onSelect={(ref) => select(turn!.id, ref)} />
        ) : tab === "tree" ? (
          <TreeTab response={response} activeRef={selected?.ref ?? null} />
        ) : (
          <TraceTab response={response} />
        )}
      </div>

      {response && response.answer_type !== "unsupported" && <Feedback key={response.query_id} queryId={response.query_id} />}
    </div>
  );
}

function SourcesTab({ response, activeRef, onSelect }: { response: ChatResponse; activeRef: number | null; onSelect: (ref: number) => void }) {
  const cards = useRef(new Map<number, HTMLElement>());
  useEffect(() => {
    if (activeRef !== null) cards.current.get(activeRef)?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [activeRef, response]);

  if (response.sources.length === 0) {
    return <EmptyState icon={<CircleAlert size={18} />} title="No sources">This reply did not use the knowledge base.</EmptyState>;
  }
  const cited = response.sources.filter((s) => s.cited).length;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-bold tracking-tight text-ink">Verified Institutional Sources</h3>
          <span className="grid h-4 min-w-4 place-items-center rounded-full bg-blue-500/15 px-1 text-[10px] font-bold text-blue-700 dark:text-blue-400">{cited}</span>
        </div>
        {response.contains_synthetic ? (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-amber-700 dark:text-amber-400">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> Includes demo data
          </span>
        ) : response.grounding.passed && (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Grounded
          </span>
        )}
      </div>
      {response.sources.map((source) => (
        <div key={source.ref} ref={(node) => { if (node) cards.current.set(source.ref, node); }}>
          <SourceCard source={source} active={source.ref === activeRef} onSelect={() => onSelect(source.ref)} />
        </div>
      ))}
    </div>
  );
}

// The knowledge-graph neighbourhood of what the answer is about; relationships can be followed.
function TreeTab({ response, activeRef }: { response: ChatResponse; activeRef: number | null }) {
  const start = (response.sources.find((s) => s.ref === activeRef && s.entity_ids.length)
                 ?? response.sources.find((s) => s.cited && s.entity_ids.length)
                 ?? response.sources.find((s) => s.entity_ids.length))?.entity_ids[0];
  const [path, setPath] = useState<string[]>(start ? [start] : []);
  useEffect(() => {
    setPath(start ? [start] : []);
  }, [start]);
  const current = path[path.length - 1];
  const item = useLoad(() => (current ? api.entity(current) : Promise.resolve(null)), [current]);

  if (!start) {
    return <EmptyState icon={<GitBranch size={18} />} title="No knowledge-graph entity">The sources of this answer are passages without a known entity.</EmptyState>;
  }
  return (
    <div className="space-y-3">
      {path.length > 1 && (
        <button type="button" onClick={() => setPath(path.slice(0, -1))}
                className="flex items-center gap-1 text-[11px] font-semibold text-blue-600 hover:underline dark:text-blue-400">
          <ArrowLeft size={12} /> Back to {path[path.length - 2]}
        </button>
      )}
      {item.loading && <Spinner label="Loading the knowledge graph…" />}
      {item.error && <ErrorNote>{item.error}</ErrorNote>}
      {item.data && <EntityTree item={item.data} onOpen={(id) => setPath([...path, id])} />}
    </div>
  );
}

function EntityTree({ item, onOpen }: { item: KnowledgeItem; onOpen: (id: string) => void }) {
  const attributes = Object.entries(item.attributes)
    .filter(([, v]) => v !== null && v !== "" && typeof v !== "object").slice(0, 6);
  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-line bg-panel p-3">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-indigo-500/10 px-1.5 py-0.5 font-mono text-[9.5px] font-bold uppercase text-indigo-600 dark:text-indigo-400">{item.type}</span>
          <TrustBadge type={item.source_type} compact />
        </div>
        <p className="mt-1.5 text-sm font-bold leading-snug text-ink">{item.title}</p>
        <p className="font-mono text-[10px] text-ink-4">{item.id}</p>
        {attributes.length > 0 && (
          <dl className="mt-2.5 space-y-1 border-t border-line-2 pt-2.5 text-[11px]">
            {attributes.map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <dt className="w-28 shrink-0 text-ink-4">{humanize(key)}</dt>
                <dd className="min-w-0 break-words text-ink-2">
                  {String(value)}
                  {item.attribute_source_types[key] && <span className={`ml-1.5 inline-block h-1.5 w-1.5 rounded-full ${trustDot(item.attribute_source_types[key])}`} title={item.attribute_source_types[key]} />}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>
      {Object.entries(item.relationships).map(([relation, targets]) => (
        <div key={relation}>
          <p className="mb-1 flex items-center gap-1.5 px-1 text-[10px] font-bold uppercase tracking-wider text-ink-4">
            <GitBranch size={11} /> {humanize(relation)}
          </p>
          <ul className="ml-2 space-y-1 border-l border-line pl-2.5">
            {targets.slice(0, 12).map((t) => (
              <li key={`${relation}-${t.id}`}>
                <button type="button" onClick={() => onOpen(t.id)}
                        className="group flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition hover:bg-panel-3">
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${trustDot(t.source_type)}`} title={t.source_type} />
                  <span className="min-w-0 flex-1 truncate text-[11.5px] text-ink-2">{t.title ?? t.id}</span>
                  <ChevronRight size={12} className="shrink-0 text-ink-4 opacity-0 transition group-hover:opacity-100" />
                </button>
              </li>
            ))}
            {targets.length > 12 && <li className="px-2 text-[10px] text-ink-4">+{targets.length - 12} more</li>}
          </ul>
        </div>
      ))}
    </div>
  );
}

// How the answer was produced: route, reasons, the grounding check, and time per stage.
function TraceTab({ response }: { response: ChatResponse }) {
  const stages = Object.entries(response.timings_ms).filter(([k]) => k !== "total");
  const total = response.timings_ms.total || 1;
  const g = response.grounding;
  return (
    <div className="space-y-4 text-xs">
      <section>
        <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-ink-4"><Route size={11} /> Route</p>
        <div className="flex flex-wrap gap-1.5">
          <span className="rounded-md bg-solid px-2 py-0.5 font-semibold capitalize text-solid-ink">{response.route}</span>
          {response.intents.map((i) => <span key={i} className="rounded-md bg-panel-3 px-2 py-0.5 font-mono text-[10.5px] text-ink-2">{i}</span>)}
        </div>
        <ul className="mt-2 space-y-1 text-[11px] text-ink-2">
          {response.reasons.map((r) => <li key={r} className="flex gap-1.5"><span className="text-ink-4">–</span>{r}</li>)}
        </ul>
      </section>
      <section className="rounded-xl border border-line p-3">
        <p className="flex items-center gap-1.5 font-semibold text-ink">
          {g.passed ? <CheckCircle2 size={14} className="text-emerald-600" /> : <CircleAlert size={14} className="text-rose-600" />}
          Grounding check {g.passed ? "passed" : "failed"}
        </p>
        <p className="mt-1 text-[11px] leading-relaxed text-ink-3">
          Every number, code and name in the answer must occur in a cited source; otherwise the sources’ own words are shown.
        </p>
        {[...g.issues.map((t) => ["issue", t]), ...g.warnings.map((t) => ["note", t])].map(([kind, t]) => (
          <p key={t} className={`mt-1.5 text-[11px] ${kind === "issue" ? "text-rose-600" : "text-ink-3"}`}>{kind === "issue" ? "✗" : "·"} {t}</p>
        ))}
      </section>
      <section>
        <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-ink-4">Answer written by</p>
        <p className="font-medium text-ink-2">{response.provider} · <span className="font-mono text-[11px]">{response.model}</span></p>
      </section>
      <section>
        <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-ink-4">Time · {total} ms</p>
        <div className="space-y-1.5">
          {stages.map(([stage, ms]) => (
            <div key={stage} className="flex items-center gap-2">
              <span className="w-20 shrink-0 capitalize text-ink-3">{stage}</span>
              <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-panel-3">
                <span className="block h-full rounded-full bg-blue-500" style={{ width: `${Math.max(2, (ms / total) * 100)}%` }} />
              </span>
              <span className="w-12 shrink-0 text-right font-mono text-[10.5px] text-ink-3">{ms} ms</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

// One rating per answer, stored with the exact sources that produced it; rating again replaces it.
function Feedback({ queryId }: { queryId: string }) {
  const [rating, setRating] = useState<Rating | null>(null);
  const [comment, setComment] = useState("");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(next: Rating, text?: string) {
    setError(null);
    setRating(next);
    try {
      await api.feedback(queryId, next, text);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Feedback could not be saved.");
    }
  }

  const thumb = (value: Rating) =>
    `rounded-lg p-1.5 transition hover:bg-panel-3 ${rating === value ? "text-blue-600 dark:text-blue-400" : "text-ink-3 hover:text-ink"}`;
  return (
    <div className="mt-4 space-y-2.5 border-t border-line pt-4">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-ink-2">{saved ? "Thanks, your feedback is saved." : "Accurate response?"}</span>
        <div className="flex items-center gap-1.5">
          <button type="button" aria-label="Good answer" aria-pressed={rating === "up"} className={thumb("up")} onClick={() => void send("up", comment)}>
            <ThumbsUp size={16} />
          </button>
          <button type="button" aria-label="Wrong or unhelpful answer" aria-pressed={rating === "down"} className={thumb("down")} onClick={() => void send("down", comment)}>
            <ThumbsDown size={16} />
          </button>
        </div>
      </div>
      <form onSubmit={(e) => { e.preventDefault(); if (comment.trim()) void send(rating ?? "down", comment); }}>
        <label htmlFor={`correction-${queryId}`} className="sr-only">Suggest a correction</label>
        <input id={`correction-${queryId}`} value={comment} maxLength={1000} onChange={(e) => setComment(e.target.value)}
               placeholder="Suggest a correction… (Enter to send)"
               className="w-full rounded-xl border border-line bg-panel px-3 py-1.5 text-xs text-ink shadow-sm outline-none placeholder:text-ink-4 focus:ring-1 focus:ring-blue-600" />
      </form>
      {error && <ErrorNote>{error}</ErrorNote>}
    </div>
  );
}
