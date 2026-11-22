import { useEffect, useRef, useState } from "react";

export default function ConstellationBackground({ particleCount = 45 }) {
    const canvasRef = useRef(null);
    const [isDesktop, setIsDesktop] = useState(true);

    // Skip mounting execution loops below typical 768px viewport tablet boundary
    useEffect(() => {
        const checkSize = () => setIsDesktop(window.innerWidth >= 768);
        checkSize();
        window.addEventListener("resize", checkSize);
        return () => window.removeEventListener("resize", checkSize);
    }, []);

    useEffect(() => {
        if (!isDesktop) return;

        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        let width, height, particles, animationId;

        const resize = () => {
            width = canvas.width = canvas.offsetWidth;
            height = canvas.height = canvas.offsetHeight;
        };
        resize();
        window.addEventListener("resize", resize);

        // Scaling particle allocation relative to panel dimensions
        particles = Array.from({ length: particleCount }, () => ({
            x: Math.random() * width,
            y: Math.random() * height,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
        }));

        const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        function draw() {
            ctx.clearRect(0, 0, width, height);
            const accent = getComputedStyle(canvas).getPropertyValue("--accent").trim();

            // Edge bouncing logic
            particles.forEach((p) => {
                if (!prefersReducedMotion) {
                    p.x += p.vx;
                    p.y += p.vy;
                }
                if (p.x < 0 || p.x > width) p.vx *= -1;
                if (p.y < 0 || p.y > height) p.vy *= -1;
            });

            // Drawing connecting proximity paths
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    const maxDist = 140;
                    if (dist < maxDist) {
                        ctx.strokeStyle = accent;
                        ctx.globalAlpha = 0.2 * (1 - dist / maxDist);
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.stroke();
                    }
                }
            }

            // Drawing node objects
            ctx.globalAlpha = 0.8;
            particles.forEach((p) => {
                ctx.fillStyle = accent;
                ctx.beginPath();
                ctx.arc(p.x, p.y, 1.8, 0, Math.PI * 2);
                ctx.fill();
            });

            if (!prefersReducedMotion) {
                animationId = requestAnimationFrame(draw);
            }
        }
        draw();

        return () => {
            window.removeEventListener("resize", resize);
            if (animationId) {
                cancelAnimationFrame(animationId);
            }
        };
    }, [particleCount, isDesktop]);

    if (!isDesktop) return null;

    return (
        <canvas
            ref={canvasRef}
            style={{ opacity: 0.65 }}
            className="absolute inset-0 w-full h-full"
            aria-hidden="true"
        />
    );
}

// AuroraBlob - morphing deep color overlay behind constellation
export function AuroraBlob() {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    return (
        <div
            className="absolute rounded-full pointer-events-none block"
            style={{
                width: "500px",
                height: "500px",
                top: "20%",
                left: "-10%",
                backgroundImage: "linear-gradient(135deg, var(--logo-deep) 0%, var(--logo-mid) 55%, var(--logo-light) 100%)",
                filter: "blur(90px)",
                WebkitFilter: "blur(90px)",
                opacity: 0.16,
                animation: prefersReducedMotion ? "none" : "morph 10s ease-in-out infinite",
            }}
            aria-hidden="true"
        />
    );
}
