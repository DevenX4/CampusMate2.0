import { engineScores as scores } from './engineScores';
import { CampyNote, CountUp, MaskedText, Reveal, Ring } from './motion';
import { useIsDesktop } from './utils';

function formatDate(value) {
    const date = new Date(`${value}T00:00:00`);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
}

function SmallRing({ value, label, delay }) {
    return (
        <Reveal delay={delay} className="flex items-center gap-4">
            <Ring value={value} size={84} stroke={6}>
                <span className="font-mono text-[15px] font-medium tabular-nums text-text-primary">
                    <CountUp value={value} suffix="%" />
                </span>
            </Ring>
            <span className="max-w-[12rem] text-sm leading-snug text-text-secondary">{label}</span>
        </Reveal>
    );
}

export default function Benchmark() {
    const isDesktop = useIsDesktop();
    if (!scores) return null;
    const heroSize = isDesktop ? 300 : 232;

    return (
        <section id="benchmark" data-campy="benchmark" aria-labelledby="benchmark-title" className="relative overflow-hidden border-y border-border-default bg-surface py-20 md:py-28">
            <div className="lp-dots" aria-hidden="true" />
            <div className="lp-container relative">
                <CampyNote section="benchmark" className="mb-6" />
                <div id="benchmark-title">
                    <MaskedText
                        text="We tested it. Here are the scores."
                        accent={[6]}
                        className="max-w-3xl text-4xl font-medium leading-[1.05] tracking-[-0.035em] text-text-primary md:text-6xl"
                    />
                </div>

                <div className="mt-12 grid items-center gap-12 md:mt-16 lg:grid-cols-[auto_1fr] lg:gap-20">
                    <Reveal className="flex justify-center lg:justify-start">
                        <Ring value={scores.right_record_found_pct} size={heroSize} stroke={isDesktop ? 14 : 11}>
                            <span className="font-mono text-5xl font-medium tracking-tight tabular-nums text-text-primary lg:text-6xl">
                                <CountUp value={scores.right_record_found_pct} suffix="%" />
                            </span>
                            <span className="mt-2 max-w-[10.5rem] text-sm leading-snug text-text-secondary">found the right campus record</span>
                        </Ring>
                    </Reveal>

                    <div>
                        <div className="grid gap-7 sm:grid-cols-2 xl:grid-cols-3">
                            <SmallRing value={scores.right_record_top3_pct} label="had the right record in the top 3" delay={0.05} />
                            <SmallRing value={scores.campus_questions_accepted_pct} label="of campus questions accepted" delay={0.12} />
                            <SmallRing value={scores.off_topic_refused_pct} label="of off-topic questions refused" delay={0.19} />
                        </div>

                        <Reveal delay={0.24} className="mt-10 grid grid-cols-2 gap-6 border-t border-border-default pt-7">
                            <div>
                                <div className="font-mono text-3xl font-medium tracking-tight tabular-nums text-text-primary md:text-4xl">
                                    <CountUp value={scores.median_search_ms} suffix=" ms" />
                                </div>
                                <div className="mt-1 text-sm text-text-secondary">median record search</div>
                            </div>
                            <div>
                                <div className="font-mono text-3xl font-medium tracking-tight tabular-nums text-text-primary md:text-4xl">
                                    <CountUp value={scores.records_indexed} />
                                </div>
                                <div className="mt-1 text-sm text-text-secondary">campus records indexed</div>
                            </div>
                        </Reveal>

                        <p className="mt-7 max-w-[62ch] text-xs leading-relaxed text-text-muted">
                            Measured on {scores.campus_questions} campus questions and {scores.off_topic_questions} off-topic questions on {formatDate(scores.measured_on)}. These scores cover question understanding and record search, not the written answers.
                        </p>
                    </div>
                </div>
            </div>
        </section>
    );
}
