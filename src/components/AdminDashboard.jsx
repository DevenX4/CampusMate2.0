import { useCallback, useEffect, useRef, useState } from 'react';
import {
    Building2, CalendarDays, GraduationCap, LayoutDashboard, LogOut, Menu, Moon, ScrollText,
    Search, Sun, Table2, UploadCloud, Users, UsersRound, X,
} from 'lucide-react';
import '../styles/admin.css';
import CampusBot from './brand/CampusBot';
import { adminFetch } from './admin/api';
import { CatalogProvider, useCatalog } from './admin/CatalogContext';
import RecordDrawer from './admin/RecordDrawer';
import GlobalSearch from './admin/GlobalSearch';
import OverviewSection from './admin/OverviewSection';
import UsersSection from './admin/UsersSection';
import KnowledgeSection from './admin/KnowledgeSection';
import AcademicsView from './admin/AcademicsView';
import PeopleView from './admin/PeopleView';
import CampusView from './admin/CampusView';
import ScheduleView from './admin/ScheduleView';
import GuidanceView from './admin/GuidanceView';
import AllTablesView from './admin/AllTablesView';

const NAV = [
    {
        group: 'Workspace',
        items: [
            { id: 'overview', label: 'Overview', icon: LayoutDashboard },
            { id: 'users', label: 'Users', icon: Users },
            { id: 'knowledge', label: 'Knowledge Base', icon: UploadCloud },
        ],
    },
    {
        group: 'Campus Data',
        items: [
            { id: 'academics', label: 'Academics', icon: GraduationCap },
            { id: 'people', label: 'People', icon: UsersRound },
            { id: 'campus', label: 'Campus', icon: Building2 },
            { id: 'schedule', label: 'Schedule and Notices', icon: CalendarDays },
            { id: 'guidance', label: 'Policies, FAQ, Grading', icon: ScrollText },
            { id: 'tables', label: 'All Tables', icon: Table2 },
        ],
    },
];

const ALL_ITEMS = NAV.flatMap((group) => group.items);
const initialSection = () => {
    const hash = window.location.hash.replace('#', '');
    return ALL_ITEMS.some((item) => item.id === hash) ? hash : 'overview';
};

function navCount(id, summary, stats) {
    const tables = summary.data?.tables;
    const count = (...names) => (tables ? names.reduce((sum, name) => sum + (tables.find((t) => t.name === name)?.count || 0), 0) : null);
    switch (id) {
        case 'users': return stats.totalUsers ?? null;
        case 'knowledge': return summary.data?.knowledgeIndex?.total ?? null;
        case 'academics': return count('courses');
        case 'people': return count('faculty');
        case 'campus': return count('rooms', 'laboratories', 'facilities');
        case 'schedule': return count('academic_calendar', 'notices');
        case 'guidance': return count('policies', 'faq', 'grading_scheme');
        case 'tables': return summary.data?.totals?.tables ?? null;
        default: return null;
    }
}

function AdminConsole({ navigate, logout, theme, toggleTheme }) {
    const { summary } = useCatalog();
    const currentUser = (() => {
        try { return JSON.parse(localStorage.getItem('currentUser') || '{}'); }
        catch { return {}; }
    })();

    const [section, setSection] = useState(initialSection);
    const [activeTable, setActiveTable] = useState(null);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [searchOpen, setSearchOpen] = useState(false);
    const [showAccountDropdown, setShowAccountDropdown] = useState(false);
    const [stats, setStats] = useState({});
    const accountRef = useRef(null);
    const contentRef = useRef(null);

    const loadStats = useCallback(async () => {
        try {
            const [uRes, kRes] = await Promise.all([
                adminFetch('/api/admin/users'),
                adminFetch('/api/admin/knowledge/files'),
            ]);
            const users = uRes.ok ? (await uRes.json()).users || [] : [];
            const files = kRes.ok ? (await kRes.json()).files || [] : [];
            setStats({
                totalUsers: users.length,
                students: users.filter(u => u.role === 'student').length,
                admins: users.filter(u => u.role === 'admin').length,
                verifiedUsers: users.filter(u => u.isVerified).length,
                unverifiedUsers: users.filter(u => !u.isVerified).length,
                knowledgeFiles: files.length,
                indexedFiles: files.filter(f => f.status === 'indexed').length,
            });
        } catch { /* noop */ }
    }, []);

    useEffect(() => { loadStats(); }, [loadStats]);

    useEffect(() => {
        function handler(e) {
            if (accountRef.current && !accountRef.current.contains(e.target)) setShowAccountDropdown(false);
        }
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    useEffect(() => {
        function onKey(e) {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                setSearchOpen(true);
            }
        }
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, []);

    const goTo = useCallback((id) => {
        setSection(id);
        setSidebarOpen(false);
        window.history.replaceState({}, '', `#${id}`);
        contentRef.current?.scrollTo?.(0, 0);
    }, []);

    const openTable = useCallback((name) => {
        setActiveTable(name);
        goTo('tables');
    }, [goTo]);

    const closeSearch = useCallback(() => setSearchOpen(false), []);
    const current = ALL_ITEMS.find((item) => item.id === section);

    return (
        <div className="adm-app font-sans">
            <div className="adm-scrim" data-open={sidebarOpen} onClick={() => setSidebarOpen(false)} />

            <aside className="adm-sidebar" data-open={sidebarOpen} aria-label="Admin navigation">
                <div className="adm-side-brand">
                    <button type="button" className="flex min-w-0 cursor-pointer items-center gap-2 border-0 bg-transparent p-0 text-text-primary" onClick={() => navigate('/')} title="CampusMate home">
                        <CampusBot size={28} mood="idle" title="CampusMate" />
                        <span className="adm-side-brand-text text-sm font-semibold tracking-tight">CampusMate <span className="font-normal adm-muted">Admin</span></span>
                    </button>
                    <button type="button" className="adm-icon-btn adm-menu-btn" onClick={() => setSidebarOpen(false)} aria-label="Close menu"><X size={15} /></button>
                </div>
                <nav className="adm-side-nav">
                    {NAV.map(({ group, items }) => (
                        <div key={group} className="contents">
                            <div className="adm-side-group">{group}</div>
                            {items.map(({ id, label, icon: Icon }) => {
                                const count = navCount(id, summary, stats);
                                return (
                                    <button
                                        key={id}
                                        type="button"
                                        className="adm-nav-item"
                                        aria-current={section === id ? 'page' : undefined}
                                        aria-label={label}
                                        title={label}
                                        onClick={() => goTo(id)}
                                    >
                                        <Icon size={15} />
                                        <span className="adm-nav-label">{label}</span>
                                        {count != null && <span className="adm-nav-count">{count}</span>}
                                    </button>
                                );
                            })}
                        </div>
                    ))}
                </nav>
                <div className="adm-side-foot">
                    <span className="adm-side-who min-w-0">
                        <span className="block truncate text-xs font-medium">U.V. Patel College of Engineering</span>
                        <span className="block truncate text-xs adm-muted">Ganpat University</span>
                    </span>
                </div>
            </aside>

            <div className="adm-main">
                <header className="adm-topbar">
                    <button type="button" className="adm-icon-btn adm-menu-btn" onClick={() => setSidebarOpen(true)} aria-label="Open menu"><Menu size={16} /></button>
                    <h1>{current?.label}</h1>
                    <button type="button" className="adm-search-trigger" onClick={() => setSearchOpen(true)} aria-label="Search all campus data">
                        <Search size={14} />
                        <span>Search all data</span>
                        <span className="adm-kbd">Ctrl K</span>
                    </button>
                    <button
                        type="button"
                        onClick={toggleTheme}
                        className="adm-icon-btn"
                        aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
                        title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
                    >
                        {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
                    </button>
                    <div className="relative" ref={accountRef}>
                        <button
                            type="button"
                            onClick={() => setShowAccountDropdown(p => !p)}
                            className="adm-icon-btn"
                            style={{ color: 'var(--accent)', background: 'var(--accent-muted)', fontWeight: 600, textTransform: 'uppercase' }}
                            aria-label="Account menu"
                            aria-expanded={showAccountDropdown}
                        >
                            {currentUser.name?.charAt(0) || 'A'}
                        </button>
                        {showAccountDropdown && (
                            <div className="adm-panel absolute right-0 z-40 mt-1.5 w-56 p-1.5" style={{ background: 'var(--bg-elevated)', boxShadow: 'var(--adm-shadow)' }}>
                                <div className="border-b border-border-default px-2 pb-2 pt-1">
                                    <p className="m-0 truncate text-xs font-semibold">{currentUser.name || 'Admin'}</p>
                                    <p className="m-0 truncate text-xs adm-muted">{currentUser.email || ''}</p>
                                    <span className="adm-tag mt-1.5" data-tone="accent">Administrator</span>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => { if (logout) logout(); else navigate('/portal/login'); }}
                                    className="adm-nav-item mt-1"
                                    style={{ color: 'var(--status-danger)', justifyContent: 'flex-start', padding: '0 8px' }}
                                >
                                    <LogOut size={14} /> Log out
                                </button>
                            </div>
                        )}
                    </div>
                </header>

                <main className="adm-content" ref={contentRef} data-lenis-prevent>
                    <div key={section} className="adm-page">
                        {section === 'overview' && <OverviewSection stats={stats} onNavigate={goTo} onOpenTable={openTable} />}
                        {section === 'users' && <UsersSection onChanged={loadStats} />}
                        {section === 'knowledge' && <KnowledgeSection onChanged={loadStats} />}
                        {section === 'academics' && <AcademicsView />}
                        {section === 'people' && <PeopleView />}
                        {section === 'campus' && <CampusView />}
                        {section === 'schedule' && <ScheduleView />}
                        {section === 'guidance' && <GuidanceView />}
                        {section === 'tables' && <AllTablesView table={activeTable} onSelect={setActiveTable} />}
                    </div>
                </main>
            </div>

            <RecordDrawer />
            {searchOpen && <GlobalSearch onClose={closeSearch} />}
        </div>
    );
}

export default function AdminDashboard(props) {
    return (
        <CatalogProvider>
            <AdminConsole {...props} />
        </CatalogProvider>
    );
}
