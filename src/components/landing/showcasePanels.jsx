import { motion, useReducedMotion } from 'framer-motion';
import { BookOpen, CalendarDays, Check, FileText, FlaskConical, GraduationCap, Layers, Megaphone, PlayCircle, Search, Users } from 'lucide-react';
import CampusBot from '../brand/CampusBot';
import { EASE } from './utils';

/** Reveals children in order when its panel becomes the active one. */
function Stagger({ active, className = '', children }) {
    const reduce = useReducedMotion();
    const controlled = active === undefined ? { whileInView: 'show', viewport: { once: true, amount: 0.25 } } : { animate: active ? 'show' : 'hidden' };
    return (
        <motion.div
            className={className}
            initial={reduce ? false : 'hidden'}
            {...(reduce ? { animate: 'show' } : controlled)}
            variants={{ show: { transition: { staggerChildren: 0.11, delayChildren: 0.08 } } }}
        >
            {children}
        </motion.div>
    );
}

const item = {
    hidden: { opacity: 0, y: 14 },
    show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};

function Item({ className = '', children }) {
    return <motion.div className={className} variants={item}>{children}</motion.div>;
}

function Question({ children }) {
    return (
        <Item className="ml-auto max-w-[88%] rounded-2xl rounded-br-sm bg-structural px-3.5 py-2 text-sm text-on-structural">
            {children}
        </Item>
    );
}

function Shell({ mood, title, children }) {
    return (
        <div className="lp-card flex min-h-[430px] w-full flex-col overflow-hidden lg:h-[min(500px,calc(100dvh-170px))] lg:min-h-0">
            <div className="flex items-center gap-2.5 border-b border-border-default px-4 py-3">
                <CampusBot size={28} mood={mood} title="Campy" />
                <span className="text-sm font-semibold text-text-primary">{title}</span>
            </div>
            {children}
        </div>
    );
}

export function CitedPanel({ active }) {
    return (
        <Shell mood="reading" title="Campus answer">
            <Stagger active={active} className="flex flex-1 flex-col gap-4 p-4 sm:p-5">
                <Question>How many credits is Artificial Intelligence?</Question>
                <Item className="text-[15px] leading-relaxed text-text-secondary">
                    Artificial Intelligence (2CEIT602) is a Semester VI course with{' '}
                    <strong className="font-semibold text-text-primary">4 credits</strong>: 3 theory and 1 practical. <span className="lp-cite">1</span>
                </Item>
                <Item className="lp-tile mt-auto p-4">
                    <div className="flex items-center gap-2">
                        <span className="lp-cite">1</span>
                        <FileText size={15} className="text-accent" />
                        <span className="truncate text-[13px] font-medium text-text-primary">B.Tech IT syllabus, page 15</span>
                    </div>
                    <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5 sm:grid-cols-4">
                        {[['Code', '2CEIT602'], ['Credits', '4'], ['Contact hours', '5'], ['Total marks', '150']].map(([label, value]) => (
                            <div key={label}>
                                <dt className="text-[11px] text-text-muted">{label}</dt>
                                <dd className="m-0 font-mono text-[13px] text-text-primary">{value}</dd>
                            </div>
                        ))}
                    </dl>
                </Item>
            </Stagger>
        </Shell>
    );
}

const PLAN = ['Processes, threads and CPU scheduling', 'Deadlocks and synchronization', 'Memory management and file systems', 'Previous papers and timed revision'];
const BOOKS = ['Operating System Concepts, Silberschatz', 'Modern Operating Systems, Tanenbaum'];
const LINKS = [{ label: 'YouTube lectures', icon: PlayCircle }, { label: 'NPTEL courses', icon: GraduationCap }, { label: 'Previous papers', icon: FileText }];

export function MentorPanel({ active }) {
    return (
        <Shell mood="writing" title="Study mentor">
            <Stagger active={active} className="flex flex-1 flex-col gap-3.5 p-4 sm:p-5">
                <Question>Operating Systems ki taiyari kaise karun?</Question>
                <Item className="text-xs text-text-muted">Your plan for 2CEIT401, 4 credits <span className="lp-cite">1</span></Item>
                <div className="flex flex-col gap-2">
                    {PLAN.map((step) => (
                        <Item key={step} className="flex items-center gap-2.5 text-sm text-text-secondary">
                            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-muted text-accent">
                                <Check size={12} strokeWidth={3} />
                            </span>
                            {step}
                        </Item>
                    ))}
                </div>
                <Item className="lp-tile mt-auto flex flex-col gap-1.5 p-3">
                    {BOOKS.map((book) => (
                        <span key={book} className="flex items-center gap-2 text-[13px] text-text-primary">
                            <BookOpen size={14} className="shrink-0 text-accent" />
                            <span className="truncate">{book}</span>
                        </span>
                    ))}
                </Item>
                <Item className="flex flex-wrap gap-1.5">
                    {LINKS.map(({ label, icon: Icon }) => (
                        <span key={label} className="lp-chip"><Icon size={13} className="text-accent" />{label}</span>
                    ))}
                </Item>
            </Stagger>
        </Shell>
    );
}

const DEPARTMENTS = ['Information Technology', 'Computer Engineering', 'Computer Science and Engineering', 'Electronics and Communication', 'Mechanical Engineering', 'Civil Engineering'];

export function FollowUpPanel({ active }) {
    return (
        <Shell mood="confused" title="Clarifying question">
            <Stagger active={active} className="flex flex-1 flex-col gap-4 p-4 sm:p-5">
                <Question>Who is the HOD?</Question>
                <Item className="text-[15px] leading-relaxed text-text-secondary">
                    Our college has several departments. Which department's HOD are you looking for?
                </Item>
                <Item className="flex flex-wrap gap-1.5">
                    {DEPARTMENTS.map((department, index) => (
                        <span key={department} className={`lp-chip ${index === 0 ? 'border-accent text-accent' : ''}`}>{department}</span>
                    ))}
                </Item>
                <Question>Information Technology</Question>
                <Item className="lp-tile mt-auto p-3.5">
                    <div className="flex items-center gap-2 text-[13px] text-text-secondary">
                        <Search size={14} className="text-accent" />
                        Reading the Information Technology record
                    </div>
                    <div className="mt-3 flex flex-col gap-2 motion-safe:animate-pulse" aria-hidden="true">
                        <span className="h-2 w-[86%] rounded-full bg-border-strong" />
                        <span className="h-2 w-[64%] rounded-full bg-border-strong" />
                    </div>
                </Item>
            </Stagger>
        </Shell>
    );
}

const CONSOLE_TABS = [
    { label: 'Semesters', count: 12, icon: Layers },
    { label: 'Courses', count: 116, icon: BookOpen },
    { label: 'Faculty', count: 20, icon: Users },
    { label: 'Labs', count: 10, icon: FlaskConical },
    { label: 'Calendar', count: 25, icon: CalendarDays },
    { label: 'Notices', count: 20, icon: Megaphone },
];

const COURSE_ROWS = [
    ['2CEIT501', 'Computer Architecture & Organization', '4'],
    ['2CEIT502', 'Software Engineering', '4'],
    ['2CEIT503', 'Computer Networks', '5'],
];

export function AdminPanel({ active }) {
    return (
        <Shell mood="idle" title="Admin knowledge console">
            <Stagger active={active} className="flex flex-1 flex-col gap-3.5 p-4 sm:p-5">
                <div className="grid grid-cols-3 gap-2">
                    {CONSOLE_TABS.map(({ label, count, icon: Icon }, index) => (
                        <Item key={label} className={`rounded-xl border px-2.5 py-2 ${index === 1 ? 'border-accent bg-accent-muted' : 'border-border-default bg-surface-hover'}`}>
                            <Icon size={14} className={index === 1 ? 'text-accent' : 'text-text-muted'} />
                            <div className="mt-1.5 font-mono text-lg font-medium leading-none tabular-nums text-text-primary">{count}</div>
                            <div className="mt-1 truncate text-[11px] text-text-secondary">{label}</div>
                        </Item>
                    ))}
                </div>
                <Item className="lp-tile overflow-hidden">
                    <div className="grid grid-cols-[5.2rem_1fr_3rem] gap-2 border-b border-border-default px-3 py-1.5 text-[11px] text-text-muted">
                        <span>Code</span><span>Semester V course</span><span className="text-right">Credits</span>
                    </div>
                    {COURSE_ROWS.map(([code, name, credits]) => (
                        <div key={code} className="grid grid-cols-[5.2rem_1fr_3rem] gap-2 px-3 py-1.5 text-[13px]">
                            <span className="font-mono text-accent">{code}</span>
                            <span className="truncate text-text-primary">{name}</span>
                            <span className="text-right font-mono text-text-secondary">{credits}</span>
                        </div>
                    ))}
                </Item>
                <Item className="mt-auto text-[11.5px] leading-relaxed text-text-muted">
                    Courses and semesters come from the official GUNI syllabus. Faculty, labs, calendar and notices are sample records for now.
                </Item>
            </Stagger>
        </Shell>
    );
}
