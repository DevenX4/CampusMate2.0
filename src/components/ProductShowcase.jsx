import { useRef, useState } from 'react';
import { motion, useMotionValueEvent, useReducedMotion, useScroll, useTransform } from 'framer-motion';
import { CampyNote, MaskedText, Reveal } from './landing/motion';
import { useIsDesktop } from './landing/utils';
import { AdminPanel, CitedPanel, FollowUpPanel, MentorPanel } from './landing/showcasePanels';

const FEATURES = [
    {
        tab: 'Cited answers',
        title: 'Ask anything about campus.',
        body: 'Campus answers point to the record they came from, so you can open it and check.',
        Panel: CitedPanel,
    },
    {
        tab: 'Study mentor',
        title: 'A study mentor for exam week.',
        body: 'Get a plan for the subject, standard textbooks, and links to YouTube lectures and NPTEL courses.',
        Panel: MentorPanel,
    },
    {
        tab: 'Follow-ups',
        title: 'Unclear question? It asks.',
        body: 'Say "Who is the HOD?" and Campy checks which department you mean before answering.',
        Panel: FollowUpPanel,
    },
    {
        tab: 'Admin console',
        title: 'Everything it knows, in one view.',
        body: 'Admins can review every semester, course, faculty record, lab, calendar event and notice.',
        Panel: AdminPanel,
    },
];

const COUNT = FEATURES.length;

function layerRanges(index) {
    const size = 1 / COUNT;
    const start = index * size;
    const end = start + size;
    // The outgoing panel is fully gone before the next one appears, so text never overlaps.
    const fade = 0.045;
    const gap = 0.004;
    if (index === 0) return { input: [0, end - fade, end - gap], opacity: [1, 1, 0], y: [0, 0, -46], scale: [1, 1, 0.965] };
    if (index === COUNT - 1) return { input: [start + gap, start + fade, 1], opacity: [0, 1, 1], y: [46, 0, 0], scale: [0.965, 1, 1] };
    return {
        input: [start + gap, start + fade, end - fade, end - gap],
        opacity: [0, 1, 1, 0],
        y: [46, 0, 0, -46],
        scale: [0.965, 1, 1, 0.965],
    };
}

function Layer({ progress, index, depth = 1, className = '', children }) {
    const reduce = useReducedMotion();
    const ranges = layerRanges(index);
    const opacity = useTransform(progress, ranges.input, ranges.opacity);
    const y = useTransform(progress, ranges.input, ranges.y.map((value) => value * depth));
    const scale = useTransform(progress, ranges.input, ranges.scale);
    const visibility = useTransform(opacity, (value) => (value < 0.01 ? 'hidden' : 'visible'));
    return (
        <motion.div className={`absolute inset-0 ${className}`} style={reduce ? { opacity, visibility } : { opacity, y, scale, visibility }}>
            {children}
        </motion.div>
    );
}

function PinnedShowcase() {
    const containerRef = useRef(null);
    const [activeStep, setActiveStep] = useState(0);
    const { scrollYProgress } = useScroll({ target: containerRef, offset: ['start start', 'end end'] });
    const railScale = useTransform(scrollYProgress, [0, 1], [0.06, 1]);

    useMotionValueEvent(scrollYProgress, 'change', (value) => {
        const next = Math.min(COUNT - 1, Math.floor(value * COUNT));
        setActiveStep((current) => (current === next ? current : next));
    });

    const jumpTo = (index) => {
        const element = containerRef.current;
        if (!element) return;
        const travel = element.offsetHeight - window.innerHeight;
        const top = element.getBoundingClientRect().top + window.scrollY + travel * ((index + 0.5) / COUNT);
        const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        window.scrollTo({ top, behavior: reduce ? 'auto' : 'smooth' });
    };

    return (
        <section ref={containerRef} id="features" data-campy="features" className="relative h-[420vh] bg-page">
            <div className="sticky top-0 flex h-[100dvh] items-center overflow-hidden pt-14">
                <div className="lp-container grid grid-cols-[0.84fr_1.16fr] items-center gap-12 xl:gap-16">
                    <div>
                        <div className="relative h-[212px] xl:h-[236px]">
                            {FEATURES.map((feature, index) => (
                                <Layer key={feature.tab} progress={scrollYProgress} index={index} depth={0.6}>
                                    <h2 className="text-[2.5rem] font-medium leading-[1.05] tracking-[-0.035em] text-text-primary xl:text-[3.2rem]">
                                        {feature.title}
                                    </h2>
                                    <p className="mt-4 max-w-[28rem] text-base leading-relaxed text-text-secondary">{feature.body}</p>
                                </Layer>
                            ))}
                        </div>

                        <div className="relative mt-8 flex flex-col gap-0.5 pl-5">
                            <span className="absolute bottom-1 left-0 top-1 w-px bg-border-default" />
                            <motion.span className="absolute bottom-1 left-0 top-1 w-px origin-top bg-accent" style={{ scaleY: railScale }} />
                            {FEATURES.map((feature, index) => (
                                <button
                                    key={feature.tab}
                                    type="button"
                                    onClick={() => jumpTo(index)}
                                    aria-current={activeStep === index ? 'step' : undefined}
                                    className={`w-fit cursor-pointer py-1 text-sm transition-colors duration-300 ${activeStep === index ? 'font-medium text-text-primary' : 'text-text-muted hover:text-text-secondary'}`}
                                >
                                    {feature.tab}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="relative h-[min(500px,calc(100dvh-170px))]">
                        {FEATURES.map(({ tab, Panel }, index) => (
                            <Layer key={tab} progress={scrollYProgress} index={index}>
                                <Panel active={activeStep === index} />
                            </Layer>
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
}

function StackedShowcase() {
    return (
        <section id="features" data-campy="features" className="bg-page py-16 md:py-24">
            <div className="lp-container flex flex-col gap-16">
                <CampyNote section="features" className="-mb-10" />
                {FEATURES.map(({ tab, title, body, Panel }) => (
                    <div key={tab}>
                        <MaskedText text={title} className="text-[2rem] font-medium leading-[1.08] tracking-[-0.035em] text-text-primary md:text-5xl" />
                        <Reveal as="p" className="mb-6 mt-3 max-w-[34rem] text-base leading-relaxed text-text-secondary">{body}</Reveal>
                        <Reveal><Panel /></Reveal>
                    </div>
                ))}
            </div>
        </section>
    );
}

export default function ProductShowcase() {
    const isDesktop = useIsDesktop();
    const reduce = useReducedMotion();
    return isDesktop && !reduce ? <PinnedShowcase /> : <StackedShowcase />;
}
