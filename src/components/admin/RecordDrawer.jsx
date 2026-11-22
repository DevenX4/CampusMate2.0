import { useEffect, useMemo } from 'react';
import { useCatalog } from './CatalogContext';
import { humanKey, humanValue, noticeStatus, recordId, recordSubtitle, recordTitle, tableForId } from './catalogMeta';
import { Drawer, SourceTag, StatusTag } from './ui';

const PROVENANCE_KEYS = new Set(['source_type', 'source_document', 'source_page', 'source_pages', 'source_section', 'document_version', 'academic_year', 'version', 'additional_sources', 'field_provenance']);

function collectIds(value, found = new Set()) {
    if (typeof value === 'string') {
        if (tableForId(value)) found.add(value);
    } else if (Array.isArray(value)) {
        value.forEach((item) => collectIds(item, found));
    } else if (value && typeof value === 'object') {
        Object.values(value).forEach((item) => collectIds(item, found));
    }
    return found;
}

function RefButton({ id }) {
    const { entityIndex, openRecord } = useCatalog();
    const entity = entityIndex.get(id);
    if (!entity) return <span className="adm-mono">{id}</span>;
    return (
        <button type="button" className="adm-ref" title={id} onClick={() => openRecord(entity.table, entity.record)}>
            {recordTitle(entity.table, entity.record)}
        </button>
    );
}

function FieldValue({ value, selfId }) {
    if (value === null || value === undefined || value === '') return <span className="adm-muted">Not recorded</span>;
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'number') return <span className="adm-num">{value}</span>;
    if (typeof value === 'string') {
        if (value !== selfId && tableForId(value) && /^[A-Z]+-[A-Za-z0-9-]+$/.test(value)) return <RefButton id={value} />;
        return value;
    }
    if (Array.isArray(value)) {
        if (value.length === 0) return <span className="adm-muted">None</span>;
        if (value.every((item) => typeof item !== 'object' || item === null)) {
            const long = value.some((item) => String(item).length > 60);
            if (long) {
                return <ul className="m-0 flex list-disc flex-col gap-1 pl-4">{value.map((item, i) => <li key={i}>{String(item)}</li>)}</ul>;
            }
            return (
                <div className="adm-val-list">
                    {value.map((item, i) => (typeof item === 'string' && tableForId(item) && item !== selfId
                        ? <RefButton key={i} id={item} />
                        : <span key={i} className="adm-val-item">{String(item)}</span>))}
                </div>
            );
        }
        return (
            <div className="flex flex-col gap-2">
                {value.map((item, i) => <FieldValue key={i} value={item} selfId={selfId} />)}
            </div>
        );
    }
    return (
        <dl className="adm-kv">
            {Object.entries(value).map(([key, item]) => (
                <div key={key} className="contents">
                    <dt>{humanKey(key)}</dt>
                    <dd><FieldValue value={item} selfId={selfId} /></dd>
                </div>
            ))}
        </dl>
    );
}

function FieldList({ record, keys, selfId }) {
    return (
        <dl className="adm-kv">
            {keys.map((key) => (
                <div key={key} className="contents">
                    <dt>{humanKey(key)}</dt>
                    <dd><FieldValue value={record[key]} selfId={selfId} /></dd>
                </div>
            ))}
        </dl>
    );
}

function RelatedSections({ table, record }) {
    const { tables, entityIndex, openRecord } = useCatalog();
    const assignments = tables.teaching_assignments?.records || [];
    const prerequisites = tables.course_prerequisites?.records || [];

    if (table === 'courses') {
        const taught = assignments.filter((row) => row.course_id === record.course_id);
        const needs = prerequisites.filter((row) => row.course_id === record.course_id);
        return (
            <>
                <section className="adm-drawer-section">
                    <h3>Assigned faculty <span className="adm-muted">({taught.length})</span></h3>
                    {taught.length === 0 ? <p className="m-0 adm-muted">No faculty assigned in the data.</p> : (
                        <div className="flex flex-col gap-1">
                            {taught.map((row) => (
                                <div key={row.assignment_id} className="flex flex-wrap items-center gap-2">
                                    <RefButton id={row.faculty_id} />
                                    <span className="adm-muted">{humanValue(row.role)}</span>
                                    <SourceTag type={row.source_type} />
                                </div>
                            ))}
                        </div>
                    )}
                </section>
                <section className="adm-drawer-section">
                    <h3>Prerequisites <span className="adm-muted">({needs.length})</span></h3>
                    {needs.length === 0 ? <p className="m-0 adm-muted">No prerequisites in the data.</p> : (
                        <div className="flex flex-col gap-1">
                            {needs.map((row) => (
                                <div key={row.prerequisite_id} className="flex flex-wrap items-center gap-2">
                                    <RefButton id={row.requires_course_id} />
                                    <span className="adm-muted">{humanValue(row.strength)}</span>
                                    <SourceTag type={row.source_type} />
                                </div>
                            ))}
                        </div>
                    )}
                </section>
            </>
        );
    }

    if (table === 'faculty') {
        const taught = assignments.filter((row) => row.faculty_id === record.faculty_id);
        return (
            <section className="adm-drawer-section">
                <h3>Courses taught <span className="adm-muted">({taught.length})</span></h3>
                {taught.length === 0 ? <p className="m-0 adm-muted">No teaching assignments in the data.</p> : (
                    <div className="flex flex-col gap-1">
                        {taught.map((row) => {
                            const course = entityIndex.get(row.course_id);
                            return (
                                <button
                                    key={row.assignment_id}
                                    type="button"
                                    className="adm-list-btn rounded"
                                    style={{ padding: '5px 6px' }}
                                    onClick={() => course && openRecord('courses', course.record)}
                                >
                                    <span className="adm-mono shrink-0">{course?.record.course_code || row.course_id}</span>
                                    <span className="min-w-0 flex-1 truncate text-text-primary">{course?.record.course_name || ''}</span>
                                    <span className="adm-muted shrink-0">{humanValue(row.role)}</span>
                                </button>
                            );
                        })}
                    </div>
                )}
            </section>
        );
    }

    return null;
}

export default function RecordDrawer() {
    const { selection, closeRecord, loadTable, summary } = useCatalog();
    const table = selection?.table;
    const record = selection?.record;

    const needed = useMemo(() => {
        if (!record) return [];
        const set = new Set();
        collectIds(record).forEach((id) => set.add(tableForId(id)));
        if (table === 'courses') ['teaching_assignments', 'course_prerequisites', 'faculty'].forEach((name) => set.add(name));
        if (table === 'faculty') ['teaching_assignments', 'courses'].forEach((name) => set.add(name));
        return [...set];
    }, [record, table]);

    useEffect(() => { needed.forEach((name) => loadTable(name)); }, [needed, loadTable]);

    if (!record) return null;

    const id = recordId(table, record);
    const label = summary.data?.tables?.find((item) => item.name === table)?.label || humanKey(table);
    const keys = Object.keys(record);
    const main = keys.filter((key) => !PROVENANCE_KEYS.has(key));
    const provenance = keys.filter((key) => PROVENANCE_KEYS.has(key));
    const notice = table === 'notices' ? noticeStatus(record) : null;
    const subtitle = recordSubtitle(table, record);

    return (
        <Drawer
            key={`${table}:${id}`}
            title={recordTitle(table, record)}
            subtitle={id && id !== recordTitle(table, record) ? id : subtitle}
            onClose={closeRecord}
            badges={(
                <>
                    <span className="adm-tag">{label}</span>
                    <SourceTag type={record.source_type} />
                    {notice && <StatusTag status={notice.status} />}
                    {record.contains_synthetic_fields && <span className="adm-tag" data-tone="sample" title="Some fields on this record are sample data. See field provenance.">Has sample fields</span>}
                </>
            )}
        >
            {notice?.stale && (
                <div className="adm-banner">
                    <span>Stored as active, but its expiry date of {record.expiry_date} has passed.</span>
                </div>
            )}
            <RelatedSections table={table} record={record} />
            <section className="adm-drawer-section">
                <h3>Record fields</h3>
                <FieldList record={record} keys={main} selfId={id} />
            </section>
            {provenance.length > 0 && (
                <section className="adm-drawer-section">
                    <h3>Source</h3>
                    <FieldList record={record} keys={provenance} selfId={id} />
                </section>
            )}
        </Drawer>
    );
}
