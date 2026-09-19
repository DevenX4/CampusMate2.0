from fastapi import APIRouter, Depends

from app.api.deps import NOT_FOUND, DbSession, require
from app.schemas.catalog import DepartmentDetail, DepartmentSummary
from app.services import organization

router = APIRouter(prefix="/departments", tags=["catalog"], dependencies=[Depends(require("catalog:read"))])


@router.get("", response_model=list[DepartmentSummary])
def list_departments(db: DbSession):
    return organization.list_departments(db)


@router.get("/{department_id}", response_model=DepartmentDetail, responses=NOT_FOUND)
def get_department(department_id: str, db: DbSession):
    return organization.get_department(db, department_id)
