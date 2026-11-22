import { useDeferredValue, useMemo, useState } from 'react';
import { useCatalog, useTables } from './CatalogContext';
import { countBy, matchesQuery } from './catalogMeta';
import { DataBoundary, DataTable, EmptyState, FilterChips, SearchField, SourceTag, Tabs } from './ui';

const TABLES = ['department_directory', 'faculty', 'teaching_assignments', 'courses', 'rooms'];

function Departments({ data, openRecord }) {
    const [query, setQuery] = useState('');
    const deferred = useDeferredValue(query);
    const rooms = useMemo(() => new Map(data.rooms.map((row) => [row.room_id, row])), [data.rooms]);
    const rows = useMemo(() => data.department_directory.filter((row) => matchesQuery(row, deferred.trim())), [data.department_directory, deferred]);

    return (
        <>
            <div className="adm-toolbar">
                <SearchField value={query} onChange={setQuery} placeholder="Search department or HOD" />
                <span className="adm-muted text-xs adm-num">{rows.length} of {data.department_directory.length}</span>
            </div>
            {rows.length === 0 ? <div className="adm-panel"><EmptyState title="No departments match" /></div> : (
                <div className="adm-cards">
                    {rows.map((row) => (
                        <button key={row.department_id} type="button" className="adm-card" onClick={() => openRecord('department_directory', row)}>
                            <span className="flex items-start justify-between gap-2">
                                <span className="adm-list-title">{row.name}</span>
                                <SourceTag type={row.source_type} />
                            </span>
                            <span className="mt-1 block text-text-primary">HOD: {row.hod_name || 'Not recorded'}</span>
                            <span className="mt-1 block text-xs">{row.building}{row.office ? `, ${rooms.get(row.office)?.room_number || row.office}` : ''}</span>
                            <span className="block truncate text-xs">{row.email}</span>
                            <span className="block text-xs adm-muted">{row.consultation_hours}</span>
                        </button>
                    ))}
                </div>
            )}
        </>
    );
}

function Faculty({ data, openRecord }) {
    const [query, setQuery] = useState('');
    const [role, setRole] = useState('all');
    const deferred = useDeferredValue(query);

    const taughtBy = useMemo(() => {
        const courses = new Map(data.courses.map((row) => [row.course_id, row]));
        const map = new Map();
        for (const row of data.teaching_assignments) {
            if (!map.has(row.faculty_id)) map.set(row.faculty_id, new Map());
            const course = courses.get(row.course_id);
            map.get(row.faculty_id).set(row.course_id, course?.course_code || row.course_id);
        }
        return map;
    }, [data.courses, data.teaching_assignments]);

    const seniority = (row) => {
        const text = row.designation || '';
        if (row.is_hod) return 'Head';
        if (/assistant/i.test(text)) return 'Assistant Professor';
        if (/associate/i.test(text)) return 'Associate Professor';
        if (/professor/i.test(text)) return 'Professor';
        return 'Other';
    };

    const counts = useMemo(() => countBy(data.faculty, seniority), [data.faculty]);
    const rows = useMemo(() => data.faculty.filter((row) => (role === 'all' || seniority(row) === role) && matchesQuery(row, deferred.trim())), [data.faculty, role, deferred]);

    const columns = useMemo(() => [
        {
            key: 'name', label: 'Name', strong: true,
            render: (row) => (
                <span className="block min-w-0">
                    <span className="block font-medium text-text-primary">{row.name}</span>
                    <span className="block text-xs adm-muted sm:hidden">{row.designation}</span>
                </span>
            ),
        },
        { key: 'designation', label: 'Designation', hide: 'sm', clip: true },
        { key: 'specialization', label: 'Specialisation', hide: 'md', clip: true },
        {
            key: 'taught', label: 'Courses', numeric: true,
            value: (row) => taughtBy.get(row.faculty_id)?.size || 0,
        },
        {
            key: 'codes', label: 'Teaches', hide: 'md', sortable: false,
            render: (row) => {
                const codes = [...(taughtBy.get(row.faculty_id)?.values() || [])];
                if (!codes.length) return <span className="adm-muted">None</span>;
                return <span className="adm-mono adm-clip" style={{ maxWidth: 210 }} title={codes.join(', ')}>{codes.join(', ')}</span>;
            },
        },
        { key: 'source_type', label: 'Source', hide: 'sm', render: (row) => <SourceTag type={row.source_type} /> },
    ], [taughtBy]);

    return (
        <>
            <div className="adm-toolbar">
                <SearchField value={query} onChange={setQuery} placeholder="Search name, subject or email" />
                <FilterChips
                    label="Filter by designation"
                    active={role}
                    onChange={setRole}
                    options={[
                        { id: 'all', label: 'All', count: data.faculty.length },
                        ...['Head', 'Professor', 'Associate Professor', 'Assistant Professor', 'Other'].filter((key) => counts[key]).map((key) => ({ id: key, label: key, count: counts[key] })),
                    ]}
                />
            </div>
            <section className="adm-panel">
                <DataTable columns={columns} rows={rows} rowKey={(row) => row.faculty_id} onRowClick={(row) => openRecord('faculty', row)} pageSize={30} />
            </section>
        </>
    );
}

export default function PeopleView() {
    const { openRecord } = useCatalog();
    const { data, loading, error, retry } = useTables(TABLES);
    const [tab, setTab] = useState('departments');

    return (
        <>
            <p className="adm-page-desc">Departments with their heads, and the faculty directory with the courses each person teaches.</p>
            <Tabs
                label="People"
                active={tab}
                onChange={setTab}
                tabs={[
                    { id: 'departments', label: 'Departments', count: loading ? undefined : data.department_directory.length },
                    { id: 'faculty', label: 'Faculty', count: loading ? undefined : data.faculty.length },
                ]}
            />
            <DataBoundary loading={loading} error={error} retry={retry}>
                {tab === 'departments' ? <Departments data={data} openRecord={openRecord} /> : <Faculty data={data} openRecord={openRecord} />}
            </DataBoundary>
        </>
    );
}
