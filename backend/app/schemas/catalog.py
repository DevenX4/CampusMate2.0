"""Response shapes for the read-only catalog API.

Rule: every object that describes an entity carries its trust level, either a full
`provenance` (summaries and details) or at least `source_type` (short references).
"""

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import FromORM, Provenance, SourceType

# --- short references to other entities --------------------------------------------------


class CourseRef(FromORM):
    course_id: str
    course_code: str
    course_name: str
    source_type: SourceType


class FacultyRef(FromORM):
    faculty_id: str
    name: str
    designation: str | None
    source_type: SourceType


class ProgramRef(FromORM):
    program_id: str
    short_name: str
    source_type: SourceType


class SemesterRef(FromORM):
    semester_id: str
    semester_number: int
    semester_name: str


class RoomRef(FromORM):
    room_id: str
    room_number: str
    source_type: SourceType


class LabRef(FromORM):
    lab_id: str
    lab_name: str
    source_type: SourceType


class Credits(BaseModel):
    theory: float | None
    practical: float | None
    total: float | None
    contact_hours: float | None

    @classmethod
    def of(cls, row) -> "Credits":
        return cls(theory=row.credit_th, practical=row.credit_pr,
                   total=row.credit_total, contact_hours=row.contact_hours)


class Marks(BaseModel):
    theory_internal_max: int | None
    theory_external_max: int | None
    practical_internal_max: int | None
    practical_external_max: int | None
    total: int | None

    @classmethod
    def of(cls, row) -> "Marks":
        return cls(theory_internal_max=row.th_internal_max, theory_external_max=row.th_external_max,
                   practical_internal_max=row.pr_internal_max,
                   practical_external_max=row.pr_external_max, total=row.total_marks)


# --- departments -------------------------------------------------------------------------


class DepartmentSummary(FromORM):
    department_id: str
    department_name: str
    short_name: str | None
    status: str
    provenance: Provenance


class DepartmentDetail(DepartmentSummary):
    university_id: str
    parent_org_unit_id: str | None
    parent_link_note: str | None
    head: FacultyRef | None
    office_room: RoomRef | None
    overview: str | None
    vision: str | None
    mission: list[str] | None
    focus_areas: list[str] | None
    contact: dict | None


# --- programmes and semesters ------------------------------------------------------------


class ProgramSummary(FromORM):
    program_id: str
    program_name: str
    short_name: str
    degree_type: str | None
    effective_year: str | None
    provenance: Provenance


class SemesterSummary(FromORM):
    semester_id: str
    semester_number: int
    semester_name: str
    total_credits: float | None
    provenance: Provenance


class ProgramDetail(ProgramSummary):
    university_id: str
    org_unit_id: str | None
    department_id: str | None
    catalog_program_code: str | None
    catalog_program_name: str | None
    description: str | None = Field(description="Official description (not present in the sources)")
    synthetic_description: str | None
    coordinator: FacultyRef | None
    field_provenance: dict | None = Field(description="Which fields are official, derived or synthetic")
    semesters: list[SemesterSummary]
    semester_count: int = Field(description="Computed: number of semesters")
    total_credits: float = Field(description="Computed: sum of the official semester totals (derived_official)")


class OfferingInSemester(BaseModel):
    offering_id: str
    course: CourseRef
    course_type: str
    credits: Credits
    marks: Marks
    provenance: Provenance


class ElectiveSlot(BaseModel):
    elective_group_id: str
    group_name: str
    slot_kind: str
    slot_title: str | None
    credits: Credits
    options: list[CourseRef] = Field(description="Students choose one of these courses")
    provenance: Provenance


class SemesterDetail(SemesterSummary):
    program: ProgramRef
    total_course: int | None
    total_credits_th: float | None
    total_credits_pr: float | None
    total_contact_hours: float | None
    total_marks: int | None
    effective_year: str | None
    syllabus_date: date | None
    regular_courses: list[OfferingInSemester]
    elective_slots: list[ElectiveSlot]


# --- courses -------------------------------------------------------------------------------


class CourseSummary(FromORM):
    course_id: str
    course_code: str
    course_name: str
    curriculum_status: str
    provenance: Provenance


class CourseOfferingOut(BaseModel):
    offering_id: str
    program: ProgramRef
    semester: SemesterRef
    course_type: str
    elective_group_id: str | None
    credits: Credits
    marks: Marks
    provenance: Provenance


class TeachingOut(BaseModel):
    faculty: FacultyRef
    semester_id: str
    role: str
    academic_year: str | None
    provenance: Provenance


class PrerequisiteOut(BaseModel):
    course: CourseRef
    strength: str
    provenance: Provenance


class CatalogListingOut(FromORM):
    academic_year: str
    catalog_program_code: str
    catalog_program_name: str | None
    listed_course_name: str
    provenance: Provenance


class CourseDetail(CourseSummary):
    department_id: str | None
    description: str | None = Field(description="Official description (not present in the sources)")
    synthetic_description: str | None
    delivered_by_note: str | None
    curriculum_note: str | None
    field_provenance: dict | None
    offerings: list[CourseOfferingOut]
    taught_by: list[TeachingOut]
    labs: list[LabRef]
    prerequisites: list[PrerequisiteOut]
    catalog_listings: list[CatalogListingOut]


# --- faculty -------------------------------------------------------------------------------


class FacultySummary(FromORM):
    faculty_id: str
    name: str
    designation: str | None
    department_id: str
    email: str | None
    status: str
    provenance: Provenance


class TeachingCourseOut(BaseModel):
    course: CourseRef
    semester_id: str
    role: str
    academic_year: str | None
    provenance: Provenance


class FacultyDetail(FacultySummary):
    qualification: str | None
    specialization: str | None
    office_room: RoomRef | None
    consultation_hours: str | None
    joining_year: int | None
    is_head_of_department: bool = Field(description="Computed from departments.head_faculty_id")
    research_areas: list[str]
    teaching: list[TeachingCourseOut]
