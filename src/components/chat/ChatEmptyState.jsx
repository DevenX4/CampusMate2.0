import React, { useMemo } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowUpRight, BookOpenCheck, CalendarDays, ClipboardCheck, Languages, ListChecks, UserRound } from 'lucide-react';
import CampusBot from '../brand/CampusBot';

const STARTERS = [
  { icon: UserRound, text: 'Who is the HOD?' },
  { icon: BookOpenCheck, text: 'How should I prepare for the Operating Systems exam?' },
  { icon: ClipboardCheck, text: 'What is the attendance rule?' },
  { icon: CalendarDays, text: 'When are the mid semester examinations?' },
  { icon: ListChecks, text: 'Which electives can I choose in Semester 6?' },
  { icon: Languages, text: 'bhai DBMS ka exam hai, kaise padhu?' },
];

function greetingFor(hour) {
  if (hour < 5) return 'Working late';
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function firstName() {
  try {
    const name = JSON.parse(localStorage.getItem('currentUser') || '{}').name || '';
    return name.trim().split(/\s+/)[0] || '';
  } catch {
    return '';
  }
}

export default function ChatEmptyState({ onSelectPrompt }) {
  const reduceMotion = useReducedMotion();
  const heading = useMemo(() => {
    const name = firstName();
    const greeting = greetingFor(new Date().getHours());
    return name ? `${greeting}, ${name}` : greeting;
  }, []);

  const rise = (delay) => (reduceMotion ? {} : {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.45, delay, ease: [0.16, 1, 0.3, 1] },
  });

  return (
    <div className="cm-column flex-1 flex flex-col justify-center py-6 sm:py-10">
      <motion.div {...rise(0)} className="flex items-center gap-4 sm:gap-5">
        <CampusBot size={84} mood="idle" title="Campy, the CampusMate mascot" className="sm:w-[104px] sm:h-[104px]" />
        <div className="min-w-0">
          <h1 className="text-[1.65rem] sm:text-4xl font-semibold tracking-tight leading-[1.12] text-text-primary">
            {heading}
          </h1>
          <p className="mt-1.5 text-sm sm:text-base leading-snug text-text-secondary">
            What do you want to know about campus?
          </p>
        </div>
      </motion.div>

      <div className="mt-7 sm:mt-9 grid grid-cols-1 sm:grid-cols-2 gap-2">
        {STARTERS.map(({ icon: Icon, text }, index) => (
          <motion.button
            key={text}
            type="button"
            {...rise(0.08 + index * 0.04)}
            onClick={() => onSelectPrompt(text)}
            className="group flex items-center gap-3 min-h-[3.25rem] px-3.5 py-2.5 rounded-2xl text-left bg-surface border border-border-default hover:border-border-strong hover:bg-surface-hover transition-colors cursor-pointer"
          >
            <Icon size={16} strokeWidth={1.8} className="shrink-0 text-text-muted group-hover:text-accent transition-colors" />
            <span className="flex-1 min-w-0 text-[13.5px] leading-snug text-text-primary [text-wrap:balance]">{text}</span>
            <ArrowUpRight size={15} className="shrink-0 text-text-muted opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 group-focus-visible:opacity-100 transition-all duration-200" />
          </motion.button>
        ))}
      </div>
    </div>
  );
}
