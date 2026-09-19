// Faculty directory, academic calendar and policies: read-only views of the knowledge base.
// In the current dataset all three are synthetic demo data, and every item says so.

import { CalendarClock, ChevronDown, FileText, Mail, Search, Sparkles, UserRound, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { api } from "../api/client";
import type { CalendarEvent, FacultyDetail, Policy } from "../api/types";
import { EmptyState, ErrorNote, Spinner, TrustBadge } from "../components/ui";
import { formatDate, humanize, initials } from "../lib/format";
import { useLoad } from "../lib/useLoad";
import { PageCard } from "./StudentLayout";
import { useWorkspace } from "./workspace";

const DemoNote = () => (
  <p className="mb-4 flex items-center gap-2 rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-300">
    <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
    This section is synthetic demo data: realistic, but not official Ganpat University information.
  </p>
);

// --- faculty ----------------------------------------------------------------------------------

export function FacultyPage() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const faculty = useLoad(() => api.faculty({ q: search || undefined, limit: 100 }), [search]);
  useEffect(() => {
    const timer = setTimeout(() => setSearch(q.trim()), 250);
    return () => clearTimeout(timer);
  }, [q]);
  const openId = params.get("id");

  return (
    <PageCard eyebrow="Faculty Directory" title="People of the IT department"
              subtitle="Designations, specialisations, consultation hours and the courses each member teaches."
              actions={
                <label className="relative block w-full sm:w-72">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-4" />
                  <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name or specialisation"
                         aria-label="Search faculty" className="w-full rounded-xl border border-line bg-panel py-2 pl-8 pr-3 text-xs outline-none focus:border-blue-500" />
                </label>
              }>
      <DemoNote />
      {faculty.error && <ErrorNote>{faculty.error}</ErrorNote>}
      {faculty.loading && !faculty.data && <Spinner label="Loading…" />}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {(faculty.data?.items ?? []).map((f) => (
          <button key={f.faculty_id} type="button" onClick={() => setParams({ id: f.faculty_id })}
                  className="group flex items-start gap-3 rounded-xl border border-line bg-panel p-3.5 text-left shadow-sm transition hover:border-ink-4/50 hover:shadow-card">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gradient-to-tr from-slate-700 to-slate-900 text-xs font-bold text-white">{initials(f.name)}</span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold text-ink group-hover:text-blue-600">{f.name}</span>
              <span className="block truncate text-[11px] text-ink-3">{f.designation}</span>
              {f.email && <span className="mt-1 flex items-center gap-1 truncate text-[11px] text-ink-4"><Mail size={11} />{f.email}</span>}
            </span>
            <TrustBadge type={f.provenance.source_type} compact />
          </button>
        ))}
      </div>
      {faculty.data?.items.length === 0 && <EmptyState icon={<UserRound size={18} />} title="No one matches">Try another name or subject.</EmptyState>}
      {openId && <FacultyDrawer facultyId={openId} onClose={() => setParams({})} />}
    </PageCard>
  );
}

function FacultyDrawer({ facultyId, onClose }: { facultyId: string; onClose: () => void }) {
  const member = useLoad(() => api.facultyMember(facultyId), [facultyId]);
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-sm" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-label="Faculty member" onClick={(e) => e.stopPropagation()}
             className="h-full w-full max-w-md animate-fade-up overflow-y-auto border-l border-line bg-panel p-6 shadow-2xl">
        <button type="button" onClick={onClose} aria-label="Close" className="float-right grid h-8 w-8 place-items-center rounded-lg text-ink-4 hover:bg-panel-3"><X size={16} /></button>
        {member.loading && <Spinner label="Loading…" />}
        {member.error && <ErrorNote>{member.error}</ErrorNote>}
        {member.data && <FacultyBody f={member.data} />}
      </aside>
    </div>
  );
}

function FacultyBody({ f }: { f: FacultyDetail }) {
  const rows: [string, string | null][] = [
    ["Qualification", f.qualification], ["Specialisation", f.specialization],
    ["Office", f.office_room?.room_number ?? null], ["Consultation hours", f.consultation_hours], ["Email", f.email],
  ];
  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <span className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-sm font-bold text-white">{initials(f.name)}</span>
        <div>
          <h2 className="text-lg font-bold text-ink">{f.name}</h2>
          <p className="text-xs text-ink-3">{f.designation}{f.is_head_of_department ? " · Head of Department" : ""}</p>
        </div>
      </div>
      <TrustBadge type={f.provenance.source_type} />
      <dl className="space-y-2 rounded-xl border border-line bg-panel-2 p-3.5 text-xs">
        {rows.filter(([, v]) => v).map(([k, v]) => (
          <div key={k} className="flex gap-3"><dt className="w-32 shrink-0 text-ink-4">{k}</dt><dd className="text-ink-2">{v}</dd></div>
        ))}
      </dl>
      {f.research_areas.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {f.research_areas.map((a) => <span key={a} className="rounded-full bg-indigo-500/10 px-2.5 py-1 text-[11px] font-medium text-indigo-700 dark:text-indigo-300">{a}</span>)}
        </div>
      )}
      {f.teaching.length > 0 && (
        <div>
          <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-ink-4">Teaches</p>
          <ul className="space-y-1.5">
            {f.teaching.map((t) => (
              <li key={t.course.course_id + t.semester_id} className="flex items-center gap-2 text-xs text-ink-2">
                <span className="font-mono text-[11px] font-semibold text-blue-700 dark:text-blue-400">{t.course.course_code}</span>
                <span className="truncate">{t.course.course_name}</span>
                <span className="ml-auto shrink-0 text-[10px] text-ink-4">{t.role}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// --- calendar ---------------------------------------------------------------------------------

export function CalendarPage() {
  const { scope } = useWorkspace();
  const [onlySemester, setOnlySemester] = useState(true);
  const [type, setType] = useState("");
  const semesterId = onlySemester ? scope.semesterId : "";
  const semesterNo = Number(scope.semesterId.split("-").pop());  // SEM-BTECH-IT-06 -> 6
  const events = useLoad(() => api.calendar(semesterId || undefined), [semesterId]);
  const types = useMemo(() => [...new Set((events.data ?? []).map((e) => e.event_type).filter(Boolean))] as string[], [events.data]);
  const shown = (events.data ?? []).filter((e) => !type || e.event_type === type);
  const months = useMemo(() => {
    const groups = new Map<string, CalendarEvent[]>();
    for (const e of shown) {
      const key = new Date(e.start_date).toLocaleDateString("en-GB", { month: "long", year: "numeric" });
      groups.set(key, [...(groups.get(key) ?? []), e]);
    }
    return [...groups.entries()];
  }, [shown]);

  return (
    <PageCard eyebrow="Exam Schedules" title="Academic calendar"
              subtitle="Terms, examinations, holidays and deadlines, in date order.">
      <DemoNote />
      <div className="mb-5 flex flex-wrap items-center gap-1.5">
        <Chip active={!type} onClick={() => setType("")}>All events</Chip>
        {types.map((t) => <Chip key={t} active={type === t} onClick={() => setType(t)}>{humanize(t)}</Chip>)}
        {scope.semesterId && (
          <label className="ml-auto flex items-center gap-2 text-xs text-ink-3">
            <input type="checkbox" checked={onlySemester} onChange={(e) => setOnlySemester(e.target.checked)} className="accent-blue-600" />
            Only {semesterNo ? `semester ${semesterNo}` : "the selected semester"}
          </label>
        )}
      </div>
      {events.loading && !events.data && <Spinner label="Loading the calendar…" />}
      {events.error && <ErrorNote>{events.error}</ErrorNote>}
      <div className="space-y-6">
        {months.map(([month, list]) => (
          <section key={month}>
            <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-ink-4">{month}</h3>
            <ul className="space-y-2">
              {list.map((e) => {
                const start = new Date(e.start_date);
                const exam = (e.event_type ?? "").toLowerCase().includes("exam");
                return (
                  <li key={e.event_id} className="flex items-center gap-3.5 rounded-xl border border-line bg-panel p-3">
                    <span className={`grid h-12 w-12 shrink-0 place-items-center rounded-xl text-center leading-none ${exam ? "bg-rose-500/10 text-rose-600 dark:text-rose-400" : "bg-blue-500/10 text-blue-600 dark:text-blue-400"}`}>
                      <span><span className="block text-base font-bold">{start.getDate()}</span><span className="text-[9px] font-semibold uppercase">{start.toLocaleDateString("en-GB", { month: "short" })}</span></span>
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-ink">{e.title}</span>
                      <span className="block text-[11px] text-ink-3">
                        {e.start_date === e.end_date ? formatDate(e.start_date) : `${formatDate(e.start_date)} – ${formatDate(e.end_date)}`}
                        {e.term ? ` · ${e.term}` : ""}{e.academic_year ? ` · ${e.academic_year}` : ""}
                      </span>
                    </span>
                    {e.event_type && <span className="hidden rounded-md bg-panel-3 px-2 py-0.5 text-[10px] font-semibold capitalize text-ink-2 sm:inline">{humanize(e.event_type)}</span>}
                    <TrustBadge type={e.provenance.source_type} compact />
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
      {events.data && shown.length === 0 && <EmptyState icon={<CalendarClock size={18} />} title="No events">Nothing is scheduled for this selection.</EmptyState>}
    </PageCard>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick}
            className={`rounded-full px-3.5 py-1.5 text-xs font-medium capitalize transition ${active ? "bg-blue-600 text-white shadow-sm" : "text-ink-2 hover:bg-panel-3"}`}>
      {children}
    </button>
  );
}

// --- policies ---------------------------------------------------------------------------------

export function PoliciesPage() {
  const policies = useLoad(() => api.policies(), []);
  const { ask } = useWorkspace();
  const navigate = useNavigate();
  return (
    <PageCard eyebrow="Academic Ordinances" title="Policies and regulations"
              subtitle="Attendance, examinations, conduct and the other rules of the department, clause by clause.">
      <DemoNote />
      {policies.loading && !policies.data && <Spinner label="Loading policies…" />}
      {policies.error && <ErrorNote>{policies.error}</ErrorNote>}
      <div className="space-y-3">
        {(policies.data ?? []).map((p) => (
          <PolicyCard key={p.policy_id} policy={p} onAsk={() => { void ask(`What does the ${p.title.replace(" (Demo)", "")} say?`); navigate("/"); }} />
        ))}
      </div>
    </PageCard>
  );
}

function PolicyCard({ policy: p, onAsk }: { policy: Policy; onAsk: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <article className="rounded-xl border border-line bg-panel shadow-sm">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-start gap-3 p-4 text-left">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400"><FileText size={16} /></span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[10px] font-semibold text-ink-4">{p.policy_number}</span>
            {p.category && <span className="rounded-md bg-panel-3 px-1.5 py-0.5 text-[10px] font-semibold capitalize text-ink-2">{humanize(p.category)}</span>}
            <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-semibold capitalize ${p.status === "active" ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400" : "bg-panel-3 text-ink-3"}`}>{p.status}</span>
          </span>
          <span className="mt-1 block text-sm font-semibold text-ink">{p.title}</span>
          {p.summary && <span className="mt-0.5 block text-xs leading-relaxed text-ink-3">{p.summary}</span>}
        </span>
        <TrustBadge type={p.provenance.source_type} compact />
        <ChevronDown size={16} className={`mt-1 shrink-0 text-ink-4 transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="border-t border-line-2 px-4 pb-4 pt-3">
          {p.clauses?.length ? (
            <ol className="list-decimal space-y-1.5 pl-5 text-xs leading-relaxed text-ink-2">
              {p.clauses.map((c, i) => <li key={i}>{c}</li>)}
            </ol>
          ) : <p className="text-xs text-ink-4">No clauses recorded.</p>}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-ink-4">
            <span>
              {p.effective_from ? `In force from ${formatDate(p.effective_from)}` : ""}{p.effective_to ? ` to ${formatDate(p.effective_to)}` : ""}
              {p.academic_year ? ` · ${p.academic_year}` : ""}
            </span>
            <button type="button" onClick={onAsk} className="inline-flex items-center gap-1 rounded-lg border border-line px-2.5 py-1 font-medium text-ink-2 hover:bg-panel-3">
              <Sparkles size={12} className="text-blue-600" /> Ask about this policy
            </button>
          </div>
        </div>
      )}
    </article>
  );
}
