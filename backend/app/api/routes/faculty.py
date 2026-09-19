from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import NOT_FOUND, DbSession, Limit, Offset, SearchText, require
from app.schemas.catalog import FacultyDetail, FacultySummary
from app.schemas.common import Page
from app.services import faculty

router = APIRouter(prefix="/faculty", tags=["catalog"], dependencies=[Depends(require("catalog:read"))])


@router.get("", response_model=Page[FacultySummary])
def list_faculty(
    db: DbSession,
    department_id: str | None = None,
    q: Annotated[SearchText, Query(description="Search in name and specialization")] = None,
    limit: Limit = 20,
    offset: Offset = 0,
):
    """Faculty members. In this dataset they are all SYNTHETIC demo identities."""
    return faculty.list_faculty(db, department_id=department_id, q=q, limit=limit, offset=offset)


@router.get("/{faculty_id}", response_model=FacultyDetail, responses=NOT_FOUND)
def get_faculty(faculty_id: str, db: DbSession):
    return faculty.get_faculty(db, faculty_id)
