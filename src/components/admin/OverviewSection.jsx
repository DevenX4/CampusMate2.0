import { useMemo } from 'react';
import { AlertTriangle, ChevronRight, Database, UploadCloud, Users } from 'lucide-react';
import { useCatalog } from './CatalogContext';
import { SOURCE_ORDER, humanKey, sourceInfo } from './catalogMeta';
import { DataTable, ErrorState, Skeleton, StatStrip } from './ui';

function SourceBar({ counts, total, label }) {
    const types = [...SOURCE_ORDER.filter((type) => counts[type]), ...Object.keys(counts).filter((type) => !SOURCE_ORDER.includes(type))];
    return (
        <div>
            <div className="mb-1.5 flex items-baseline justify-between gap-2">
                <span className="font-medium text-text-primary">{label}</span>
                <span className="adm-num adm-muted text-xs">{total} records</span>
            </div>
            <div className="adm-stack" role="img" aria-label={`${label}: ${types.map((type) => `${counts[type]} ${sourceInfo(type).label}`).join(', ')}`}>
                {types.map((type) => (
                    <span key={type} style={{ width: `${(counts[type] / total) * 100}%`, background: sourceInfo(type).color }} title={`${sourceInfo(type).label}: ${counts[type]}`} />
                ))}
            </div>
            <ul className="adm-legend">
                {types.map((type) => (
                    <li key={type} title={sourceInfo(type).hint}>
                        <i style={{ background: sourceInfo(type).color }} />
                        {sourceInfo(type).label} <b>{counts[type]}</b>
                    </li>
                ))}
            </ul>
        </div>
    );
}

function CategoryBars({ counts }) {
    const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const max = entries[0]?.[1] || 1;
    return (
        <dl className="adm-bars">
            {entries.map(([category, count]) => (
                <div key={category} className="contents" title={`${humanKey(category)}: ${count}`}>
                    <dt>{humanKey(category)}</dt>
                    <dd><span className="adm-bar" style={{ width: `${(count / max) * 100}%` }} /></dd>
                    <dd className="adm-bar-value">{count}</dd>
                </div>
            ))}
        </dl>
    );
}

export default function OverviewSection({ stats, onNavigate, onOpenTable }) {
    const { summary, loadSummary } = useCatalog();
    const data = summary.data;
    const totals = data?.totals;
    const knowledge = data?.knowledgeIndex;

    const columns = useMemo(() => [
        { key: 'label', label: 'Dataset', strong: true },
        { key: 'group', label: 'Area', hide: 'sm' },
        { key: 'count', label: 'Records', numeric: true },
        {
            key: 'mix', label: 'Source', sortable: false,
            render: (row) => {
                if (row.error) return <span className="adm-tag" data-tone="danger">Unavailable</span>;
                return (
                    <span className="flex flex-wrap gap-1">
                        {SOURCE_ORDER.filter((type) => row.sourceTypes[type]).map((type) => (
                            <span key={type} className="adm-tag" data-tone={sourceInfo(type).tone} title={sourceInfo(type).hint}>
                                {sourceInfo(type).label} <span className="adm-num">{row.sourceTypes[type]}</span>
                            </span>
                        ))}
                    </span>
                );
            },
        },
    ], []);

    const sampleCount = totals?.sourceTypes?.synthetic || 0;

    return (
        <>
            <p className="adm-page-desc">Everything the assistant knows, counted directly from its data files.</p>

            <StatStrip items={[
                { label: 'Datasets', value: totals?.tables, sub: totals?.unavailableTables ? `${totals.unavailableTables} unavailable` : 'Structured tables' },
                { label: 'Structured records', value: totals?.records, sub: 'Across all datasets' },
                { label: 'Knowledge index', value: knowledge?.total, sub: knowledge?.error ? 'Could not be read' : 'Searchable entries' },
                { label: 'User accounts', value: stats.totalUsers, sub: stats.totalUsers != null ? `${stats.verifiedUsers} verified, ${stats.unverifiedUsers} pending` : ' ' },
                { label: 'Uploaded files', value: stats.knowledgeFiles, sub: stats.knowledgeFiles != null ? `${stats.indexedFiles} indexed` : ' ' },
            ]} />

            {summary.status === 'error' && <div className="adm-panel"><ErrorState message={summary.error} onRetry={loadSummary} /></div>}

            {sampleCount > 0 && (
                <div className="adm-banner">
                    <AlertTriangle size={15} />
                    <span>
                        <b className="font-semibold">{sampleCount} of {totals.records}</b> structured records are sample data used for demonstration, including faculty, notices, rooms and policies. Each one carries a Sample tag.
                    </span>
                </div>
            )}

            <div className="adm-grid-2">
                <section className="adm-panel">
                    <div className="adm-panel-head"><h2>Where the data comes from</h2></div>
                    <div className="adm-panel-body flex flex-col gap-5">
                        {data ? (
                            <>
                                <SourceBar label="Structured datasets" counts={totals.sourceTypes} total={totals.records} />
                                {knowledge?.total > 0 && <SourceBar label="Knowledge index" counts={knowledge.bySourceType} total={knowledge.total} />}
                            </>
                        ) : summary.status === 'loading' ? (
                            <div className="flex flex-col gap-3"><Skeleton height={10} /><Skeleton width="60%" /><Skeleton height={10} /><Skeleton width="60%" /></div>
                        ) : null}
                    </div>
                </section>

                <section className="adm-panel">
                    <div className="adm-panel-head"><h2>Knowledge index by category</h2></div>
                    <div className="adm-panel-body">
                        {knowledge && !knowledge.error ? <CategoryBars counts={knowledge.byCategory} /> : null}
                        {knowledge?.error && <p className="m-0 adm-muted">{knowledge.error}</p>}
                        {!knowledge && summary.status === 'loading' && (
                            <div className="flex flex-col gap-2.5">{[90, 34, 22, 18, 12].map((w) => <Skeleton key={w} width={`${w}%`} height={9} />)}</div>
                        )}
                    </div>
                </section>
            </div>

            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
                {[
                    { id: 'academics', icon: Database, title: 'Explore campus data', text: 'Programmes, people, rooms, notices' },
                    { id: 'users', icon: Users, title: 'Manage users', text: 'Reset, verify, delete, invite' },
                    { id: 'knowledge', icon: UploadCloud, title: 'Knowledge base', text: 'Upload campus documents' },
                ].map(({ id, icon: Icon, title, text }) => (
                    <button key={id} type="button" className="adm-card adm-card-row" onClick={() => onNavigate(id)}>
                        <Icon size={16} className="shrink-0 text-accent" />
                        <span className="min-w-0 flex-1">
                            <span className="adm-list-title">{title}</span>
                            <span className="block truncate text-xs adm-muted">{text}</span>
                        </span>
                        <ChevronRight size={14} className="shrink-0 adm-muted" />
                    </button>
                ))}
            </div>

            <section className="adm-panel">
                <div className="adm-panel-head"><h2>All datasets</h2><span className="adm-muted text-xs">Select a row to browse its records</span></div>
                {data ? (
                    <DataTable columns={columns} rows={data.tables} rowKey={(row) => row.name} onRowClick={(row) => onOpenTable(row.name)} pageSize={30} />
                ) : summary.status === 'loading' ? <div className="p-3 flex flex-col gap-3">{[1, 2, 3, 4, 5].map((n) => <Skeleton key={n} />)}</div> : null}
            </section>
        </>
    );
}
