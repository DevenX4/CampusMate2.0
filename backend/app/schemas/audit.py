import uuid
from datetime import datetime

from pydantic import IPvAnyAddress

from app.schemas.common import FromORM


class AuditLogOut(FromORM):
    id: int
    occurred_at: datetime
    actor_user_id: uuid.UUID | None
    action: str
    entity_type: str | None
    entity_id: str | None
    request_id: str | None
    ip_address: IPvAnyAddress | None
    details: dict
