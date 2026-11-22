import { useEffect, useRef, useState } from 'react';
import {
    AnimatePresence,
    animate,
    motion,
    useMotionValue,
    useMotionValueEvent,
    useReducedMotion,
    useScroll,
    useSpring,
    useTransform,
    useVelocity,
} from 'framer-motion';
import CampusBot from '../brand/CampusBot';
import { CAMPY_PERCHES, CAMPY_REACTIONS, CAMPY_SECTIONS } from './campy';
import { useIsDesktop } from './utils';

const MIN_FLIGHT_PX = 150;
const smoothstep = (t) => t * t * (3 - 2 * t);

/** Builds Campy's flight path: hover beside each section, then arc across to the next one. */
function buildRoute() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const maxScroll = Math.max(1, document.documentElement.scrollHeight - height);
    const container = document.querySelector('.lp-container');
    if (!container) return null;
    const box = container.getBoundingClientRect();
    const size = width >= 1280 ? 76 : 48;
    const sideX = {
        left: Math.max(size / 2 + 6, box.left / 2),
        right: Math.min(width - size / 2 - 6, width - box.left / 2),
        'inner-right': box.right - size * 0.75,
    };

    const sections = [...document.querySelectorAll('[data-campy]')]
        .map((element) => {
            const rect = element.getBoundingClientRect();
            return { key: element.dataset.campy, top: rect.top + window.scrollY, height: rect.height };
        })
        .sort((a, b) => a.top - b.top);

    const points = [];
    const add = (scroll, x, y) => {
        const last = points[points.length - 1];
        if (!last || scroll > last.scroll + 1) points.push({ scroll, x, y });
    };

    sections.forEach((section, index) => {
        const perch = CAMPY_PERCHES[section.key] || CAMPY_PERCHES.home;
        const x = sideX[perch.side];
        const y = perch.y * height;
        const next = sections[index + 1];
        const nextStart = next ? next.top - height * 0.3 : maxScroll;
        const start = index === 0 ? 0 : Math.max(section.top - height * 0.3, (points[points.length - 1]?.scroll || 0) + 2);
        const end = next
            ? Math.max(start + 10, Math.min(section.top + section.height - height * 0.7, nextStart - MIN_FLIGHT_PX))
            : maxScroll;
        const direction = index % 2 === 0 ? 1 : -1;

        add(start, x, y);
        // A slow drift while hovering keeps Campy alive during long pinned sections.
        add((start + end) / 2, x - (perch.side === 'right' ? 10 : -10), y + direction * height * 0.045);
        add(end, x, y);

        if (next) {
            const nextPerch = CAMPY_PERCHES[next.key] || CAMPY_PERCHES.home;
            const nextX = sideX[nextPerch.side];
            const nextY = nextPerch.y * height;
            const arcTop = Math.max(height * 0.1, Math.min(y, nextY) - height * 0.14);
            add((end + Math.max(end + 20, next.top - height * 0.3)) / 2, (x + nextX) / 2, arcTop);
        }
    });
    return points;
}

function pointAt(route, scroll) {
    if (scroll <= route[0].scroll) return route[0];
    const lastPoint = route[route.length - 1];
    if (scroll >= lastPoint.scroll) return lastPoint;
    let low = 0;
    let high = route.length - 1;
    while (high - low > 1) {
        const middle = (low + high) >> 1;
        if (route[middle].scroll <= scroll) low = middle;
        else high = middle;
    }
    const from = route[low];
    const to = route[high];
    const t = smoothstep((scroll - from.scroll) / (to.scroll - from.scroll));
    return { x: from.x + (to.x - from.x) * t, y: from.y + (to.y - from.y) * t };
}

/** Campy flies around the page with the scroll position and hovers in clear space. */
function FlyingBot() {
    const reduce = useReducedMotion();
    const wide = useIsDesktop('(min-width: 1280px)');
    const { scrollY } = useScroll();
    const routeRef = useRef(null);

    const targetX = useMotionValue(typeof window === 'undefined' ? 0 : window.innerWidth - 70);
    const targetY = useMotionValue(typeof window === 'undefined' ? 0 : window.innerHeight * 0.24);
    const flightSpring = { stiffness: 58, damping: 15, mass: 0.85 };
    const springX = useSpring(targetX, flightSpring);
    const springY = useSpring(targetY, flightSpring);
    const x = reduce ? targetX : springX;
    const y = reduce ? targetY : springY;

    const velocityX = useVelocity(springX);
    const velocityY = useVelocity(springY);
    const bankTarget = useTransform(velocityX, [-1100, 0, 1100], [-26, 0, 26]);
    const bank = useSpring(bankTarget, { stiffness: 120, damping: 16 });
    const speed = useTransform([velocityX, velocityY], ([vx, vy]) => Math.min(1, Math.hypot(vx, vy) / 620));
    const flameOpacity = useTransform(speed, [0.04, 0.5], [0.25, 1]);
    const flameScale = useTransform(speed, [0, 1], [0.55, 1.5]);
    const bubbleOpacity = useTransform(speed, [0.12, 0.34], [1, 0]);
    const spin = useMotionValue(0);
    const rotate = useTransform([bank, spin], ([tilt, extra]) => tilt + extra);

    const [section, setSection] = useState('home');
    const [reaction, setReaction] = useState(null);
    const reactionTimer = useRef(null);
    const reactionIndex = useRef(0);

    const moveTo = (scroll) => {
        if (!routeRef.current?.length) return;
        const point = pointAt(routeRef.current, scroll);
        targetX.set(point.x);
        targetY.set(point.y);
    };

    useMotionValueEvent(scrollY, 'change', moveTo);

    useEffect(() => {
        let frame;
        const measure = () => {
            cancelAnimationFrame(frame);
            frame = requestAnimationFrame(() => {
                routeRef.current = buildRoute();
                moveTo(window.scrollY);
            });
        };
        measure();
        const observer = new ResizeObserver(measure);
        observer.observe(document.body);
        window.addEventListener('resize', measure);
        return () => {
            cancelAnimationFrame(frame);
            observer.disconnect();
            window.removeEventListener('resize', measure);
        };
        // moveTo only writes to stable motion values.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        const targets = document.querySelectorAll('[data-campy]');
        const observer = new IntersectionObserver(
            (entries) => {
                const entering = entries.find((entry) => entry.isIntersecting);
                if (entering) setSection(entering.target.dataset.campy);
            },
            { rootMargin: '-45% 0px -50% 0px' },
        );
        targets.forEach((target) => observer.observe(target));
        return () => observer.disconnect();
    }, []);

    useEffect(() => () => clearTimeout(reactionTimer.current), []);

    const onPoke = () => {
        const line = CAMPY_REACTIONS[reactionIndex.current % CAMPY_REACTIONS.length];
        reactionIndex.current += 1;
        setReaction(line);
        clearTimeout(reactionTimer.current);
        reactionTimer.current = setTimeout(() => setReaction(null), 1900);
        if (!reduce) {
            animate(spin, [0, 360], { duration: 0.8, ease: [0.45, 0, 0.2, 1], onComplete: () => spin.set(0) });
        }
    };

    const config = CAMPY_SECTIONS[section] || CAMPY_SECTIONS.home;
    const mood = reaction ? 'happy' : config.mood;
    const line = reaction || config.line;
    const botSize = wide ? 76 : 48;

    return (
        <motion.div aria-hidden="true" className="pointer-events-none fixed left-0 top-0 z-40" style={{ x, y, width: 0, height: 0 }}>
            <div className="absolute" style={{ left: -botSize / 2, top: -botSize / 2, width: botSize }}>
                <div className={reduce ? '' : 'lp-campy-drift'}>
                    <div className={reduce ? '' : 'lp-campy-float'}>
                        <motion.button
                            type="button"
                            tabIndex={-1}
                            onClick={onPoke}
                            className="pointer-events-auto relative block cursor-pointer"
                            style={{ width: botSize, rotate: reduce ? 0 : rotate }}
                            whileHover={reduce ? undefined : { scale: 1.1, transition: { type: 'spring', stiffness: 320, damping: 12 } }}
                            whileTap={reduce ? undefined : { scale: 0.9 }}
                        >
                            {!reduce && (
                                <motion.span
                                    className="absolute left-1/2 top-[88%] flex -translate-x-1/2 gap-[18%]"
                                    style={{ opacity: flameOpacity, scaleY: flameScale, transformOrigin: 'top', width: '46%', justifyContent: 'center' }}
                                >
                                    <span className="lp-campy-flame" />
                                    <span className="lp-campy-flame" style={{ animationDelay: '0.09s' }} />
                                </motion.span>
                            )}
                            <CampusBot size={botSize} mood={mood} title="Campy" className="relative mx-auto" />
                        </motion.button>
                    </div>
                </div>

                <motion.div
                    className="absolute left-1/2 hidden w-[122px] -translate-x-1/2 xl:block"
                    style={{ top: botSize + 14, opacity: reduce ? 1 : bubbleOpacity }}
                >
                    <AnimatePresence mode="wait">
                        <motion.p
                            key={line}
                            initial={reduce ? false : { opacity: 0, y: -6, scale: 0.92 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={reduce ? undefined : { opacity: 0, y: 4, scale: 0.96 }}
                            transition={{ duration: 0.26, ease: 'easeOut' }}
                            className="m-0 rounded-xl border border-border-strong bg-elevated px-2.5 py-1.5 text-center text-[11.5px] font-medium leading-snug text-text-primary shadow-lg"
                        >
                            {line}
                        </motion.p>
                    </AnimatePresence>
                </motion.div>
            </div>
        </motion.div>
    );
}

export default function ScrollBot() {
    const isDesktop = useIsDesktop();
    return isDesktop ? <FlyingBot /> : null;
}
