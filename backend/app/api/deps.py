"""Reusable endpoint parameters. `Annotated[...]` bundles a type with how FastAPI obtains
and validates it, so every endpoint declares e.g. `limit: Limit` the same way."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.common import ErrorResponse

DbSession = Annotated[Session, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=100, description="Maximum number of items to return")]
Offset = Annotated[int, Query(ge=0, description="Number of items to skip (for paging)")]
SearchText = Annotated[str | None, Query(min_length=1, max_length=100)]

NOT_FOUND = {404: {"model": ErrorResponse, "description": "No such resource"}}
