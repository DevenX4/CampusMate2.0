import { useDeferredValue, useEffect, useMemo, useState } from 'react';
import { useCatalog, useTables } from './CatalogContext';
import { countBy, humanValue, matchesQuery } from './catalogMeta';
import { DataBoundary, EmptyState, FilterChips, SearchField, Skeleton, SourceTag, StatStrip } from './ui';

const TABLES = ['programs', 'semesters', 'course_offerings', 'courses', 'elective_groups', 'teaching_assignments', 'course_prerequisites', 'faculty'];
const TYPE_ORDER = { regular: 0, elective: 1, open: 2, audit: 3 };
const TYPE_TONE = { regular: 'neutral', elective: 'accent', open: 'derived', audit: 'warning' };

function useAcademicIndex(data) {
    return useMemo(() => {
        const courses = new Map(data.courses.map((row) => [row.course_id, row]));
        const faculty = new Map(data.faculty.map((row) => [row.faculty_id, row]));
        const groups = new Map(data.elective_groups.map((row) => [row.elective_group_id, row]));
        const teaching = new Map();
        for (const row of data.teaching_assignments) {
            const key = `${row.semester_id}|${row.course_id}`;
            if (!teaching.has(key)) teaching.set(key, []);
            teaching.get(key).push(row);
        }
        const prerequisites = new Map();
        for (const row of data.course_prerequisites) {
            if (!prerequisites.has(row.course_id)) prerequisites.set(row.course_id, []);
            prerequisites.get(row.course_id).push(row);
        }
        return { courses, faculty, groups, teaching, prerequisites };
    }, [data]);
}

function buildRows(offerings, index) {
    return offerings.map((offering) => {
        const course = index.courses.get(offering.course_id);
        const scheme = offering.credit_scheme || course?.credit_scheme || {};
        const assignments = index.teaching.get(`${offering.semester_id}|${offering.course_id}`) || [];
        const needs = index.prerequisites.get(offering.course_id) || [];
        return {
            offering,
            course,
            scheme,
            credits: scheme.credit_total ?? course?.credits ?? null,
            type: offering.course_type || course?.course_type || 'unknown',
            group: offering.elective_group_id ? index.groups.get(offering.elective_group_id) : null,
            assignments: assignments.map((row) => ({ ...row, person: index.faculty.get(row.faculty_id) })),
            needs: needs.map((row) => ({ ...row, required: index.courses.get(row.requires_course_id) })),
        };
    });
}

function groupRows(rows) {
    const buckets = new Map();
    for (const row of rows) {
        const key = row.group ? row.group.elective_group_id : `type:${row.type}`;
        if (!buckets.has(key)) buckets.set(key, { key, group: row.group, type: row.type, rows: [] });
        buckets.get(key).rows.push(row);
    }
    const list = [...buckets.values()];
    list.forEach((bucket) => bucket.rows.sort((a, b) => String(a.course?.course_code).localeCompare(String(b.course?.course_code))));
    return list.sort((a, b) => {
        if (!a.group !== !b.group) return a.group ? 1 : -1;
        if (a.group && b.group) return (a.group.slot_no ?? 0) - (b.group.slot_no ?? 0);
        return (TYPE_ORDER[a.type] ?? 9) - (TYPE_ORDER[b.type] ?? 9);
    });
}

function CourseRow({ row, onOpen }) {
    const { course, scheme, credits, type, assignments, needs } = row;
    const open = () => course && onOpen(course);
    return (
        <tr data-click="true" tabIndex={0} onClick={open} onKeyDown={(e) => { if (e.key === 'Enter') open(); }}>
            <td className="adm-mono adm-strong whitespace-nowrap">{course?.course_code || row.offering.course_id}</td>
            <td className="adm-strong"><span className="adm-clip adm-clip-wide" title={course?.course_name}>{course?.course_name || 'Course not found'}</span></td>
            <td className="adm-right adm-num whitespace-nowrap">
                {credits ?? 'Not set'}
                {(scheme.credit_th != null || scheme.credit_pr != null) && <span className="adm-muted adm-hide-sm"> ({scheme.credit_th ?? 0}+{scheme.credit_pr ?? 0})</span>}
            </td>
            <td className="adm-hide-sm"><span className="adm-tag" data-tone={TYPE_TONE[type] || 'neutral'}>{humanValue(type)}</span></td>
            <td className="adm-hide-md">
                {needs.length === 0 ? <span className="adm-muted">None</span> : (
                    <span className="adm-mono" title={needs.map((item) => item.required?.course_name).filter(Boolean).join(', ')}>
                        {needs.map((item) => item.required?.course_code || item.requires_course_id).join(', ')}
                    </span>
                )}
            </td>
            <td className="adm-hide-sm">
                {assignments.length === 0 ? <span className="adm-muted">Unassigned</span> : (
                    <span className="adm-clip" style={{ maxWidth: 220 }} title={assignments.map((item) => `${item.person?.name || item.faculty_id} (${humanValue(item.role)})`).join(', ')}>
                        {assignments.map((item) => item.person?.name || item.faculty_id).join(', ')}
                    </span>
                )}
            </td>
            <td className="adm-hide-md"><SourceTag type={course?.source_type || row.offering.source_type} /></td>
        </tr>
    );
}

export default function AcademicsView() {
    const { openRecord } = useCatalog();
    const { data, loading, error, retry } = useTables(TABLES);
    const index = useAcademicIndex(data);
    const [programId, setProgramId] = useState(null);
    const [semesterId, setSemesterId] = useState(null);
    const [query, setQuery] = useState('');
    const [type, setType] = useState('all');
    const deferredQuery = useDeferredValue(query);

    const program = data.programs.find((row) => row.program_id === programId) || data.programs[0];
    const semesters = useMemo(
        () => data.semesters.filter((row) => row.program_id === program?.program_id).sort((a, b) => a.semester_number - b.semester_number),
        [data.semesters, program],
    );
    const semester = semesters.find((row) => row.semester_id === semesterId) || semesters[0];

    useEffect(() => { setType('all'); }, [semester?.semester_id]);

    const rows = useMemo(() => {
        if (!semester) return [];
        return buildRows(data.course_offerings.filter((row) => row.semester_id === semester.semester_id), index);
    }, [data.course_offerings, semester, index]);

    const typeCounts = useMemo(() => countBy(rows, (row) => row.type), [rows]);

    const visible = useMemo(() => rows.filter((row) => {
        if (type !== 'all' && row.type !== type) return false;
        if (!deferredQuery.trim()) return true;
        const names = row.assignments.map((item) => item.person?.name || '').join(' ');
        return matchesQuery({ code: row.course?.course_code, name: row.course?.course_name, names, group: row.group?.slot_title }, deferredQuery);
    }), [rows, type, deferredQuery]);

    const groups = useMemo(() => groupRows(visible), [visible]);

    const skeleton = (
        <div className="adm-panel p-3 flex flex-col gap-3">
            <Skeleton height={44} />
            {[1, 2, 3, 4, 5, 6].map((n) => <Skeleton key={n} />)}
        </div>
    );

    return (
        <>
            <p className="adm-page-desc">Pick a programme and semester to see its courses, electives, prerequisites and assigned faculty.</p>
            <DataBoundary loading={loading} error={error} retry={retry} skeleton={skeleton}>
                {!program ? <div className="adm-panel"><EmptyState title="No programmes in the data" /></div> : (
                    <>
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                            {data.programs.map((row) => (
                                <button
                                    key={row.program_id}
                                    type="button"
                                    className="adm-rail-item"
                                    style={{ maxWidth: 'none' }}
                                    aria-pressed={row.program_id === program.program_id}
                                    onClick={() => { setProgramId(row.program_id); setSemesterId(null); }}
                                >
                                    <b>{row.short_name}</b>
                                    <small style={{ whiteSpace: 'normal' }}>{row.program_name}</small>
                                    <small className="adm-num">{row.number_of_semesters} semesters, {row.total_credits} credits</small>
                                </button>
                            ))}
                        </div>

                        <div className="adm-rail" role="group" aria-label="Semester">
                            {semesters.map((row) => (
                                <button
                                    key={row.semester_id}
                                    type="button"
                                    className="adm-rail-item"
                                    aria-pressed={row.semester_id === semester?.semester_id}
                                    onClick={() => setSemesterId(row.semester_id)}
                                >
                                    <b>Sem {row.semester_roman}</b>
                                    <small className="adm-num">{row.total_credits} credits</small>
                                </button>
                            ))}
                        </div>

                        {semester && (
                            <StatStrip items={[
                                { label: 'Course slots', value: semester.total_course, sub: `${semester.total_regular_course} regular, ${semester.total_elective_course} elective` },
                                { label: 'Courses listed', value: rows.length, sub: 'Including elective options' },
                                { label: 'Credits', value: semester.total_credits, sub: `${semester.total_credits_th} theory, ${semester.total_credits_pr} practical` },
                                { label: 'Contact hours', value: semester.total_contact_hours, sub: 'Per week' },
                                { label: 'Total marks', value: semester.total_marks, sub: `Effective ${semester.effective_year}` },
                            ]} />
                        )}

                        <section className="adm-panel">
                            <div className="adm-panel-head">
                                <h2>{program.short_name}, {semester?.semester_name}</h2>
                                <SourceTag type={semester?.source_type} />
                                <span className="adm-spacer" />
                                <FilterChips
                                    label="Filter by course type"
                                    active={type}
                                    onChange={setType}
                                    options={[
                                        { id: 'all', label: 'All', count: rows.length },
                                        ...Object.keys(TYPE_ORDER).filter((key) => typeCounts[key]).map((key) => ({ id: key, label: humanValue(key), count: typeCounts[key] })),
                                    ]}
                                />
                            </div>
                            <div className="adm-panel-body" style={{ paddingBottom: 8 }}>
                                <SearchField value={query} onChange={setQuery} placeholder="Search code, course or faculty" />
                            </div>
                            {visible.length === 0 ? <EmptyState title="No courses match">Try a different search or type.</EmptyState> : (
                                <div className="adm-table-wrap">
                                    <table className="adm-table">
                                        <thead>
                                            <tr>
                                                <th>Code</th>
                                                <th>Course</th>
                                                <th className="adm-right">Credits</th>
                                                <th className="adm-hide-sm">Type</th>
                                                <th className="adm-hide-md">Prerequisites <SourceTag type="synthetic" /></th>
                                                <th className="adm-hide-sm">Faculty <SourceTag type="synthetic" /></th>
                                                <th className="adm-hide-md">Source</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {groups.map((bucket) => (
                                                <GroupRows key={bucket.key} bucket={bucket} onOpen={(course) => openRecord('courses', course)} />
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </section>
                    </>
                )}
            </DataBoundary>
        </>
    );
}

function GroupRows({ bucket, onOpen }) {
    const { group, type, rows } = bucket;
    const credits = group?.slot_scheme?.credit_total;
    return (
        <>
            <tr className="adm-group-row">
                <td colSpan={7}>
                    {group ? group.slot_title : `${humanValue(type)} courses`}
                    <span className="adm-muted font-normal">
                        {' '}{rows.length} {rows.length === 1 ? 'course' : group ? 'options' : 'courses'}{credits != null ? `, ${credits} credits` : ''}
                    </span>
                </td>
            </tr>
            {rows.map((row) => <CourseRow key={row.offering.offering_id} row={row} onOpen={onOpen} />)}
        </>
    );
}
