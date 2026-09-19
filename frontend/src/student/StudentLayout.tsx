import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { Outlet } from "react-router";

import { CommandPalette } from "./CommandPalette";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { WorkspaceProvider } from "./workspace";

// The student workspace from the Stitch design: header, navigation on the left, the page in the
// middle (the assistant adds its sources panel on the right).
export function StudentLayout() {
  const [searching, setSearching] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {  // Ctrl K / Cmd K: Omni-Search
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setSearching(true); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <WorkspaceProvider>
      <div className="campus-backdrop min-h-screen">
        <div className="mx-auto flex h-screen max-w-[1780px] flex-col gap-3 overflow-hidden p-2.5 sm:p-3.5 lg:p-4">
          <Header onSearch={() => setSearching(true)} onMenu={() => setMenuOpen(true)} />
          <div className="relative grid min-h-0 flex-1 grid-cols-12 gap-3">
            <aside aria-label="Navigation"
                   className="hidden overflow-y-auto rounded-2xl border border-line bg-panel p-3.5 shadow-glass lg:col-span-3 lg:block xl:col-span-2">
              <Sidebar />
            </aside>
            <Outlet />
          </div>
        </div>
        {menuOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm lg:hidden" onClick={() => setMenuOpen(false)}>
            <aside className="h-full w-72 animate-fade-up overflow-y-auto border-r border-line bg-panel p-3.5" onClick={(e) => e.stopPropagation()}>
              <button type="button" onClick={() => setMenuOpen(false)} aria-label="Close navigation"
                      className="mb-3 ml-auto grid h-8 w-8 place-items-center rounded-lg text-ink-3 hover:bg-panel-3"><X size={16} /></button>
              <Sidebar onNavigate={() => setMenuOpen(false)} />
            </aside>
          </div>
        )}
        {searching && <CommandPalette onClose={() => setSearching(false)} />}
      </div>
    </WorkspaceProvider>
  );
}

// The frame of the non-chat student pages (Curriculum, Faculty, ...): the wide centre card.
export function PageCard({ eyebrow, title, subtitle, actions, children }: {
  eyebrow: string; title: string; subtitle: string; actions?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <main className="col-span-12 flex min-h-0 flex-col overflow-hidden rounded-2xl border border-line bg-panel shadow-glass lg:col-span-9 xl:col-span-10">
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="flex flex-col gap-3 border-b border-line pb-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">{eyebrow}</span>
            <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-ink">{title}</h1>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-ink-3 sm:text-sm">{subtitle}</p>
          </div>
          {actions}
        </div>
        <div className="pt-5">{children}</div>
      </div>
    </main>
  );
}
