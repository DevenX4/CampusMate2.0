import {
  AlertTriangle, BookOpen, Check, ChevronRight, Clipboard, Clock, Eye, FileText, GitBranch, Info, Layers, PanelRightOpen,
  PenLine, Route, Sun, UserRound,
} from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { api } from "../api/client";
import type { AnswerTable, ChatResponse } from "../api/types";
import { AnswerText, SYNTHETIC_NOTE } from "../components/AnswerText";
import { useLoad } from "../lib/useLoad";
import { Composer } from "./Composer";
import { InsightPanel } from "./InsightPanel";
import { useWorkspace, type Turn } from "./workspace";

// Example questions only: the answers, and every fact in them, come from the API.
const INQUIRIES = [
  { label: "Semester VI courses & credits", question: "What courses are offered in Semester VI of B.Tech IT?", Icon: BookOpen, tone: "blue" },
  { label: "Attendance policy", question: "What does the attendance policy say?", Icon: Clock, tone: "emerald" },
  { label: "DBMS credits & scheme", question: "How many credits does DATABASE MANAGEMENT SYSTEM carry?", Icon: PenLine, tone: "indigo" },
  { label: "Head of the IT department", question: "Who is the head of the IT department?", Icon: UserRound, tone: "amber" },
] as const;

const TONES = {
  blue: "bg-blue-500/10 text-blue-600 dark:text-blue-400 group-hover:text-blue-600",
  emerald: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  indigo: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
  amber: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
};

// A different usage tip each day (instead of a quotation: nothing here needs a source).
const TIPS = [
  "Click any number like [1] in an answer to see the exact document and page it comes from.",
  "Choose your programme and semester at the top, then simply ask “Which courses are in this semester?”",
  "Amber means synthetic demo data: never official Ganpat University information.",
  "Ask “According to official sources, …” and CampusMate leaves demo data out of the answer.",
  "When the knowledge base does not say, CampusMate tells you instead of guessing.",
  "Press Ctrl K to jump to any course or faculty member.",
];

export function AssistantPage() {
  const { turns, busy, ask, panelOpen, setPanelOpen } = useWorkspace();
  const bottom = useRef<HTMLDivElement>(null);

  // A block body on purpose: Chromium's scrollIntoView returns a Promise, and an effect must not
  // return anything but a clean-up function (React calls it on unmount, and crashed the page).
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [turns]);

  return (
    <>
      <main className={`relative col-span-12 flex min-h-0 flex-col overflow-hidden rounded-2xl border border-line bg-panel shadow-glass
                        lg:col-span-9 ${panelOpen ? "xl:col-span-7" : "xl:col-span-10"}`}>
        {!panelOpen && (
          <button type="button" onClick={() => setPanelOpen(true)}
                  className="absolute right-3 top-3 z-10 hidden items-center gap-1.5 rounded-lg border border-line bg-panel px-2.5 py-1.5 text-[11px] font-semibold text-ink-2 shadow-sm hover:text-ink xl:flex">
            <PanelRightOpen size={14} /> Sources
          </button>
        )}
        <div className="flex-1 space-y-6 overflow-y-auto p-4 sm:p-6">
          <Welcome onAsk={ask} busy={busy} />
          {turns.map((turn) => <TurnView key={turn.id} turn={turn} />)}
          <div ref={bottom} />
        </div>
        <Composer onAsk={(q) => void ask(q)} busy={busy} />
      </main>

      <aside aria-label="Sources"
             className={`${panelOpen ? "flex" : "hidden"} fixed inset-y-3 right-3 z-40 w-[min(26rem,calc(100vw-1.5rem))] flex-col rounded-2xl border border-line bg-panel p-4 shadow-float
                         xl:static xl:z-auto xl:col-span-3 xl:w-auto xl:shadow-glass`}>
        <InsightPanel />
      </aside>
    </>
  );
}

function Welcome({ onAsk, busy }: { onAsk: (q: string) => void; busy: boolean }) {
  const programs = useLoad(() => api.programs(), []);
  const effective = programs.data?.find((p) => p.effective_year)?.effective_year;
  const tip = TIPS[Math.floor(Date.now() / 86400000) % TIPS.length];

  return (
    <div className="space-y-4 pt-1">
      <div className="flex flex-col gap-1 border-b border-line pb-2 sm:flex-row sm:items-baseline sm:justify-between">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">University Knowledge Base</span>
          <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-ink sm:text-3xl">Welcome to CampusMate</h1>
        </div>
        {effective && <span className="text-xs font-medium text-ink-4">Official syllabus in effect · {effective.replace("-20", "–")}</span>}
      </div>
      <p className="max-w-2xl text-xs leading-relaxed text-ink-2 sm:text-sm">
        Your campus assistant for the B.Tech and M.Tech IT programmes: courses, credits, electives, faculty, labs, policies
        and the academic calendar. Grounded strictly in verified records, with every source cited.
      </p>

      <div className="group relative overflow-hidden rounded-2xl border border-amber-200/60 bg-gradient-to-r from-amber-50/70 via-orange-50/40 to-yellow-50/60 p-4 transition hover:border-amber-300/80
                      dark:border-amber-500/20 dark:from-amber-500/[0.07] dark:via-orange-500/[0.04] dark:to-yellow-500/[0.05]">
        <div className="flex items-start gap-3.5">
          <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl border border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-400">
            <Sun size={16} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800/80 dark:text-amber-400/90">Tip for today</span>
              <span className="font-mono text-[10px] text-amber-600/70">• Using CampusMate</span>
            </div>
            <p className="font-serif text-sm italic leading-relaxed text-ink sm:text-base">“{tip}”</p>
            <p className="mt-1 text-[11px] font-medium text-ink-3">
              — CampusMate <span className="mx-1 text-ink-4">|</span>
              <span className="font-normal text-amber-700/80 dark:text-amber-400/80">Answers cite the exact page they come from</span>
            </p>
          </div>
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold text-ink-2">Explore Quick Inquiries</span>
          <span className="font-mono text-[10px] text-ink-4">Press tab to select</span>
        </div>
        <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
          {INQUIRIES.map(({ label, question, Icon, tone }) => (
            <button key={label} type="button" disabled={busy} onClick={() => onAsk(question)} title={question}
                    className="group flex h-24 flex-col justify-between rounded-xl border border-line bg-panel p-3 text-left shadow-sm transition hover:border-ink-4/50 hover:bg-panel-2 disabled:opacity-50">
              <span className="flex w-full items-center justify-between">
                <span className={`grid h-6 w-6 place-items-center rounded-lg transition-transform group-hover:scale-105 ${TONES[tone]}`}>
                  <Icon size={14} />
                </span>
                <ChevronRight size={12} className="text-ink-4 transition group-hover:translate-x-0.5 group-hover:text-blue-600" />
              </span>
              <span className="text-[11px] font-medium leading-snug text-ink-2 group-hover:text-ink">{label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  const r = turn.response;
  return (
    <section className="animate-fade-up space-y-4">
      <div className="flex items-start justify-end gap-2.5">
        <p className="max-w-md rounded-2xl rounded-tr-sm bg-solid px-4 py-2.5 text-xs font-medium text-solid-ink shadow-sm">{turn.question}</p>
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-panel bg-panel-3 text-ink-2">
          <UserRound size={14} />
        </span>
      </div>
      <div className="flex items-start gap-3">
        <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-sm">
          <Layers size={15} strokeWidth={2.2} />
        </span>
        <div className="min-w-0 flex-1 space-y-3">
          {!r && !turn.error && <Thinking />}
          {turn.error && <p role="alert" className="text-xs font-medium text-rose-600">{turn.error}</p>}
          {r && <Answer turnId={turn.id} response={r} />}
        </div>
      </div>
    </section>
  );
}

function Thinking() {
  return (
    <div className="space-y-2" aria-live="polite">
      <p className="text-xs font-medium text-ink-3">Searching the knowledge base…</p>
      <div className="h-2.5 w-3/4 animate-pulse rounded-full bg-panel-3" />
      <div className="h-2.5 w-1/2 animate-pulse rounded-full bg-panel-3" />
    </div>
  );
}

function Answer({ turnId, response: r }: { turnId: number; response: ChatResponse }) {
  const { selected, select } = useWorkspace();
  const [copied, setCopied] = useState(false);
  const activeRef = selected?.turn === turnId ? selected.ref : null;
  const cited = r.sources.filter((s) => s.cited);
  const muted = r.answer_type === "abstained" || r.answer_type === "unsupported";

  async function copy() {
    try {
      await navigator.clipboard.writeText(r.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* clipboard not available */ }
  }

  return (
    <>
      <div className={`text-[14px] ${muted ? "text-ink-3" : "text-ink-2"}`}>
        <AnswerText text={r.answer} activeRef={activeRef} onCite={(ref) => select(turnId, ref, "sources")}
                    tabled={r.tables.map((t) => t.ref)} omit={r.contains_synthetic ? SYNTHETIC_NOTE : undefined} />
      </div>
      {r.tables.map((table) => <TableCard key={`${table.ref}-${table.title}`} table={table} onCite={() => select(turnId, table.ref, "sources")} />)}
      {r.contains_synthetic && (
        <Note tone="demo" icon={<AlertTriangle size={14} />}>This answer uses synthetic demo data, which is not official Ganpat University information.</Note>
      )}
      {r.answer_type === "fallback" && (
        <Note tone="info" icon={<Info size={14} />}>Shown in the sources’ own words: the generated answer did not pass the source check.</Note>
      )}
      {r.answer_type === "abstained" && (
        <Note tone="info" icon={<Info size={14} />}>CampusMate only answers from its knowledge base, so it does not guess.</Note>
      )}
      {cited.length > 0 && (
        <button type="button" onClick={() => select(turnId, cited[0].ref, "sources")}
                className="inline-flex max-w-full items-center gap-2 rounded-full border border-blue-200/80 bg-blue-50/90 px-3 py-1 text-[11px] font-medium text-blue-800 transition hover:bg-blue-100
                           dark:border-blue-500/25 dark:bg-blue-500/10 dark:text-blue-300">
          <span className="flex shrink-0 items-center gap-1 font-semibold">
            <FileText size={13} className="text-blue-600 dark:text-blue-400" />
            {cited.length} verified source{cited.length > 1 ? "s" : ""}
          </span>
          <span className="text-blue-300">|</span>
          <span className="truncate text-ink-2">{cited[0].citation.title}</span>
          {cited.length > 1 && <span className="shrink-0 font-semibold text-blue-600 dark:text-blue-400">+{cited.length - 1} more</span>}
        </button>
      )}
      {r.sources.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <Pill icon={<Eye size={12} />} onClick={() => select(turnId, cited[0]?.ref ?? null, "sources")}>Inspect Citations</Pill>
          <Pill icon={<GitBranch size={12} />} onClick={() => select(turnId, cited[0]?.ref ?? null, "tree")}>Knowledge Tree</Pill>
          <Pill icon={<Route size={12} />} onClick={() => select(turnId, cited[0]?.ref ?? null, "trace")}>How it was answered</Pill>
          <Pill icon={copied ? <Check size={12} /> : <Clipboard size={12} />} onClick={() => void copy()}>{copied ? "Copied" : "Copy Answer"}</Pill>
        </div>
      )}
    </>
  );
}

function TableCard({ table, onCite }: { table: AnswerTable; onCite: () => void }) {
  const codeColumn = table.columns[0].toLowerCase().includes("code");
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-panel shadow-sm">
      <div className="flex items-center justify-between gap-2 border-b border-line bg-panel-2 px-3 py-2">
        <span className="truncate text-[11px] font-semibold text-ink-2">{table.title}</span>
        <button type="button" onClick={onCite} className="shrink-0 font-mono text-[10px] font-semibold text-blue-600 hover:underline dark:text-blue-400">
          source [{table.ref}]
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-line bg-panel-2/60 text-ink-3">
            <tr>{table.columns.map((c, i) => <th key={c} className={`px-3 py-2.5 font-semibold ${i === 0 && codeColumn ? "font-mono text-[11px]" : ""}`}>{c}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-line-2 text-ink-2">
            {table.rows.map((row, r) => (
              <tr key={r} className="transition hover:bg-panel-2">
                {row.map((cell, i) => (
                  <td key={i} className={`px-3 py-2.5 ${i === 0 && codeColumn ? "font-mono text-[11px] font-semibold text-blue-700 dark:text-blue-400"
                                                    : i === 1 && codeColumn ? "font-medium text-ink" : ""}`}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Note({ tone, icon, children }: { tone: "demo" | "info"; icon: ReactNode; children: ReactNode }) {
  const style = tone === "demo" ? "border-amber-500/20 bg-amber-500/10 text-amber-800 dark:text-amber-300" : "border-line bg-panel-2 text-ink-2";
  return <p className={`flex items-start gap-2 rounded-xl border px-3 py-2 text-xs ${style}`}><span className="mt-px shrink-0">{icon}</span><span>{children}</span></p>;
}

function Pill({ icon, onClick, children }: { icon: ReactNode; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick}
            className="inline-flex items-center gap-1 rounded-lg border border-line bg-panel px-2.5 py-1 text-[11px] font-medium text-ink-2 shadow-sm transition hover:bg-panel-2 hover:text-ink">
      <span className="text-ink-4">{icon}</span>{children}
    </button>
  );
}
