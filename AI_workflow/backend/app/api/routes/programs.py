from fastapi import APIRouter, Depends

from app.api.deps import NOT_FOUND, DbSession, require
from app.schemas.catalog import ProgramDetail, ProgramSummary, SemesterDetail
from app.services import organization

router = APIRouter(tags=["catalog"], dependencies=[Depends(require("catalog:read"))])


@router.get("/programs", response_model=list[ProgramSummary])
def list_programs(db: DbSession):
    return organization.list_programs(db)


@router.get("/programs/{program_id}", response_model=ProgramDetail, responses=NOT_FOUND)
def get_program(program_id: str, db: DbSession):
    """A programme with its semesters. Semester count and total credits are computed."""
    return organization.get_program(db, program_id)


@router.get("/semesters/{semester_id}", response_model=SemesterDetail, responses=NOT_FOUND)
def get_semester(semester_id: str, db: DbSession):
    """Everything offered in one semester: regular courses and elective/audit/open slots."""
    return organization.get_semester(db, semester_id)
