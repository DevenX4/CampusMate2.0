import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Bell, Check, LogOut, Moon, Sun } from 'lucide-react';
import ChatContainer from './chat/ChatContainer';

const iconButton = 'w-9 h-9 shrink-0 flex items-center justify-center rounded-xl transition-colors cursor-pointer';
const popover = { initial: { opacity: 0, y: -4 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -4 }, transition: { duration: 0.14 } };

function readUser() {
    try {
        return JSON.parse(localStorage.getItem('currentUser') || '{}');
    } catch {
        return {};
    }
}

const SEEN_NOTICES_KEY = 'cm_seen_notices';

function readSeenNotices() {
    try {
        return JSON.parse(localStorage.getItem(SEEN_NOTICES_KEY) || '[]');
    } catch {
        return [];
    }
}

function formatNoticeDate(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

function HeaderActions({ theme, toggleTheme, onLogout }) {
    const currentUser = readUser();
    const [openMenu, setOpenMenu] = useState(null); // 'bell' | 'account' | null
    const rootRef = useRef(null);

    const [notifications, setNotifications] = useState([]);
    const hasUnread = notifications.some((n) => n.unread);

    useEffect(() => {
        let active = true;
        const headers = currentUser.token ? { Authorization: `Bearer ${currentUser.token}` } : {};
        fetch('/api/chat/notices', { headers, credentials: 'include' })
            .then((res) => (res.ok ? res.json() : { notices: [] }))
            .then(({ notices = [] }) => {
                if (!active) return;
                const read = readSeenNotices();
                setNotifications(notices.map((n) => ({
                    id: n.id,
                    text: n.title,
                    time: formatNoticeDate(n.date),
                    unread: !read.includes(n.id),
                })));
            })
            .catch(() => {});
        return () => { active = false; };
        // Notices load once when the dashboard opens.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const markAllRead = () => {
        setNotifications((list) => list.map((n) => ({ ...n, unread: false })));
        try {
            localStorage.setItem(SEEN_NOTICES_KEY, JSON.stringify(notifications.map((n) => n.id)));
        } catch {
            // The read state is a convenience and can be lost safely.
        }
    };

    useEffect(() => {
        if (!openMenu) return undefined;
        const onDown = (e) => {
            if (rootRef.current && !rootRef.current.contains(e.target)) setOpenMenu(null);
        };
        const onKey = (e) => { if (e.key === 'Escape') setOpenMenu(null); };
        document.addEventListener('mousedown', onDown);
        document.addEventListener('keydown', onKey);
        return () => {
            document.removeEventListener('mousedown', onDown);
            document.removeEventListener('keydown', onKey);
        };
    }, [openMenu]);

    const toggle = (name) => setOpenMenu((current) => (current === name ? null : name));
    const isDark = theme === 'dark';
    const name = currentUser.name || 'Student';

    return (
        <div ref={rootRef} className="relative shrink-0 flex items-center gap-0.5">
            <button
                type="button"
                onClick={() => toggle('bell')}
                aria-label="Notifications"
                aria-expanded={openMenu === 'bell'}
                title="Notifications"
                className={`${iconButton} relative hover:bg-surface-hover ${openMenu === 'bell' ? 'text-text-primary bg-surface-hover' : 'text-text-secondary hover:text-text-primary'}`}
            >
                <Bell size={17} strokeWidth={1.8} />
                {hasUnread && <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-accent ring-2 ring-page" />}
            </button>

            <button
                type="button"
                onClick={toggleTheme}
                aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
                title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
                className={`${iconButton} hidden sm:flex text-text-secondary hover:text-text-primary hover:bg-surface-hover`}
            >
                {isDark ? <Sun size={17} strokeWidth={1.8} /> : <Moon size={17} strokeWidth={1.8} />}
            </button>

            <button
                type="button"
                onClick={() => toggle('account')}
                aria-label="Account menu"
                aria-expanded={openMenu === 'account'}
                title="Account"
                className={`${iconButton} ml-0.5`}
            >
                <span className={`w-7.5 h-7.5 rounded-full flex items-center justify-center text-xs font-semibold uppercase bg-accent text-on-accent transition-shadow ${openMenu === 'account' ? 'ring-2 ring-accent/40 ring-offset-2 ring-offset-page' : ''}`}>
                    {name.charAt(0)}
                </span>
            </button>

            <AnimatePresence>
                {openMenu === 'bell' && (
                    <motion.div {...popover} className="absolute right-0 top-full mt-1.5 w-[min(20rem,calc(100vw-1rem))] p-1.5 rounded-2xl bg-elevated border border-border-default shadow-2xl z-40">
                        <div className="flex items-center justify-between pl-2.5 pr-1 py-1">
                            <span className="text-[13px] font-medium text-text-primary">Notifications</span>
                            <button
                                type="button"
                                onClick={markAllRead}
                                className="inline-flex items-center gap-1 h-7 px-2 rounded-lg text-xs text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
                            >
                                <Check size={13} />
                                Mark read
                            </button>
                        </div>
                        <ul className="cm-scroll max-h-72 overflow-y-auto">
                            {notifications.length === 0 && (
                                <li className="px-2.5 py-3 text-[13px] text-text-muted">No active notices right now.</li>
                            )}
                            {notifications.map((n) => (
                                <li key={n.id} className="flex gap-2.5 px-2.5 py-2 rounded-xl">
                                    <span className={`mt-1.5 w-1.5 h-1.5 shrink-0 rounded-full ${n.unread ? 'bg-accent' : 'bg-transparent'}`} />
                                    <span className="min-w-0">
                                        <span className={`block text-[13px] leading-snug ${n.unread ? 'text-text-primary' : 'text-text-secondary'}`}>{n.text}</span>
                                        <span className="block mt-0.5 text-[11px] text-text-muted">{n.time}</span>
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </motion.div>
                )}

                {openMenu === 'account' && (
                    <motion.div {...popover} role="menu" className="absolute right-0 top-full mt-1.5 w-56 p-1 rounded-2xl bg-elevated border border-border-default shadow-2xl z-40">
                        <div className="px-2.5 py-2 mb-1 border-b border-border-default">
                            <p className="text-[13px] font-medium text-text-primary truncate">{name}</p>
                            <p className="text-xs text-text-muted truncate">{currentUser.email || 'student@gnu.ac.in'}</p>
                        </div>
                        <button
                            type="button"
                            role="menuitem"
                            onClick={toggleTheme}
                            className="w-full flex items-center gap-2 h-8 px-2.5 rounded-lg text-[13px] text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
                        >
                            {isDark ? <Sun size={14} /> : <Moon size={14} />}
                            {isDark ? 'Light theme' : 'Dark theme'}
                        </button>
                        <button
                            type="button"
                            role="menuitem"
                            onClick={onLogout}
                            className="w-full flex items-center gap-2 h-8 px-2.5 rounded-lg text-[13px] text-status-danger hover:bg-status-danger/10 transition-colors cursor-pointer"
                        >
                            <LogOut size={14} />
                            Log out
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export default function StudentDashboard({ navigate, logout, theme, toggleTheme }) {
    const handleLogout = () => {
        if (logout) logout();
        else navigate('/login');
    };

    return (
        <div className="h-[100dvh] bg-page text-text-primary font-sans overflow-hidden">
            <ChatContainer
                onHome={() => navigate('/')}
                headerActions={<HeaderActions theme={theme} toggleTheme={toggleTheme} onLogout={handleLogout} />}
            />
        </div>
    );
}
