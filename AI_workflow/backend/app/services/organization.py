"""Departments, programmes and semesters."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campus import Room
from app.models.curriculum import Course, CourseOffering, ElectiveGroup, Program, Semester
from app.models.organization import Department
from app.models.people import Faculty
from app.schemas.catalog import (
    CourseRef, Credits, DepartmentDetail, DepartmentSummary, ElectiveSlot, FacultyRef, Marks,
    OfferingInSemester, ProgramDetail, ProgramRef, ProgramSummary, RoomRef, SemesterDetail,
    SemesterSummary,
)
from app.services.errors import NotFoundError
from app.services.helpers import build


def _optional(db: Session, model, key: str | None):
    return db.get(model, key) if key else None


def list_departments(db: Session) -> list[DepartmentSummary]:
    departments = db.scalars(select(Department).order_by(Department.department_name)).all()
    return [DepartmentSummary.model_validate(d) for d in departments]


def get_department(db: Session, department_id: str) -> DepartmentDetail:
    department = db.get(Department, department_id)
    if department is None:
        raise NotFoundError("Department", department_id)
    head = _optional(db, Faculty, department.head_faculty_id)
    office = _optional(db, Room, department.office_room_id)
    return build(
        DepartmentDetail, department,
        head=FacultyRef.model_validate(head) if head else None,
        office_room=RoomRef.model_validate(office) if office else None,
    )


def list_programs(db: Session) -> list[ProgramSummary]:
    programs = db.scalars(select(Program).order_by(Program.program_id)).all()
    return [ProgramSummary.model_validate(p) for p in programs]


def get_program(db: Session, program_id: str) -> ProgramDetail:
    program = db.get(Program, program_id)
    if program is None:
        raise NotFoundError("Program", program_id)
    semesters = program.semesters  # relationship, ordered by semester_number
    coordinator = _optional(db, Faculty, program.coordinator_faculty_id)
    return build(
        ProgramDetail, program,
        coordinator=FacultyRef.model_validate(coordinator) if coordinator else None,
        semesters=[SemesterSummary.model_validate(s) for s in semesters],
        # Computed, not stored: the programme total is the sum of the official semester totals.
        semester_count=len(semesters),
        total_credits=float(sum(s.total_credits or 0 for s in semesters)),
    )


def get_semester(db: Session, semester_id: str) -> SemesterDetail:
    semester = db.get(Semester, semester_id)
    if semester is None:
        raise NotFoundError("Semester", semester_id)

    offerings = db.execute(
        select(CourseOffering, Course).join(Course)
        .where(CourseOffering.semester_id == semester_id).order_by(Course.course_code)
    ).all()
    slots = db.scalars(
        select(ElectiveGroup).where(ElectiveGroup.semester_id == semester_id)
        .order_by(ElectiveGroup.slot_no, ElectiveGroup.elective_group_id)
    ).all()

    # A slot's options are the offerings that point at it (stored once, in course_offerings).
    options: dict[str, list[CourseRef]] = {}
    for offering, course in offerings:
        if offering.elective_group_id:
            options.setdefault(offering.elective_group_id, []).append(CourseRef.model_validate(course))

    return build(
        SemesterDetail, semester,
        program=ProgramRef.model_validate(semester.program),
        regular_courses=[
            build(OfferingInSemester, o, course=CourseRef.model_validate(c),
                  credits=Credits.of(o), marks=Marks.of(o))
            for o, c in offerings if o.course_type == "regular"
        ],
        elective_slots=[
            build(ElectiveSlot, g, credits=Credits.of(g), options=options.get(g.elective_group_id, []))
            for g in slots
        ],
    )
