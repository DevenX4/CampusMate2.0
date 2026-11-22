import { useEffect, useState } from 'react';

const DEFAULT_LINES = {
    idle: 'Hi, I am Campy. Sign in and I will take it from here.',
    watching: 'Reading along.',
    hiding: 'Eyes covered. Type your password.',
    away: 'Password is visible, so I am looking away.',
    thinking: 'Checking that for you.',
    confused: 'That did not work. See the message on the form.',
    happy: 'Looks good. Ready when you are.',
};

/**
 * Presentation only: maps what the form is already doing to a Campy pose and line.
 * It reads form state and never writes to it.
 */
export function useCampyState({ loading, success, error, focus, secretFields = [], revealed, ready, gazeText = '', lines = {} }) {
    const [flash, setFlash] = useState(false);

    useEffect(() => {
        if (!error) {
            setFlash(false);
            return undefined;
        }
        setFlash(true);
        const timer = setTimeout(() => setFlash(false), 2800);
        return () => clearTimeout(timer);
    }, [error]);

    let state = 'idle';
    if (loading) state = 'thinking';
    else if (success) state = 'happy';
    else if (flash) state = 'confused';
    else if (revealed) state = 'away';
    else if (focus && secretFields.includes(focus)) state = 'hiding';
    else if (focus) state = 'watching';
    else if (error) state = 'confused';
    else if (ready) state = 'happy';

    return {
        state,
        gaze: Math.min(1, (gazeText || '').length / 26),
        speech: lines[state] || DEFAULT_LINES[state],
    };
}
