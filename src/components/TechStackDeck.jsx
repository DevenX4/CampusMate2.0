import { useRef } from 'react';
import { motion, useReducedMotion, useScroll, useTransform } from 'framer-motion';
import { Brain, Database, Layers, Server, Sparkles } from 'lucide-react';
import { CampyNote, MaskedText, Reveal } from './landing/motion';
import { useIsDesktop } from './landing/utils';

const technologies = [
    {
        title: 'Keyword search',
        tech: 'BM25',
        icon: Database,
        desc: 'Finds exact terms such as course codes, faculty names and policy IDs across every indexed campus record.',
        details: [['k1', '1.2'], ['b', '0.65'], ['Index', 'Inverted']],
        code: `# BM25 term score
idf = math.log(1 + (N - n + 0.5) / (n + 0.5))
norm = k1 * (1 - b + b * length / avgdl)
score += idf * freq * (k1 + 1) / (freq + norm)`,
    },
    {
        title: 'Semantic search',
        tech: 'ChromaDB + BGE-small',
        icon: Brain,
        desc: 'Matches meaning when the words differ. Embeddings are created locally with an ONNX model and stored in ChromaDB.',
        details: [['Dimensions', '384'], ['Distance', 'Cosine'], ['Runs on', 'Local CPU']],
        code: `# Embedding model
model = "BAAI/bge-small-en-v1.5"
metadata = {
    "hnsw:space": "cosine",
    "dimension": 384,
}`,
    },
    {
        title: 'Rank fusion',
        tech: 'Reciprocal Rank Fusion',
        icon: Layers,
        desc: 'Combines both result lists into one ranking, then follows links from a course to its faculty or lab.',
        details: [['RRF k', '60'], ['Records read', 'Up to 7'], ['History', 'Last 4 messages']],
        code: `# Reciprocal Rank Fusion
for rank, hit in enumerate(hits, 1):
    fused[hit["id"]] += 1.0 / (60 + rank)

ranked = sorted(fused.items(), key=lambda x: -x[1])`,
    },
    {
        title: 'Answer generation',
        tech: 'Groq: gpt-oss-120b + Qwen',
        icon: Sparkles,
        desc: 'Groq hosts OpenAI gpt-oss-120b to write answers and Qwen to understand questions. If Groq is unreachable, a local answer is built from the records.',
        details: [['Answers', 'gpt-oss-120b'], ['Understanding', 'Qwen'], ['Fallback', 'Local']],
        code: `# Models served by Groq
GROQ_URL = "https://api.groq.com/openai/v1/"
ANSWER_MODEL = "openai/gpt-oss-120b"
PLANNER_MODEL = "qwen/qwen3.8-27b"`,
    },
    {
        title: 'Application services',
        tech: 'FastAPI + Express + React',
        icon: Server,
        desc: 'FastAPI serves the answer engine and campus data. Express handles student and admin sessions. React runs the interface.',
        details: [['Campus data', 'PostgreSQL'], ['Sessions', 'JWT cookies'], ['Admin login', 'TOTP 2FA']],
        code: `// Express proxy to the answer engine
const reply = await axios.post(
  \`\${AI_WORKFLOW_URL}/api/v1/chat/hybrid\`,
  { question, conversation_id, history },
);`,
    },
];

const LAST = technologies.length - 1;

function trackGlow(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty('--x', `${event.clientX - rect.left}px`);
    event.currentTarget.style.setProperty('--y', `${event.clientY - rect.top}px`);
}

const glowStyle = {
    backgroundImage: 'radial-gradient(circle 280px at var(--x, -300px) var(--y, -300px), var(--accent-muted), transparent 70%)',
};

function CardBody({ tech, compact = false }) {
    const Icon = tech.icon;
    return (
        <div className={`flex h-full gap-6 ${compact ? 'flex-col' : ''}`}>
            <div className="flex min-w-0 flex-1 flex-col">
                <div className="flex items-center gap-3">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent-muted text-accent">
                        <Icon size={21} />
                    </span>
                    <div className="min-w-0">
                        <p className="m-0 text-xs text-text-muted">{tech.title}</p>
                        <h3 className="m-0 mt-0.5 text-lg font-semibold leading-tight tracking-[-0.02em] text-text-primary xl:text-xl">{tech.tech}</h3>
                    </div>
                </div>
                <p className="mt-4 text-sm leading-relaxed text-text-secondary">{tech.desc}</p>
                <dl className="m-0 mt-auto grid grid-cols-3 gap-2 pt-4">
                    {tech.details.map(([label, value]) => (
                        <div key={label} className="lp-tile min-w-0 px-2.5 py-2">
                            <dt className="truncate text-[11px] text-text-muted">{label}</dt>
                            <dd className="m-0 mt-0.5 truncate text-[12.5px] font-medium text-text-primary" title={value}>{value}</dd>
                        </div>
                    ))}
                </dl>
            </div>
            <pre className={`lp-tile m-0 overflow-hidden whitespace-pre-wrap break-words p-4 font-mono text-[11px] leading-relaxed text-text-secondary ${compact ? '' : 'w-[42%] shrink-0'}`}>
                <code>{tech.code}</code>
            </pre>
        </div>
    );
}

// Each card rests for the first third of its scroll range so it can be read before the next arrives.
function steppedPosition(value) {
    const raw = Math.min(Math.max(value, 0), 1) * LAST;
    const whole = Math.floor(raw);
    const eased = Math.min(Math.max((raw - whole - 0.34) / 0.66, 0), 1);
    return whole + eased * eased * (3 - 2 * eased);
}

function DeckCard({ tech, index, progress }) {
    const position = useTransform(progress, (value) => steppedPosition(value) - index);
    // A new card rises from below, then earlier cards fan out to the left inside the content column.
    const x = useTransform(position, (t) => (t < 0 ? '0%' : `${-Math.min(t, LAST) * 3.9}%`));
    const y = useTransform(position, (t) => (t < 0 ? `${Math.min(-t, 1) * 125}%` : `${-Math.min(t, LAST) * 1.5}%`));
    const scale = useTransform(position, (t) => (t < 0 ? 1 : 1 - Math.min(t, LAST) * 0.036));
    const rotate = useTransform(position, (t) => (t < 0 ? Math.min(-t, 1) * 3.5 : -Math.min(t, LAST) * 0.75));
    const visibility = useTransform(position, (t) => (t <= -1 ? 'hidden' : 'visible'));
    const shade = useTransform(position, (t) => (t <= 0 ? 0 : Math.min(t * 0.3, 0.72)));

    return (
        <motion.article
            onMouseMove={trackGlow}
            className="lp-card absolute inset-y-0 right-0 w-[86%] origin-left overflow-hidden p-6"
            style={{ x, y, scale, rotate, visibility, zIndex: index, ...glowStyle, backgroundColor: 'var(--bg-surface)' }}
        >
            <CardBody tech={tech} />
            <motion.div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-page" style={{ opacity: shade }} />
        </motion.article>
    );
}

function ReducedList() {
    return (
        <div className="grid gap-5 lg:grid-cols-2">
            {technologies.map((tech) => (
                <article key={tech.title} className="lp-card p-5"><CardBody tech={tech} compact /></article>
            ))}
        </div>
    );
}

function PinnedDeck() {
    const containerRef = useRef(null);
    const { scrollYProgress } = useScroll({ target: containerRef, offset: ['start start', 'end end'] });
    const progress = useTransform(scrollYProgress, [0.06, 0.94], [0, 1]);

    return (
        <section ref={containerRef} id="tech-stack" data-campy="tech-stack" className="relative h-[420vh] bg-page">
            <div className="sticky top-0 flex h-[100dvh] flex-col justify-center overflow-hidden pt-16">
                <div className="lp-container">
                    <MaskedText
                        text="The stack behind every answer"
                        className="max-w-3xl text-4xl font-medium leading-[1.05] tracking-[-0.035em] text-text-primary xl:text-[3.4rem]"
                    />
                    <div className="relative mt-9 h-[min(370px,calc(100dvh-290px))]">
                        {technologies.map((tech, index) => (
                            <DeckCard key={tech.title} tech={tech} index={index} progress={progress} />
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
}

function CarouselDeck() {
    return (
        <section id="tech-stack" data-campy="tech-stack" className="bg-page py-16">
            <div className="lp-container">
                <CampyNote section="tech-stack" className="mb-6" />
                <MaskedText
                    text="The stack behind every answer"
                    className="text-4xl font-medium leading-[1.05] tracking-[-0.035em] text-text-primary"
                />
                <Reveal className="mt-8 -mx-5 flex snap-x snap-mandatory gap-3 overflow-x-auto px-5 pb-4 md:mx-0 md:px-0">
                    {technologies.map((tech) => (
                        <article key={tech.title} className="lp-card w-[86%] max-w-[420px] shrink-0 snap-center p-5">
                            <CardBody tech={tech} compact />
                        </article>
                    ))}
                </Reveal>
            </div>
        </section>
    );
}

export default function TechStackDeck() {
    const isDesktop = useIsDesktop();
    const reduce = useReducedMotion();

    if (reduce) {
        return (
            <section id="tech-stack" data-campy="tech-stack" className="bg-page py-20">
                <div className="lp-container">
                    <MaskedText text="The stack behind every answer" className="mb-10 text-4xl font-medium tracking-[-0.035em] text-text-primary md:text-5xl" />
                    <ReducedList />
                </div>
            </section>
        );
    }

    return isDesktop ? <PinnedDeck /> : <CarouselDeck />;
}
