from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: Literal["ok", "unreachable"]
    schema_revision: str | None  # migration the database is at
    expected_revision: str | None  # newest migration in the code
