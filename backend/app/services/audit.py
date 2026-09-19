"""The audit trail: who did what, when, from where.

`record` only ADDS the row to the session. It is committed together with the action it
describes, so an action and its audit entry succeed or fail together.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.operations import AuditLog
from app.schemas.audit import AuditLogOut
from app.schemas.common import Page
from app.services.helpers import paginate


@dataclass(frozen=True)
class RequestContext:
    """Facts about the HTTP request that the audit log keeps (never passwords or tokens)."""

    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None


def list_logs(db: Session, *, action: str | None, entity_type: str | None, entity_id: str | None,
              actor_user_id: uuid.UUID | None, limit: int, offset: int) -> Page[AuditLogOut]:
    query = select(AuditLog).order_by(AuditLog.id.desc())
    for column, value in ((AuditLog.action, action), (AuditLog.entity_type, entity_type),
                          (AuditLog.entity_id, entity_id), (AuditLog.actor_user_id, actor_user_id)):
        if value is not None:
            query = query.where(column == value)
    return paginate(db, query, AuditLogOut, limit, offset)


def record(
    db: Session, action: str, *, actor_id: uuid.UUID | None, context: RequestContext,
    entity_type: str | None = None, entity_id: str | None = None, details: dict | None = None,
) -> None:
    db.add(AuditLog(
        action=action, actor_user_id=actor_id, entity_type=entity_type, entity_id=entity_id,
        request_id=context.request_id, ip_address=context.ip_address, details=details or {},
    ))
