import { useCallback, useLayoutEffect, useState } from 'react';
import { motion, useReducedMotion, useScroll, useSpring } from 'framer-motion';
import Navbar from './Navbar';
import Hero from './Hero';
import CampusKnowledge from './CampusKnowledge';
import ProductShowcase from './ProductShowcase';
import TechPipeline from './TechPipeline';
import TechStackDeck from './TechStackDeck';
import Footer from './Footer';
import Benchmark from './landing/Benchmark';
import IntroSplash from './landing/IntroSplash';
import ProjectBlueprint from './landing/ProjectBlueprint';
import ScrollBot from './landing/ScrollBot';

// A browser reload resets this flag, so the intro plays on every reload.
// Moving between pages inside the app, such as back from login, does not replay it.
let introPlayedThisLoad = false;

function shouldPlayIntro() {
    return !introPlayedThisLoad
        && !window.location.hash
        && !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// Shows position on a long page that contains pinned scroll sections.
function ScrollProgress() {
    const { scrollYProgress } = useScroll();
    const scaleX = useSpring(scrollYProgress, { stiffness: 140, damping: 28, mass: 0.3 });
    const reduceMotion = useReducedMotion();

    return (
        <motion.div
            aria-hidden="true"
            className="fixed top-0 left-0 right-0 z-[60] h-0.5 origin-left bg-accent"
            style={{ scaleX: reduceMotion ? scrollYProgress : scaleX }}
        />
    );
}

export default function LandingPage({ navigate, theme, toggleTheme }) {
    const [introPlaying, setIntroPlaying] = useState(shouldPlayIntro);
    // Remounting the hero at the reveal lets its entrance play as the intro opens onto it.
    const [heroRun, setHeroRun] = useState(0);

    const onIntroReveal = useCallback(() => setHeroRun((run) => run + 1), []);
    const onIntroDone = useCallback(() => {
        introPlayedThisLoad = true;
        setIntroPlaying(false);
    }, []);

    // The intro always opens onto the hero, even if the page was reloaded further down.
    useLayoutEffect(() => {
        if (!introPlaying) return;
        window.history.scrollRestoration = 'manual';
        window.scrollTo(0, 0);
    }, [introPlaying]);
    const replayIntro = useCallback(() => {
        window.scrollTo({ top: 0, behavior: 'instant' });
        setIntroPlaying(true);
    }, []);

    return (
        <div className="min-h-screen bg-page text-text-primary">
            {introPlaying && <IntroSplash onReveal={onIntroReveal} onDone={onIntroDone} />}
            <ScrollProgress />
            <Navbar navigate={navigate} theme={theme} toggleTheme={toggleTheme} />
            <ScrollBot />

            <main>
                <div key={heroRun} className={heroRun > 0 ? 'lp-hero-settle' : undefined}>
                    <Hero navigate={navigate} />
                </div>
                <CampusKnowledge />
                <ProductShowcase />
                <Benchmark />
                <TechPipeline />
                <TechStackDeck />
                <ProjectBlueprint />
            </main>

            <Footer navigate={navigate} onReplayIntro={replayIntro} />
        </div>
    );
}
