// Small building blocks shared by the student workspace and the admin console.

import { Layers, Loader2, X } from "lucide-react";
import { useEffect, type ReactNode } from "react";

import type { SourceType } from "../api/types";

export function LogoMark({ size = "md" }: { size?: "sm" | "md" }) {
  const box = size === "sm" ? "h-8 w-8 rounded-lg" : "h-9 w-9 rounded-xl";
  return (
    <span className={`${box} grid shrink-0 place-items-center bg-slate-900 text-white shadow-sm ring-1 ring-white/20 dark:bg-slate-800`}>
      <Layers size={16} strokeWidth={2.2} className="text-blue-400" aria-hidden />
    </span>
  );
}

const TRUST: Record<SourceType, { label: string; className: string; dot: string; title: string }> = {
  official: {
    label: "Official", dot: "bg-emerald-500",
    className: "bg-emerald-500/10 text-emerald-700 ring-emerald-500/20 dark:text-emerald-400",
    title: "Directly from an official Ganpat University source",
  },
  derived_official: {
    label: "Derived", dot: "bg-blue-500",
    className: "bg-blue-500/10 text-blue-700 ring-blue-500/20 dark:text-blue-400",
    title: "Computed from official sources (for example a total of official figures)",
  },
  synthetic: {
    label: "Synthetic demo", dot: "bg-amber-500",
    className: "bg-amber-500/10 text-amber-800 ring-amber-500/25 dark:text-amber-400",
    title: "Artificial demo data: not official Ganpat University information",
  },
};

// Every fact shows how far it can be trusted. Synthetic demo data is amber, never green or blue.
export function TrustBadge({ type, compact = false }: { type: SourceType; compact?: boolean }) {
  const t = TRUST[type];
  return (
    <span title={t.title}
          className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 font-semibold ring-1 ring-inset ${compact ? "text-[9.5px]" : "text-[10.5px]"} ${t.className}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${t.dot}`} aria-hidden />
      {t.label}
    </span>
  );
}

export const trustDot = (type: SourceType) => TRUST[type].dot;

export function Spinner({ label, className = "" }: { label?: string; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 text-ink-3 ${className}`}>
      <Loader2 size={15} className="animate-spin" aria-hidden />
      {label && <span className="text-xs">{label}</span>}
    </span>
  );
}

export function EmptyState({ icon, title, children }: { icon: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <span className="grid h-11 w-11 place-items-center rounded-2xl bg-panel-3 text-ink-3">{icon}</span>
      <p className="mt-3 text-sm font-semibold text-ink">{title}</p>
      {children && <div className="mt-1 max-w-sm text-xs leading-relaxed text-ink-3">{children}</div>}
    </div>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return <p role="alert" className="rounded-xl bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-700 dark:text-rose-400">{children}</p>;
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-line bg-panel px-1.5 py-0.5 font-mono text-[10px] text-ink-3 shadow-[0_1px_1px_rgba(0,0,0,0.05)]">
      {children}
    </kbd>
  );
}

// A dialog over a dimmed backdrop. Escape and a click outside close it.
export function Modal({ title, subtitle, icon, onClose, children, wide = false }: {
  title: string; subtitle?: string; icon?: ReactNode; onClose: () => void; children: ReactNode; wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} onMouseDown={(e) => e.stopPropagation()}
           className={`w-full ${wide ? "max-w-2xl" : "max-w-lg"} animate-fade-up overflow-hidden rounded-2xl border border-line bg-panel shadow-2xl`}>
        <div className="flex items-center justify-between border-b border-line-2 p-5">
          <div className="flex items-center gap-2.5">
            {icon && <span className="grid h-8 w-8 place-items-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">{icon}</span>}
            <div>
              <h3 className="text-base font-bold text-ink">{title}</h3>
              {subtitle && <p className="text-xs text-ink-3">{subtitle}</p>}
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label="Close"
                  className="grid h-8 w-8 place-items-center rounded-lg text-ink-4 hover:bg-panel-3 hover:text-ink-2">
            <X size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export const fieldClass =
  "w-full rounded-xl border border-line bg-panel px-3 py-2 text-sm text-ink placeholder:text-ink-4 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20";
