import { useEffect, useRef, useState } from 'react';
import { animate, useMotionValue, useSpring } from 'framer-motion';

const EMPTY = { filled: 0, total: 0, active: null, firstName: '', emailState: 'empty', matched: false };
const SCAN_MS = 320;
const RAIL_SPRING = { stiffness: 340, damping: 32, mass: 0.6 };

const isVisible = (element) => element.offsetParent !== null;
const isEmailField = (element) => element.type === 'email' || element.name === 'email';

function readForm(root) {
    const inputs = [...root.querySelectorAll('input.auth-input, select.auth-input, .auth-check input')].filter(isVisible);
    const hasRequired = inputs.some((element) => element.required);
    const tracked = inputs.filter((element) => (hasRequired ? element.required : true));
    const password = inputs.find((element) => element.name === 'password' || element.id === 'password');
    const confirm = inputs.find((element) => element.name === 'confirmPassword');

    const isComplete = (element) => {
        if (element.type === 'checkbox') return element.checked;
        const value = element.value.trim();
        if (!value) return false;
        if (isEmailField(element)) return /@gnu\.ac\.in$/i.test(value) && element.validity.valid;
        if (element === password && confirm) return value.length >= 8;
        if (element === confirm) return element.value === password?.value;
        if (element.classList.contains('auth-input-otp')) return value.length >= 6;
        return true;
    };

    let filled = 0;
    tracked.forEach((element) => {
        const complete = isComplete(element);
        if (complete) filled += 1;
        const field = element.closest('.auth-field');
        if (field && field.dataset.ok !== String(complete)) field.dataset.ok = String(complete);
    });

    const focused = document.activeElement;
    const activeElement = focused && root.contains(focused) && focused.matches('input, select') ? focused : null;
    const email = inputs.find(isEmailField);
    const nameField = inputs.find((element) => element.name === 'name');

    return {
        activeElement,
        snapshot: {
            filled,
            total: tracked.length,
            active: activeElement ? (activeElement.name || activeElement.id) : null,
            firstName: nameField ? nameField.value.trim().split(/\s+/)[0].slice(0, 18) : '',
            emailState: !email?.value ? 'empty' : isComplete(email) ? 'valid' : 'typing',
            matched: Boolean(confirm?.value) && confirm.value === password?.value,
        },
    };
}

/**
 * Presentation only: watches the form on screen so Campy can react to it.
 * It never writes to a field, and password text is only compared, never stored.
 */
export function useAuthLive(mainRef) {
    const [live, setLive] = useState(EMPTY);
    const liveRef = useRef(EMPTY);
    const keystroke = useMotionValue(0);
    const railTopTarget = useMotionValue(0);
    const railHeightTarget = useMotionValue(44);
    const railTop = useSpring(railTopTarget, RAIL_SPRING);
    const railHeight = useSpring(railHeightTarget, RAIL_SPRING);
    const railLeft = useMotionValue(0);
    const railOpacity = useMotionValue(0);

    useEffect(() => {
        const root = mainRef.current;
        if (!root) return undefined;
        let keyAnimation;

        const scan = () => {
            const { snapshot, activeElement } = readForm(root);
            const previous = liveRef.current;
            if (Object.keys(snapshot).some((key) => snapshot[key] !== previous[key])) {
                liveRef.current = snapshot;
                setLive(snapshot);
            }
            if (activeElement && activeElement.type !== 'checkbox') {
                const rootBox = root.getBoundingClientRect();
                const box = activeElement.getBoundingClientRect();
                const wasHidden = railOpacity.get() === 0;
                railLeft.set(box.left - rootBox.left - 12);
                if (wasHidden) {
                    railTop.jump(box.top - rootBox.top);
                    railHeight.jump(box.height);
                }
                railTopTarget.set(box.top - rootBox.top);
                railHeightTarget.set(box.height);
                railOpacity.set(1);
            } else {
                railOpacity.set(0);
            }
        };

        const onInput = () => {
            keyAnimation?.stop();
            keyAnimation = animate(keystroke, [1, 0], { duration: 0.34, ease: 'easeOut' });
            scan();
        };
        const onFocusChange = () => requestAnimationFrame(scan);

        scan();
        // Demo login buttons fill the fields from code, which fires no input event.
        const timer = setInterval(scan, SCAN_MS);
        root.addEventListener('input', onInput);
        root.addEventListener('change', scan);
        root.addEventListener('focusin', onFocusChange);
        root.addEventListener('focusout', onFocusChange);
        window.addEventListener('resize', scan);

        return () => {
            clearInterval(timer);
            keyAnimation?.stop();
            root.removeEventListener('input', onInput);
            root.removeEventListener('change', scan);
            root.removeEventListener('focusin', onFocusChange);
            root.removeEventListener('focusout', onFocusChange);
            window.removeEventListener('resize', scan);
        };
    }, [mainRef, keystroke, railHeight, railHeightTarget, railLeft, railOpacity, railTop, railTopTarget]);

    return { live, keystroke, rail: { top: railTop, height: railHeight, left: railLeft, opacity: railOpacity } };
}

/** What Campy says about the field in focus. Returns null when it has nothing specific to add. */
export function fieldLine({ active, firstName, emailState, matched }) {
    switch (active) {
        case 'name':
            return firstName ? `Nice to meet you, ${firstName}!` : 'What should I call you?';
        case 'email':
            if (emailState === 'valid') return 'Perfect, that is a college email.';
            return emailState === 'typing' ? 'It should end with @gnu.ac.in.' : 'Your college email goes here.';
        case 'password':
            return 'Eyes covered. I am not looking.';
        case 'confirmPassword':
            return matched ? 'They match. Nicely done.' : 'One more time, same password.';
        case 'enrollmentNumber':
            return 'Your roll number, please.';
        case 'employeeId':
            return 'Your employee ID, please.';
        case 'department':
            return 'Which department are you in?';
        case 'semester':
            return 'Which semester are you in?';
        case 'phone':
            return 'This one is optional.';
        default:
            return null;
    }
}
