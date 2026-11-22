import { useEffect, useRef } from 'react';

const SYMBOLS = ['</>', '+', '*', '/', 'π', 'x²', '√', 'A+', '{ }', 'mod', 'f(x)', '∑', '[1]'];

export default function PlayfulHoverParticles({ containerRef }) {
    const canvasRef = useRef(null);
    const particlesRef = useRef([]);
    const lastMousePosRef = useRef({ x: 0, y: 0 });
    const animationFrameIdRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

        const resizeCanvas = () => {
            const rect = canvas.parentElement.getBoundingClientRect();
            // Use devicePixelRatio for super crisp rendering on high-DPI screens
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            canvas.style.width = `${rect.width}px`;
            canvas.style.height = `${rect.height}px`;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };

        // Initial sizing
        resizeCanvas();

        // Resize on window resize
        const resizeObserver = new ResizeObserver(() => {
            resizeCanvas();
        });
        if (canvas.parentElement) {
            resizeObserver.observe(canvas.parentElement);
        }

        const createParticle = (x, y) => {
            const symbol = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];
            const color = getComputedStyle(canvas).getPropertyValue('--accent').trim();

            const speedMagnitude = Math.random() * 1.2 + 0.4;
            const angle = (Math.random() * Math.PI) / 3 - Math.PI / 1.5; // Upward drift with slight spread

            particlesRef.current.push({
                id: Date.now() + Math.random(),
                x,
                y,
                vx: Math.cos(angle) * speedMagnitude,
                vy: Math.sin(angle) * speedMagnitude - 0.4, // Shift upwards slightly more
                rotation: Math.random() * Math.PI * 2,
                spin: (Math.random() - 0.5) * 0.05,
                scale: Math.random() * 0.4 + 0.8, // 0.8 to 1.2 size factor
                opacity: 1,
                // decay rate: between 1 and 2.5 seconds lifetime
                decay: Math.random() * 0.015 + 0.01,
                color,
                symbol,
            });

            // Cap particles limit to avoid memory leaks
            if (particlesRef.current.length > 48) {
                particlesRef.current.shift();
            }
        };

        const updateAndDraw = () => {
            const rect = canvas.getBoundingClientRect();
            ctx.clearRect(0, 0, rect.width, rect.height);

            const activeParticles = particlesRef.current.filter((p) => p.opacity > 0);

            activeParticles.forEach((p) => {
                // Apply velocity
                p.x += p.vx;
                p.y += p.vy;

                // Spin rotation
                p.rotation += p.spin;

                // Decay opacity
                p.opacity -= p.decay;

                if (p.opacity > 0) {
                    ctx.save();
                    ctx.globalAlpha = p.opacity;
                    ctx.translate(p.x, p.y);
                    ctx.rotate(p.rotation);

                    // Define font size based on scale
                    const baseSize = 14;
                    const fontSize = Math.round(baseSize * p.scale);
                    ctx.font = `500 ${fontSize}px 'Geist Mono Variable', ui-monospace, monospace`;
                    ctx.fillStyle = p.color;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';

                    ctx.fillText(p.symbol, 0, 0);
                    ctx.restore();
                }
            });

            particlesRef.current = activeParticles;

            // Keep running the loop as long as there are visible active particles
            if (activeParticles.length > 0) {
                animationFrameIdRef.current = requestAnimationFrame(updateAndDraw);
            } else {
                animationFrameIdRef.current = null;
            }
        };

        const handleMouseMove = (e) => {
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const lastPos = lastMousePosRef.current;
            const distance = Math.hypot(x - lastPos.x, y - lastPos.y);

            // Throttling: Spawn a new particle only when cursor moves more than 16px
            if (distance > 16) {
                createParticle(x, y);
                lastMousePosRef.current = { x, y };

                // Start animation loop if not already running
                if (!animationFrameIdRef.current) {
                    animationFrameIdRef.current = requestAnimationFrame(updateAndDraw);
                }
            }
        };

        const handleTouchMove = (e) => {
            if (e.touches.length === 0) return;
            const touch = e.touches[0];
            const rect = canvas.getBoundingClientRect();
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;

            const lastPos = lastMousePosRef.current;
            const distance = Math.hypot(x - lastPos.x, y - lastPos.y);

            if (distance > 18) {
                createParticle(x, y);
                lastMousePosRef.current = { x, y };

                if (!animationFrameIdRef.current) {
                    animationFrameIdRef.current = requestAnimationFrame(updateAndDraw);
                }
            }
        };

        const container = containerRef.current;
        if (container) {
            container.addEventListener('mousemove', handleMouseMove);
            container.addEventListener('touchmove', handleTouchMove);
        }

        return () => {
            if (container) {
                container.removeEventListener('mousemove', handleMouseMove);
                container.removeEventListener('touchmove', handleTouchMove);
            }
            if (animationFrameIdRef.current) {
                cancelAnimationFrame(animationFrameIdRef.current);
            }
            resizeObserver.disconnect();
        };
    }, [containerRef]);

    return (
        <canvas
            ref={canvasRef}
            aria-hidden="true"
            className="absolute inset-0 pointer-events-none z-0 w-full h-full"
            style={{ display: 'block' }}
        />
    );
}
