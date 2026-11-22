import { useEffect, useRef } from 'react';

/**
 * Custom hook to track mouse coordinates throttled by requestAnimationFrame.
 * Automatically updates CSS variables --mouse-x and --mouse-y on the target element.
 */
export function useMouseGlow(targetRef) {
    const coords = useRef({ x: 0, y: 0 });
    const rafId = useRef(null);

    useEffect(() => {
        const target = targetRef.current;
        if (!target) return;

        const handleMouseMove = (e) => {
            // Calculate coordinates relative to the target element
            const rect = target.getBoundingClientRect();
            coords.current = {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top,
            };
        };

        const updateGlow = () => {
            if (target) {
                target.style.setProperty('--mouse-x', `${coords.current.x}px`);
                target.style.setProperty('--mouse-y', `${coords.current.y}px`);
            }
            rafId.current = requestAnimationFrame(updateGlow);
        };

        target.addEventListener('mousemove', handleMouseMove);
        rafId.current = requestAnimationFrame(updateGlow);

        return () => {
            if (target) {
                target.removeEventListener('mousemove', handleMouseMove);
            }
            if (rafId.current) {
                cancelAnimationFrame(rafId.current);
            }
        };
    }, [targetRef]);
}
