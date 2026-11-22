import { useDeferredValue, useMemo, useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { useCatalog, useTables } from './CatalogContext';
import { countBy, formatDate, humanValue, matchesQuery } from './catalogMeta';
import { DataBoundary, DataTable, EmptyState, FilterChips, SearchField, SourceTag, StatusTag, Tabs } from './ui';

const TABLES = ['policies', 'faq', 'grading_scheme'];

function Policies({ rows, openRecord }) {
    const [query, setQuery] = useState('');
    const [category, setCategory] = useState('all');
    const deferred = useDeferredValue(query);
    const counts = useMemo(() => countBy(rows, (row) => row.category), [rows]);
    const visible = useMemo(() => rows.filter((row) => (category === 'all' || row.category === category) && matchesQuery(row, deferred.trim())), [rows, category, deferred]);
    const columns = useMemo(() => [
        { key: 'policy_number', label: 'Number', mono: true, hide: 'sm' },
        { key: 'title', label: 'Policy', strong: true, clip: true },
        { key: 'category', label: 'Category', hide: 'sm', render: (row) => <span className="adm-tag">{humanValue(row.category)}</span> },
        { key: 'clauses', label: 'Clauses', numeric: true, hide: 'md', value: (row) => row.clauses?.length || 0 },
        { key: 'effective_from', label: 'Effective', mono: true, hide: 'md', render: (row) => formatDate(row.effective_from) },
        { key: 'status', label: 'Status', render: (row) => <StatusTag status={row.status} /> },
        { key: 'source_type', label: 'Source', hide: 'sm', render: (row) => <SourceTag type={row.source_type} /> },
    ], []);
    return (
        <>
            <div className="adm-toolbar">
                <SearchField value={query} onChange={setQuery} placeholder="Search policies and clauses" />
                <label className="sr-only" htmlFor="adm-policy-category">Category</label>
                <select id="adm-policy-category" className="adm-input" style={{ width: 'auto' }} value={category} onChange={(e) => setCategory(e.target.value)}>
                    <option value="all">All categories ({rows.length})</option>
                    {Object.entries(counts).sort().map(([key, count]) => <option key={key} value={key}>{humanValue(key)} ({count})</option>)}
                </select>
            </div>
            <section className="adm-panel">
                <DataTable columns={columns} rows={visible} rowKey={(row) => row.policy_id} onRowClick={(row) => openRecord('policies', row)} />
            </section>
        </>
    );
}

function Faq({ rows, openRecord }) {
    const [query, setQuery] = useState('');
    const [category, setCategory] = useState('all');
    const deferred = useDeferredValue(query);
    const counts = useMemo(() => countBy(rows, (row) => row.category), [rows]);
    const visible = useMemo(() => rows.filter((row) => (category === 'all' || row.category === category) && matchesQuery(row, deferred.trim())), [rows, category, deferred]);
    return (
        <>
            <div className="adm-toolbar"><SearchField value={query} onChange={setQuery} placeholder="Search questions and answers" /></div>
            <FilterChips
                label="Filter by category"
                active={category}
                onChange={setCategory}
                options={[
                    { id: 'all', label: 'All', count: rows.length },
                    ...Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([key, count]) => ({ id: key, label: humanValue(key), count })),
                ]}
            />
            <section className="adm-panel overflow-hidden">
                {visible.length === 0 ? <EmptyState title="No questions match" /> : visible.map((row) => (
                    <details key={row.faq_id} className="adm-faq">
                        <summary>
                            <ChevronRight size={14} />
                            <span className="min-w-0 flex-1">{row.question}</span>
                            <span className="adm-tag adm-hide-sm">{humanValue(row.category)}</span>
                            <SourceTag type={row.source_type} />
                        </summary>
                        <div className="adm-faq-body">
                            <p className="m-0">{row.answer}</p>
                            <button type="button" className="adm-btn mt-2" style={{ height: 26, fontSize: 12 }} onClick={() => openRecord('faq', row)}>View full record</button>
                        </div>
                    </details>
                ))}
            </section>
        </>
    );
}

function Grading({ rows, openRecord }) {
    const columns = useMemo(() => [
        { key: 'marks_range', label: 'Marks', mono: true, strong: true, sortable: false },
        { key: 'grade_regular', label: 'Grade', strong: true, sortable: false },
        { key: 'grade_point_regular', label: 'Points', numeric: true },
        { key: 'grade_remedial', label: 'Remedial', sortable: false },
        { key: 'grade_point_remedial', label: 'Rem. points', numeric: true },
        { key: 'source_type', label: 'Source', hide: 'sm', sortable: false, render: (row) => <SourceTag type={row.source_type} /> },
    ], []);
    const source = rows[0];
    return (
        <>
            <section className="adm-panel">
                <div className="adm-panel-head"><h2>Grade bands</h2></div>
                <DataTable columns={columns} rows={rows} rowKey={(row) => row.grade_band_id} onRowClick={(row) => openRecord('grading_scheme', row)} />
            </section>
            {source && (
                <p className="m-0 text-xs adm-muted">
                    From {source.source_section}, page {source.source_page}. {source.document_version}.
                </p>
            )}
        </>
    );
}

export default function GuidanceView() {
    const { openRecord } = useCatalog();
    const { data, loading, error, retry } = useTables(TABLES);
    const [tab, setTab] = useState('policies');

    return (
        <>
            <p className="adm-page-desc">The rules and answers the assistant uses for student questions.</p>
            <Tabs
                label="Policies, FAQ and grading"
                active={tab}
                onChange={setTab}
                tabs={[
                    { id: 'policies', label: 'Policies', count: loading ? undefined : data.policies.length },
                    { id: 'faq', label: 'FAQ', count: loading ? undefined : data.faq.length },
                    { id: 'grading', label: 'Grading', count: loading ? undefined : data.grading_scheme.length },
                ]}
            />
            <DataBoundary loading={loading} error={error} retry={retry}>
                {tab === 'policies' && <Policies rows={data.policies} openRecord={openRecord} />}
                {tab === 'faq' && <Faq rows={data.faq} openRecord={openRecord} />}
                {tab === 'grading' && <Grading rows={data.grading_scheme} openRecord={openRecord} />}
            </DataBoundary>
        </>
    );
}
