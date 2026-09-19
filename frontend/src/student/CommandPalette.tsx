import { BookOpen, CornerDownLeft, GraduationCap, Search, Sparkles, UserRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";

import { api } from "../api/client";
import { Kbd } from "../components/ui";
import { useWorkspace } from "./workspace";

interface Item {
  key: string;
  label: string;
  hint: string;
  Icon: typeof Search;
  run: () => void;
}

const PAGES = [
  { to: "/curriculum", label: "Curriculum & Syllabi" }, { to: "/calendar", label: "Exam Schedules" },
  { to: "/policies", label: "Academic Ordinances" }, { to: "/faculty", label: "Faculty Directory" },
];

// Ctrl K: find a course, a faculty member or a page, or ask the question directly.
export function CommandPalette({ onClose }: { onClose: () => void }) {
  const { ask } = useWorkspace();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [courses, setCourses] = useState<{ course_id: string; course_code: string; course_name: string }[]>([]);
  const [faculty, setFaculty] = useState<{ faculty_id: string; name: string; designation: string | null }[]>([]);
  const [active, setActive] = useState(0);

  useEffect(() => {
    const text = q.trim();
    if (text.length < 2) { setCourses([]); setFaculty([]); return; }
    const timer = setTimeout(() => {
      api.courses({ q: text, limit: 5 }).then((p) => setCourses(p.items)).catch(() => setCourses([]));
      api.faculty({ q: text, limit: 4 }).then((p) => setFaculty(p.items)).catch(() => setFaculty([]));
    }, 180);
    return () => clearTimeout(timer);
  }, [q]);

  const items = useMemo<Item[]>(() => {
    const go = (to: string) => () => { navigate(to); onClose(); };
    const text = q.trim();
    const list: Item[] = [];
    if (text.length >= 2) {
      list.push({ key: "ask", label: `Ask CampusMate: “${text}”`, hint: "Answer with sources", Icon: Sparkles,
                  run: () => { void ask(text); navigate("/"); onClose(); } });
    }
    list.push(...courses.map((c) => ({ key: c.course_id, label: `${c.course_code} ${c.course_name}`, hint: "Course",
                                       Icon: BookOpen, run: go(`/curriculum?course=${encodeURIComponent(c.course_id)}`) })));
    list.push(...faculty.map((f) => ({ key: f.faculty_id, label: f.name, hint: f.designation ?? "Faculty", Icon: UserRound,
                                       run: go(`/faculty?id=${encodeURIComponent(f.faculty_id)}`) })));
    list.push(...PAGES.filter((p) => !text || p.label.toLowerCase().includes(text.toLowerCase()))
      .map((p) => ({ key: p.to, label: p.label, hint: "Page", Icon: GraduationCap, run: go(p.to) })));
    return list;
  }, [q, courses, faculty, ask, navigate, onClose]);

  useEffect(() => setActive(0), [items.length]);

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === "ArrowDown") { event.preventDefault(); setActive((a) => Math.min(a + 1, items.length - 1)); }
    else if (event.key === "ArrowUp") { event.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (event.key === "Enter") { event.preventDefault(); items[active]?.run(); }
    else if (event.key === "Escape") onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/40 p-4 pt-[12vh] backdrop-blur-sm" onMouseDown={onClose}>
      <div role="dialog" aria-label="Omni-Search" onMouseDown={(e) => e.stopPropagation()}
           className="w-full max-w-xl animate-fade-up overflow-hidden rounded-2xl border border-line bg-panel shadow-2xl">
        <div className="flex items-center gap-3 border-b border-line-2 px-4 py-3">
          <Search size={17} className="text-ink-4" />
          <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKeyDown}
                 placeholder="Search courses, faculty and pages, or type a question…" aria-label="Search"
                 className="flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-4" />
          <Kbd>Esc</Kbd>
        </div>
        <ul className="max-h-80 overflow-y-auto p-2" role="listbox">
          {items.map((item, i) => (
            <li key={item.key} role="option" aria-selected={i === active}>
              <button type="button" onMouseEnter={() => setActive(i)} onClick={item.run}
                      className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition ${i === active ? "bg-panel-3" : ""}`}>
                <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-lg ${item.key === "ask" ? "bg-blue-600 text-white" : "bg-panel-3 text-ink-3"}`}>
                  <item.Icon size={14} />
                </span>
                <span className="min-w-0 flex-1 truncate text-sm text-ink">{item.label}</span>
                <span className="shrink-0 text-[11px] text-ink-4">{item.hint}</span>
                {i === active && <CornerDownLeft size={13} className="shrink-0 text-ink-4" />}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
