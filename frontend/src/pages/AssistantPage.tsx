import { AlertTriangle, BookOpen, Calculator, FlaskConical, Info, ListChecks, Loader2, Sparkles } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { api, ApiError } from "../api/client";
import type { ChatResponse } from "../api/types";
import { useAuth } from "../auth";
import { AnswerText } from "../components/AnswerText";
import { Composer } from "../components/Composer";
import { FeedbackBar } from "../components/FeedbackBar";
import { SourceCard } from "../components/SourceCard";
import { TopBar } from "../components/TopBar";

interface Turn {
  id: number;
  question: string;
  response?: ChatResponse;
  error?: string;
}

// Example questions only: the answers, and every fact in them, come from the API.
const SUGGESTIONS = [
  { Icon: Calculator, label: "Credits of Artificial Intelligence", question: "How many credits does ARTIFICIAL INTELLIGENCE carry in B.Tech IT?" },
  { Icon: ListChecks, label: "Courses in Semester VI", question: "What courses are offered in Semester VI of B.Tech IT?" },
  { Icon: BookOpen, label: "Grade for 85 marks", question: "What grade do I get for 85 marks?" },
  { Icon: FlaskConical, label: "Where AI practicals are held", question: "Which lab hosts the AI practicals?" },
];

const firstCited = (response: ChatResponse) => response.sources.find((s) => s.cited)?.ref ?? response.sources[0]?.ref ?? null;

export function AssistantPage() {
  const { refresh } = useAuth();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<{ turn: number; ref: number | null } | null>(null);
  const nextId = useRef(1);
  const bottom = useRef<HTMLDivElement>(null);

  // A block body on purpose: Chromium's scrollIntoView returns a Promise, and an effect must not
  // return anything but a clean-up function (React calls it on unmount, and crashed the page).
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [turns]);

  async function ask(question: string) {
    const id = nextId.current++;
    setTurns((all) => [...all, { id, question }]);
    setBusy(true);
    try {
      const response = await api.ask(question);
      setTurns((all) => all.map((t) => (t.id === id ? { ...t, response } : t)));
      setSelected({ turn: id, ref: firstCited(response) });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) void refresh();  // session expired: back to login
      const message = error instanceof Error ? error.message : "Something went wrong.";
      setTurns((all) => all.map((t) => (t.id === id ? { ...t, error: message } : t)));
    } finally {
      setBusy(false);
    }
  }

  const active = turns.find((t) => t.id === selected?.turn)?.response ?? null;

  return (
    <div className="min-h-screen">
      <TopBar />
      <div className="mx-auto flex max-w-[1280px] gap-6 px-4 lg:px-8">
        <main className="flex min-h-[calc(100vh-3.5rem)] min-w-0 flex-1 flex-col">
          <div className="mx-auto w-full max-w-[720px] flex-1 py-8">
            {turns.length === 0 ? <Welcome onAsk={ask} busy={busy} /> : turns.map((turn) => (
              <TurnView key={turn.id} turn={turn}
                        activeRef={selected?.turn === turn.id ? selected.ref : null}
                        onCite={(ref) => setSelected({ turn: turn.id, ref })} />
            ))}
            <div ref={bottom} />
          </div>
          <div className="sticky bottom-0 mx-auto w-full max-w-[720px] bg-gradient-to-t from-canvas via-canvas pb-4 pt-2">
            <Composer onAsk={ask} busy={busy} />
            <p className="mt-2 text-center text-xs text-ink-3">
              CampusMate answers only from its knowledge base and cites every source. Sources marked synthetic are
              demo data, not official GUNI information.
            </p>
          </div>
        </main>
        <aside className="sticky top-14 hidden h-[calc(100vh-3.5rem)] w-[400px] shrink-0 overflow-y-auto border-l border-line py-8 pl-6 lg:block"
               aria-label="Sources">
          <SourcesPanel response={active} activeRef={selected?.ref ?? null} />
        </aside>
      </div>
    </div>
  );
}

function Welcome({ onAsk, busy }: { onAsk: (q: string) => void; busy: boolean }) {
  return (
    <section className="pt-6">
      <p className="text-xs font-medium uppercase tracking-wider text-accent">GUNI IT department</p>
      <h1 className="mt-2 text-3xl font-medium tracking-tight sm:text-[32px]">Welcome to CampusMate</h1>
      <p className="mt-3 text-[17px] leading-7 text-ink-2">
        Ask about the B.Tech and M.Tech IT programmes: courses, credits, electives, faculty, labs, policies and the
        academic calendar. Every answer shows where it comes from, and CampusMate says so when it does not know.
      </p>
      <h2 className="mt-10 text-sm font-medium text-ink-2">Try a question</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map(({ Icon, label, question }) => (
          <button key={label} type="button" disabled={busy} onClick={() => onAsk(question)}
                  className="flex items-center gap-3 rounded-lg border border-line bg-surface p-4 text-left text-sm
                             transition-shadow hover:shadow-float disabled:opacity-50">
            <span className="grid h-8 w-8 place-items-center rounded-md bg-accent-soft text-accent"><Icon size={16} aria-hidden /></span>
            {label}
          </button>
        ))}
      </div>
    </section>
  );
}

function TurnView({ turn, activeRef, onCite }: { turn: Turn; activeRef: number | null; onCite: (ref: number) => void }) {
  const r = turn.response;
  return (
    <section className="mb-8">
      <p className="ml-auto w-fit max-w-[85%] rounded-2xl bg-ink px-4 py-2.5 text-[15px] text-white">{turn.question}</p>
      <div className="mt-4 flex gap-3">
        <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md bg-accent text-white"><Sparkles size={15} aria-hidden /></span>
        <div className="min-w-0 flex-1 text-[15px]">
          {!r && !turn.error && (
            <p className="flex items-center gap-2 text-ink-3"><Loader2 size={15} className="animate-spin" aria-hidden />
              Searching the knowledge base...</p>
          )}
          {turn.error && <p role="alert" className="text-danger">{turn.error}</p>}
          {r && (
            <>
              <div className={r.answer_type === "abstained" || r.answer_type === "unsupported" ? "text-ink-2" : ""}>
                <AnswerText text={r.answer} onCite={onCite} activeRef={activeRef} />
              </div>
              {r.contains_synthetic && (
                <Note tone="demo" Icon={AlertTriangle}>
                  This answer uses synthetic demo data, which is not official Ganpat University information.
                </Note>
              )}
              {r.answer_type === "fallback" && (
                <Note tone="info" Icon={Info}>
                  Shown in the sources' own words: the generated answer did not pass the source check.
                </Note>
              )}
              {r.answer_type === "abstained" && (
                <Note tone="info" Icon={Info}>CampusMate only answers from its knowledge base, so it does not guess.</Note>
              )}
              {r.sources.length > 0 && (
                <details className="mt-3 lg:hidden">
                  <summary className="cursor-pointer text-sm text-accent">{r.sources.length} sources</summary>
                  <div className="mt-2 space-y-3">{r.sources.map((s) => <SourceCard key={s.ref} source={s} active={false} />)}</div>
                </details>
              )}
              {r.answer_type !== "unsupported" && <FeedbackBar queryId={r.query_id} />}
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function Note({ tone, Icon, children }: { tone: "demo" | "info"; Icon: typeof Info; children: ReactNode }) {
  const style = tone === "demo" ? "bg-demo-soft text-demo" : "bg-sunken text-ink-2";
  return (
    <p className={`mt-3 flex items-start gap-2 rounded-md px-3 py-2 text-sm ${style}`}>
      <Icon size={15} className="mt-0.5 shrink-0" aria-hidden /> <span>{children}</span>
    </p>
  );
}

function SourcesPanel({ response, activeRef }: { response: ChatResponse | null; activeRef: number | null }) {
  const cards = useRef(new Map<number, HTMLElement>());
  useEffect(() => {
    if (activeRef !== null) cards.current.get(activeRef)?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [activeRef, response]);

  if (!response) {
    return <p className="text-sm text-ink-3">The sources of an answer appear here: which document, which page, and how
      far it can be trusted.</p>;
  }
  if (response.sources.length === 0) {
    return <p className="text-sm text-ink-3">No sources were used for this answer.</p>;
  }
  const cited = response.sources.filter((s) => s.cited).length;
  return (
    <div>
      <h2 className="text-sm font-medium">Sources <span className="text-ink-3">· {cited} cited of {response.sources.length}</span></h2>
      <div className="mt-4 space-y-3">
        {response.sources.map((source) => (
          <SourceCard key={source.ref} source={source} active={source.ref === activeRef}
                      ref={(node) => { if (node) cards.current.set(source.ref, node); else cards.current.delete(source.ref); }} />
        ))}
      </div>
    </div>
  );
}
