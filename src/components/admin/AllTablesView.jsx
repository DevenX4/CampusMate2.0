import { useDeferredValue, useEffect, useMemo, useState } from 'react';
import { useCatalog, useTables } from './CatalogContext';
import { TABLE_META, humanKey, humanValue, matchesQuery, recordId } from './catalogMeta';
import { DataBoundary, DataTable, ErrorState, SearchField, Skeleton, SourceFilter, SourceTag } from './ui';

function cellText(value) {
    if (value === null || value === undefined || value === '') return null;
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (Array.isArray(value)) return value.length ? `${value.length} items` : 'None';
    if (typeof value === 'object') return `${Object.keys(value).length} fields`;
    return typeof value === 'string' ? humanValue(value) : value;
}

function TableRecords({ table, info }) {
    const { openRecord } = useCatalog();
    const { data, loading, error, retry } = useTables([table]);
    const [query, setQuery] = useState('');
    const [source, setSource] = useState('all');
    const deferred = useDeferredValue(query);
    const rows = data[table];

    useEffect(() => { setQuery(''); setSource('all'); }, [table]);

    const visible = useMemo(() => rows.filter((row) => (source === 'all' || row.source_type === source) && matchesQuery(row, deferred.trim())), [rows, source, deferred]);

    const columns = useMemo(() => {
        const keys = TABLE_META[table]?.cols || Object.keys(rows[0] || {}).slice(0, 5);
        const built = keys.map((key, index) => ({
            key,
            label: humanKey(key),
            strong: index === 0,
            clip: true,
            hide: index > 2 ? 'md' : index > 1 ? 'sm' : undefined,
            numeric: rows.some((row) => typeof row[key] === 'number') && rows.every((row) => row[key] == null || typeof row[key] === 'number'),
            sortValue: (row) => row[key],
            value: (row) => cellText(row[key]),
        }));
        built.push({ key: 'source_type', label: 'Source', render: (row) => <SourceTag type={row.source_type} /> });
        return built;
    }, [table, rows]);

    return (
        <section className="adm-panel min-w-0">
            <div className="adm-panel-head">
                <h2>{info?.label || humanKey(table)}</h2>
                <span className="adm-nav-count">{visible.length === rows.length ? rows.length : `${visible.length} of ${rows.length}`}</span>
            </div>
            <div className="adm-panel-body flex flex-col gap-2" style={{ paddingBottom: 8 }}>
                {info?.note && <p className="m-0 text-xs adm-muted" style={{ maxWidth: '110ch' }}>{info.note}</p>}
                <div className="adm-toolbar">
                    <SearchField value={query} onChange={setQuery} placeholder={`Search ${(info?.label || table).toLowerCase()}`} />
                    <SourceFilter rows={rows} active={source} onChange={setSource} />
                </div>
            </div>
            <DataBoundary loading={loading} error={error} retry={retry}>
                <DataTable
                    columns={columns}
                    rows={visible}
                    rowKey={(row) => recordId(table, row) ?? JSON.stringify(row).slice(0, 80)}
                    onRowClick={(row) => openRecord(table, row)}
                />
            </DataBoundary>
        </section>
    );
}

export default function AllTablesView({ table, onSelect }) {
    const { summary, loadSummary } = useCatalog();
    const tables = useMemo(() => summary.data?.tables || [], [summary.data]);
    const active = table && tables.some((item) => item.name === table) ? table : tables[0]?.name;
    const info = tables.find((item) => item.name === active);

    const grouped = useMemo(() => {
        const map = new Map();
        for (const item of tables) {
            if (!map.has(item.group)) map.set(item.group, []);
            map.get(item.group).push(item);
        }
        return [...map.entries()];
    }, [tables]);

    if (summary.status === 'error') {
        return <div className="adm-panel"><ErrorState message={summary.error} onRetry={loadSummary} /></div>;
    }

    if (!summary.data) {
        return <div className="adm-panel p-3 flex flex-col gap-3">{[1, 2, 3, 4, 5, 6].map((n) => <Skeleton key={n} />)}</div>;
    }

    return (
        <>
            <p className="adm-page-desc">Every dataset the assistant uses. Search, sort, and select a row to see the complete record.</p>

            <div className="min-[1100px]:hidden">
                <label htmlFor="adm-table-picker" className="mb-1 block text-xs text-text-secondary">Dataset</label>
                <select id="adm-table-picker" className="adm-input" value={active} onChange={(e) => onSelect(e.target.value)}>
                    {grouped.map(([group, items]) => (
                        <optgroup key={group} label={group}>
                            {items.map((item) => <option key={item.name} value={item.name}>{item.label} ({item.count})</option>)}
                        </optgroup>
                    ))}
                </select>
            </div>

            <div className="adm-grid-2 adm-grid-side items-start">
                <nav className="adm-panel hidden overflow-hidden min-[1100px]:block" aria-label="Datasets">
                    {grouped.map(([group, items]) => (
                        <div key={group}>
                            <div className="adm-tl-month" style={{ fontWeight: 500, color: 'var(--text-secondary)', padding: '4px 12px' }}>{group}</div>
                            {items.map((item) => (
                                <button
                                    key={item.name}
                                    type="button"
                                    className="adm-list-btn"
                                    style={{ padding: '5px 12px' }}
                                    aria-pressed={item.name === active}
                                    onClick={() => onSelect(item.name)}
                                >
                                    <span className="min-w-0 flex-1 truncate">{item.label}</span>
                                    {item.error ? <span className="adm-tag" data-tone="danger">Error</span> : <span className="adm-nav-count">{item.count}</span>}
                                </button>
                            ))}
                        </div>
                    ))}
                </nav>
                {active && <TableRecords key={active} table={active} info={info} />}
            </div>
        </>
    );
}
