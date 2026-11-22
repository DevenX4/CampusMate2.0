import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AlertTriangle, ArrowDown, ArrowUp, ChevronLeft, ChevronRight, ChevronsUpDown, Inbox, RefreshCw, Search, X } from 'lucide-react';
import { SOURCE_ORDER, countBy, sourceInfo } from './catalogMeta';

export function SourceTag({ type }) {
    const info = sourceInfo(type);
    return <span className="adm-tag" data-tone={info.tone} title={info.hint}>{info.label}</span>;
}

const STATUS_TONE = {
    active: 'success', verified: 'success', indexed: 'success', current: 'success', upcoming: 'accent',
    expired: 'neutral', past: 'neutral', superseded: 'warning', pending: 'warning', processing: 'accent', error: 'danger',
};

export function StatusTag({ status, children }) {
    const key = String(status || 'unknown').toLowerCase();
    const label = children || key.charAt(0).toUpperCase() + key.slice(1);
    return <span className="adm-tag" data-tone={STATUS_TONE[key] || 'neutral'}>{label}</span>;
}

export function Skeleton({ width = '100%', height = 12 }) {
    return <span className="adm-skel" style={{ width, height }} aria-hidden="true" />;
}

export function TableSkeleton({ rows = 8, columns = 5 }) {
    return (
        <div role="status" aria-label="Loading records">
            {Array.from({ length: rows }).map((_, row) => (
                <div key={row} className="grid items-center gap-4 border-b border-border-default/50 px-3" style={{ height: 36, gridTemplateColumns: `2fr repeat(${columns - 1}, 1fr)` }}>
                    {Array.from({ length: columns }).map((__, col) => <Skeleton key={col} width={`${88 - ((row + col) % 4) * 14}%`} />)}
                </div>
            ))}
        </div>
    );
}

export function EmptyState({ title = 'Nothing to show', children, icon: Icon = Inbox }) {
    return (
        <div className="adm-state">
            <Icon size={22} className="text-text-muted" />
            <p className="font-medium text-text-primary">{title}</p>
            {children && <p className="text-[12.5px]">{children}</p>}
        </div>
    );
}

export function ErrorState({ message, onRetry }) {
    return (
        <div className="adm-state" role="alert">
            <AlertTriangle size={22} className="text-status-danger" />
            <p className="font-medium text-text-primary">Could not load this data</p>
            <p className="text-[12.5px]">{message}</p>
            {onRetry && <button type="button" className="adm-btn" onClick={onRetry}><RefreshCw size={13} /> Try again</button>}
        </div>
    );
}

/** Standard wrapper for a view that depends on loaded datasets. */
export function DataBoundary({ loading, error, retry, skeleton, children }) {
    if (error) return <div className="adm-panel"><ErrorState message={error} onRetry={retry} /></div>;
    if (loading) return skeleton || <div className="adm-panel"><TableSkeleton /></div>;
    return children;
}

export function StatStrip({ items }) {
    return (
        <dl className="adm-stats m-0" data-cols={items.length}>
            {items.map((item) => (
                <div key={item.label} className="adm-stat">
                    <dt>{item.label}</dt>
                    <dd>{item.value ?? <Skeleton width={46} height={20} />}</dd>
                    {item.sub && <small>{item.sub}</small>}
                </div>
            ))}
        </dl>
    );
}

export function SearchField({ value, onChange, placeholder = 'Search', label }) {
    return (
        <div className="adm-search">
            <Search size={14} />
            <input
                type="search"
                className="adm-input"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder}
                aria-label={label || placeholder}
            />
            {value && (
                <button type="button" className="adm-search-clear" onClick={() => onChange('')} aria-label="Clear search"><X size={13} /></button>
            )}
        </div>
    );
}

export function Tabs({ tabs, active, onChange, label }) {
    return (
        <div className="adm-tabs" role="tablist" aria-label={label}>
            {tabs.map((tab) => (
                <button
                    key={tab.id}
                    type="button"
                    role="tab"
                    aria-selected={active === tab.id}
                    className="adm-tab"
                    onClick={() => onChange(tab.id)}
                >
                    {tab.label}
                    {tab.count != null && <span className="adm-nav-count">{tab.count}</span>}
                </button>
            ))}
        </div>
    );
}

export function FilterChips({ options, active, onChange, label }) {
    return (
        <div className="adm-chips" role="group" aria-label={label}>
            {options.map((option) => (
                <button
                    key={option.id}
                    type="button"
                    className="adm-chip"
                    aria-pressed={active === option.id}
                    onClick={() => onChange(option.id)}
                >
                    {option.label}{option.count != null && <b>{option.count}</b>}
                </button>
            ))}
        </div>
    );
}

export function SourceFilter({ rows, active, onChange }) {
    const counts = useMemo(() => countBy(rows, (row) => row?.source_type), [rows]);
    const types = [...SOURCE_ORDER.filter((type) => counts[type]), ...Object.keys(counts).filter((type) => !SOURCE_ORDER.includes(type))];
    if (types.length < 2) return null;
    return (
        <FilterChips
            label="Filter by source"
            active={active}
            onChange={onChange}
            options={[{ id: 'all', label: 'All sources', count: rows.length }, ...types.map((type) => ({ id: type, label: sourceInfo(type).label, count: counts[type] }))]}
        />
    );
}

function compareValues(a, b) {
    const emptyA = a == null || a === '';
    const emptyB = b == null || b === '';
    if (emptyA || emptyB) return emptyA === emptyB ? 0 : emptyA ? 1 : -1;
    if (typeof a === 'number' && typeof b === 'number') return a - b;
    return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
}

export function DataTable({ columns, rows, rowKey, onRowClick, pageSize = 25, emptyTitle = 'No matching records', emptyHint = 'Try a different search or filter.', minWidth }) {
    const [sort, setSort] = useState(null);
    const [page, setPage] = useState(0);

    useEffect(() => { setPage(0); }, [rows]);

    const sorted = useMemo(() => {
        if (!sort) return rows;
        const column = columns.find((c) => c.key === sort.key);
        if (!column) return rows;
        const read = column.sortValue || column.value || ((row) => row[column.key]);
        const factor = sort.dir === 'asc' ? 1 : -1;
        return [...rows].sort((x, y) => {
            const a = read(x);
            const b = read(y);
            if (a == null || a === '' || b == null || b === '') return compareValues(a, b);
            return compareValues(a, b) * factor;
        });
    }, [rows, sort, columns]);

    if (rows.length === 0) return <EmptyState title={emptyTitle}>{emptyHint}</EmptyState>;

    const pages = Math.max(1, Math.ceil(sorted.length / pageSize));
    const current = Math.min(page, pages - 1);
    const visible = sorted.slice(current * pageSize, (current + 1) * pageSize);

    const toggleSort = (key) => setSort((prev) => {
        if (!prev || prev.key !== key) return { key, dir: 'asc' };
        if (prev.dir === 'asc') return { key, dir: 'desc' };
        return null;
    });

    return (
        <>
            <div className="adm-table-wrap">
                <table className="adm-table" style={minWidth ? { minWidth } : undefined}>
                    <thead>
                        <tr>
                            {columns.map((column) => {
                                const dir = sort?.key === column.key ? sort.dir : null;
                                const Icon = dir === 'asc' ? ArrowUp : dir === 'desc' ? ArrowDown : ChevronsUpDown;
                                return (
                                    <th
                                        key={column.key}
                                        className={`${column.hide ? `adm-hide-${column.hide}` : ''} ${column.numeric ? 'adm-right' : ''}`}
                                        aria-sort={dir === 'asc' ? 'ascending' : dir === 'desc' ? 'descending' : 'none'}
                                    >
                                        {column.sortable === false ? column.label : (
                                            <button type="button" className="adm-sort" onClick={() => toggleSort(column.key)}>
                                                {column.label}
                                                <Icon size={11} className={dir ? 'text-accent' : 'opacity-50'} />
                                            </button>
                                        )}
                                    </th>
                                );
                            })}
                        </tr>
                    </thead>
                    <tbody>
                        {visible.map((row, index) => (
                            <tr
                                key={rowKey ? rowKey(row) : index}
                                data-click={onRowClick ? 'true' : undefined}
                                tabIndex={onRowClick ? 0 : undefined}
                                onClick={onRowClick ? () => onRowClick(row) : undefined}
                                onKeyDown={onRowClick ? (e) => { if (e.key === 'Enter') onRowClick(row); } : undefined}
                            >
                                {columns.map((column) => {
                                    const raw = column.value ? column.value(row) : row[column.key];
                                    const content = column.render ? column.render(row) : raw;
                                    const display = content == null || content === '' ? <span className="adm-muted">Not set</span> : content;
                                    return (
                                        <td
                                            key={column.key}
                                            className={`${column.hide ? `adm-hide-${column.hide}` : ''} ${column.strong ? 'adm-strong' : ''} ${column.numeric ? 'adm-right adm-num' : ''} ${column.mono ? 'adm-mono' : ''}`}
                                        >
                                            {column.clip ? <span className={`adm-clip ${column.clipClass || ''}`} title={typeof raw === 'string' ? raw : undefined}>{display}</span> : display}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="adm-pager">
                <span className="adm-num">
                    {current * pageSize + 1} to {Math.min((current + 1) * pageSize, sorted.length)} of {sorted.length}
                </span>
                {pages > 1 && (
                    <span className="flex items-center gap-1.5">
                        <button type="button" className="adm-icon-btn" style={{ width: 26, height: 26 }} disabled={current === 0} onClick={() => setPage(current - 1)} aria-label="Previous page"><ChevronLeft size={13} /></button>
                        <span className="adm-num">{current + 1} / {pages}</span>
                        <button type="button" className="adm-icon-btn" style={{ width: 26, height: 26 }} disabled={current >= pages - 1} onClick={() => setPage(current + 1)} aria-label="Next page"><ChevronRight size={13} /></button>
                    </span>
                )}
            </div>
        </>
    );
}

export function Drawer({ title, subtitle, badges, onClose, children, labelledBy = 'adm-drawer-title' }) {
    const panelRef = useRef(null);

    useEffect(() => {
        const previous = document.activeElement;
        panelRef.current?.querySelector('[data-drawer-close]')?.focus();
        const onKey = (e) => {
            if (e.key === 'Escape') {
                e.stopPropagation();
                onClose();
                return;
            }
            if (e.key !== 'Tab' || !panelRef.current) return;
            const focusable = panelRef.current.querySelectorAll('button:not(:disabled), input:not(:disabled), select, textarea, a[href], [tabindex="0"]');
            if (!focusable.length) return;
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
            else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
        };
        document.addEventListener('keydown', onKey);
        return () => {
            document.removeEventListener('keydown', onKey);
            if (previous && previous.isConnected) previous.focus?.();
        };
    }, [onClose]);

    return createPortal(
        <>
            <div className="adm-overlay" onClick={onClose} />
            <aside ref={panelRef} className="adm-drawer font-sans" role="dialog" aria-modal="true" aria-labelledby={labelledBy}>
                <div className="adm-drawer-head">
                    <div className="min-w-0 flex-1">
                        <h2 id={labelledBy}>{title}</h2>
                        {subtitle && <p className="m-0 mt-0.5 adm-mono adm-muted" style={{ overflowWrap: 'anywhere' }}>{subtitle}</p>}
                        {badges && <div className="mt-1.5 flex flex-wrap gap-1">{badges}</div>}
                    </div>
                    <button type="button" data-drawer-close className="adm-icon-btn" onClick={onClose} aria-label="Close details"><X size={15} /></button>
                </div>
                <div className="adm-drawer-body" data-lenis-prevent>{children}</div>
            </aside>
        </>,
        document.body,
    );
}
