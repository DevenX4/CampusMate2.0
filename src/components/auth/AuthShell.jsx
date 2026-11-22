import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useMotionValue, useReducedMotion, useSpring, useTransform } from 'framer-motion';
import { AlertTriangle, ArrowRight, CheckCircle2, Eye, EyeOff, Loader2, Moon, ShieldAlert, Sun } from 'lucide-react';
import CampusLogo from '../brand/CampusLogo';
import AuthCampy from './AuthCampy';
import { fieldLine, useAuthLive } from './useAuthLive';
import './auth.css';

const SUBJECTS = [
    { label: 'DBMS', left: '7%', top: '20%', depth: 16 },
    { label: 'AI', right: '10%', top: '16%', depth: 24 },
    { label: 'Networks', left: '5%', top: '47%', depth: 28 },
    { label: 'OS', right: '7%', top: '43%', depth: 14 },
    { label: 'Cloud', left: '12%', top: '68%', depth: 20 },
    { label: 'TOC', right: '12%', top: '66%', depth: 30 },
];
const POKE_LINES = ['Hey, that tickles!', 'Ready when you are.', 'Boop!', 'Let us get you in.'];
const BURST = Array.from({ length: 16 }, (_, index) => {
    const angle = (index / 16) * Math.PI * 2;
    const distance = 92 + (index % 3) * 26;
    return { x: Math.cos(angle) * distance, y: Math.sin(angle) * distance, delay: (index % 4) * 18, wide: index % 2 === 0 };
});

function SubjectChip({ subject, lit, lookX, lookY, index }) {
    const x = useTransform(lookX, (value) => value * subject.depth);
    const y = useTransform(lookY, (value) => value * subject.depth * 0.7);
    const { left, right, top } = subject;
    return (
        <motion.span className="auth-orbit-chip" data-lit={lit} style={{ left, right, top, x, y }}>
            <span style={{ animationDelay: `${index * -0.9}s` }}>{subject.label}</span>
        </motion.span>
    );
}

export default function AuthShell({ campy, headline, subline, theme, toggleTheme, wide = false, children }) {
    const reduceMotion = useReducedMotion();
    const asideRef = useRef(null);
    const stageRef = useRef(null);
    const mainRef = useRef(null);
    const { live, keystroke, rail } = useAuthLive(mainRef);

    const pointerX = useMotionValue(0);
    const pointerY = useMotionValue(0);
    const pointerSpring = { stiffness: 120, damping: 17, mass: 0.5 };
    const lookX = useSpring(pointerX, pointerSpring);
    const lookY = useSpring(pointerY, pointerSpring);
    const glowX = useTransform(lookX, (value) => value * 150);
    const glowY = useTransform(lookY, (value) => value * 130);

    const [poke, setPoke] = useState(null);
    const [celebrating, setCelebrating] = useState(false);
    const [burstRun, setBurstRun] = useState(0);
    const pokeIndex = useRef(0);
    const pokeTimer = useRef(null);
    const wasComplete = useRef(false);
    const complete = live.total > 0 && live.filled === live.total;

    useEffect(() => {
        if (reduceMotion) return undefined;
        const onMove = (event) => {
            const box = stageRef.current?.getBoundingClientRect();
            if (!box) return;
            const reach = Math.max(window.innerWidth, 900) * 0.42;
            pointerX.set(Math.max(-1, Math.min(1, (event.clientX - (box.left + box.width / 2)) / reach)));
            pointerY.set(Math.max(-1, Math.min(1, (event.clientY - (box.top + box.height / 2)) / reach)));
        };
        const onLeave = () => {
            pointerX.set(0);
            pointerY.set(0);
        };
        window.addEventListener('pointermove', onMove, { passive: true });
        document.documentElement.addEventListener('pointerleave', onLeave);
        return () => {
            window.removeEventListener('pointermove', onMove);
            document.documentElement.removeEventListener('pointerleave', onLeave);
        };
    }, [pointerX, pointerY, reduceMotion]);

    useEffect(() => {
        if (complete === wasComplete.current) return undefined;
        wasComplete.current = complete;
        if (!complete) return undefined;
        setBurstRun((run) => run + 1);
        setCelebrating(true);
        const timer = setTimeout(() => setCelebrating(false), 2200);
        return () => clearTimeout(timer);
    }, [complete]);

    useEffect(() => () => clearTimeout(pokeTimer.current), []);

    const onPoke = () => {
        setPoke(POKE_LINES[pokeIndex.current % POKE_LINES.length]);
        pokeIndex.current += 1;
        clearTimeout(pokeTimer.current);
        pokeTimer.current = setTimeout(() => setPoke(null), 1700);
    };

    // Loading, errors and the visible-password pose always come from the form's real state.
    const formIsBusy = ['thinking', 'confused', 'away'].includes(campy.state);
    const cheerful = !formIsBusy && campy.state !== 'hiding' && (Boolean(poke) || celebrating);
    const displayState = cheerful ? 'happy' : campy.state;
    let speech = campy.speech;
    if (!formIsBusy) {
        speech = poke || (celebrating ? 'All set. Press the button!' : fieldLine(live)) || campy.speech;
    }
    const progress = live.total > 0 ? live.filled / live.total : 0;
    const litChips = Math.round(progress * SUBJECTS.length);

    const themeButton = toggleTheme ? (
        <button
            type="button"
            onClick={toggleTheme}
            className="auth-icon-btn auth-theme"
            aria-label={theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'}
            title={theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'}
        >
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
        </button>
    ) : null;

    return (
        <div className="auth-shell font-sans">
            <aside ref={asideRef} className="auth-aside">
                <div className="auth-live-bg" aria-hidden="true">
                    <motion.span className="auth-glow" style={reduceMotion ? undefined : { x: glowX, y: glowY }} />
                    {SUBJECTS.map((subject, index) => (
                        <SubjectChip key={subject.label} subject={subject} index={index} lit={index < litChips} lookX={lookX} lookY={lookY} />
                    ))}
                </div>

                <div className="auth-brandrow contents md:flex">
                    <div className="auth-brand"><CampusLogo size="sm" showTag={false} /></div>
                    {themeButton}
                </div>

                <div className="auth-center contents md:flex">
                    <div className="auth-speech-slot" aria-live="polite">
                        <AnimatePresence mode="wait" initial={false}>
                            <motion.span
                                key={speech}
                                className="auth-speech"
                                initial={reduceMotion ? false : { opacity: 0, y: 7, scale: 0.96 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={reduceMotion ? { opacity: 1 } : { opacity: 0, y: -3, scale: 0.98 }}
                                transition={{ duration: reduceMotion ? 0 : 0.16, ease: [0.16, 1, 0.3, 1] }}
                            >
                                {speech}
                            </motion.span>
                        </AnimatePresence>
                    </div>
                    <div ref={stageRef} className="auth-stage">
                        {live.total > 0 && (
                            <svg className="auth-ring" viewBox="0 0 120 120" aria-hidden="true">
                                <circle cx="60" cy="60" r="57" pathLength="1" className="auth-ring-track" />
                                <motion.circle
                                    cx="60" cy="60" r="57" className="auth-ring-fill"
                                    initial={false}
                                    animate={{ pathLength: progress, opacity: progress > 0 ? 1 : 0 }}
                                    transition={{ type: 'spring', stiffness: 90, damping: 18 }}
                                />
                            </svg>
                        )}
                        {!reduceMotion && burstRun > 0 && (
                            <span key={burstRun} className="auth-burst" aria-hidden="true">
                                {BURST.map((piece, index) => (
                                    <i
                                        key={index}
                                        data-wide={piece.wide}
                                        style={{ '--dx': `${piece.x}px`, '--dy': `${piece.y}px`, animationDelay: `${piece.delay}ms` }}
                                    />
                                ))}
                            </span>
                        )}
                        <motion.button
                            type="button"
                            onClick={onPoke}
                            aria-label="Say hi to Campy"
                            className="auth-campy-btn"
                            whileHover={reduceMotion ? undefined : { scale: 1.035 }}
                            whileTap={reduceMotion ? undefined : { scale: 0.94 }}
                            transition={{ type: 'spring', stiffness: 320, damping: 16 }}
                        >
                            <AuthCampy state={displayState} gaze={campy.gaze} lookX={lookX} lookY={lookY} keystroke={keystroke} />
                        </motion.button>
                    </div>
                    {live.total > 0 && (
                        <div className="auth-progress" aria-live="off">
                            <AnimatePresence mode="popLayout" initial={false}>
                                <motion.b
                                    key={live.filled}
                                    initial={reduceMotion ? false : { y: 9, opacity: 0 }}
                                    animate={{ y: 0, opacity: 1 }}
                                    exit={reduceMotion ? undefined : { y: -9, opacity: 0 }}
                                    transition={{ duration: 0.2 }}
                                >
                                    {live.filled}
                                </motion.b>
                            </AnimatePresence>
                            <span>of {live.total} done</span>
                        </div>
                    )}
                </div>

                <div className="auth-pitch">
                    <h2>{headline}</h2>
                    <p>{subline}</p>
                </div>
            </aside>

            <main ref={mainRef} className="auth-main">
                <motion.span
                    className="auth-rail"
                    aria-hidden="true"
                    style={{ top: rail.top, height: rail.height, left: rail.left, opacity: rail.opacity }}
                />
                <div className="auth-column" data-wide={wide}>
                    {children}
                </div>
            </main>
        </div>
    );
}

export function AuthHeading({ title, children }) {
    return (
        <div>
            <h1 className="auth-title">{title}</h1>
            {children && <p className="auth-subtitle">{children}</p>}
        </div>
    );
}

export function AuthField({ id, label, labelNote, aside, error, hint, inputClassName = '', children, ...inputProps }) {
    const errorId = error ? `${id}-error` : undefined;
    return (
        <div className="auth-field">
            <div className="flex items-baseline justify-between gap-3">
                <label htmlFor={id} className="auth-label">
                    {label}{labelNote && <small> {labelNote}</small>}
                </label>
                {aside}
            </div>
            {children || (
                <input
                    id={id}
                    aria-invalid={error ? 'true' : undefined}
                    aria-describedby={errorId}
                    className={`auth-input ${inputClassName}`}
                    {...inputProps}
                />
            )}
            {hint && <p className="auth-hint">{hint}</p>}
            {error && <p id={errorId} className="auth-error" role="alert">{error}</p>}
        </div>
    );
}

export function AuthPasswordField({ id, label, aside, error, hint, revealed, onToggle, ...inputProps }) {
    const errorId = error ? `${id}-error` : undefined;
    return (
        <AuthField id={id} label={label} aside={aside} error={error} hint={hint}>
            <div className="auth-input-wrap">
                <input
                    id={id}
                    type={revealed ? 'text' : 'password'}
                    aria-invalid={error ? 'true' : undefined}
                    aria-describedby={errorId}
                    className="auth-input auth-input-secret"
                    {...inputProps}
                />
                <button
                    type="button"
                    onClick={onToggle}
                    className="auth-eye"
                    aria-label={revealed ? 'Hide password' : 'Show password'}
                >
                    {revealed ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
            </div>
        </AuthField>
    );
}

export function AuthSelect({ id, label, error, children, ...selectProps }) {
    const errorId = error ? `${id}-error` : undefined;
    return (
        <AuthField id={id} label={label} error={error}>
            <select
                id={id}
                aria-invalid={error ? 'true' : undefined}
                aria-describedby={errorId}
                className="auth-input"
                {...selectProps}
            >
                {children}
            </select>
        </AuthField>
    );
}

export function AuthSubmit({ loading, disabled, children, className = '', ...props }) {
    return (
        <button type="submit" disabled={disabled} aria-busy={loading || undefined} className={`auth-btn auth-btn-primary ${className}`} {...props}>
            {loading ? <Loader2 size={18} className="auth-spin" aria-label="Working" /> : (
                <>
                    <span>{children}</span>
                    <ArrowRight size={16} className="auth-arrow" />
                </>
            )}
        </button>
    );
}

const ALERT_ICON = { danger: AlertTriangle, warning: ShieldAlert, success: CheckCircle2 };

export function AuthAlert({ tone = 'danger', title, icon, children }) {
    const reduceMotion = useReducedMotion();
    const Icon = icon || ALERT_ICON[tone];
    return (
        <motion.div
            className="auth-alert"
            data-tone={tone}
            role="alert"
            initial={reduceMotion ? false : { opacity: 0, y: -5 }}
            animate={reduceMotion || tone !== 'danger' ? { opacity: 1, y: 0 } : { opacity: 1, y: 0, x: [0, -7, 6, -4, 2, 0] }}
            transition={{ duration: tone === 'danger' ? 0.42 : 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
            <Icon size={15} />
            <div className="min-w-0">
                {title && <strong>{title}</strong>}
                <p>{children}</p>
            </div>
        </motion.div>
    );
}
