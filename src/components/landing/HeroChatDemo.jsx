import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion, useInView, useMotionValue, useReducedMotion, useSpring, useTransform } from 'framer-motion';
import { ArrowUp, FileText } from 'lucide-react';
import CampusBot from '../brand/CampusBot';
import { EASE } from './utils';

// Course facts are from the official syllabus records. Refusal and follow-up lines are the assistant's own wording.
const SCRIPTS = [
    {
        tab: 'Credits',
        question: 'What are the credits for 2CEIT601?',
        stages: ['understand', 'search', 'read', 'write'],
        answer: 'Theory of Computation (2CEIT601) carries **4 credits**: 3 theory and 1 practical, with 5 contact hours and 150 total marks. [1]',
        source: { title: '2CEIT601, Theory of Computation', detail: 'B.Tech IT syllabus, Semester VI, page 15' },
    },
    {
        tab: 'Hinglish',
        question: '2CEIT503 ke kitne credits hain?',
        stages: ['understand', 'search', 'read', 'write'],
        answer: 'Computer Networks (2CEIT503) ke **5 credits** hain: 4 theory aur 1 practical. Total marks 150 hain. [1]',
        source: { title: '2CEIT503, Computer Networks', detail: 'B.Tech IT syllabus, Semester V, page 14' },
    },
    {
        tab: 'Follow-up',
        question: 'Who is the HOD?',
        stages: ['understand'],
        answer: "Our college has several departments. Which department's HOD are you looking for?",
        options: ['Information Technology', 'Computer Engineering', 'Mechanical Engineering', 'Civil Engineering'],
    },
    {
        tab: 'Off-topic',
        question: 'Who won the cricket world cup?',
        stages: ['understand'],
        answer: "I'm CampusMate, an assistant built for campus questions, so I can't help with that one. Ask me about courses, faculty, exams, attendance, labs or notices and I'll gladly help.",
    },
];

const STAGES = {
    understand: { label: 'Understanding your question', mood: 'thinking' },
    search: { label: 'Searching campus records', mood: 'searching' },
    read: { label: 'Reading the matching records', mood: 'reading' },
    write: { label: 'Writing the answer', mood: 'writing' },
};

function tokenize(text) {
    let bold = false;
    return text.split(' ').map((raw) => {
        const marks = (raw.match(/\*\*/g) || []).length;
        const isBold = bold || raw.startsWith('**');
        if (marks % 2 === 1) bold = !bold;
        return { text: raw.replace(/\*\*/g, ''), bold: isBold };
    });
}

function Token({ token }) {
    if (/^\[\d+\]$/.test(token.text)) return <span className="lp-cite">{token.text.slice(1, -1)}</span>;
    return token.bold ? <strong className="font-semibold text-text-primary">{token.text}</strong> : token.text;
}

const EMPTY = { typed: 0, sent: false, stage: null, words: 0, done: false };

export default function HeroChatDemo() {
    const rootRef = useRef(null);
    const inView = useInView(rootRef, { amount: 0.25 });
    const reduce = useReducedMotion();
    const [index, setIndex] = useState(0);
    const [run, setRun] = useState(0);
    const [view, setView] = useState(EMPTY);

    const script = SCRIPTS[index];
    const tokens = useMemo(() => tokenize(script.answer), [script]);

    useEffect(() => {
        if (reduce) {
            setView({ typed: script.question.length, sent: true, stage: null, words: tokens.length, done: true });
            return undefined;
        }
        if (!inView) return undefined;

        let cancelled = false;
        const timers = [];
        const wait = (ms) => new Promise((resolve) => { timers.push(setTimeout(resolve, ms)); });

        const play = async () => {
            setView(EMPTY);
            await wait(420);
            for (let typed = 1; typed <= script.question.length; typed += 1) {
                if (cancelled) return;
                setView((current) => ({ ...current, typed }));
                await wait(30);
            }
            await wait(300);
            if (cancelled) return;
            setView((current) => ({ ...current, sent: true }));
            await wait(320);
            for (const stage of script.stages) {
                if (cancelled) return;
                setView((current) => ({ ...current, stage }));
                await wait(640);
            }
            if (cancelled) return;
            setView((current) => ({ ...current, stage: null }));
            for (let words = 1; words <= tokens.length; words += 1) {
                if (cancelled) return;
                setView((current) => ({ ...current, words }));
                await wait(44);
            }
            if (cancelled) return;
            setView((current) => ({ ...current, done: true }));
            await wait(4200);
            if (!cancelled) setIndex((current) => (current + 1) % SCRIPTS.length);
        };
        play();

        return () => {
            cancelled = true;
            timers.forEach(clearTimeout);
        };
    }, [index, run, inView, reduce, script, tokens]);

    // Gentle pointer tilt gives the panel physical depth.
    const pointerX = useMotionValue(0);
    const pointerY = useMotionValue(0);
    const rotateY = useSpring(useTransform(pointerX, [-0.5, 0.5], [-4.5, 4.5]), { stiffness: 120, damping: 18 });
    const rotateX = useSpring(useTransform(pointerY, [-0.5, 0.5], [3.5, -3.5]), { stiffness: 120, damping: 18 });

    const onPointerMove = (event) => {
        if (reduce || event.pointerType !== 'mouse') return;
        const rect = event.currentTarget.getBoundingClientRect();
        pointerX.set((event.clientX - rect.left) / rect.width - 0.5);
        pointerY.set((event.clientY - rect.top) / rect.height - 0.5);
    };
    const onPointerLeave = () => {
        pointerX.set(0);
        pointerY.set(0);
    };

    const selectScript = (next) => {
        setIndex(next);
        setRun((current) => current + 1);
    };

    const botMood = view.stage ? STAGES[view.stage].mood : view.done && !script.options ? 'happy' : view.done ? 'confused' : 'idle';
    const draft = view.sent ? '' : script.question.slice(0, view.typed);

    return (
        <div ref={rootRef} style={{ perspective: 1100 }} onPointerMove={onPointerMove} onPointerLeave={onPointerLeave}>
            <motion.div
                className="lp-card flex h-[452px] w-full flex-col overflow-hidden lg:h-[min(480px,calc(100dvh-150px))]"
                style={reduce ? undefined : { rotateX, rotateY, transformStyle: 'preserve-3d' }}
            >
                <div className="flex items-center gap-2.5 border-b border-border-default px-4 py-3">
                    <CampusBot size={30} mood={botMood} title="Campy" />
                    <span className="text-sm font-semibold text-text-primary">CampusMate</span>
                    <span className="ml-auto text-xs text-text-muted">Example conversation</span>
                </div>

                <div className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-hidden px-4 py-4" aria-live="off">
                    <AnimatePresence mode="wait">
                        {view.sent && (
                            <motion.div
                                key={`${index}-${run}`}
                                className="flex flex-col gap-3.5"
                                initial={reduce ? false : { opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={reduce ? undefined : { opacity: 0, y: -8 }}
                                transition={{ duration: 0.25 }}
                            >
                                <motion.p
                                    initial={reduce ? false : { opacity: 0, y: 12, scale: 0.97 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    transition={{ duration: 0.45, ease: EASE }}
                                    className="ml-auto max-w-[86%] rounded-2xl rounded-br-sm bg-structural px-3.5 py-2 text-sm text-on-structural"
                                >
                                    {script.question}
                                </motion.p>

                                {view.stage && (
                                    <div className="flex items-center gap-2 text-[13px] text-text-muted">
                                        <span className="h-1.5 w-1.5 rounded-full bg-accent motion-safe:animate-pulse" />
                                        <AnimatePresence mode="wait">
                                            <motion.span
                                                key={view.stage}
                                                initial={{ opacity: 0, y: 5 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                exit={{ opacity: 0, y: -5 }}
                                                transition={{ duration: 0.18 }}
                                            >
                                                {STAGES[view.stage].label}
                                            </motion.span>
                                        </AnimatePresence>
                                    </div>
                                )}

                                {view.words > 0 && (
                                    <p className="max-w-[94%] text-[14.5px] leading-relaxed text-text-secondary">
                                        {tokens.slice(0, view.words).map((token, tokenIndex) => (
                                            <span key={`${token.text}-${tokenIndex}`}>
                                                <Token token={token} />{' '}
                                            </span>
                                        ))}
                                    </p>
                                )}

                                {view.done && script.source && (
                                    <motion.div
                                        initial={reduce ? false : { opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.5, ease: EASE }}
                                        className="lp-tile flex items-center gap-2.5 px-3 py-2.5"
                                    >
                                        <span className="lp-cite">1</span>
                                        <FileText size={15} className="shrink-0 text-accent" />
                                        <span className="min-w-0">
                                            <span className="block truncate text-[13px] font-medium text-text-primary">{script.source.title}</span>
                                            <span className="block truncate text-xs text-text-muted">{script.source.detail}</span>
                                        </span>
                                    </motion.div>
                                )}

                                {view.done && script.options && (
                                    <motion.div
                                        className="flex flex-wrap gap-1.5"
                                        initial="hidden"
                                        animate="show"
                                        variants={{ show: { transition: { staggerChildren: reduce ? 0 : 0.07 } } }}
                                    >
                                        {script.options.map((option) => (
                                            <motion.span
                                                key={option}
                                                className="lp-chip"
                                                variants={{ hidden: reduce ? {} : { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }}
                                            >
                                                {option}
                                            </motion.span>
                                        ))}
                                    </motion.div>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                <div className="border-t border-border-default px-3 py-3">
                    <div className="flex h-11 items-center gap-2 rounded-full border border-border-strong bg-page pl-4 pr-1.5">
                        <span className="min-w-0 flex-1 truncate text-sm text-text-primary">
                            {draft || <span className="text-text-muted">Ask about your campus</span>}
                            {draft && !reduce && <span className="animate-cursor-blink">|</span>}
                        </span>
                        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-colors duration-200 ${draft ? 'bg-accent text-on-accent' : 'bg-surface-hover text-text-muted'}`}>
                            <ArrowUp size={15} />
                        </span>
                    </div>
                    <div className="mt-2.5 flex gap-1 overflow-x-auto" role="tablist" aria-label="Example questions">
                        {SCRIPTS.map((item, itemIndex) => (
                            <button
                                key={item.tab}
                                type="button"
                                role="tab"
                                aria-selected={itemIndex === index}
                                onClick={() => selectScript(itemIndex)}
                                className={`shrink-0 cursor-pointer rounded-full px-2.5 py-1 text-xs font-medium transition-colors duration-200 ${itemIndex === index ? 'bg-accent-muted text-accent' : 'text-text-muted hover:text-text-primary'}`}
                            >
                                {item.tab}
                            </button>
                        ))}
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
