"""Building blocks shared by every API response."""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal["official", "derived_official", "synthetic"]


class FromORM(BaseModel):
    """Base for schemas built from database objects: fields are read from attributes."""

    model_config = ConfigDict(from_attributes=True)


class Provenance(BaseModel):
    """Where a fact comes from. 'synthetic' means demo data, never a Ganpat University fact."""

    source_type: SourceType
    document_id: str
    version_no: int
    page: int | None
    section: str | None


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """One page of a collection. `total` counts every match, not just this page."""

    items: list[T]
    total: int = Field(description="Number of matching items across all pages")
    limit: int
    offset: int


class ErrorBody(BaseModel):
    code: str = Field(examples=["not_found"])
    message: str
    details: list[dict] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
