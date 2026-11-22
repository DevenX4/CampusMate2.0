"""Faculty members (synthetic demo data in this dataset)."""

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.models.campus import Room
from app.models.curriculum import Course
from app.models.organization import Department, ResearchArea
from app.models.people import Faculty, TeachingAssignment, faculty_research_areas
from app.schemas.catalog import CourseRef, FacultyDetail, FacultySummary, RoomRef, TeachingCourseOut
from app.schemas.common import Page
from app.services.errors import NotFoundError
from app.services.helpers import build, contains, paginate


def list_faculty(
    db: Session, *, department_id: str | None = None, q: str | None = None,
    limit: int = 20, offset: int = 0,
) -> Page[FacultySummary]:
    query = select(Faculty).order_by(Faculty.faculty_id)
    if department_id:
        query = query.where(Faculty.department_id == department_id)
    if q:
        query = query.where(or_(contains(Faculty.name, q), contains(Faculty.specialization, q)))
    return paginate(db, query, FacultySummary, limit, offset)


def get_faculty(db: Session, faculty_id: str) -> FacultyDetail:
    member = db.get(Faculty, faculty_id)
    if member is None:
        raise NotFoundError("Faculty member", faculty_id)

    research_areas = db.scalars(
        select(ResearchArea.name)
        .join(faculty_research_areas, faculty_research_areas.c.research_area_id == ResearchArea.research_area_id)
        .where(faculty_research_areas.c.faculty_id == faculty_id).order_by(ResearchArea.name)
    ).all()
    teaching = db.execute(
        select(TeachingAssignment, Course).join(Course, Course.course_id == TeachingAssignment.course_id)
        .where(TeachingAssignment.faculty_id == faculty_id).order_by(Course.course_code)
    ).all()
    office = db.get(Room, member.office_room_id) if member.office_room_id else None

    return build(
        FacultyDetail, member,
        office_room=RoomRef.model_validate(office) if office else None,
        # Computed, not stored: someone is head if a department names them as its head.
        is_head_of_department=db.scalar(select(exists().where(Department.head_faculty_id == faculty_id))),
        research_areas=list(research_areas),
        teaching=[build(TeachingCourseOut, t, course=CourseRef.model_validate(c)) for t, c in teaching],
    )
