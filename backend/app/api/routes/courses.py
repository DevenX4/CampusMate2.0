from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.deps import NOT_FOUND, DbSession, Limit, Offset, SearchText
from app.schemas.catalog import CourseDetail, CourseSummary
from app.schemas.common import Page
from app.services import courses

router = APIRouter(prefix="/courses", tags=["catalog"])


@router.get("", response_model=Page[CourseSummary])
def list_courses(
    db: DbSession,
    q: Annotated[SearchText, Query(description="Search in course code and name, e.g. 'artificial'")] = None,
    code: Annotated[str | None, Query(description="Exact course code, e.g. 2CEIT602")] = None,
    program_id: Annotated[str | None, Query(description="Offered in this programme")] = None,
    semester_id: Annotated[str | None, Query(description="Offered in this semester")] = None,
    course_type: Literal["regular", "elective", "audit", "open"] | None = None,
    limit: Limit = 20,
    offset: Offset = 0,
):
    return courses.list_courses(db, q=q, code=code, program_id=program_id, semester_id=semester_id,
                                course_type=course_type, limit=limit, offset=offset)


@router.get("/{course_id}", response_model=CourseDetail, responses=NOT_FOUND)
def get_course(course_id: str, db: DbSession):
    """A course with its offerings and credits, teaching staff, labs, prerequisites and
    official catalog listings. Every part carries its own provenance."""
    return courses.get_course(db, course_id)
