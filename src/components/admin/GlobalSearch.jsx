import { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Search } from 'lucide-react';
import { useCatalog, useTables } from './CatalogContext';
import { matchesQuery, recordId, recordSubtitle, recordTitle } from './catalogMeta';
import { EmptyState, ErrorState, Skeleton, SourceTag } from './ui';

const PER_GROUP = 6;

export default function GlobalSearch({ onClose }) {
    const { summary, openRecord } = useCatalog();
    const names = useMemo(() => (summary.data?.tables || []).filter((table) => !table.error).map((table) => table.name), [summary.data]);
    const { data, loading, error, retry } = useTables(names);
    const [query, setQuery] = useState('');
    const [activeIndex, setActiveIndex] = useState(0);
    const deferred = useDeferredValue(query.trim());
    const inputRef = useRef(null);
    const resultsRef = useRef(null);

    useEffect(() => {
        const previous = document.activeElement;
        inputRef.current?.focus();
        return () => { if (previous && previous.isConnected) previous.focus?.(); };
    }, []);

    const { groups, flat, total } = useMemo(() => {
        if (deferred.length < 2) return { groups: [], flat: [], total: 0 };
        const out = [];
        const items = [];
        let count = 0;
        for (const table of summary.data?.tables || []) {
            const rows = data[table.name] || [];
            const matches = rows.filter((row) => matchesQuery(row, deferred));
            if (!matches.length) continue;
            count += matches.length;
            const shown = matches.slice(0, PER_GROUP).map((record) => ({ table: table.name, record }));
            out.push({ name: table.name, label: table.label, total: matches.length, shown });
            items.push(...shown);
        }
        return { groups: out, flat: items, total: count };
    }, [deferred, data, summary.data]);

    useEffect(() => { setActiveIndex(0); }, [deferred]);

    useEffect(() => {
        resultsRef.current?.querySelector('[data-active="true"]')?.scrollIntoView({ block: 'nearest' });
    }, [activeIndex]);

    const choose = (item) => {
        onClose();
        openRecord(item.table, item.record);
    };

    const onKeyDown = (e) => {
        if (e.key === 'Escape') { e.preventDefault(); onClose(); }
        else if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIndex((i) => Math.min(i + 1, Math.max(flat.length - 1, 0))); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIndex((i) => Math.max(i - 1, 0)); }
        else if (e.key === 'Enter' && flat[activeIndex]) { e.preventDefault(); choose(flat[activeIndex]); }
    };

    let cursor = -1;

    return createPortal(
        <>
            <div className="adm-overlay" style={{ zIndex: 70 }} onClick={onClose} />
            <div className="adm-palette font-sans" role="dialog" aria-modal="true" aria-label="Search all campus data">
                <div className="adm-palette-input">
                    <Search size={16} />
                    <input
                        ref={inputRef}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={onKeyDown}
                        placeholder="Search courses, faculty, rooms, notices..."
                        aria-label="Search all campus data"
                    />
                    <button type="button" className="adm-kbd cursor-pointer" onClick={onClose}>Esc</button>
                </div>
                <div className="adm-palette-results" ref={resultsRef} data-lenis-prevent>
                    {error ? <ErrorState message={error} onRetry={retry} />
                        : loading ? (
                            <div className="flex flex-col gap-3 p-3" role="status" aria-label="Loading datasets">
                                {[1, 2, 3, 4].map((n) => <Skeleton key={n} width={`${90 - n * 12}%`} />)}
                            </div>
                        ) : deferred.length < 2 ? (
                            <EmptyState icon={Search} title={`Search all ${summary.data?.totals?.records ?? ''} records`}>
                                Type at least two characters. Try a course code, a faculty name or a room.
                            </EmptyState>
                        ) : groups.length === 0 ? (
                            <EmptyState title="No results">Nothing matches "{deferred}" in any dataset.</EmptyState>
                        ) : (
                            <>
                                <p className="m-0 px-3 pt-2 text-xs adm-muted" role="status">{total} results in {groups.length} datasets</p>
                                {groups.map((group) => (
                                    <div key={group.name}>
                                        <div className="adm-palette-group">
                                            <span>{group.label}</span>
                                            <span className="adm-num">{group.total > PER_GROUP ? `${PER_GROUP} of ${group.total}` : group.total}</span>
                                        </div>
                                        {group.shown.map((item) => {
                                            cursor += 1;
                                            const index = cursor;
                                            const key = `${item.table}:${recordId(item.table, item.record) ?? index}`;
                                            const subtitle = recordSubtitle(item.table, item.record);
                                            return (
                                                <button
                                                    key={key}
                                                    type="button"
                                                    className="adm-palette-item"
                                                    data-active={index === activeIndex}
                                                    onMouseEnter={() => setActiveIndex(index)}
                                                    onClick={() => choose(item)}
                                                >
                                                    <span className="min-w-0 flex-1">
                                                        <span className="adm-list-title truncate">{recordTitle(item.table, item.record)}</span>
                                                        {subtitle && <span className="block truncate text-xs adm-muted">{subtitle}</span>}
                                                    </span>
                                                    <SourceTag type={item.record?.source_type} />
                                                </button>
                                            );
                                        })}
                                    </div>
                                ))}
                            </>
                        )}
                </div>
            </div>
        </>,
        document.body,
    );
}

