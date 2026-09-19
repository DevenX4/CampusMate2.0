import type { SourceType } from "../api/types";

// Every source says how far it can be trusted. Synthetic demo data is amber, never sapphire,
// so it cannot be mistaken for official GUNI information.
const STYLES: Record<SourceType, { label: string; className: string; title: string }> = {
  official: {
    label: "Official",
    className: "bg-accent-soft text-accent",
    title: "Directly from an official Ganpat University source",
  },
  derived_official: {
    label: "Derived from official",
    className: "border border-accent/30 text-accent",
    title: "Computed from official sources (for example a total of official figures)",
  },
  synthetic: {
    label: "Synthetic demo",
    className: "bg-demo-soft text-demo",
    title: "Artificial demo data: not official Ganpat University information",
  },
};

export function TrustBadge({ type }: { type: SourceType }) {
  const style = STYLES[type];
  return (
    <span title={style.title}
          className={`inline-flex h-5 items-center whitespace-nowrap rounded-full px-2 text-[11px] font-medium tracking-wide ${style.className}`}>
      {style.label}
    </span>
  );
}
