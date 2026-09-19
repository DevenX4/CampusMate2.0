from fastapi import APIRouter, Depends

from app.api.deps import AUTH_ERRORS, DbSession, Limit, require
from app.schemas.content import CalendarEventOut, KnowledgeSource, NoticeOut, PolicyOut
from app.services import content

router = APIRouter(tags=["catalog"], responses=AUTH_ERRORS, dependencies=[Depends(require("catalog:read"))])


@router.get("/policies", response_model=list[PolicyOut])
def list_policies(db: DbSession):
    """Academic and department policies, with their clauses."""
    return content.list_policies(db)


@router.get("/notices", response_model=list[NoticeOut])
def list_notices(db: DbSession, limit: Limit = 20):
    """Department notices, newest first. `is_current`: in force today and not superseded."""
    return content.list_notices(db, limit)


@router.get("/calendar", response_model=list[CalendarEventOut])
def list_calendar(db: DbSession, semester_id: str | None = None):
    """Academic calendar events in date order, optionally for one semester."""
    return content.list_calendar(db, semester_id)


@router.get("/knowledge/sources", response_model=list[KnowledgeSource])
def knowledge_sources(db: DbSession):
    """The documents CampusMate can answer from right now (active versions), with their size."""
    return content.knowledge_sources(db)
