import { useEffect, useRef } from 'react';
import {
    animate,
    motion,
    useInView,
    useMotionValue,
    useReducedMotion,
    useScroll,
    useSpring,
    useTransform,
} from 'framer-motion';
import CampusBot from '../brand/CampusBot';
import { CAMPY_SECTIONS } from './campy';
import { EASE } from './utils';

export function Reveal({ as = 'div', delay = 0, y = 22, className = '', children, ...rest }) {
    const reduce = useReducedMotion();
    const Component = motion[as];
    return (
        <Component
            className={className}
            initial={reduce ? false : { opacity: 0, y }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.8, delay, ease: EASE }}
            {...rest}
        >
            {children}
        </Component>
    );
}

/** Headline whose words rise out of a mask when it enters the viewport. */
export function MaskedText({ as: Tag = 'h2', text, accent = [], className = '', delay = 0 }) {
    const reduce = useReducedMotion();
    const words = text.split(' ');
    const wordClass = (index) => (accent.includes(index) ? 'text-accent' : '');

    if (reduce) {
        return (
            <Tag className={className}>
                {words.map((word, index) => (
                    <span key={`${word}-${index}`} className={wordClass(index)}>{word} </span>
                ))}
            </Tag>
        );
    }

    return (
        <Tag className={className} aria-label={text}>
            <motion.span
                aria-hidden="true"
                className="block"
                initial="hidden"
                whileInView="show"
                viewport={{ once: true, amount: 0.4 }}
                variants={{ show: { transition: { staggerChildren: 0.055, delayChildren: delay } } }}
            >
                {words.map((word, index) => (
                    <span key={`${word}-${index}`}>
                        <span className="lp-mask-word">
                            <motion.span
                                className={`inline-block ${wordClass(index)}`}
                                variants={{
                                    hidden: { y: '115%', rotate: 3 },
                                    show: { y: 0, rotate: 0, transition: { duration: 0.85, ease: EASE } },
                                }}
                            >
                                {word}
                            </motion.span>
                        </span>{' '}
                    </span>
                ))}
            </motion.span>
        </Tag>
    );
}

function ScrubWord({ progress, range, children }) {
    const opacity = useTransform(progress, range, [0.16, 1]);
    return <motion.span style={{ opacity }}>{children} </motion.span>;
}

/** A sentence that lights up word by word as it is scrolled through. */
export function ScrubWords({ text, className = '' }) {
    const ref = useRef(null);
    const reduce = useReducedMotion();
    const { scrollYProgress } = useScroll({ target: ref, offset: ['start 0.86', 'end 0.5'] });
    const words = text.split(' ');

    if (reduce) return <p className={className}>{text}</p>;

    return (
        <p ref={ref} className={className} aria-label={text}>
            <span aria-hidden="true">
                {words.map((word, index) => (
                    <ScrubWord
                        key={`${word}-${index}`}
                        progress={scrollYProgress}
                        range={[index / words.length, (index + 1.6) / words.length]}
                    >
                        {word}
                    </ScrubWord>
                ))}
            </span>
        </p>
    );
}

/** Moves its children at a different speed from the page to create depth. */
export function Parallax({ from = 40, to = -40, className = '', children }) {
    const ref = useRef(null);
    const reduce = useReducedMotion();
    const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] });
    const y = useTransform(scrollYProgress, [0, 1], [from, to]);
    return (
        <motion.div ref={ref} className={className} style={reduce ? undefined : { y }}>
            {children}
        </motion.div>
    );
}

/** Pulls a control toward a mouse pointer. Touch input is ignored. */
export function Magnetic({ strength = 0.26, className = '', children }) {
    const reduce = useReducedMotion();
    const x = useMotionValue(0);
    const y = useMotionValue(0);
    const springX = useSpring(x, { stiffness: 240, damping: 18, mass: 0.4 });
    const springY = useSpring(y, { stiffness: 240, damping: 18, mass: 0.4 });

    const onPointerMove = (event) => {
        if (reduce || event.pointerType !== 'mouse') return;
        const rect = event.currentTarget.getBoundingClientRect();
        x.set((event.clientX - rect.left - rect.width / 2) * strength);
        y.set((event.clientY - rect.top - rect.height / 2) * strength);
    };
    const onPointerLeave = () => {
        x.set(0);
        y.set(0);
    };

    return (
        <motion.div
            className={`inline-block ${className}`}
            style={{ x: springX, y: springY }}
            onPointerMove={onPointerMove}
            onPointerLeave={onPointerLeave}
        >
            {children}
        </motion.div>
    );
}

const decimalsOf = (value) => (String(value).split('.')[1] || '').length;

/** Counts up to the exact value and always finishes on it. */
export function CountUp({ value, suffix = '', duration = 1.7 }) {
    const ref = useRef(null);
    const inView = useInView(ref, { once: true, amount: 0.6 });
    const reduce = useReducedMotion();
    const exact = `${value}${suffix}`;

    useEffect(() => {
        const element = ref.current;
        if (!inView || !element) return undefined;
        if (reduce) {
            element.textContent = exact;
            return undefined;
        }
        const decimals = decimalsOf(value);
        const controls = animate(0, value, {
            duration,
            ease: EASE,
            onUpdate: (latest) => {
                element.textContent = `${latest.toFixed(decimals)}${suffix}`;
            },
            onComplete: () => {
                element.textContent = exact;
            },
        });
        return () => controls.stop();
    }, [inView, reduce, value, suffix, duration, exact]);

    return <span ref={ref} aria-label={exact}>{reduce ? exact : `0${suffix}`}</span>;
}

/** Circular gauge that draws to a percentage when it enters the viewport. */
export function Ring({ value, size = 120, stroke = 8, className = '', children }) {
    const reduce = useReducedMotion();
    const radius = (size - stroke) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - Math.min(value, 100) / 100);
    const center = size / 2;

    return (
        <div className={`relative shrink-0 ${className}`} style={{ width: size, height: size }}>
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
                <circle cx={center} cy={center} r={radius} fill="none" stroke="var(--border)" strokeWidth={stroke} />
                <motion.circle
                    cx={center}
                    cy={center}
                    r={radius}
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth={stroke}
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    initial={reduce ? { strokeDashoffset: offset } : { strokeDashoffset: circumference }}
                    whileInView={{ strokeDashoffset: offset }}
                    viewport={{ once: true, amount: 0.5 }}
                    transition={{ duration: 1.7, ease: EASE }}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">{children}</div>
        </div>
    );
}

/** Below the desktop breakpoint the hanging bot is hidden, so Campy speaks inline instead. */
export function CampyNote({ section, className = '' }) {
    const ref = useRef(null);
    const inView = useInView(ref, { amount: 0.4 });
    const config = CAMPY_SECTIONS[section];

    return (
        <div ref={ref} className={`flex items-center gap-2.5 lg:hidden ${className}`}>
            <div className="h-10 w-10 shrink-0">
                {inView && <CampusBot size={40} mood={config.mood} title="Campy" />}
            </div>
            <p className="rounded-2xl rounded-bl-sm border border-border-default bg-elevated px-3 py-1.5 text-xs text-text-secondary">
                {config.line}
            </p>
        </div>
    );
}
