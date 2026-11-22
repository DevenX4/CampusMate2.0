import { useId } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

const EYE_MOTION = {
    idle: { x: 0, y: 0, scaleY: [1, 1, 0.08, 1, 1], transition: { duration: 4.2, times: [0, 0.46, 0.5, 0.54, 1], repeat: Infinity } },
    thinking: { x: [0, 2.4, 2.4, -1, 0], y: [-2, -2.6, -2, -2.6, -2], scaleY: 1, transition: { duration: 2.4, repeat: Infinity, ease: 'easeInOut' } },
    searching: { x: [-4, 4, -4], y: 0, scaleY: 1, transition: { duration: 1.25, repeat: Infinity, ease: 'easeInOut' } },
    reading: { x: [-3, 3, -3], y: [0, 0, 1.6], scaleY: 0.8, transition: { duration: 1.5, repeat: Infinity, ease: 'easeInOut' } },
    writing: { x: 0, y: 1.4, scaleY: [0.72, 0.5, 0.72], transition: { duration: 0.8, repeat: Infinity, ease: 'easeInOut' } },
    confused: { x: 1.5, y: 0, scaleY: 1, transition: { duration: 0.3 } },
    happy: { x: 0, y: 0, scaleY: 1, transition: { duration: 0.2 } },
};

const BODY_MOTION = {
    idle: { y: [0, -1.6, 0], rotate: 0, transition: { duration: 3.6, repeat: Infinity, ease: 'easeInOut' } },
    thinking: { y: [0, -1, 0], rotate: [-2.5, 2.5, -2.5], transition: { duration: 2.6, repeat: Infinity, ease: 'easeInOut' } },
    searching: { y: 0, rotate: [-4, 4, -4], transition: { duration: 1.25, repeat: Infinity, ease: 'easeInOut' } },
    reading: { y: [0, 1, 0], rotate: 2, transition: { duration: 1.5, repeat: Infinity, ease: 'easeInOut' } },
    writing: { y: [0, -1.2, 0], rotate: [-1, 1, -1], transition: { duration: 0.48, repeat: Infinity, ease: 'easeInOut' } },
    confused: { y: 0, rotate: 8, transition: { type: 'spring', stiffness: 180, damping: 12 } },
    happy: { y: [0, -6, 0, -3, 0], rotate: [0, -4, 4, 0], transition: { duration: 0.85, ease: 'easeOut' } },
};

/**
 * Campy, the CampusMate mascot.
 * mood: idle | thinking | searching | reading | writing | confused | happy
 */
export default function CampusBot({ size = 64, mood = 'idle', className = '', title = 'CampusMate bot' }) {
    const reduceMotion = useReducedMotion();
    const id = useId().replace(/:/g, '');
    const active = ['thinking', 'searching', 'reading', 'writing'].includes(mood);
    const eye = EYE_MOTION[mood] || EYE_MOTION.idle;
    const body = BODY_MOTION[mood] || BODY_MOTION.idle;
    const still = (animation) => (reduceMotion ? {} : animation);

    return (
        <svg width={size} height={size} viewBox="0 0 96 96" fill="none" role="img" aria-label={title} className={`shrink-0 overflow-visible ${className}`}>
            <defs>
                <linearGradient id={`${id}-shell`} x1="20" y1="24" x2="76" y2="84" gradientUnits="userSpaceOnUse">
                    <stop stopColor="var(--bot-shell-light)" />
                    <stop offset="1" stopColor="var(--bot-shell-dark)" />
                </linearGradient>
            </defs>

            <motion.g animate={still(body)} style={{ transformOrigin: '48px 62px' }}>
                {/* Antenna */}
                <path d="M72 30 L80 17" stroke="var(--bot-line)" strokeWidth="3" strokeLinecap="round" />
                <motion.circle
                    cx="81" cy="15" r="4" fill="var(--accent)"
                    animate={still(active ? { scale: [1, 1.5, 1], opacity: [1, 0.55, 1] } : { opacity: [1, 0.72, 1] })}
                    transition={{ duration: active ? 0.75 : 2.6, repeat: Infinity, ease: 'easeInOut' }}
                    style={{ transformOrigin: '81px 15px' }}
                />

                {/* Side ports */}
                <rect x="9" y="52" width="8" height="17" rx="4" fill="var(--bot-line)" />
                <rect x="79" y="52" width="8" height="17" rx="4" fill="var(--bot-line)" />

                {/* Head */}
                <rect x="15" y="31" width="66" height="56" rx="20" fill={`url(#${id}-shell)`} stroke="var(--bot-line)" strokeWidth="1.5" />
                <rect x="23" y="42" width="50" height="34" rx="14" fill="var(--bot-visor)" />

                {/* Eyes */}
                {mood === 'happy' ? (
                    <g stroke="var(--accent)" strokeWidth="4.2" strokeLinecap="round">
                        <path d="M33 60 Q38 52 43 60" />
                        <path d="M53 60 Q58 52 63 60" />
                    </g>
                ) : (
                    <motion.g animate={still(eye)} style={{ transformOrigin: '48px 58px' }}>
                        <rect x="33" y={mood === 'confused' ? 49 : 51} width="9" height={mood === 'confused' ? 15 : 13} rx="4.5" fill="var(--accent)" />
                        <rect x="54" y="51" width="9" height="13" rx="4.5" fill="var(--accent)" />
                    </motion.g>
                )}

                {/* Mouth */}
                {mood === 'happy' && <path d="M43 67 Q48 72 53 67" stroke="var(--accent)" strokeWidth="2.6" strokeLinecap="round" />}
                {mood === 'confused' && <path d="M43 70 Q47 67 53 70" stroke="var(--accent)" strokeWidth="2.4" strokeLinecap="round" />}

                {/* Graduation cap */}
                <g>
                    <path d="M31 28 V36 C31 40 65 40 65 36 V28" fill="var(--bot-cap-side)" />
                    <path d="M48 7 L80 21 L48 35 L16 21 Z" fill="var(--bot-cap)" stroke="var(--bot-line)" strokeWidth="1.5" strokeLinejoin="round" />
                    <motion.g
                        animate={still({ rotate: active ? [-14, 16, -14] : [-5, 7, -5] })}
                        transition={{ duration: active ? 0.9 : 3, repeat: Infinity, ease: 'easeInOut' }}
                        style={{ transformOrigin: '48px 21px' }}
                    >
                        <path d="M48 21 L25 28 V42" stroke="var(--accent)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                        <rect x="22" y="41" width="6" height="8" rx="2" fill="var(--accent)" />
                    </motion.g>
                    <circle cx="48" cy="21" r="2.6" fill="var(--accent)" />
                </g>
            </motion.g>
        </svg>
    );
}
