import { CampyNote, CountUp, Reveal, ScrubWords } from './landing/motion';
import { engineScores } from './landing/engineScores';

// Verified against AI_workflow/storage/knowledge_base.json. A fresh score file supplies the live record count.
const RECORDS = [
    { value: engineScores?.records_indexed ?? 261, label: 'campus records indexed' },
    { value: 116, label: 'courses from the official syllabus' },
    { value: 12, label: 'semesters of B.Tech and M.Tech IT' },
];

const QUESTIONS = [
    'What are the credits for 2CEIT601?',
    'Who is the HOD of Information Technology?',
    'What happens if my attendance drops below 75 percent?',
    'When are the mid semester examinations?',
    'How is my capstone project graded?',
    'Where is the Database Systems Lab?',
    'What electives can I choose in Semester 6?',
    'What do I need before Industrial Training?',
    'How are SGPA and CGPA calculated?',
    'What are the Department Office hours?',
];

export default function CampusKnowledge() {
    return (
        <section aria-label="What CampusMate knows" data-campy="knowledge" className="lp-curtain pb-16 pt-20 md:pb-20 md:pt-32">
            <div className="lp-container">
                <CampyNote section="knowledge" className="mb-6" />
                <ScrubWords
                    text="Credits, syllabus, exams, labs, notices. Ask once in your own words and get the answer with the record it came from."
                    className="max-w-[20ch] text-[2rem] font-medium leading-[1.12] tracking-[-0.035em] text-text-primary sm:max-w-[26ch] md:text-5xl lg:text-[3.4rem]"
                />

                <div className="mt-14 grid gap-8 sm:grid-cols-3 md:mt-20">
                    {RECORDS.map((record, index) => (
                        <Reveal key={record.label} delay={index * 0.08}>
                            <div className="font-mono text-5xl font-medium tracking-tight tabular-nums text-text-primary md:text-6xl">
                                <CountUp value={record.value} />
                            </div>
                            <div className="mt-2 text-sm text-text-secondary">{record.label}</div>
                        </Reveal>
                    ))}
                </div>

                <div
                    className="question-marquee-wrap mt-14 overflow-hidden"
                    style={{
                        maskImage: 'linear-gradient(90deg, transparent, #000 7%, #000 93%, transparent)',
                        WebkitMaskImage: 'linear-gradient(90deg, transparent, #000 7%, #000 93%, transparent)',
                    }}
                >
                    <ul className="question-marquee m-0 list-none p-0" aria-label="Example questions">
                        {[...QUESTIONS, ...QUESTIONS].map((question, index) => (
                            <li
                                key={`${question}-${index}`}
                                aria-hidden={index >= QUESTIONS.length ? 'true' : undefined}
                                className="mx-1.5 shrink-0 whitespace-nowrap rounded-full border border-border-default bg-page px-4 py-2 text-sm text-text-secondary transition-colors duration-200 hover:border-accent hover:text-accent"
                            >
                                {question}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
        </section>
    );
}
