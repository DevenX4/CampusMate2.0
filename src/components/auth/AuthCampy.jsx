import { useId } from 'react';
import { motion, useMotionValue, useReducedMotion, useTransform } from 'framer-motion';

const SPRING = { type: 'spring', stiffness: 240, damping: 22 };

const BODY = {
    idle: { y: [0, -1.6, 0], rotate: 0, transition: { duration: 3.6, repeat: Infinity, ease: 'easeInOut' } },
    watching: { y: 1, rotate: 2, transition: SPRING },
    hiding: { y: 2, rotate: 0, transition: SPRING },
    away: { y: 1, rotate: -9, transition: SPRING },
    thinking: { y: [0, -1, 0], rotate: [-2.5, 2.5, -2.5], transition: { duration: 2.2, repeat: Infinity, ease: 'easeInOut' } },
    confused: { y: 0, rotate: 8, transition: { type: 'spring', stiffness: 180, damping: 12 } },
    happy: { y: [0, -6, 0, -3, 0], rotate: [0, -4, 4, 0], transition: { duration: 0.85, ease: 'easeOut' } },
};

function eyeTarget(state, gaze) {
    switch (state) {
        case 'watching': return { x: -3 + gaze * 8, y: 3 };
        case 'hiding': return { x: 0, y: 1 };
        case 'away': return { x: -6, y: -3 };
        case 'thinking': return { x: 2.5, y: -3 };
        case 'confused': return { x: 1.5, y: 0 };
        default: return { x: 0, y: 0 };
    }
}

/**
 * Campy for the auth screens. Same artwork as brand/CampusBot, with a controllable gaze and hands.
 * state: idle | watching | hiding | away | thinking | confused | happy
 * gaze: 0 to 1, how far along the field Campy is reading.
 */
export default function AuthCampy({ state = 'idle', gaze = 0, size = '100%', className = '', lookX, lookY, keystroke }) {
    const reduceMotion = useReducedMotion();
    const id = useId().replace(/:/g, '');
    const hiding = state === 'hiding';
    const lively = state === 'thinking';
    const handTransition = reduceMotion ? { duration: 0 } : SPRING;
    const blink = !reduceMotion && (state === 'idle' || state === 'watching');

    // The pointer steers the head and eyes, except when Campy is deliberately not looking.
    const still = useMotionValue(0);
    const followsPointer = !reduceMotion && !['hiding', 'away'].includes(state);
    const pointerX = followsPointer && lookX ? lookX : still;
    const pointerY = followsPointer && lookY ? lookY : still;
    const eyeX = useTransform(pointerX, (value) => value * 6);
    const eyeY = useTransform(pointerY, (value) => value * 4);
    const headX = useTransform(pointerX, (value) => value * 2.4);
    const headY = useTransform(pointerY, (value) => value * 1.6);
    const headTilt = useTransform(pointerX, (value) => value * 6);
    const capLift = useTransform(keystroke || still, [0, 1], [0, -2.2]);
    const antennaGlow = useTransform(keystroke || still, [0, 1], [1, 1.9]);

    return (
        <svg width={size} height={size} viewBox="0 0 96 96" fill="none" role="img" aria-label="Campy, the CampusMate mascot" className={`block overflow-visible ${className}`}>
            <defs>
                <linearGradient id={`${id}-shell`} x1="20" y1="24" x2="76" y2="84" gradientUnits="userSpaceOnUse">
                    <stop stopColor="var(--bot-shell-light)" />
                    <stop offset="1" stopColor="var(--bot-shell-dark)" />
                </linearGradient>
            </defs>

            <motion.g style={{ x: headX, y: headY, rotate: headTilt, transformBox: 'view-box', transformOrigin: '48px 62px' }}>
            <motion.g animate={reduceMotion ? { y: 0, rotate: state === 'confused' ? 8 : 0 } : (BODY[state] || BODY.idle)}>
                {/* Antenna */}
                <path d="M72 30 L80 17" stroke="var(--bot-line)" strokeWidth="3" strokeLinecap="round" />
                <motion.g style={{ scale: antennaGlow, transformBox: 'view-box', transformOrigin: '81px 15px' }}>
                    <motion.circle
                        cx="81" cy="15" r="4" fill="var(--accent)"
                        animate={reduceMotion ? {} : (lively ? { scale: [1, 1.5, 1], opacity: [1, 0.55, 1] } : { scale: 1, opacity: [1, 0.72, 1] })}
                        transition={{ duration: lively ? 0.75 : 2.6, repeat: Infinity, ease: 'easeInOut' }}
                    />
                </motion.g>

                {/* Side ports */}
                <rect x="9" y="52" width="8" height="17" rx="4" fill="var(--bot-line)" />
                <rect x="79" y="52" width="8" height="17" rx="4" fill="var(--bot-line)" />

                {/* Head and visor */}
                <rect x="15" y="31" width="66" height="56" rx="20" fill={`url(#${id}-shell)`} stroke="var(--bot-line)" strokeWidth="1.5" />
                <rect x="23" y="42" width="50" height="34" rx="14" fill="var(--bot-visor)" />

                {/* Eyes */}
                {state === 'happy' ? (
                    <g stroke="var(--accent)" strokeWidth="4.2" strokeLinecap="round">
                        <path d="M33 60 Q38 52 43 60" />
                        <path d="M53 60 Q58 52 63 60" />
                    </g>
                ) : (
                    <motion.g style={{ x: eyeX, y: eyeY }}>
                        <motion.g animate={eyeTarget(state, gaze)} transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 210, damping: 20 }}>
                            <motion.g
                                animate={hiding ? { scaleY: 0.14 } : blink ? { scaleY: [1, 1, 0.08, 1, 1] } : { scaleY: 1 }}
                                transition={hiding || !blink ? { duration: reduceMotion ? 0 : 0.14 } : { duration: 4.2, times: [0, 0.46, 0.5, 0.54, 1], repeat: Infinity }}
                            >
                                <rect x="33" y={state === 'confused' ? 49 : 51} width="9" height={state === 'confused' ? 15 : 13} rx="4.5" fill="var(--accent)" />
                                <rect x="54" y="51" width="9" height="13" rx="4.5" fill="var(--accent)" />
                            </motion.g>
                        </motion.g>
                    </motion.g>
                )}

                {/* Mouth */}
                {state === 'happy' && <path d="M43 67 Q48 72 53 67" stroke="var(--accent)" strokeWidth="2.6" strokeLinecap="round" />}
                {state === 'confused' && <path d="M43 70 Q47 67 53 70" stroke="var(--accent)" strokeWidth="2.4" strokeLinecap="round" />}

                {/* Graduation cap hops a little with each keystroke */}
                <motion.g style={{ y: capLift }}>
                    <path d="M31 28 V36 C31 40 65 40 65 36 V28" fill="var(--bot-cap-side)" />
                    <path d="M48 7 L80 21 L48 35 L16 21 Z" fill="var(--bot-cap)" stroke="var(--bot-line)" strokeWidth="1.5" strokeLinejoin="round" />
                    <motion.g
                        animate={reduceMotion ? {} : { rotate: lively ? [-14, 16, -14] : [-5, 7, -5] }}
                        transition={{ duration: lively ? 0.9 : 3, repeat: Infinity, ease: 'easeInOut' }}
                        style={{ transformBox: 'view-box', transformOrigin: '48px 21px' }}
                    >
                        <path d="M48 21 L25 28 V42" stroke="var(--accent)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                        <rect x="22" y="41" width="6" height="8" rx="2" fill="var(--accent)" />
                    </motion.g>
                    <circle cx="48" cy="21" r="2.6" fill="var(--accent)" />
                </motion.g>

                {/* Hands rest at the sides and rise to cover the visor during password entry */}
                <motion.g initial={false} animate={hiding ? { x: 25, y: -27 } : { x: 0, y: 0 }} transition={handTransition}>
                    <rect x="3" y="72" width="24" height="20" rx="10" fill={`url(#${id}-shell)`} stroke="var(--bot-line)" strokeWidth="1.5" />
                    <path d="M11 74 V80 M18 74 V80" stroke="var(--bot-line)" strokeWidth="1.4" strokeLinecap="round" />
                </motion.g>
                <motion.g initial={false} animate={hiding ? { x: -24, y: -27 } : { x: 0, y: 0 }} transition={handTransition}>
                    <rect x="69" y="72" width="24" height="20" rx="10" fill={`url(#${id}-shell)`} stroke="var(--bot-line)" strokeWidth="1.5" />
                    <path d="M78 74 V80 M85 74 V80" stroke="var(--bot-line)" strokeWidth="1.4" strokeLinecap="round" />
                </motion.g>

                {state === 'confused' && (
                    <text x="88" y="38" fill="var(--accent)" fontSize="17" fontWeight="700" fontFamily="var(--font-sans)">?</text>
                )}
            </motion.g>
            </motion.g>
        </svg>
    );
}
