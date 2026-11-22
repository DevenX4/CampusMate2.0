import { useEffect, useLayoutEffect, useRef } from 'react';

const WORD = 'CampusMate';
const ZOOM_LETTER = WORD.indexOf('p');
// The word renders large and starts scaled down, so it stays sharp while the camera flies through it.
const RENDER_SCALE = 3;
const LETTERS_MS = 1050;
const HOLD_MS = 260;
const PULL_BACK_MS = 620;
const ZOOM_MS = 1250;
const REVEAL_AT = 0.72;
const FADE_MS = 460;
const BOWL_X = 0.57;
const BOWL_HEIGHT_EM = 0.265;

/** Opening title: the wordmark appears, pulls back, then the camera zooms through the "p" into the site. */
export default function IntroSplash({ onReveal, onDone }) {
    const rootRef = useRef(null);
    const backdropRef = useRef(null);
    const stageRef = useRef(null);
    const holeRef = useRef(null);
    const baselineRef = useRef(null);
    const skipRef = useRef(null);
    const finished = useRef(false);
    const revealed = useRef(false);
    const callbacks = useRef({ onReveal, onDone });

    useLayoutEffect(() => {
        callbacks.current = { onReveal, onDone };
    });

    useEffect(() => {
        const stage = stageRef.current;
        const backdrop = backdropRef.current;
        const timers = [];
        const animations = [];

        const reveal = () => {
            if (revealed.current) return;
            revealed.current = true;
            callbacks.current.onReveal?.();
        };
        const finish = () => {
            if (finished.current) return;
            finished.current = true;
            reveal();
            callbacks.current.onDone?.();
        };
        const fadeOut = (duration) => {
            reveal();
            const fade = rootRef.current?.animate([{ opacity: 1 }, { opacity: 0 }], { duration, easing: 'ease-out', fill: 'forwards' });
            if (fade) fade.onfinish = finish;
            else finish();
        };
        const skip = () => {
            timers.forEach(clearTimeout);
            fadeOut(240);
        };

        const startZoom = () => {
            skipRef.current?.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 220, fill: 'forwards' });
            const stageBox = stage.getBoundingClientRect();
            const letter = holeRef.current.getBoundingClientRect();
            const baseline = baselineRef.current.getBoundingClientRect().bottom;
            const renderedFont = parseFloat(getComputedStyle(stage).fontSize);
            const scaleNow = stageBox.width / stage.offsetWidth;
            // Center of the bowl of the "p" on screen, and in the stage's own coordinates.
            const screenX = letter.left + letter.width * BOWL_X;
            const screenY = baseline - renderedFont * scaleNow * BOWL_HEIGHT_EM;
            const holeX = (screenX - stageBox.left) / scaleNow;
            const holeY = (screenY - stageBox.top) / scaleNow;
            // Where that point sits before any transform. Offsets from here keep the switch of origin invisible.
            const layoutX = stageBox.left + stageBox.width / 2 - stage.offsetWidth / 2 + holeX;
            const layoutY = stageBox.top + stageBox.height / 2 - stage.offsetHeight / 2 + holeY;
            const startX = screenX - layoutX;
            const startY = screenY - layoutY;
            const endX = window.innerWidth / 2 - layoutX;
            const endY = window.innerHeight / 2 - layoutY;
            const diagonal = Math.hypot(window.innerWidth, window.innerHeight);
            const finalScale = diagonal / (renderedFont * 0.2);

            stage.style.transformOrigin = `${holeX}px ${holeY}px`;
            const zoom = stage.animate(
                [
                    { transform: `translate(${startX}px, ${startY}px) scale(${scaleNow})`, opacity: 1, offset: 0 },
                    { opacity: 1, offset: 0.82 },
                    { transform: `translate(${endX}px, ${endY}px) scale(${finalScale})`, opacity: 0, offset: 1 },
                ],
                { duration: ZOOM_MS, easing: 'cubic-bezier(0.7, 0, 0.84, 0)', fill: 'forwards' },
            );
            animations.push(zoom);
            timers.push(setTimeout(() => {
                reveal();
                animations.push(backdrop.animate([{ opacity: 1 }, { opacity: 0 }], { duration: FADE_MS, easing: 'ease-out', fill: 'forwards' }));
            }, ZOOM_MS * REVEAL_AT));
            timers.push(setTimeout(finish, Math.max(ZOOM_MS, ZOOM_MS * REVEAL_AT + FADE_MS) + 30));
        };

        const startPullBack = () => {
            stage.style.transformOrigin = '50% 50%';
            animations.push(stage.animate(
                [{ transform: `scale(${1 / RENDER_SCALE})` }, { transform: `scale(${0.9 / RENDER_SCALE})` }],
                { duration: PULL_BACK_MS, easing: 'cubic-bezier(0.33, 1, 0.68, 1)', fill: 'forwards' },
            ));
            timers.push(setTimeout(startZoom, PULL_BACK_MS));
        };

        timers.push(setTimeout(startPullBack, LETTERS_MS + HOLD_MS));

        const onKey = (event) => {
            if (!['Shift', 'Control', 'Alt', 'Meta'].includes(event.key)) skip();
        };
        window.addEventListener('keydown', onKey);
        window.addEventListener('wheel', skip, { passive: true });
        window.addEventListener('touchmove', skip, { passive: true });
        const root = rootRef.current;
        root.addEventListener('pointerdown', skip);

        return () => {
            timers.forEach(clearTimeout);
            animations.forEach((animation) => animation.cancel());
            window.removeEventListener('keydown', onKey);
            window.removeEventListener('wheel', skip);
            window.removeEventListener('touchmove', skip);
            root.removeEventListener('pointerdown', skip);
        };
    }, []);

    return (
        <div ref={rootRef} role="img" aria-label="CampusMate" className="fixed inset-0 z-[100] cursor-pointer overflow-hidden">
            <div ref={backdropRef} className="lp-intro-backdrop absolute inset-0" />
            <div className="absolute inset-0 flex items-center justify-center">
                <div
                    ref={stageRef}
                    className="lp-intro-word"
                    style={{ transform: `scale(${1 / RENDER_SCALE})`, fontSize: `calc(min(15.5vw, 190px) * ${RENDER_SCALE})` }}
                >
                    {WORD.split('').map((letter, index) => (
                        <span key={index} className="lp-intro-mask">
                            <span
                                ref={index === ZOOM_LETTER ? holeRef : undefined}
                                className={`lp-intro-letter ${index >= 6 ? 'lp-intro-accent' : ''}`}
                                style={{ animationDelay: `${90 + index * 62}ms` }}
                            >
                                {letter}
                                {index === ZOOM_LETTER && <span ref={baselineRef} className="inline-block h-0 w-0" />}
                            </span>
                        </span>
                    ))}
                </div>
            </div>
            <span ref={skipRef} className="lp-intro-skip">Press any key to skip</span>
        </div>
    );
}
