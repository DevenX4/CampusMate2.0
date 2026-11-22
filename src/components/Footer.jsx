import { ArrowRight, ExternalLink } from 'lucide-react';
import CampusLogo from './brand/CampusLogo';
import { CampyNote, Magnetic, MaskedText, Parallax, Reveal } from './landing/motion';
import { scrollToSection } from './landing/utils';

const LINKS = [
    { label: 'Home', href: '#home' },
    { label: 'Features', href: '#features' },
    { label: 'How it works', href: '#how-it-works' },
    { label: 'Tech Stack', href: '#tech-stack' },
    { label: 'Blueprint', href: '#blueprint' },
];

export default function Footer({ navigate, onReplayIntro }) {
    const onLink = (event, href) => {
        event.preventDefault();
        scrollToSection(href);
    };

    const getStarted = () => {
        if (!navigate) return;
        try {
            const user = JSON.parse(localStorage.getItem('currentUser') || 'null');
            if (user?.role === 'admin') navigate('/dashboard/admin');
            else if (user?.role === 'student') navigate('/dashboard/student');
            else navigate('/register');
        } catch {
            navigate('/register');
        }
    };

    return (
        <footer id="contact" data-campy="contact" className="relative overflow-hidden border-t border-border-default bg-surface">
            <div className="lp-dots" aria-hidden="true" />
            <div className="lp-container relative pb-8 pt-20 md:pt-32">
                <CampyNote section="contact" className="mb-6" />
                <MaskedText
                    text="Got a campus question? Ask Campy."
                    accent={[4, 5]}
                    className="max-w-[14em] text-[2.6rem] font-medium leading-[1.04] tracking-[-0.04em] text-text-primary md:text-7xl"
                />
                <Reveal delay={0.1} className="mt-8">
                    <Magnetic className="w-full sm:w-auto">
                        <button onClick={getStarted} className="lp-btn lp-btn-primary w-full sm:w-auto">
                            Get started
                            <ArrowRight size={17} className="lp-btn-icon" />
                        </button>
                    </Magnetic>
                </Reveal>

                <div className="mt-20 flex flex-col gap-6 border-t border-border-default pt-8 md:flex-row md:items-center md:justify-between">
                    <a href="#home" onClick={(event) => onLink(event, '#home')} className="group w-fit">
                        <CampusLogo size="sm" showTag={false} />
                    </a>
                    <nav aria-label="Footer" className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-text-secondary">
                        {LINKS.map((link) => (
                            <a key={link.href} href={link.href} onClick={(event) => onLink(event, link.href)} className="transition-colors duration-200 hover:text-accent">
                                {link.label}
                            </a>
                        ))}
                        <a href="https://www.ganpatuniversity.ac.in" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 transition-colors duration-200 hover:text-accent">
                            Ganpat University <ExternalLink size={12} />
                        </a>
                        {onReplayIntro && (
                            <button type="button" onClick={onReplayIntro} className="cursor-pointer transition-colors duration-200 hover:text-accent">
                                Replay intro
                            </button>
                        )}
                    </nav>
                </div>

                <p className="mt-6 text-xs text-text-muted">
                    &copy; {new Date().getFullYear()} CampusMate, built for U.V. Patel College of Engineering.
                </p>

                <Parallax from={46} to={0} className="lp-wordmark mt-10">
                    <span aria-hidden="true">CampusMate</span>
                </Parallax>
            </div>
        </footer>
    );
}
