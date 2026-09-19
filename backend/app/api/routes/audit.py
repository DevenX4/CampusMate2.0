import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import AUTH_ERRORS, DbSession, Limit, Offset, require
from app.schemas.audit import AuditLogOut
from app.schemas.common import Page
from app.services import audit

router = APIRouter(prefix="/audit-logs", tags=["audit"], responses=AUTH_ERRORS,
                   dependencies=[Depends(require("audit:read"))])


@router.get("", response_model=Page[AuditLogOut])
def list_audit_logs(
    db: DbSession, action: str | None = None, entity_type: str | None = None,
    entity_id: str | None = None, actor_user_id: uuid.UUID | None = None,
    limit: Limit = 50, offset: Offset = 0,
):
    """Newest first. Read-only: the database rejects any change to audit entries."""
    return audit.list_logs(db, action=action, entity_type=entity_type, entity_id=entity_id,
                           actor_user_id=actor_user_id, limit=limit, offset=offset)
