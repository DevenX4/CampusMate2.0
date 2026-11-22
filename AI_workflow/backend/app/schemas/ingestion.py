import uuid
from datetime import datetime

from app.schemas.common import FromORM


class IngestionJobOut(FromORM):
    id: uuid.UUID
    document_id: str
    version_no: int
    job_type: str
    status: str
    current_stage: str | None
    attempts: int
    chunk_count: int | None
    error_message: str | None
    error_detail: dict | None
    stage_timings: dict  # stage -> milliseconds
    requested_by: uuid.UUID | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
