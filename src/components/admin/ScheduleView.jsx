import { useDeferredValue, useMemo, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { useCatalog, useTables } from './CatalogContext';
import { countBy, formatDate, humanValue, matchesQuery, noticeStatus, todayISO } from './catalogMeta';
import { DataBoundary, DataTable, EmptyState, FilterChips, SearchField, SourceTag, StatStrip, StatusTag, Tabs } from './ui';

const TABLES = ['academic_calendar', 'notices'];

function whenIs(event, today) {
    const end = event.end_date || event.start_date;
    if (end < today) return 'past';
    if (event.start_date > today) return 'upcoming';
    return 'current';
}

const WHEN_LABEL = { past: 'Past', current: 'Happening now', upcoming: 'Upcoming' };

function CalendarTimeline({ events, openRecord }) {
    const today = todayISO();
    const [type, setType] = useState('all');
    const [when, setWhen] = useState('all');
    const [query, setQuery] = useState('');
    const deferred = useDeferredValue(query);

    const typeCounts = useMemo(() => countBy(events, (row) => row.event_type), [events]);
    const whenCounts = useMemo(() => countBy(events, (row) => whenIs(row, today)), [events, today]);

    const months = useMemo(() => {
        const visible = events
            .filter((row) => (type === 'all' || row.event_type === type) && (when === 'all' || whenIs(row, today) === when) && matchesQuery(row, deferred.trim()))
            .sort((a, b) => String(a.start_date).localeCompare(String(b.start_date)));
        const map = new Map();
        for (const row of visible) {
            const key = String(row.start_date).slice(0, 7);
            if (!map.has(key)) map.set(key, []);
            map.get(key).push(row);
        }
        return [...map.entries()];
    }, [events, type, when, deferred, today]);

    return (
        <>
            <div className="adm-toolbar">
                <SearchField value={query} onChange={setQuery} placeholder="Search events" />
                <FilterChips
                    label="Filter by timing"
                    active={when}
                    onChange={setWhen}
                    options={[
                        { id: 'all', label: 'All', count: events.length },
                        ...['current', 'upcoming', 'past'].filter((key) => whenCounts[key]).map((key) => ({ id: key, label: WHEN_LABEL[key], count: whenCounts[key] })),
                    ]}
                />
            </div>
            <FilterChips
                label="Filter by event type"
                active={type}
                onChange={setType}
                options={[
                    { id: 'all', label: 'All types' },
                    ...Object.entries(typeCounts).sort((a, b) => b[1] - a[1]).map(([key, count]) => ({ id: key, label: humanValue(key), count })),
                ]}
            />
            <section className="adm-panel overflow-hidden">
                {months.length === 0 ? <EmptyState title="No events match">Try a different filter.</EmptyState> : months.map(([month, rows]) => (
                    <div key={month}>
                        <div className="adm-tl-month">{formatDate(`${month}-01`, { month: 'long', year: 'numeric' })}</div>
                        {rows.map((row) => {
                            const state = whenIs(row, today);
                            const multi = row.end_date && row.end_date !== row.start_date;
                            return (
                                <button key={row.event_id} type="button" className="adm-tl-row" data-when={state} onClick={() => openRecord('academic_calendar', row)}>
                                    <span className="adm-mono adm-tl-date">
                                        {formatDate(row.start_date, { day: 'numeric', month: 'short' })}{multi ? ` to ${formatDate(row.end_date, { day: 'numeric', month: 'short' })}` : ''}
                                    </span>
                                    <span className="min-w-0">
                                        <span className="adm-list-title truncate">{row.title}</span>
                                        <span className="block truncate text-xs adm-muted">{humanValue(row.event_type)}, {row.term}</span>
                                    </span>
                                    <span className="flex items-center gap-1">
                                        <StatusTag status={state}>{WHEN_LABEL[state]}</StatusTag>
                                        <span className="adm-hide-sm"><SourceTag type={row.source_type} /></span>
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                ))}
            </section>
        </>
    );
}

function NoticesList({ notices, openRecord }) {
    const [status, setStatus] = useState('all');
    const [category, setCategory] = useState('all');
    const [query, setQuery] = useState('');
    const deferred = useDeferredValue(query);

    const decorated = useMemo(() => notices.map((row) => ({ row, ...noticeStatus(row) })), [notices]);
    const statusCounts = useMemo(() => countBy(decorated, (item) => item.status), [decorated]);
    const categoryCounts = useMemo(() => countBy(notices, (row) => row.category), [notices]);
    const staleCount = decorated.filter((item) => item.stale).length;

    const rows = useMemo(() => decorated.filter((item) => (status === 'all' || item.status === status)
        && (category === 'all' || item.row.category === category)
        && matchesQuery(item.row, deferred.trim())), [decorated, status, category, deferred]);

    const columns = useMemo(() => [
        { key: 'date', label: 'Date', mono: true, value: (item) => item.row.date, render: (item) => formatDate(item.row.date) },
        {
            key: 'title', label: 'Notice', strong: true, value: (item) => item.row.title,
            render: (item) => <span className="adm-clip adm-clip-wide" title={item.row.title}>{item.row.title}</span>,
        },
        { key: 'category', label: 'Category', hide: 'md', value: (item) => item.row.category, render: (item) => <span className="adm-tag">{humanValue(item.row.category)}</span> },
        { key: 'expiry', label: 'Expires', hide: 'md', mono: true, value: (item) => item.row.expiry_date, render: (item) => (item.row.expiry_date ? formatDate(item.row.expiry_date) : 'No expiry') },
        {
            key: 'status', label: 'Status', value: (item) => item.status,
            render: (item) => (
                <span className="flex flex-wrap items-center gap-1">
                    <StatusTag status={item.status} />
                    {item.stale && <span className="adm-tag" data-tone="warning" title={`Stored as active, but the expiry date ${item.row.expiry_date} has passed.`}>Stale</span>}
                </span>
            ),
        },
        { key: 'source', label: 'Source', hide: 'sm', sortable: false, render: (item) => <SourceTag type={item.row.source_type} /> },
    ], []);

    return (
        <>
            <StatStrip items={[
                { label: 'Active', value: statusCounts.active || 0, sub: 'Valid as of today' },
                { label: 'Expired', value: statusCounts.expired || 0, sub: staleCount ? `${staleCount} past expiry date` : 'Past expiry date' },
                { label: 'Superseded', value: statusCounts.superseded || 0, sub: 'Replaced by a newer notice' },
            ]} />
            {staleCount > 0 && (
                <div className="adm-banner">
                    <AlertTriangle size={15} />
                    <span><b className="font-semibold">{staleCount} notices</b> are stored as active but their expiry date has passed. They are counted as expired here and marked Stale.</span>
                </div>
            )}
            <div className="adm-toolbar">
                <SearchField value={query} onChange={setQuery} placeholder="Search notices" />
                <FilterChips
                    label="Filter by status"
                    active={status}
                    onChange={setStatus}
                    options={[
                        { id: 'all', label: 'All', count: notices.length },
                        ...['active', 'expired', 'superseded'].filter((key) => statusCounts[key]).map((key) => ({ id: key, label: humanValue(key), count: statusCounts[key] })),
                    ]}
                />
                <label className="sr-only" htmlFor="adm-notice-category">Category</label>
                <select id="adm-notice-category" className="adm-input" style={{ width: 'auto' }} value={category} onChange={(e) => setCategory(e.target.value)}>
                    <option value="all">All categories</option>
                    {Object.entries(categoryCounts).sort().map(([key, count]) => <option key={key} value={key}>{humanValue(key)} ({count})</option>)}
                </select>
            </div>
            <section className="adm-panel">
                <DataTable columns={columns} rows={rows} rowKey={(item) => item.row.notice_id} onRowClick={(item) => openRecord('notices', item.row)} />
            </section>
        </>
    );
}

export default function ScheduleView() {
    const { openRecord } = useCatalog();
    const { data, loading, error, retry } = useTables(TABLES);
    const [tab, setTab] = useState('calendar');

    return (
        <>
            <p className="adm-page-desc">The academic calendar as a timeline, and notices with their real status as of today.</p>
            <Tabs
                label="Schedule and notices"
                active={tab}
                onChange={setTab}
                tabs={[
                    { id: 'calendar', label: 'Calendar', count: loading ? undefined : data.academic_calendar.length },
                    { id: 'notices', label: 'Notices', count: loading ? undefined : data.notices.length },
                ]}
            />
            <DataBoundary loading={loading} error={error} retry={retry}>
                {tab === 'calendar'
                    ? <CalendarTimeline events={data.academic_calendar} openRecord={openRecord} />
                    : <NoticesList notices={data.notices} openRecord={openRecord} />}
            </DataBoundary>
        </>
    );
}
