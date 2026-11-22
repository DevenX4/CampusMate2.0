import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useInView, useReducedMotion } from 'framer-motion';
import { Brain, Check, Combine, MessageSquare, Pause, Play, Search, SendHorizontal, ShieldCheck, Sparkles } from 'lucide-react';
import trace from '../data/pipeline_trace.json';
import CampusBot from './brand/CampusBot';
import { CampyNote, MaskedText } from './landing/motion';
import { EASE } from './landing/utils';

const STEPS = [
    {
        title: 'Ask',
        icon: MessageSquare,
        tech: 'React chat',
        text: 'A student types a question in English, Hindi or Hinglish, the way they would ask a senior.',
    },
    {
        title: 'Understand',
        icon: Brain,
        tech: 'Qwen on Groq',
        text: 'Qwen works out the meaning, rewrites it for search, and decides whether to answer, ask a follow-up or refuse.',
    },
    {
        title: 'Search',
        icon: Search,
        tech: 'BM25 + ChromaDB',
        text: 'BM25 catches exact terms like course codes. ChromaDB with BGE-small embeddings catches the meaning.',
    },
    {
        title: 'Fuse',
        icon: Combine,
        tech: 'Reciprocal Rank Fusion',
        text: 'Both result lists merge into one ranking, so a record that both methods trust rises to the top.',
    },
    {
        title: 'Write',
        icon: Sparkles,
        tech: 'gpt-oss-120b on Groq',
        text: 'OpenAI gpt-oss-120b, hosted on Groq, writes the answer from those records and cites each fact.',
    },
    {
        title: 'Check',
        icon: ShieldCheck,
        tech: 'Grounding check',
        text: 'Numbers and codes in the answer are checked against the records before the sources are shown.',
    },
];

const LAST = STEPS.length - 1;
const RESUME_AFTER_MS = 8000;

function stepDuration(step, run) {
    if (step === 4) return Math.min(6000, Math.max(3200, 1500 + run.answer.split(' ').length * 85));
    return [2600, 2800, 3200, 2800, 0, 3000][step];
}

function useCounter(total, durationMs, instant) {
    const [count, setCount] = useState(instant ? total : 0);

    useEffect(() => {
        if (instant) {
            setCount(total);
            return undefined;
        }
        let frame;
        const started = performance.now();
        const tick = (now) => {
            const next = Math.min(total, Math.ceil(((now - started) / durationMs) * total));
            setCount(next);
            if (next < total) frame = requestAnimationFrame(tick);
        };
        frame = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(frame);
    }, [total, durationMs, instant]);

    return count;
}

const rise = (index, instant, x = 0) => ({
    initial: instant ? false : { opacity: 0, y: x ? 0 : 12, x },
    animate: { opacity: 1, y: 0, x: 0 },
    transition: { duration: 0.5, delay: instant ? 0 : 0.12 + index * 0.16, ease: EASE },
});

function AskStage({ run, instant }) {
    const count = useCounter(run.question.length, 1500, instant);
    const typed = count === run.question.length;
    return (
        <div className="flex h-full flex-col justify-center gap-4">
            <AnimatePresence>
                {typed && (
                    <motion.div {...rise(0, instant)} className="ml-auto max-w-[88%] rounded-2xl rounded-br-md bg-surface-hover px-4 py-2.5 text-sm text-text-primary">
                        {run.question}
                    </motion.div>
                )}
            </AnimatePresence>
            <div className={`flex items-center gap-3 rounded-2xl border bg-page px-4 py-3 transition-colors duration-300 ${typed ? 'border-border-default' : 'border-accent'}`}>
                <span className="min-h-5 min-w-0 flex-1 truncate text-sm text-text-primary">
                    {typed ? <span className="text-text-muted">Sent to the engine</span> : run.question.slice(0, count)}
                    {!typed && <span className="lp-caret" />}
                </span>
                <motion.span
                    animate={typed && !instant ? { x: [0, 7, 0], scale: [1, 1.12, 1] } : {}}
                    transition={{ duration: 0.55 }}
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${typed ? 'bg-accent text-on-accent' : 'bg-surface-hover text-text-muted'}`}
                >
                    <SendHorizontal size={15} />
                </motion.span>
            </div>
        </div>
    );
}

function UnderstandStage({ run, instant }) {
    const rows = [
        ['Intent', run.intent === 'campus' ? 'Campus question' : run.intent],
        ['Language', run.language],
        ['Search for', run.search_query],
    ];
    return (
        <div className="flex h-full flex-col justify-center gap-5">
            <div className="flex items-center gap-3">
                <CampusBot size={46} mood={instant ? 'idle' : 'thinking'} title="Campy thinking" />
                <p className="m-0 min-w-0 truncate text-sm text-text-secondary">{run.question}</p>
            </div>
            <dl className="m-0 grid grid-cols-[minmax(0,1fr)] gap-2">
                {rows.map(([label, value], index) => (
                    <motion.div key={label} {...rise(index, instant)} className="lp-tile flex items-baseline justify-between gap-4 px-4 py-2.5">
                        <dt className="shrink-0 text-xs text-text-muted">{label}</dt>
                        <dd className="m-0 min-w-0 truncate text-right font-mono text-[13px] text-text-primary">{value}</dd>
                    </motion.div>
                ))}
            </dl>
        </div>
    );
}

function SearchLane({ label, items, offset, instant, decimals }) {
    return (
        <div className="relative min-w-0 overflow-hidden rounded-xl border border-border-default bg-page p-3">
            {!instant && <span className="lp-scan" style={{ animationDelay: `${offset * 0.35}s` }} />}
            <p className="m-0 mb-2.5 font-mono text-[11px] text-accent">{label}</p>
            <ol className="m-0 grid grid-cols-[minmax(0,1fr)] list-none gap-1.5 p-0">
                {items.map((item, index) => (
                    <motion.li key={item.title} {...rise(index + offset, instant)} className="flex items-center justify-between gap-2 rounded-lg bg-surface-hover px-2.5 py-2">
                        <span className="min-w-0 truncate text-xs text-text-primary">{item.title.replace(/^(Course|FAQ|Faculty|Policy|Lab|Notice|Calendar): /, '')}</span>
                        <span className="shrink-0 font-mono text-[11px] text-text-muted">{item.score.toFixed(decimals)}</span>
                    </motion.li>
                ))}
            </ol>
        </div>
    );
}

function SearchStage({ run, instant }) {
    return (
        <div className="grid h-full grid-cols-[minmax(0,1fr)] content-center gap-3 sm:grid-cols-2">
            <SearchLane label="BM25 keywords" items={run.bm25} offset={0} instant={instant} decimals={2} />
            <SearchLane label="ChromaDB meaning" items={run.vector} offset={1} instant={instant} decimals={2} />
        </div>
    );
}

function FuseStage({ run, instant }) {
    return (
        <div className="flex h-full flex-col justify-center gap-2">
            <p className="m-0 mb-1 font-mono text-[11px] text-accent">RRF ranking, k = 60</p>
            {run.fused.map((item, index) => (
                <motion.div
                    key={item.title}
                    {...rise(index, instant, index % 2 === 0 ? -34 : 34)}
                    className={`flex items-center gap-3 rounded-xl border px-3.5 py-3 ${index === 0 ? 'border-accent bg-accent-muted' : 'border-border-default bg-page'}`}
                >
                    <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full font-mono text-xs ${index === 0 ? 'bg-accent text-on-accent' : 'bg-surface-hover text-text-secondary'}`}>
                        {index + 1}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm text-text-primary">{item.title}</span>
                    <span className="shrink-0 font-mono text-xs text-text-muted">{item.score.toFixed(4)}</span>
                </motion.div>
            ))}
        </div>
    );
}

function WriteStage({ run, instant }) {
    const words = run.answer.split(' ');
    const count = useCounter(words.length, Math.max(1, stepDuration(4, run) - 850), instant);
    return (
        <div className="flex h-full flex-col justify-center gap-3">
            <div className="flex items-center gap-2.5">
                <CampusBot size={38} mood={count < words.length ? 'writing' : 'happy'} title="Campy writing" />
                <span className="font-mono text-[11px] text-text-muted">{run.provider}</span>
            </div>
            <p className="m-0 text-[15px] leading-relaxed text-text-primary">
                {words.slice(0, count).map((word, index) => {
                    const parts = word.split(/(\[\d+\])/);
                    return (
                        <span key={`${word}-${index}`}>
                            {parts.map((part, partIndex) => (/^\[\d+\]$/.test(part)
                                ? <span key={partIndex} className="lp-cite">{part.slice(1, -1)}</span>
                                : part))}{' '}
                        </span>
                    );
                })}
                {count < words.length && <span className="lp-caret" />}
            </p>
        </div>
    );
}

function CheckStage({ run, instant }) {
    return (
        <div className="flex h-full flex-col justify-center gap-4">
            <div>
                <p className="m-0 mb-2 text-xs text-text-muted">Found in the records</p>
                <div className="flex flex-wrap gap-2">
                    {run.checked_facts.map((fact, index) => (
                        <motion.span key={fact} {...rise(index, instant)} className="inline-flex items-center gap-1.5 rounded-full border border-accent bg-accent-muted px-3 py-1 font-mono text-xs text-text-primary">
                            <Check size={12} className="text-accent" />
                            {fact}
                        </motion.span>
                    ))}
                </div>
            </div>
            <div>
                <p className="m-0 mb-2 text-xs text-text-muted">Sources shown with the answer</p>
                <ul className="m-0 grid grid-cols-[minmax(0,1fr)] list-none gap-1.5 p-0">
                    {run.sources.map((source, index) => (
                        <motion.li key={source} {...rise(index + run.checked_facts.length, instant)} className="lp-tile flex items-center gap-2.5 px-3 py-2 text-xs text-text-primary">
                            <span className="lp-cite m-0">{index + 1}</span>
                            <span className="min-w-0 truncate">{source}</span>
                        </motion.li>
                    ))}
                </ul>
            </div>
        </div>
    );
}

const STAGES = [AskStage, UnderstandStage, SearchStage, FuseStage, WriteStage, CheckStage];

function Rail({ position, onSelect, reduce }) {
    const { step, cycle } = position;
    const travel = { duration: reduce ? 0 : 0.85, ease: [0.65, 0, 0.35, 1] };
    const percent = (step / LAST) * 100;

    return (
        <div className="relative">
            <div className="lp-flow absolute left-[8.33%] right-[8.33%] top-[18px] h-px sm:top-6"><span /></div>
            <div className="absolute left-[8.33%] right-[8.33%] top-[18px] h-px sm:top-6">
                <motion.div
                    key={`fill-${cycle}`}
                    className="h-full origin-left bg-accent"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: step / LAST }}
                    transition={travel}
                />
                {[0, 1, 2].map((trail) => (
                    <motion.div
                        key={`${cycle}-${trail}`}
                        className="absolute inset-x-0 top-0"
                        initial={{ x: '0%' }}
                        animate={{ x: `${percent}%` }}
                        transition={{ ...travel, delay: reduce ? 0 : trail * 0.055 }}
                    >
                        <span
                            className="absolute block rounded-full bg-accent"
                            style={{
                                width: 11 - trail * 3,
                                height: 11 - trail * 3,
                                left: -(11 - trail * 3) / 2,
                                top: -(11 - trail * 3) / 2,
                                opacity: 1 - trail * 0.3,
                                boxShadow: trail === 0 ? '0 0 0 5px var(--accent-muted)' : 'none',
                            }}
                        />
                    </motion.div>
                ))}
            </div>

            <div className="relative grid grid-cols-6">
                {STEPS.map((item, index) => {
                    const Icon = item.icon;
                    const isActive = index === step;
                    const reached = index < step;
                    return (
                        <button
                            key={item.title}
                            type="button"
                            onClick={() => onSelect(index)}
                            aria-label={`Show step: ${item.title}`}
                            aria-pressed={isActive}
                            className="group flex cursor-pointer flex-col items-center gap-2 sm:gap-3"
                        >
                            <span className="relative">
                                {isActive && !reduce && <span key={`${cycle}-${index}`} className="lp-node-ping" />}
                                <motion.span
                                    animate={{ scale: isActive && !reduce ? 1.14 : 1 }}
                                    transition={{ type: 'spring', stiffness: 320, damping: 19 }}
                                    className={`relative flex h-9 w-9 items-center justify-center rounded-full border transition-colors duration-500 sm:h-12 sm:w-12 ${isActive ? 'border-accent bg-accent text-on-accent' : reached ? 'border-accent bg-surface text-accent' : 'border-border-strong bg-surface text-text-muted group-hover:text-text-primary'}`}
                                >
                                    <Icon size={18} />
                                </motion.span>
                            </span>
                            <span className={`hidden text-sm font-medium transition-colors duration-300 sm:block ${isActive ? 'text-text-primary' : 'text-text-muted'}`}>
                                {item.title}
                            </span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

export default function TechPipeline() {
    const containerRef = useRef(null);
    const resumeTimer = useRef(null);
    const inView = useInView(containerRef, { amount: 0.25 });
    const reduce = useReducedMotion();
    const [position, setPosition] = useState({ run: 0, step: 0, cycle: 0 });
    const [playing, setPlaying] = useState(true);
    const [held, setHeld] = useState(false);

    const run = trace[position.run];
    const current = STEPS[position.step];
    const Stage = STAGES[position.step];
    const duration = stepDuration(position.step, run);
    const advancing = inView && playing && !held && !reduce;

    useEffect(() => {
        if (!advancing) return undefined;
        const timer = setTimeout(() => {
            setPosition(({ run: runIndex, step, cycle }) => (step === LAST
                ? { run: (runIndex + 1) % trace.length, step: 0, cycle: cycle + 1 }
                : { run: runIndex, step: step + 1, cycle }));
        }, duration);
        return () => clearTimeout(timer);
    }, [advancing, duration, position]);

    useEffect(() => () => clearTimeout(resumeTimer.current), []);

    const selectStep = (step) => {
        setPosition((value) => ({ ...value, step }));
        setHeld(true);
        clearTimeout(resumeTimer.current);
        resumeTimer.current = setTimeout(() => setHeld(false), RESUME_AFTER_MS);
    };

    const togglePlaying = () => {
        clearTimeout(resumeTimer.current);
        setHeld(false);
        setPlaying((value) => !value);
    };

    return (
        <section id="how-it-works" data-campy="how-it-works" ref={containerRef} className="relative overflow-hidden bg-page py-20 md:py-32">
            <div className="lp-container">
                <CampyNote section="how-it-works" className="mb-6" />
                <MaskedText
                    text="How questions become answers"
                    accent={[3]}
                    className="max-w-3xl text-4xl font-medium leading-[1.05] tracking-[-0.035em] text-text-primary md:text-6xl"
                />
                <p className="mb-0 mt-5 max-w-xl text-base leading-relaxed text-text-secondary">
                    A real question moving through the engine, using the scores and answer recorded from a live run.
                </p>

                <div className="mt-12 md:mt-16">
                    <Rail position={position} onSelect={selectStep} reduce={reduce} />
                </div>

                <div className="lp-card relative mt-8 overflow-hidden md:mt-10">
                    {advancing && (
                        <motion.span
                            key={`${position.cycle}-${position.step}-${position.run}`}
                            className="absolute inset-x-0 top-0 h-0.5 origin-left bg-accent"
                            initial={{ scaleX: 0 }}
                            animate={{ scaleX: 1 }}
                            transition={{ duration: duration / 1000, ease: 'linear' }}
                        />
                    )}

                    <div className="grid lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
                        <div className="flex flex-col justify-between gap-6 border-b border-border-default p-6 md:p-8 lg:border-b-0 lg:border-r">
                            <AnimatePresence mode="wait">
                                <motion.div
                                    key={current.title}
                                    initial={reduce ? false : { opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={reduce ? undefined : { opacity: 0, y: -8 }}
                                    transition={{ duration: 0.26, ease: EASE }}
                                >
                                    <span className="font-mono text-xs text-accent">{current.tech}</span>
                                    <h3 className="m-0 mt-2 text-2xl font-medium tracking-[-0.02em] text-text-primary">{current.title}</h3>
                                    <p className="m-0 mt-3 text-[15px] leading-relaxed text-text-secondary">{current.text}</p>
                                </motion.div>
                            </AnimatePresence>

                            <div className="flex items-center justify-between gap-3">
                                <span className="min-w-0 truncate text-xs text-text-muted">
                                    Example {position.run + 1} of {trace.length}, {run.language}
                                </span>
                                {!reduce && (
                                    <button
                                        type="button"
                                        onClick={togglePlaying}
                                        className="inline-flex h-8 shrink-0 cursor-pointer items-center gap-1.5 rounded-full border border-border-default px-3 text-xs text-text-secondary transition-colors hover:border-border-strong hover:text-text-primary"
                                    >
                                        {playing ? <Pause size={12} /> : <Play size={12} />}
                                        {playing ? 'Pause' : 'Play'}
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="min-h-[300px] p-5 md:p-7">
                            <AnimatePresence mode="wait">
                                <motion.div
                                    key={`${position.run}-${position.step}`}
                                    className="h-full"
                                    initial={reduce ? false : { opacity: 0, scale: 0.985 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={reduce ? undefined : { opacity: 0, scale: 0.985 }}
                                    transition={{ duration: 0.2 }}
                                >
                                    <Stage run={run} instant={Boolean(reduce) || !playing || held} />
                                </motion.div>
                            </AnimatePresence>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
