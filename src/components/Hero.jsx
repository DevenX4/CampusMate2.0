import { useEffect, useRef, useState } from 'react';
import { motion, useReducedMotion, useScroll, useTransform } from 'framer-motion';
import { ArrowRight, Hand } from 'lucide-react';
import PlayfulHoverParticles from './PlayfulHoverParticles';
import HeroChatDemo from './landing/HeroChatDemo';
import { Magnetic } from './landing/motion';
import { EASE, scrollToSection } from './landing/utils';

const LINE_ONE = 'Welcome to your';
const LINE_TWO = 'CampusMate';
const FULL_TEXT = `${LINE_ONE} ${LINE_TWO}`;

function TypedHeadline() {
    const reduce = useReducedMotion();
    const [count, setCount] = useState(reduce ? FULL_TEXT.length : 0);
    const done = count >= FULL_TEXT.length;

    useEffect(() => {
        if (reduce) {
            setCount(FULL_TEXT.length);
            return undefined;
        }
        if (done) return undefined;
        const timer = setTimeout(() => setCount((value) => value + 1), count === 0 ? 420 : 58);
        return () => clearTimeout(timer);
    }, [count, done, reduce]);

    const first = FULL_TEXT.slice(0, Math.min(count, LINE_ONE.length));
    const second = count > LINE_ONE.length + 1 ? FULL_TEXT.slice(LINE_ONE.length + 1, count) : '';
    const cursor = !done && <span className="animate-cursor-blink font-light">|</span>;

    return (
        <h1 aria-label={FULL_TEXT} className="text-[2.75rem] font-medium leading-[1.04] tracking-[-0.045em] text-text-primary sm:text-6xl lg:text-[3.55rem] xl:text-[4.15rem]">
            <span aria-hidden="true" className="block">
                <span className="relative block">
                    <span className="invisible">{LINE_ONE}</span>
                    <span className="absolute inset-0">{first}{count <= LINE_ONE.length && cursor}</span>
                </span>
                <span className="relative flex items-center gap-3">
                    <span className="relative inline-block pb-1">
                        <span className="invisible font-semibold">{LINE_TWO}</span>
                        <span className="absolute inset-0 whitespace-nowrap font-semibold">
                            <span className="gradient-text animate-moving-gradient pb-1">{second}</span>
                            {count > LINE_ONE.length && cursor}
                        </span>
                    </span>
                    <motion.span
                        className="inline-flex text-accent"
                        initial={reduce ? false : { opacity: 0, scale: 0.4, rotate: -30 }}
                        animate={done ? { opacity: 1, scale: 1, rotate: 0 } : undefined}
                        transition={{ type: 'spring', stiffness: 260, damping: 14 }}
                    >
                        <Hand className={`h-[0.82em] w-[0.82em] ${done ? 'animate-wave-shake' : ''}`} strokeWidth={1.75} />
                    </motion.span>
                </span>
            </span>
        </h1>
    );
}

export default function Hero({ navigate }) {
    const containerRef = useRef(null);
    const glowFrame = useRef(0);
    const reduce = useReducedMotion();
    const { scrollYProgress } = useScroll({ target: containerRef, offset: ['start start', 'end start'] });
    const textY = useTransform(scrollYProgress, [0, 1], [0, -90]);
    const textOpacity = useTransform(scrollYProgress, [0, 0.62], [1, 0]);
    const demoY = useTransform(scrollYProgress, [0, 1], [0, 70]);
    const demoScale = useTransform(scrollYProgress, [0, 1], [1, 0.93]);

    useEffect(() => () => cancelAnimationFrame(glowFrame.current), []);

    // Cursor glow writes CSS variables, so moving the mouse never re-renders React.
    const onMouseMove = (event) => {
        if (reduce) return;
        const { clientX, clientY } = event;
        cancelAnimationFrame(glowFrame.current);
        glowFrame.current = requestAnimationFrame(() => {
            const element = containerRef.current;
            if (!element) return;
            const rect = element.getBoundingClientRect();
            element.style.setProperty('--mouse-x', `${clientX - rect.left}px`);
            element.style.setProperty('--mouse-y', `${clientY - rect.top}px`);
        });
    };

    const reveal = (delay) => ({
        initial: reduce ? false : { opacity: 0, y: 18 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.8, delay, ease: EASE },
    });

    const getStarted = () => {
        if (!navigate) return;
        try {
            const user = JSON.parse(localStorage.getItem('currentUser') || 'null');
            if (user?.role === 'admin') navigate('/dashboard/admin');
            else if (user?.role === 'student') navigate('/dashboard/student');
            else navigate('/login');
        } catch {
            navigate('/login');
        }
    };

    return (
        <section
            id="home"
            data-campy="home"
            ref={containerRef}
            onMouseMove={onMouseMove}
            className="hero-section relative min-h-[100dvh] overflow-hidden"
        >
            <div className="lp-dots" aria-hidden="true" />
            <div className="lp-dots-lit" aria-hidden="true" />
            <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0"
                style={{ background: 'radial-gradient(520px circle at var(--mouse-x, -600px) var(--mouse-y, -600px), var(--hero-glow), transparent 70%)' }}
            />
            <PlayfulHoverParticles containerRef={containerRef} />

            <div className="lp-container relative z-10 grid min-h-[100dvh] items-center gap-10 pb-16 pt-24 lg:grid-cols-[1.04fr_1fr] lg:gap-12 lg:pb-12 lg:pt-20">
                <motion.div style={reduce ? undefined : { y: textY, opacity: textOpacity }}>
                    <motion.p {...reveal(0.05)} className="mb-5 text-sm text-text-secondary">
                        U.V. Patel College of Engineering, Ganpat University
                    </motion.p>

                    <TypedHeadline />

                    <motion.p {...reveal(0.2)} className="mt-5 max-w-[30rem] text-[17px] leading-relaxed text-text-secondary">
                        Ask about courses, faculty, exams and campus rules in English, Hindi or Hinglish, and see the records behind its answers.
                    </motion.p>

                    <motion.div {...reveal(0.32)} className="mt-8 flex flex-col gap-3 sm:flex-row">
                        <Magnetic className="w-full sm:w-auto">
                            <button onClick={getStarted} className="lp-btn lp-btn-primary w-full sm:w-auto">
                                Get started
                                <ArrowRight size={17} className="lp-btn-icon" />
                            </button>
                        </Magnetic>
                        <Magnetic className="w-full sm:w-auto">
                            <button onClick={() => scrollToSection('#how-it-works')} className="lp-btn lp-btn-ghost w-full sm:w-auto">
                                See how it works
                            </button>
                        </Magnetic>
                    </motion.div>
                </motion.div>

                <motion.div
                    style={reduce ? undefined : { y: demoY, scale: demoScale }}
                    initial={reduce ? false : { opacity: 0, x: 34 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 1, delay: 0.25, ease: EASE }}
                >
                    <HeroChatDemo />
                </motion.div>
            </div>
        </section>
    );
}
