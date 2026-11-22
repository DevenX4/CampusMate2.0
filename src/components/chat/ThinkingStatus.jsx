import React, { useId, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Check, ChevronDown } from 'lucide-react';
import CampusBot from '../brand/CampusBot';

/** Campy without animation, so long conversations do not run a motion loop per message. */
export function CampyStill({ size = 30, confused = false }) {
  const id = useId().replace(/:/g, '');
  return (
    <svg width={size} height={size} viewBox="0 0 96 96" fill="none" aria-hidden="true" className="shrink-0 overflow-visible">
      <defs>
        <linearGradient id={`${id}-shell`} x1="20" y1="24" x2="76" y2="84" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--bot-shell-light)" />
          <stop offset="1" stopColor="var(--bot-shell-dark)" />
        </linearGradient>
      </defs>
      <g transform={confused ? 'rotate(8 48 62)' : undefined}>
        <path d="M72 30 L80 17" stroke="var(--bot-line)" strokeWidth="3" strokeLinecap="round" />
        <circle cx="81" cy="15" r="4" fill="var(--accent)" />
        <rect x="9" y="52" width="8" height="17" rx="4" fill="var(--bot-line)" />
        <rect x="79" y="52" width="8" height="17" rx="4" fill="var(--bot-line)" />
        <rect x="15" y="31" width="66" height="56" rx="20" fill={`url(#${id}-shell)`} stroke="var(--bot-line)" strokeWidth="1.5" />
        <rect x="23" y="42" width="50" height="34" rx="14" fill="var(--bot-visor)" />
        <rect x="33" y={confused ? 49 : 51} width="9" height={confused ? 15 : 13} rx="4.5" fill="var(--accent)" />
        <rect x="54" y="51" width="9" height="13" rx="4.5" fill="var(--accent)" />
        {confused && <path d="M43 70 Q47 67 53 70" stroke="var(--accent)" strokeWidth="2.4" strokeLinecap="round" />}
        <path d="M31 28 V36 C31 40 65 40 65 36 V28" fill="var(--bot-cap-side)" />
        <path d="M48 7 L80 21 L48 35 L16 21 Z" fill="var(--bot-cap)" stroke="var(--bot-line)" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M48 21 L25 28 V42" stroke="var(--accent)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        <rect x="22" y="41" width="6" height="8" rx="2" fill="var(--accent)" />
        <circle cx="48" cy="21" r="2.6" fill="var(--accent)" />
      </g>
    </svg>
  );
}

const seconds = (ms) => (ms < 100 ? '<0.1s' : `${(ms / 1000).toFixed(1)}s`);

function stepDuration(stage, next, isLive) {
  if (typeof stage.ms === 'number') return stage.ms;
  if (isLive && next) return next.at - stage.at;
  return null;
}

function TrustTag({ tone = 'quiet', title, children }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center h-5 px-2 rounded-full border text-[11px] leading-none whitespace-nowrap ${
        tone === 'warn'
          ? 'border-status-warning/40 text-status-warning'
          : 'border-border-default text-text-muted'
      }`}
    >
      {children}
    </span>
  );
}

function TrustTags({ grounding }) {
  if (!grounding) return null;
  const issues = Array.isArray(grounding.issues) ? grounding.issues.join('. ') : '';
  return (
    <>
      {grounding.mode === 'study' && <TrustTag title="A study plan, so match it with your official syllabus.">Study plan</TrustTag>}
      {grounding.contains_demo_data && <TrustTag title="This answer uses sample records. Confirm details with your department.">Sample data</TrustTag>}
      {grounding.passed === false && (
        <TrustTag tone="warn" title={issues || 'Part of this answer could not be matched to its sources.'}>Check sources</TrustTag>
      )}
    </>
  );
}

export default function ThinkingStatus({ mood, animated, isLive, statusLabel, stages = [], grounding, provider, totalMs }) {
  const [open, setOpen] = useState(false);
  const reduceMotion = useReducedMotion();
  const canExpand = stages.length > 0;
  const showProvider = /^groq/i.test(provider || '');

  return (
    <div>
      <div className="flex items-center gap-2 min-h-8 flex-wrap">
        {animated
          ? <CampusBot size={36} mood={mood} title={`Campy is ${mood}`} />
          : <CampyStill size={36} confused={mood === 'confused'} />}

        {isLive ? (
          <button
            type="button"
            onClick={() => canExpand && setOpen((value) => !value)}
            aria-expanded={canExpand ? open : undefined}
            className={`flex items-center gap-1 min-w-0 text-sm font-medium ${canExpand ? 'cursor-pointer' : 'cursor-default'}`}
          >
            <span role="status" className="cm-shimmer">{statusLabel}</span>
            {canExpand && <ChevronDown size={14} className={`shrink-0 text-text-muted transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />}
          </button>
        ) : (
          <>
            <span className="text-sm font-medium text-text-primary">CampusMate</span>
            {canExpand && (
              <button
                type="button"
                onClick={() => setOpen((value) => !value)}
                aria-expanded={open}
                className="flex items-center gap-0.5 h-6 pl-1.5 pr-1 rounded-lg text-xs text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
              >
                <span>{stages.length} {stages.length === 1 ? 'step' : 'steps'}</span>
                <ChevronDown size={13} className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
              </button>
            )}
            <TrustTags grounding={grounding} />
          </>
        )}
      </div>

      <AnimatePresence initial={false}>
        {open && canExpand && (
          <motion.div
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <ol className="mt-1.5 mb-1 ml-[17px] pl-[22px] border-l border-border-default space-y-1">
              {stages.map((stage, index) => {
                const next = stages[index + 1];
                const running = isLive && !next;
                const duration = stepDuration(stage, next, isLive);
                return (
                  <li key={`${stage.key}-${index}`} className="relative flex items-center gap-2 text-[13px] leading-5 text-text-secondary">
                    <span className="absolute -left-[29px] flex items-center justify-center w-3.5 h-3.5 rounded-full bg-page">
                      {running ? <span className="cm-step-dot" /> : <Check size={12} strokeWidth={2.4} className="text-accent" />}
                    </span>
                    <span className="min-w-0">{stage.label}</span>
                    {duration != null && <span className="ml-auto pl-2 font-mono text-[11px] text-text-muted">{seconds(duration)}</span>}
                  </li>
                );
              })}
              {!isLive && showProvider && (
                <li className="pt-0.5 text-xs text-text-muted">
                  {provider}{typeof totalMs === 'number' ? `, ${seconds(totalMs)} total` : ''}
                </li>
              )}
            </ol>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
