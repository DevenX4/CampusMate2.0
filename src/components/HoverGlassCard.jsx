export default function HoverGlassCard({ children, className = "", disableGlow = false, ...props }) {
    const handleMove = (e) => {
        if (disableGlow) return;
        const rect = e.currentTarget.getBoundingClientRect();
        e.currentTarget.style.setProperty("--x", `${e.clientX - rect.left}px`);
        e.currentTarget.style.setProperty("--y", `${e.clientY - rect.top}px`);
    };

    return (
        <div
            {...props}
            onMouseMove={disableGlow ? undefined : handleMove}
            className={`hover-glass-card relative overflow-hidden ${className}`}
            style={{
                backgroundImage: disableGlow
                    ? "none"
                    : "radial-gradient(circle 280px at var(--x, 0px) var(--y, 0px), var(--accent-glow), transparent 70%)",
                ...props.style
            }}
        >
            {children}
        </div>
    );
}
