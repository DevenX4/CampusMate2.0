import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useMotionValueEvent, useReducedMotion, useScroll } from 'framer-motion';
import { Menu, Moon, Sun, X } from 'lucide-react';
import CampusLogo from './brand/CampusLogo';
import { scrollToSection } from './landing/utils';

const NAV_LINKS = [
    { label: 'Home', href: '#home' },
    { label: 'Features', href: '#features' },
    { label: 'How it works', href: '#how-it-works' },
    { label: 'Tech Stack', href: '#tech-stack' },
    { label: 'Blueprint', href: '#blueprint' },
    { label: 'Contact', href: '#contact' },
];

function readUser() {
    try {
        return JSON.parse(localStorage.getItem('currentUser') || 'null');
    } catch {
        return null;
    }
}

export default function Navbar({ navigate, theme, toggleTheme }) {
    const [scrolled, setScrolled] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [activeHref, setActiveHref] = useState('#home');
    const scrolledRef = useRef(false);
    const reduce = useReducedMotion();
    const { scrollY } = useScroll();
    const activeUser = readUser();

    useMotionValueEvent(scrollY, 'change', (value) => {
        const next = value > 40;
        if (next !== scrolledRef.current) {
            scrolledRef.current = next;
            setScrolled(next);
        }
    });

    useEffect(() => {
        const sections = NAV_LINKS.map((link) => document.querySelector(link.href)).filter(Boolean);
        const observer = new IntersectionObserver(
            (entries) => {
                const entering = entries.find((entry) => entry.isIntersecting);
                if (entering) setActiveHref(`#${entering.target.id}`);
            },
            { rootMargin: '-45% 0px -50% 0px' },
        );
        sections.forEach((section) => observer.observe(section));
        return () => observer.disconnect();
    }, []);

    useEffect(() => {
        if (!mobileMenuOpen) return undefined;
        const previous = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = previous;
        };
    }, [mobileMenuOpen]);

    const handleLinkClick = (event, href) => {
        event.preventDefault();
        setMobileMenuOpen(false);
        requestAnimationFrame(() => scrollToSection(href));
    };

    const go = (path) => {
        setMobileMenuOpen(false);
        navigate(path);
    };

    const dashboardPath = activeUser?.role === 'admin' ? '/dashboard/admin' : '/dashboard/student';
    const ThemeIcon = theme === 'dark' ? Moon : Sun;

    return (
        <>
            <nav className={`glass-navbar fixed left-0 right-0 top-0 z-50 ${scrolled ? 'scrolled' : ''}`}>
                <div className="lp-container flex h-16 items-center justify-between gap-4">
                    <a href="#home" onClick={(event) => handleLinkClick(event, '#home')} className="group flex cursor-pointer items-center gap-2">
                        <CampusLogo size="md" showTag={false} />
                    </a>

                    <div className="hidden items-center gap-0.5 lg:flex">
                        {NAV_LINKS.map((link) => (
                            <a
                                key={link.href}
                                href={link.href}
                                onClick={(event) => handleLinkClick(event, link.href)}
                                aria-current={activeHref === link.href ? 'true' : undefined}
                                className={`relative whitespace-nowrap rounded-full px-3 py-1.5 text-[13.5px] transition-colors duration-200 ${activeHref === link.href ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'}`}
                            >
                                {activeHref === link.href && (
                                    <motion.span
                                        layoutId="nav-active"
                                        className="absolute inset-0 rounded-full bg-surface-hover"
                                        transition={reduce ? { duration: 0 } : { type: 'spring', stiffness: 380, damping: 32 }}
                                    />
                                )}
                                <span className="relative">{link.label}</span>
                            </a>
                        ))}
                    </div>

                    <div className="hidden items-center gap-2 lg:flex">
                        <button
                            onClick={toggleTheme}
                            className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-full text-text-secondary transition-colors duration-200 hover:bg-surface-hover hover:text-accent"
                            aria-label="Toggle theme"
                        >
                            <AnimatePresence mode="wait" initial={false}>
                                <motion.span
                                    key={theme}
                                    initial={reduce ? false : { rotate: -70, opacity: 0, scale: 0.6 }}
                                    animate={{ rotate: 0, opacity: 1, scale: 1 }}
                                    exit={reduce ? undefined : { rotate: 70, opacity: 0, scale: 0.6 }}
                                    transition={{ duration: 0.18 }}
                                    className="flex"
                                >
                                    <ThemeIcon size={17} />
                                </motion.span>
                            </AnimatePresence>
                        </button>
                        {activeUser ? (
                            <button onClick={() => navigate(dashboardPath)} className="lp-btn lp-btn-primary !h-9 !px-4 !text-[13.5px]">
                                Dashboard
                            </button>
                        ) : (
                            <>
                                <button onClick={() => navigate('/login')} className="cursor-pointer whitespace-nowrap rounded-full px-3 py-1.5 text-[13.5px] text-text-primary transition-colors duration-200 hover:bg-surface-hover">
                                    Log in
                                </button>
                                <button onClick={() => navigate('/register')} className="lp-btn lp-btn-primary !h-9 !px-4 !text-[13.5px]">
                                    Register
                                </button>
                            </>
                        )}
                    </div>

                    <button
                        onClick={() => setMobileMenuOpen((open) => !open)}
                        className="flex h-10 w-10 cursor-pointer items-center justify-center text-text-primary lg:hidden"
                        aria-label="Toggle menu"
                        aria-expanded={mobileMenuOpen}
                    >
                        {mobileMenuOpen ? <X size={23} /> : <Menu size={23} />}
                    </button>
                </div>
            </nav>

            {/* Rendered outside the nav because its backdrop filter would trap fixed children. */}
            <AnimatePresence>
                {mobileMenuOpen && (
                    <motion.div
                        initial={reduce ? false : { opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={reduce ? undefined : { opacity: 0, y: -10 }}
                        transition={{ duration: 0.22 }}
                        className="fixed inset-0 top-16 z-40 overflow-y-auto border-t border-border-default bg-page lg:hidden"
                    >
                        <div className="flex min-h-full flex-col gap-1 px-5 py-6">
                            {NAV_LINKS.map((link) => (
                                <a
                                    key={link.href}
                                    href={link.href}
                                    onClick={(event) => handleLinkClick(event, link.href)}
                                    className="py-3 text-2xl font-medium tracking-tight text-text-primary"
                                >
                                    {link.label}
                                </a>
                            ))}
                            <div className="mt-3 flex items-center justify-between border-t border-border-default py-4">
                                <span className="text-sm text-text-secondary">Theme</span>
                                <button
                                    onClick={toggleTheme}
                                    className="flex h-10 w-10 cursor-pointer items-center justify-center rounded-full border border-border-default bg-surface text-text-secondary"
                                    aria-label="Toggle theme"
                                >
                                    <ThemeIcon size={18} />
                                </button>
                            </div>
                            <div className="mt-auto flex flex-col gap-3 pt-4">
                                {activeUser ? (
                                    <button onClick={() => go(dashboardPath)} className="lp-btn lp-btn-primary w-full">Dashboard</button>
                                ) : (
                                    <>
                                        <button onClick={() => go('/login')} className="lp-btn lp-btn-ghost w-full">Log in</button>
                                        <button onClick={() => go('/register')} className="lp-btn lp-btn-primary w-full">Register</button>
                                    </>
                                )}
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
