// The score file is produced by AI_workflow/backend/scripts/score_assistant.py and may not exist yet.
const modules = import.meta.glob('../../data/engine_scores.json', { eager: true });
const loaded = Object.values(modules)[0];
const data = loaded?.default ?? loaded;

const NUMERIC_KEYS = [
    'right_record_found_pct',
    'right_record_top3_pct',
    'campus_questions_accepted_pct',
    'off_topic_refused_pct',
    'median_search_ms',
    'records_indexed',
    'campus_questions',
    'off_topic_questions',
];

const isComplete = data && data.measured_on && NUMERIC_KEYS.every((key) => Number.isFinite(data[key]));

export const engineScores = isComplete ? data : null;
