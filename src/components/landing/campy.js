// What Campy does and says in each section of the landing page.
export const CAMPY_SECTIONS = {
    home: { mood: 'idle', line: "Hi, I'm Campy. Let's fly." },
    knowledge: { mood: 'thinking', line: 'So many good questions.' },
    features: { mood: 'writing', line: 'Watch me work.' },
    benchmark: { mood: 'happy', line: 'Real scores. I was tested.' },
    'how-it-works': { mood: 'searching', line: 'Follow the question.' },
    'tech-stack': { mood: 'reading', line: 'Reading up on my insides.' },
    blueprint: { mood: 'reading', line: 'The whole project, right here.' },
    contact: { mood: 'happy', line: 'Your turn. Ask me!' },
};

// Where Campy hovers in each section, in clear space beside the content.
export const CAMPY_PERCHES = {
    home: { side: 'right', y: 0.24 },
    knowledge: { side: 'inner-right', y: 0.2 },
    features: { side: 'left', y: 0.74 },
    benchmark: { side: 'right', y: 0.3 },
    'how-it-works': { side: 'inner-right', y: 0.2 },
    'tech-stack': { side: 'left', y: 0.36 },
    blueprint: { side: 'right', y: 0.62 },
    contact: { side: 'inner-right', y: 0.3 },
};

export const CAMPY_REACTIONS = [
    'Wheee!',
    'Barrel roll!',
    'That tickles.',
    'Still flying!',
];
