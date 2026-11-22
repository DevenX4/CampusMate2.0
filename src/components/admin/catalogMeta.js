// How each dataset is identified, titled and tabulated in the console.
export const TABLE_META = {
    university: { id: 'university_id', title: 'name', sub: 'short_name', cols: ['name', 'short_name', 'email', 'phone', 'website'] },
    org_units: { id: 'org_unit_id', title: 'name', sub: 'unit_type', cols: ['org_unit_id', 'name', 'unit_type', 'parent_id'] },
    departments: { id: 'department_id', title: 'department_name', sub: 'short_name', cols: ['department_name', 'short_name', 'head_faculty_id', 'status', 'academic_year'] },
    department_directory: { id: 'department_id', title: 'name', sub: 'hod_name', cols: ['name', 'hod_name', 'building', 'office', 'email'] },
    programs: { id: 'program_id', title: 'program_name', sub: 'short_name', cols: ['short_name', 'program_name', 'degree_type', 'number_of_semesters', 'total_credits', 'effective_year'] },
    semesters: { id: 'semester_id', title: 'semester_id', sub: 'semester_name', cols: ['semester_id', 'semester_name', 'total_course', 'total_credits', 'total_contact_hours', 'total_marks'] },
    courses: { id: 'course_id', title: 'course_name', sub: 'course_code', cols: ['course_code', 'course_name', 'course_type', 'credits', 'curriculum_status'] },
    course_offerings: { id: 'offering_id', title: 'offering_id', sub: 'course_type', cols: ['offering_id', 'course_id', 'semester_id', 'course_type', 'elective_group_id'] },
    course_prerequisites: { id: 'prerequisite_id', title: 'prerequisite_id', sub: 'strength', cols: ['prerequisite_id', 'course_id', 'requires_course_id', 'strength'] },
    elective_groups: { id: 'elective_group_id', title: 'slot_title', sub: 'group_name', cols: ['elective_group_id', 'slot_title', 'slot_kind', 'semester_id', 'slot_no'] },
    grading_scheme: { id: 'grade_band_id', title: (r) => `Grade ${r.grade_regular}`, sub: 'marks_range', cols: ['grade_band_id', 'marks_range', 'grade_regular', 'grade_point_regular', 'grade_remedial', 'grade_point_remedial'] },
    faculty: { id: 'faculty_id', title: 'name', sub: 'designation', cols: ['name', 'designation', 'specialization', 'email', 'status'] },
    teaching_assignments: { id: 'assignment_id', title: 'assignment_id', sub: 'role', cols: ['assignment_id', 'faculty_id', 'course_id', 'semester_id', 'role'] },
    research_areas: { id: 'research_area_id', title: 'name', sub: 'research_area_id', cols: ['research_area_id', 'name', 'department_id'] },
    buildings: { id: 'building_id', title: 'name', sub: 'code', cols: ['building_id', 'name', 'code', 'floors', 'description'] },
    rooms: { id: 'room_id', title: (r) => r.label || r.room_number, sub: 'room_number', cols: ['room_number', 'label', 'room_type', 'building_id', 'floor'] },
    laboratories: { id: 'lab_id', title: 'lab_name', sub: 'room_number', cols: ['lab_name', 'building', 'room_number', 'capacity', 'opening_hours', 'status'] },
    facilities: { id: 'facility_id', title: 'facility_name', sub: 'facility_type', cols: ['facility_name', 'facility_type', 'location', 'capacity', 'status'] },
    academic_calendar: { id: 'event_id', title: 'title', sub: 'event_type', cols: ['event_id', 'title', 'event_type', 'start_date', 'end_date', 'term'] },
    notices: { id: 'notice_id', title: 'title', sub: 'category', cols: ['notice_id', 'title', 'category', 'date', 'expiry_date', 'status'] },
    policies: { id: 'policy_id', title: 'title', sub: 'category', cols: ['policy_id', 'title', 'category', 'effective_from', 'status'] },
    faq: { id: 'faq_id', title: 'question', sub: 'category', cols: ['faq_id', 'question', 'category', 'status'] },
    data_quality_conflicts: { id: 'conflict_id', title: 'conflict_id', sub: 'course_code', cols: ['conflict_id', 'course_code', 'syllabus_course_name', 'catalog_course_name', 'academic_year'] },
};

export const SOURCE_META = {
    official: { label: 'Official', tone: 'official', color: 'var(--adm-src-official)', hint: 'Taken directly from an official university document.' },
    derived_official: { label: 'Derived', tone: 'derived', color: 'var(--adm-src-derived)', hint: 'Worked out from official documents.' },
    synthetic: { label: 'Sample', tone: 'sample', color: 'var(--adm-src-sample)', hint: 'Sample data for demonstration. Not an official record.' },
};

export const SOURCE_ORDER = ['official', 'derived_official', 'synthetic'];

export const sourceInfo = (type) => SOURCE_META[type] || { label: 'Unlabelled', tone: 'neutral', color: 'var(--text-muted)', hint: 'No source type recorded.' };

const ID_PREFIXES = [
    ['COURSE-', 'courses'],
    ['FAC-', 'faculty'],
    ['ROOM-', 'rooms'],
    ['LAB-', 'laboratories'],
    ['FCL-', 'facilities'],
    ['POLICY-', 'policies'],
    ['CAL-', 'academic_calendar'],
    ['NOTICE-', 'notices'],
    ['PROG-', 'programs'],
    ['SEM-', 'semesters'],
    ['DEPT-', 'department_directory'],
    ['EGRP-', 'elective_groups'],
    ['RA-', 'research_areas'],
    ['BLDG-', 'buildings'],
    ['FAQ-', 'faq'],
];

export function tableForId(value) {
    if (typeof value !== 'string') return null;
    const hit = ID_PREFIXES.find(([prefix]) => value.startsWith(prefix));
    return hit ? hit[1] : null;
}

export function recordId(table, record) {
    const key = TABLE_META[table]?.id;
    return key ? record?.[key] : undefined;
}

function readField(record, field) {
    if (typeof field === 'function') return field(record);
    return record?.[field];
}

export function recordTitle(table, record) {
    const meta = TABLE_META[table];
    const value = meta ? readField(record, meta.title) : null;
    return value == null || value === '' ? String(recordId(table, record) ?? 'Record') : String(value);
}

export function recordSubtitle(table, record) {
    const meta = TABLE_META[table];
    const value = meta ? readField(record, meta.sub) : null;
    return value == null ? '' : humanValue(value);
}

const ACRONYMS = { id: 'ID', ids: 'IDs', hod: 'HOD', th: 'Theory', pr: 'Practical', faq: 'FAQ', url: 'URL' };

export function humanKey(key) {
    const words = String(key).split('_').map((word) => ACRONYMS[word] || word);
    const text = words.join(' ');
    return text.charAt(0).toUpperCase() + text.slice(1);
}

export function humanValue(value) {
    if (typeof value !== 'string') return String(value);
    if (/^[a-z]+(_[a-z]+)*$/.test(value)) {
        const text = value.replace(/_/g, ' ');
        return text.charAt(0).toUpperCase() + text.slice(1);
    }
    return value;
}

const haystacks = new WeakMap();

export function matchesQuery(record, query) {
    if (!query) return true;
    let hay = haystacks.get(record);
    if (!hay) {
        hay = JSON.stringify(record).toLowerCase();
        haystacks.set(record, hay);
    }
    return query.toLowerCase().split(/\s+/).filter(Boolean).every((term) => hay.includes(term));
}

export function countBy(rows, read) {
    const counts = {};
    for (const row of rows) {
        const key = read(row) ?? 'unknown';
        counts[key] = (counts[key] || 0) + 1;
    }
    return counts;
}

const pad = (n) => String(n).padStart(2, '0');

export function todayISO(now = new Date()) {
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function formatDate(iso, options = { day: 'numeric', month: 'short', year: 'numeric' }) {
    if (!iso) return 'Not set';
    const date = new Date(`${String(iso).slice(0, 10)}T00:00:00`);
    return Number.isNaN(date.getTime()) ? String(iso) : date.toLocaleDateString('en-IN', options);
}

/** A notice counts as active only while its expiry date has not passed. */
export function noticeStatus(notice, today = todayISO()) {
    const stored = notice?.status || 'unknown';
    if (stored === 'active' && notice.expiry_date && notice.expiry_date < today) {
        return { status: 'expired', stale: true, stored };
    }
    return { status: stored, stale: false, stored };
}
