import { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import {
    ArrowDown, BookOpen, Boxes, CheckCircle2, ClipboardList, Database, FlaskConical, Gauge, Milestone, Users,
} from 'lucide-react';
import facts from '../../data/project_facts.json';
import { CampyNote, MaskedText, Reveal } from './motion';
import { engineScores } from './engineScores';
import { EASE } from './utils';

const FUNCTIONAL = [
    ['FR-01', 'Student registration and login', 'Institute email, OTP verification and a session cookie.'],
    ['FR-02', 'Admin login', 'Password and authenticator-app 2FA for administrators.'],
    ['FR-03', 'Cited campus answers', 'Answers come from retrieved records and link to each source.'],
    ['FR-04', 'Follow-up questions', 'Asks which department or subject when a question is unclear.'],
    ['FR-05', 'Off-topic refusal', 'Politely declines anything outside campus and academics.'],
    ['FR-06', 'Study mentor', 'Exam plans, standard textbooks, and lecture and notes links.'],
    ['FR-07', 'Three languages', 'Understands and replies in English, Hindi and Hinglish.'],
    ['FR-08', 'Chat workspace', 'History, search, rename, delete, export and live streaming.'],
    ['FR-09', 'Admin data console', 'Browse programmes, semesters, courses, people, labs and notices.'],
    ['FR-10', 'Knowledge upload', 'Admins add PDF documents to the searchable knowledge base.'],
];

const NON_FUNCTIONAL = [
    ['Performance', `Hybrid search has a measured median of ${engineScores?.median_search_ms ?? 49} ms. Answers stream as they are written.`],
    ['Reliability', 'A launcher restarts any crashed service. If Groq is unavailable, a local extractive engine still answers.'],
    ['Accuracy', 'Numbers and codes in each campus answer are checked against the retrieved records.'],
    ['Privacy', 'Search runs locally. Only the question, recent turns and matched records are sent to Groq.'],
    ['Usability', 'Responsive from phone to desktop, with dark and light themes and reduced-motion support.'],
    ['Maintainability', 'Separate React, Express and FastAPI services, with the data kept in versioned JSON files.'],
];

const LAYERS = [
    { name: 'Client', tech: 'React 19, Vite, Tailwind, Framer Motion', items: ['Landing page', 'Student chat', 'Admin console'] },
    { name: 'Gateway', tech: 'Node.js, Express', items: ['Sessions and roles', 'Chat streaming proxy', 'Admin APIs'] },
    { name: 'AI engine', tech: 'Python, FastAPI', items: ['Query understanding', 'Hybrid retrieval', 'Grounded generation'] },
    { name: 'Knowledge', tech: 'ChromaDB, BM25, PostgreSQL, JSON', items: [`${facts.vectors} vectors`, 'Keyword index', `${facts.datasets} datasets`] },
];

const DATA_GROUPS = [
    ['Courses', facts.tables.courses],
    ['Course offerings', facts.tables.course_offerings],
    ['Teaching assignments', facts.tables.teaching_assignments],
    ['FAQ', facts.tables.faq],
    ['Rooms', facts.tables.rooms],
    ['Calendar events', facts.tables.academic_calendar],
    ['Faculty', facts.tables.faculty],
    ['Notices', facts.tables.notices],
    ['Elective groups', facts.tables.elective_groups],
    ['Semesters', facts.tables.semesters],
    ['Policies', facts.tables.policies],
    ['Laboratories', facts.tables.laboratories],
];

function Stat({ value, label }) {
    return (
        <div className="lp-tile px-4 py-3.5">
            <div className="font-mono text-2xl font-medium tracking-tight text-text-primary">{value}</div>
            <div className="mt-1 text-xs leading-snug text-text-secondary">{label}</div>
        </div>
    );
}

function Lead({ children }) {
    return <p className="m-0 max-w-[62ch] text-[15px] leading-relaxed text-text-secondary">{children}</p>;
}

function SubHeading({ children }) {
    return <h4 className="m-0 mb-3 mt-7 text-sm font-medium text-text-primary first:mt-0">{children}</h4>;
}

function Overview() {
    return (
        <>
            <Lead>
                CampusMate is an AI campus assistant for U.V. Patel College of Engineering, Ganpat University. Students ask a question
                in their own words and get an answer built from college records, with the source one click away.
            </Lead>
            <SubHeading>Problem</SubHeading>
            <Lead>Syllabus, faculty, exam dates and rules usually sit across PDFs, notice boards and department offices, so a simple question can take a long time to answer.</Lead>
            <SubHeading>Objectives</SubHeading>
            <ul className="m-0 grid list-none gap-2 p-0 sm:grid-cols-2">
                {['One place for campus questions', 'Answers tied to their source', 'Study support for every subject', 'A clear view of college data for admins'].map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-text-secondary">
                        <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-accent" />
                        {item}
                    </li>
                ))}
            </ul>
        </>
    );
}

function UsersPanel() {
    const roles = [
        ['Student', 'Asks campus questions, gets study plans, opens sources and keeps chat history.'],
        ['Teacher', 'Registers with an employee ID and can use the same campus knowledge.'],
        ['Administrator', 'Manages users and invites, uploads documents and reviews all campus data.'],
    ];
    return (
        <div className="grid gap-3">
            {roles.map(([role, text]) => (
                <div key={role} className="lp-tile px-5 py-4">
                    <h4 className="m-0 text-base font-medium text-text-primary">{role}</h4>
                    <p className="m-0 mt-1 text-sm leading-relaxed text-text-secondary">{text}</p>
                </div>
            ))}
        </div>
    );
}

function Functional() {
    return (
        <dl className="m-0 grid gap-x-6 gap-y-4 sm:grid-cols-2">
            {FUNCTIONAL.map(([id, name, text]) => (
                <div key={id} className="flex gap-3">
                    <span className="mt-0.5 shrink-0 font-mono text-[11px] text-accent">{id}</span>
                    <div>
                        <dt className="text-sm font-medium text-text-primary">{name}</dt>
                        <dd className="m-0 mt-0.5 text-[13px] leading-relaxed text-text-secondary">{text}</dd>
                    </div>
                </div>
            ))}
        </dl>
    );
}

function NonFunctional() {
    return (
        <dl className="m-0 grid gap-3 sm:grid-cols-2">
            {NON_FUNCTIONAL.map(([name, text]) => (
                <div key={name} className="lp-tile px-4 py-3.5">
                    <dt className="text-sm font-medium text-text-primary">{name}</dt>
                    <dd className="m-0 mt-1 text-[13px] leading-relaxed text-text-secondary">{text}</dd>
                </div>
            ))}
        </dl>
    );
}

function Architecture() {
    const reduce = useReducedMotion();
    return (
        <div className="grid gap-1">
            {LAYERS.map((layer, index) => (
                <div key={layer.name}>
                    <motion.div
                        initial={reduce ? false : { opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: index * 0.09, ease: EASE }}
                        className="lp-tile grid gap-2 px-4 py-3 md:grid-cols-[150px_minmax(0,1fr)] md:items-center"
                    >
                        <div>
                            <div className="text-sm font-medium text-text-primary">{layer.name}</div>
                            <div className="text-[11px] leading-snug text-text-muted">{layer.tech}</div>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                            {layer.items.map((item) => (
                                <span key={item} className="rounded-full border border-border-default bg-page px-2.5 py-1 text-xs text-text-secondary">{item}</span>
                            ))}
                        </div>
                    </motion.div>
                    {index < LAYERS.length - 1 && <ArrowDown size={13} className="mx-auto my-0.5 text-accent" aria-hidden="true" />}
                </div>
            ))}
            <p className="m-0 mt-3 text-[13px] leading-relaxed text-text-secondary">
                External service: Groq hosts OpenAI gpt-oss-120b for writing answers and Qwen for understanding questions.
            </p>
        </div>
    );
}

function DataDesign() {
    const types = facts.source_types;
    return (
        <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat value={facts.datasets} label="datasets" />
                <Stat value={facts.structured_records} label="structured records" />
                <Stat value={facts.indexed_records} label="searchable records" />
                <Stat value="384" label="vector dimensions" />
            </div>
            <SubHeading>Main datasets</SubHeading>
            <dl className="m-0 grid grid-cols-2 gap-x-6 gap-y-1.5 md:grid-cols-3">
                {DATA_GROUPS.map(([name, count]) => (
                    <div key={name} className="flex items-baseline justify-between gap-2 text-[13px]">
                        <dt className="min-w-0 truncate text-text-secondary">{name}</dt>
                        <dd className="m-0 font-mono text-text-primary">{count}</dd>
                    </div>
                ))}
            </dl>
            <SubHeading>Where the records come from</SubHeading>
            <p className="m-0 text-[13px] leading-relaxed text-text-secondary">
                {types.official} from official documents, {types.derived_official} derived from them, and {types.synthetic} sample records used for demonstration.
            </p>
        </>
    );
}

function Testing() {
    const scores = engineScores;
    return (
        <>
            {scores && (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                    <Stat value={`${scores.right_record_found_pct}%`} label={`right record found, ${scores.campus_questions} questions`} />
                    <Stat value={`${scores.right_record_top3_pct}%`} label="right record in top 3" />
                    <Stat value={`${scores.campus_questions_accepted_pct}%`} label="campus questions accepted" />
                    <Stat value={`${scores.off_topic_refused_pct}%`} label={`off-topic refused, ${scores.off_topic_questions} questions`} />
                </div>
            )}
            <SubHeading>How it was tested</SubHeading>
            <ul className="m-0 grid list-disc gap-1.5 pl-5 text-sm leading-relaxed text-text-secondary">
                <li>Retrieval and routing were scored on the project's evaluation question set{scores ? ` on ${scores.measured_on}` : ''}.</li>
                <li>198 automated backend tests pass. Another 108 need the original PDFs and were skipped.</li>
                <li>Browser tests cover login, chat, follow-ups, refusals and every admin section.</li>
            </ul>
        </>
    );
}

function Scope() {
    return (
        <div className="grid gap-6 md:grid-cols-2">
            <div>
                <SubHeading>Current constraints</SubHeading>
                <ul className="m-0 grid list-disc gap-2 pl-5 text-sm leading-relaxed text-text-secondary">
                    <li>{facts.source_types.synthetic} of {facts.structured_records} records are sample data and are labelled in the app.</li>
                    <li>The Groq plan allows 8,000 tokens per minute.</li>
                    <li>Accounts stay in memory unless MongoDB is running.</li>
                </ul>
            </div>
            <div>
                <SubHeading>Roadmap</SubHeading>
                <ul className="m-0 grid list-disc gap-2 pl-5 text-sm leading-relaxed text-text-secondary">
                    <li>Replace sample records with verified college data.</li>
                    <li>Add permanent accounts and college single sign-on.</li>
                    <li>Extend coverage to every department.</li>
                </ul>
            </div>
        </div>
    );
}

const CHAPTERS = [
    { title: 'Overview', icon: BookOpen, Panel: Overview },
    { title: 'Users', icon: Users, Panel: UsersPanel },
    { title: 'Functional requirements', icon: ClipboardList, Panel: Functional },
    { title: 'Quality requirements', icon: Gauge, Panel: NonFunctional },
    { title: 'Architecture', icon: Boxes, Panel: Architecture },
    { title: 'Data design', icon: Database, Panel: DataDesign },
    { title: 'Testing and results', icon: FlaskConical, Panel: Testing },
    { title: 'Scope and roadmap', icon: Milestone, Panel: Scope },
];

export default function ProjectBlueprint() {
    const [active, setActive] = useState(0);
    const reduce = useReducedMotion();
    const chapter = CHAPTERS[active];
    const Panel = chapter.Panel;

    return (
        <section id="blueprint" data-campy="blueprint" className="relative bg-page py-20 md:py-32">
            <div className="lp-container">
                <CampyNote section="blueprint" className="mb-6" />
                <MaskedText
                    text="The complete project blueprint"
                    accent={[3]}
                    className="max-w-3xl text-4xl font-medium leading-[1.05] tracking-[-0.035em] text-text-primary md:text-6xl"
                />
                <p className="mb-0 mt-5 max-w-xl text-base leading-relaxed text-text-secondary">
                    Requirements, architecture, data and test results in one place, written like a software requirements specification.
                </p>

                <Reveal className="lp-card mt-12 grid overflow-hidden md:mt-16 lg:grid-cols-[260px_minmax(0,1fr)]">
                    <nav aria-label="Blueprint chapters" className="flex gap-1 overflow-x-auto border-b border-border-default p-2 lg:flex-col lg:overflow-visible lg:border-b-0 lg:border-r lg:p-3">
                        {CHAPTERS.map((item, index) => {
                            const Icon = item.icon;
                            const isActive = index === active;
                            return (
                                <button
                                    key={item.title}
                                    type="button"
                                    onClick={() => setActive(index)}
                                    aria-current={isActive ? 'true' : undefined}
                                    className={`relative flex shrink-0 cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-[13px] transition-colors ${isActive ? 'font-medium text-text-primary' : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary'}`}
                                >
                                    {isActive && (
                                        <motion.span
                                            layoutId={reduce ? undefined : 'blueprint-active'}
                                            className="absolute inset-0 rounded-lg bg-accent-muted"
                                            transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                                        />
                                    )}
                                    <Icon size={15} className={`relative shrink-0 ${isActive ? 'text-accent' : ''}`} />
                                    <span className="relative whitespace-nowrap">{item.title}</span>
                                </button>
                            );
                        })}
                    </nav>

                    <div className="min-h-[430px] p-6 md:p-8">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={chapter.title}
                                initial={reduce ? false : { opacity: 0, y: 12 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={reduce ? undefined : { opacity: 0, y: -8 }}
                                transition={{ duration: 0.24, ease: EASE }}
                            >
                                <h3 className="m-0 mb-5 text-2xl font-medium tracking-[-0.02em] text-text-primary">{chapter.title}</h3>
                                <Panel />
                            </motion.div>
                        </AnimatePresence>
                    </div>
                </Reveal>
            </div>
        </section>
    );
}
