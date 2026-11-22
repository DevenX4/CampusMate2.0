import { useEffect, useState } from 'react';

export const EASE = [0.16, 1, 0.3, 1];

export function useIsDesktop(query = '(min-width: 1024px)') {
    const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

    useEffect(() => {
        const media = window.matchMedia(query);
        const onChange = () => setMatches(media.matches);
        onChange();
        media.addEventListener('change', onChange);
        return () => media.removeEventListener('change', onChange);
    }, [query]);

    return matches;
}

export function scrollToSection(href) {
    const element = document.querySelector(href);
    if (!element) return;
    const pinned = href === '#features' || href === '#tech-stack' || href === '#home';
    const top = element.getBoundingClientRect().top + window.scrollY - (pinned ? 0 : 64);
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top, behavior: reduce ? 'auto' : 'smooth' });
}
