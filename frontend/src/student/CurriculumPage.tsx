import { BookOpen, FlaskConical, GraduationCap, Sparkles, Users, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { api } from "../api/client";
import type { CourseDetail, SemesterDetail } from "../api/types";
import { EmptyState, ErrorNote, Spinner, TrustBadge } from "../components/ui";
import { useLoad } from "../lib/useLoad";
import { PageCard } from "./StudentLayout";
import { useWorkspace } from "./workspace";

const num = (v: number | null | undefined) => (v === null || v === undefined ? "–" : String(v));

export function CurriculumPage() {
  const { scope, setScope, ask } = useWorkspace();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const programs = useLoad(() => api.programs(), []);
  const [programId, setProgramId] = useState(scope.programId);
  const [semesterId, setSemesterId] = useState(scope.semesterId);
  const program = useLoad(() => (programId ? api.program(programId) : Promise.resolve(null)), [programId]);
  const semester = useLoad(() => (semesterId ? api.semester(semesterId) : Promise.resolve(null)), [semesterId]);

  useEffect(() => {  // default: the selected (or first) programme and its first semester
    if (!programId && programs.data?.length) setProgramId(programs.data[0].program_id);
  }, [programId, programs.data]);
  useEffect(() => {
    const semesters = program.data?.semesters ?? [];
    if (semesters.length && !semesters.some((s) => s.semester_id === semesterId)) setSemesterId(semesters[0].semester_id);
  }, [program.data, semesterId]);

  const courseId = params.get("course");

  function askAboutSemester(s: SemesterDetail) {
    setScope({ ...scope, programId: s.program.program_id, semesterId: s.semester_id });
    void ask(`Which courses are offered in ${s.semester_name} of ${s.program.short_name}?`);
    navigate("/");
  }

  return (
    <PageCard eyebrow="Curriculum & Syllabi" title="Programmes, semesters and courses"
              subtitle="Straight from the official GUNI structured syllabus: credits, contact hours and marks for every course, semester by semester.">
      {programs.error && <ErrorNote>{programs.error}</ErrorNote>}
      <div className="flex flex-wrap gap-2">
        {(programs.data ?? []).map((p) => (
          <button key={p.program_id} type="button" onClick={() => { setProgramId(p.program_id); setSemesterId(""); }}
                  className={`flex items-center gap-2 rounded-xl border px-3.5 py-2 text-left text-xs transition ${
                    p.program_id === programId ? "border-transparent bg-solid text-solid-ink shadow-sm" : "border-line bg-panel text-ink-2 hover:bg-panel-2"}`}>
            <GraduationCap size={15} className={p.program_id === programId ? "text-blue-400" : "text-ink-4"} />
            <span>
              <span className="block font-semibold">{p.short_name}</span>
              <span className="block text-[10px] opacity-70">{p.program_name}</span>
            </span>
          </button>
        ))}
      </div>

      {program.data && (
        <div className="mt-5 grid gap-3 sm:grid-cols-4">
          <Stat label="Semesters" value={String(program.data.semester_count)} />
          <Stat label="Total credits" value={String(program.data.total_credits)} note="computed from the official semester totals" />
          <Stat label="Syllabus in effect" value={program.data.effective_year ?? "–"} />
          <div className="flex items-center rounded-xl border border-line bg-panel-2 p-3"><TrustBadge type={program.data.provenance.source_type} /></div>
        </div>
      )}

      <div className="mt-5 flex flex-wrap gap-1.5" role="tablist" aria-label="Semesters">
        {(program.data?.semesters ?? []).map((s) => (
          <button key={s.semester_id} type="button" role="tab" aria-selected={s.semester_id === semesterId} onClick={() => setSemesterId(s.semester_id)}
                  className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition ${
                    s.semester_id === semesterId ? "bg-blue-600 text-white shadow-sm" : "text-ink-2 hover:bg-panel-3"}`}>
            {s.semester_name.replace("Semester", "Sem")}
            <span className="ml-1.5 opacity-70">{s.total_credits ?? "–"} cr</span>
          </button>
        ))}
      </div>

      <div className="mt-4">
        {semester.loading && <Spinner label="Loading the semester…" />}
        {semester.error && <ErrorNote>{semester.error}</ErrorNote>}
        {semester.data && <SemesterView semester={semester.data} onCourse={(id) => setParams({ course: id })} onAsk={() => askAboutSemester(semester.data!)} />}
      </div>
      {courseId && <CourseDrawer courseId={courseId} onClose={() => setParams({})} />}
    </PageCard>
  );
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-xl border border-line bg-panel-2 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-ink-4">{label}</p>
      <p className="mt-1 text-lg font-bold text-ink">{value}</p>
      {note && <p className="text-[10px] text-ink-4">{note}</p>}
    </div>
  );
}

function SemesterView({ semester: s, onCourse, onAsk }: { semester: SemesterDetail; onCourse: (id: string) => void; onAsk: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2 text-xs text-ink-3">
          <span className="text-sm font-bold text-ink">{s.program.short_name} · {s.semester_name}</span>
          <span>{num(s.total_credits)} credits</span><span>·</span><span>{num(s.total_marks)} marks</span>
          <TrustBadge type={s.provenance.source_type} compact />
          <span className="font-mono text-[10px] text-ink-4">{s.provenance.document_id} p.{s.provenance.page}</span>
        </div>
        <button type="button" onClick={onAsk}
                className="inline-flex items-center gap-1.5 rounded-lg bg-solid px-3 py-1.5 text-xs font-medium text-solid-ink shadow-sm hover:opacity-90">
          <Sparkles size={13} className="text-blue-400" /> Ask about this semester
        </button>
      </div>

      <div className="overflow-hidden rounded-xl border border-line">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-line bg-panel-2 text-ink-3">
            <tr>
              <th className="px-3 py-2.5 font-mono text-[11px] font-semibold">Course code</th>
              <th className="px-3 py-2.5 font-semibold">Course title</th>
              <th className="px-3 py-2.5 font-semibold">Type</th>
              <th className="px-3 py-2.5 text-center font-semibold">Credits (T + P)</th>
              <th className="px-3 py-2.5 text-center font-semibold">Contact hrs</th>
              <th className="px-3 py-2.5 text-center font-semibold">Marks</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line-2 text-ink-2">
            {s.regular_courses.map((r) => (
              <tr key={r.offering_id} onClick={() => onCourse(r.course.course_id)} className="cursor-pointer transition hover:bg-panel-2">
                <td className="px-3 py-2.5 font-mono text-[11px] font-semibold text-blue-700 dark:text-blue-400">{r.course.course_code}</td>
                <td className="px-3 py-2.5 font-medium text-ink">{r.course.course_name}</td>
                <td className="px-3 py-2.5 capitalize">{r.course_type}</td>
                <td className="px-3 py-2.5 text-center">{num(r.credits.total)} <span className="text-ink-4">({num(r.credits.theory)} + {num(r.credits.practical)})</span></td>
                <td className="px-3 py-2.5 text-center">{num(r.credits.contact_hours)}</td>
                <td className="px-3 py-2.5 text-center">{num(r.marks.total)}</td>
              </tr>
            ))}
            {s.regular_courses.length === 0 && <tr><td colSpan={6} className="px-3 py-6 text-center text-ink-4">No regular courses in this semester.</td></tr>}
          </tbody>
        </table>
      </div>

      {s.elective_slots.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2">
          {s.elective_slots.map((slot) => (
            <div key={slot.elective_group_id} className="rounded-xl border border-line bg-panel p-3.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-ink">{slot.group_name}</span>
                <span className="rounded-md bg-indigo-500/10 px-2 py-0.5 text-[10px] font-semibold text-indigo-600 dark:text-indigo-400">
                  choose one · {num(slot.credits.total)} credits
                </span>
              </div>
              <ul className="mt-2 space-y-1">
                {slot.options.map((c) => (
                  <li key={c.course_id}>
                    <button type="button" onClick={() => onCourse(c.course_id)}
                            className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs transition hover:bg-panel-3">
                      <span className="w-24 shrink-0 font-mono text-[11px] font-semibold text-blue-700 dark:text-blue-400">{c.course_code}</span>
                      <span className="truncate text-ink-2">{c.course_name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CourseDrawer({ courseId, onClose }: { courseId: string; onClose: () => void }) {
  const course = useLoad(() => api.course(courseId), [courseId]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-sm" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-label="Course" onClick={(e) => e.stopPropagation()}
             className="h-full w-full max-w-lg animate-fade-up overflow-y-auto border-l border-line bg-panel p-6 shadow-2xl">
        <button type="button" onClick={onClose} aria-label="Close" className="float-right grid h-8 w-8 place-items-center rounded-lg text-ink-4 hover:bg-panel-3"><X size={16} /></button>
        {course.loading && <Spinner label="Loading the course…" />}
        {course.error && <ErrorNote>{course.error}</ErrorNote>}
        {course.data && <CourseBody course={course.data} />}
      </aside>
    </div>
  );
}

function CourseBody({ course: c }: { course: CourseDetail }) {
  return (
    <div className="space-y-5">
      <div>
        <span className="font-mono text-xs font-semibold text-blue-700 dark:text-blue-400">{c.course_code}</span>
        <h2 className="mt-1 text-xl font-bold tracking-tight text-ink">{c.course_name}</h2>
        <div className="mt-2 flex items-center gap-2"><TrustBadge type={c.provenance.source_type} /><span className="text-[11px] capitalize text-ink-3">{c.curriculum_status.replaceAll("_", " ")}</span></div>
      </div>
      {c.offerings.map((o) => (
        <div key={o.offering_id} className="grid grid-cols-3 gap-2 rounded-xl border border-line bg-panel-2 p-3 text-center">
          <Mini label="Credits" value={`${num(o.credits.total)} (${num(o.credits.theory)}+${num(o.credits.practical)})`} />
          <Mini label="Contact hours" value={num(o.credits.contact_hours)} />
          <Mini label="Total marks" value={num(o.marks.total)} />
          <p className="col-span-3 text-[11px] text-ink-3">
            {o.program.short_name} · {o.semester.semester_name} · <span className="capitalize">{o.course_type}</span>
            {o.elective_group_id ? ` · ${o.elective_group_id}` : ""} · <span className="font-mono">{o.provenance.document_id} p.{o.provenance.page}</span>
          </p>
        </div>
      ))}
      {c.offerings.length === 0 && c.catalog_listings.map((l) => (
        <p key={l.academic_year + l.catalog_program_code} className="rounded-xl border border-line bg-panel-2 p-3 text-xs text-ink-2">
          Listed in the official employability course list for {l.academic_year} (programme code {l.catalog_program_code}); not part of the 2021–22 syllabus.
        </p>
      ))}
      {c.synthetic_description && (
        <Section icon={<BookOpen size={13} />} title="Description"><p className="text-xs leading-relaxed text-ink-2">{c.synthetic_description}</p><div className="mt-1.5"><TrustBadge type="synthetic" compact /></div></Section>
      )}
      {c.taught_by.length > 0 && (
        <Section icon={<Users size={13} />} title="Taught by">
          {c.taught_by.map((t) => (
            <p key={t.faculty.faculty_id + t.semester_id} className="flex items-center justify-between text-xs text-ink-2">
              <span>{t.faculty.name} <span className="text-ink-4">· {t.role}</span></span><TrustBadge type={t.provenance.source_type} compact />
            </p>
          ))}
        </Section>
      )}
      {c.labs.length > 0 && (
        <Section icon={<FlaskConical size={13} />} title="Practicals in">
          {c.labs.map((l) => <p key={l.lab_id} className="flex items-center justify-between text-xs text-ink-2">{l.lab_name}<TrustBadge type={l.source_type} compact /></p>)}
        </Section>
      )}
      {c.prerequisites.length > 0 && (
        <Section icon={<GraduationCap size={13} />} title="Prerequisites">
          {c.prerequisites.map((p) => (
            <p key={p.course.course_id} className="flex items-center justify-between text-xs text-ink-2">
              <span><span className="font-mono text-[11px] text-blue-700 dark:text-blue-400">{p.course.course_code}</span> {p.course.course_name}</span>
              <TrustBadge type={p.provenance.source_type} compact />
            </p>
          ))}
        </Section>
      )}
      {!c.taught_by.length && !c.labs.length && !c.prerequisites.length && !c.synthetic_description && (
        <EmptyState icon={<BookOpen size={18} />} title="Nothing more recorded">The sources only give this course’s scheme.</EmptyState>
      )}
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return <div><p className="text-[10px] uppercase tracking-wider text-ink-4">{label}</p><p className="mt-0.5 text-sm font-bold text-ink">{value}</p></div>;
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-ink-4">{icon}{title}</p>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}
