import { Bell, ChevronDown, LayoutDashboard, LogOut, Menu, Moon, Search, ShieldCheck, Sun } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";

import { api } from "../api/client";
import type { Notice } from "../api/types";
import { useAuth } from "../auth";
import { Kbd, LogoMark, TrustBadge } from "../components/ui";
import { formatDate, initials } from "../lib/format";
import { useLoad } from "../lib/useLoad";
import { useTheme } from "../theme";
import { useWorkspace } from "./workspace";

export function Header({ onSearch, onMenu }: { onSearch: () => void; onMenu: () => void }) {
  const { me, can } = useAuth();
  const { theme, toggle } = useTheme();
  const info = useLoad(() => api.systemInfo(), []);

  return (
    <header className="flex shrink-0 items-center justify-between gap-3 rounded-2xl border border-line bg-panel px-3 py-2.5 shadow-glass sm:px-4">
      <div className="flex min-w-0 items-center gap-4">
        <button type="button" onClick={onMenu} aria-label="Open navigation"
                className="grid h-8 w-8 place-items-center rounded-lg text-ink-3 hover:bg-panel-3 lg:hidden">
          <Menu size={18} />
        </button>
        <Link to="/" className="flex items-center gap-3">
          <LogoMark />
          <div className="hidden sm:block">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-tight text-ink">CampusMate</span>
              {info.data && (
                <span className="rounded-md border border-line bg-panel-3 px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-3">
                  v{info.data.version}
                </span>
              )}
            </div>
            <p className="text-[11px] font-medium text-ink-3">GUNI IT campus assistant</p>
          </div>
        </Link>
        <span className="hidden h-5 w-px bg-line md:block" />
        <LiveStatus />
        <ScopeSelectors />
      </div>

      <div className="flex items-center gap-2">
        <button type="button" onClick={onSearch} title="Search courses and faculty, or ask (Ctrl K)"
                className="hidden items-center gap-2 rounded-lg border border-line bg-panel-3 px-2.5 py-1.5 text-[11px] font-medium text-ink-3 transition hover:text-ink lg:flex">
          <Search size={14} className="text-ink-4" />
          <span className="w-40 text-left xl:w-48">Omni-Search courses, faculty…</span>
          <Kbd>Ctrl K</Kbd>
        </button>
        {me && (
          <span className="hidden items-center gap-1.5 rounded-full border border-line bg-panel-3 px-2.5 py-1 text-[11px] font-medium capitalize text-ink-2 2xl:inline-flex">
            <ShieldCheck size={13} className="text-blue-600 dark:text-blue-400" />
            {me.user.role} access
          </span>
        )}
        {can("documents:read") && (
          <Link to="/admin" title="Knowledge console"
                className="grid h-8 w-8 place-items-center rounded-lg text-ink-3 transition hover:bg-panel-3 hover:text-ink">
            <LayoutDashboard size={16} />
          </Link>
        )}
        <NoticesMenu />
        <button type="button" onClick={toggle} aria-label={theme === "dark" ? "Use light theme" : "Use dark theme"}
                className="grid h-8 w-8 place-items-center rounded-lg text-ink-3 transition hover:bg-panel-3 hover:text-ink">
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <UserMenu />
      </div>
    </header>
  );
}

function LiveStatus() {
  const [live, setLive] = useState<boolean | null>(null);
  useEffect(() => {
    const check = () => api.ready().then(() => setLive(true)).catch(() => setLive(false));
    void check();
    const timer = setInterval(check, 30000);
    return () => clearInterval(timer);
  }, []);
  if (live === null) return null;
  return (
    <span className={`hidden items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-medium md:flex
                      ${live ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                             : "border-rose-500/20 bg-rose-500/10 text-rose-700 dark:text-rose-400"}`}>
      <span className="relative flex h-2 w-2">
        {live && <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-emerald-400 opacity-75" />}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${live ? "bg-emerald-600" : "bg-rose-600"}`} />
      </span>
      {live ? "Knowledge base · Live" : "Server offline"}
    </span>
  );
}

// Department / programme / semester. The semester is used by the assistant when a question does
// not name one ("Which courses are in this semester?").
function ScopeSelectors() {
  const { scope, setScope } = useWorkspace();
  const departments = useLoad(() => api.departments(), []);
  const programs = useLoad(() => api.programs(), []);
  const program = useLoad(() => (scope.programId ? api.program(scope.programId) : Promise.resolve(null)), [scope.programId]);

  useEffect(() => {  // sensible first choice: the (only) department and its first programme
    if (!scope.departmentId && departments.data?.length) setScope({ ...scope, departmentId: departments.data[0].department_id });
    else if (!scope.programId && programs.data?.length) setScope({ ...scope, programId: programs.data[0].program_id });
  }, [departments.data, programs.data, scope, setScope]);

  return (
    <nav aria-label="Academic context" className="hidden items-center gap-1.5 text-xs xl:flex">
      <ScopeSelect label="Dept" value={scope.departmentId} onChange={(v) => setScope({ ...scope, departmentId: v })}
                   options={(departments.data ?? []).map((d) => ({ value: d.department_id, label: d.short_name ?? d.department_name }))} />
      <ScopeSelect label="Program" value={scope.programId} onChange={(v) => setScope({ ...scope, programId: v, semesterId: "" })}
                   options={(programs.data ?? []).map((p) => ({ value: p.program_id, label: p.short_name }))} />
      <ScopeSelect label="Term" value={scope.semesterId} onChange={(v) => setScope({ ...scope, semesterId: v })}
                   placeholder="All semesters"
                   options={(program.data?.semesters ?? []).map((s) => ({ value: s.semester_id, label: s.semester_name.replace("Semester", "Sem") }))} />
    </nav>
  );
}

function ScopeSelect({ label, value, onChange, options, placeholder }: {
  label: string; value: string; onChange: (value: string) => void;
  options: { value: string; label: string }[]; placeholder?: string;
}) {
  return (
    <label className="group relative flex items-center gap-1.5 rounded-lg border border-line bg-panel py-1.5 pl-3 pr-7 font-medium shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition hover:border-ink-4/60">
      <span className="text-ink-4 transition group-hover:text-blue-600">{label}:</span>
      <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}
              className="max-w-36 cursor-pointer appearance-none truncate bg-transparent font-semibold text-ink outline-none">
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      <ChevronDown size={12} className="pointer-events-none absolute right-2.5 text-ink-4" />
    </label>
  );
}

function useOutsideClose(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => { if (!ref.current?.contains(event.target as Node)) close(); };
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && close();
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open, close]);
  return ref;
}

function NoticesMenu() {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const notices = useLoad(() => api.notices(8), []);
  const ref = useOutsideClose(open, () => setOpen(false));
  const current = (notices.data ?? []).filter((n) => n.is_current).length;

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen(!open)} aria-label="Department notices" aria-expanded={open}
              className="relative grid h-8 w-8 place-items-center rounded-lg text-ink-3 transition hover:bg-panel-3 hover:text-ink">
        <Bell size={16} />
        {current > 0 && <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-blue-600" />}
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-40 w-[22rem] animate-fade-up overflow-hidden rounded-2xl border border-line bg-panel shadow-float">
          <div className="flex items-center justify-between border-b border-line-2 px-4 py-3">
            <span className="text-xs font-bold text-ink">Department notices</span>
            <span className="text-[10px] text-ink-3">{current} in force</span>
          </div>
          <ul className="max-h-96 divide-y divide-line-2 overflow-y-auto">
            {(notices.data ?? []).map((n: Notice) => (
              <li key={n.notice_id}>
                <button type="button" onClick={() => setExpanded(expanded === n.notice_id ? null : n.notice_id)}
                        className="w-full px-4 py-3 text-left transition hover:bg-panel-2">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-semibold leading-snug text-ink">{n.title}</span>
                    {n.is_current && <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-600" title="In force" />}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-ink-3">
                    <span>{formatDate(n.notice_date)}</span>
                    <TrustBadge type={n.provenance.source_type} compact />
                  </div>
                  {expanded === n.notice_id && <p className="mt-2 whitespace-pre-line text-[11px] leading-relaxed text-ink-2">{n.content}</p>}
                </button>
              </li>
            ))}
            {notices.data?.length === 0 && <li className="px-4 py-6 text-center text-xs text-ink-3">No notices.</li>}
          </ul>
        </div>
      )}
    </div>
  );
}

function UserMenu() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useOutsideClose(open, () => setOpen(false));
  if (!me) return null;
  const name = me.user.full_name ?? me.user.username ?? me.user.email;

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen(!open)} aria-label="Account" aria-expanded={open}
              className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 text-[11px] font-bold text-white ring-2 ring-panel">
        {initials(name)}
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-40 w-60 animate-fade-up rounded-2xl border border-line bg-panel p-2 shadow-float">
          <div className="px-2.5 py-2">
            <p className="truncate text-xs font-bold text-ink">{name}</p>
            <p className="truncate text-[11px] text-ink-3">{me.user.email}</p>
            <span className="mt-1.5 inline-block rounded-md bg-panel-3 px-1.5 py-0.5 text-[10px] font-semibold capitalize text-ink-2">{me.user.role}</span>
          </div>
          <button type="button" onClick={async () => { await logout(); navigate("/login"); }}
                  className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-xs font-medium text-ink-2 hover:bg-panel-3">
            <LogOut size={14} /> Log out
          </button>
        </div>
      )}
    </div>
  );
}
