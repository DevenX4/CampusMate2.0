import { BookOpen, CalendarClock, FileText, History, Home, Plus, Search, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router";

import { api } from "../api/client";
import { trustDot } from "../components/ui";
import { useLoad } from "../lib/useLoad";
import { useWorkspace } from "./workspace";

const TOOLS = [
  { to: "/", label: "Home Hub", Icon: Home, end: true },
  { to: "/curriculum", label: "Curriculum & Syllabi", Icon: BookOpen },
  { to: "/calendar", label: "Exam Schedules", Icon: CalendarClock },
  { to: "/policies", label: "Academic Ordinances", Icon: FileText },
  { to: "/faculty", label: "Faculty Directory", Icon: Users },
];

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { reset, ask, historyVersion } = useWorkspace();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const sources = useLoad(() => api.sources(), []);
  const info = useLoad(() => api.systemInfo(), []);
  const history = useLoad(() => api.history(search || undefined), [search, historyVersion]);

  useEffect(() => {  // search the archive once typing pauses
    const timer = setTimeout(() => setSearch(q.trim()), 250);
    return () => clearTimeout(timer);
  }, [q]);

  const chunks = (sources.data ?? []).reduce((sum, s) => sum + s.chunks, 0);

  return (
    <div className="flex h-full flex-col justify-between gap-4">
      <div className="space-y-4">
        <button type="button" onClick={() => { reset(); navigate("/"); onNavigate?.(); }}
                className="group flex w-full items-center justify-between rounded-xl bg-solid px-3.5 py-2.5 text-xs font-medium text-solid-ink shadow-sm transition hover:opacity-90 active:scale-[0.98]">
          <span className="flex items-center gap-2">
            <Plus size={16} strokeWidth={2.2} className="text-blue-400 transition-transform duration-300 group-hover:rotate-90" />
            New Academic Query
          </span>
          <span className="rounded border border-white/10 bg-white/10 px-1.5 py-0.5 font-mono text-[10px] opacity-80 dark:border-black/10 dark:bg-black/10">Alt N</span>
        </button>

        <div>
          <label className="relative block">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-4" />
            <span className="sr-only">Search your questions</span>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search archive..."
                   className="w-full rounded-xl border border-line bg-panel py-1.5 pl-8 pr-3 text-xs text-ink outline-none transition placeholder:text-ink-4 focus:border-ink-2" />
          </label>
          {(history.data?.length ?? 0) > 0 && (
            <ul className="mt-2 space-y-0.5">
              {history.data!.filter((h, i, all) => all.findIndex((o) => o.question === h.question) === i).slice(0, 5).map((h) => (
                <li key={h.query_id}>
                  <button type="button" title={h.question}
                          onClick={() => { void ask(h.question); navigate("/"); onNavigate?.(); }}
                          className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[11px] text-ink-3 transition hover:bg-panel-3 hover:text-ink">
                    <History size={12} className="shrink-0 text-ink-4" />
                    <span className="truncate">{h.question}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {search && history.data?.length === 0 && <p className="mt-2 px-2 text-[11px] text-ink-4">No earlier question matches.</p>}
        </div>

        <div>
          <div className="mb-1.5 px-2 text-[10px] font-bold uppercase tracking-wider text-ink-4">Universal Tools</div>
          <nav aria-label="Tools" className="space-y-0.5 text-xs font-medium">
            {TOOLS.map(({ to, label, Icon, end }) => (
              <NavLink key={to} to={to} end={end} onClick={onNavigate}
                       className={({ isActive }) => `flex items-center justify-between rounded-xl px-3 py-2 transition ${
                         isActive ? "bg-solid font-semibold text-solid-ink shadow-sm" : "text-ink-2 hover:bg-panel-3"}`}>
                {({ isActive }) => (
                  <>
                    <span className="flex items-center gap-2.5">
                      <Icon size={16} className={isActive ? "text-blue-400" : "text-ink-4"} />
                      {label}
                    </span>
                    {isActive && <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />}
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="border-t border-line pt-3">
          <div className="mb-2 px-2 text-[10px] font-bold uppercase tracking-wider text-ink-4">Verified Repositories</div>
          <ul className="space-y-1.5 px-1 text-[11px]">
            {(sources.data ?? []).map((s) => (
              <li key={s.document_id} title={`${s.title} · ${s.chunks} indexed passages`}
                  className="flex items-center justify-between gap-2 rounded-lg border border-line-2 bg-panel px-2 py-1">
                <span className="flex min-w-0 items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${trustDot(s.source_type)}`} />
                  <span className="truncate font-medium text-ink-2">{s.title}</span>
                </span>
                <span className="shrink-0 font-mono text-[9px] text-ink-4">{s.source_type === "official" ? "Official" : "Demo"}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-slate-700/50 bg-gradient-to-br from-slate-900 to-slate-800 p-3.5 text-white shadow-sm">
        <div className="mb-1 flex items-center justify-between text-[11px] font-semibold text-blue-400">
          <span>Grounded answers</span>
          <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
        </div>
        <p className="text-xs font-semibold leading-snug">Every answer cites its source</p>
        <p className="mt-1 text-[10px] leading-relaxed text-slate-300">
          Official records and synthetic demo data are labelled, and CampusMate says so when it does not know.
        </p>
        <div className="mt-3 flex items-center justify-between border-t border-slate-700/70 pt-2 text-[10px] text-slate-300">
          <span>{sources.data ? `${sources.data.length} documents · ${chunks} passages` : "…"}</span>
          {info.data && <span className="font-mono text-emerald-400">v{info.data.version}</span>}
        </div>
      </div>
    </div>
  );
}

