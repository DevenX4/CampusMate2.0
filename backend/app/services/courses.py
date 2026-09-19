"""Courses: search and full detail (offerings, staff, labs, prerequisites, catalog listings)."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.campus import Laboratory, lab_courses
from app.models.curriculum import CatalogListing, Course, CourseOffering, CoursePrerequisite, Program, Semester
from app.models.people import Faculty, TeachingAssignment
from app.schemas.catalog import (
    CatalogListingOut, CourseDetail, CourseOfferingOut, CourseRef, CourseSummary, Credits,
    FacultyRef, LabRef, Marks, PrerequisiteOut, ProgramRef, SemesterRef, TeachingOut,
)
from app.schemas.common import Page
from app.services.errors import NotFoundError
from app.services.helpers import build, contains, paginate


def list_courses(
    db: Session, *, q: str | None = None, code: str | None = None, program_id: str | None = None,
    semester_id: str | None = None, course_type: str | None = None, limit: int = 20, offset: int = 0,
) -> Page[CourseSummary]:
    query = select(Course).order_by(Course.course_code)
    if q:
        query = query.where(or_(contains(Course.course_code, q), contains(Course.course_name, q)))
    if code:
        query = query.where(func.upper(Course.course_code) == code.upper())
    if program_id or semester_id or course_type:
        # "Offered in ..." filters go through course_offerings (a course has no program_id).
        offered = select(CourseOffering.course_id).join(Semester)
        if program_id:
            offered = offered.where(Semester.program_id == program_id)
        if semester_id:
            offered = offered.where(CourseOffering.semester_id == semester_id)
        if course_type:
            offered = offered.where(CourseOffering.course_type == course_type)
        query = query.where(Course.course_id.in_(offered))
    return paginate(db, query, CourseSummary, limit, offset)


def get_course(db: Session, course_id: str) -> CourseDetail:
    course = db.get(Course, course_id)
    if course is None:
        raise NotFoundError("Course", course_id)

    offerings = db.execute(
        select(CourseOffering, Semester, Program)
        .join(Semester, CourseOffering.semester_id == Semester.semester_id)
        .join(Program, Semester.program_id == Program.program_id)
        .where(CourseOffering.course_id == course_id)
        .order_by(Program.program_id, Semester.semester_number)
    ).all()
    teaching = db.execute(
        select(TeachingAssignment, Faculty).join(Faculty)
        .where(TeachingAssignment.course_id == course_id).order_by(Faculty.faculty_id)
    ).all()
    labs = db.scalars(
        select(Laboratory).join(lab_courses, lab_courses.c.lab_id == Laboratory.lab_id)
        .where(lab_courses.c.course_id == course_id).order_by(Laboratory.lab_id)
    ).all()
    prerequisites = db.execute(
        select(CoursePrerequisite, Course)
        .join(Course, Course.course_id == CoursePrerequisite.requires_course_id)
        .where(CoursePrerequisite.course_id == course_id).order_by(Course.course_code)
    ).all()
    listings = db.scalars(
        select(CatalogListing).where(CatalogListing.course_id == course_id)
        .order_by(CatalogListing.academic_year, CatalogListing.catalog_program_code)
    ).all()

    return build(
        CourseDetail, course,
        offerings=[
            build(CourseOfferingOut, o, program=ProgramRef.model_validate(p),
                  semester=SemesterRef.model_validate(s), credits=Credits.of(o), marks=Marks.of(o))
            for o, s, p in offerings
        ],
        taught_by=[build(TeachingOut, t, faculty=FacultyRef.model_validate(f)) for t, f in teaching],
        labs=[LabRef.model_validate(lab) for lab in labs],
        prerequisites=[build(PrerequisiteOut, p, course=CourseRef.model_validate(c)) for p, c in prerequisites],
        catalog_listings=[CatalogListingOut.model_validate(entry) for entry in listings],
    )
