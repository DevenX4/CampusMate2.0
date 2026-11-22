from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]


class SystemInfo(BaseModel):
    """What this installation runs: shown in the UI header and the admin settings page."""

    version: str
    environment: str
    generation_provider: str
    generation_model: str
    embedding_model: str
    vector_store: str
    vector_store_version: str
    reranker_model: str
    ingestion_in_api: bool
    limits: dict[str, int]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: Literal["ok", "unreachable"]
    schema_revision: str | None  # migration the database is at
    expected_revision: str | None  # newest migration in the code
