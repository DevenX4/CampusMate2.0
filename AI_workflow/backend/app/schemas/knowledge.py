from pydantic import BaseModel, Field

from app.schemas.common import Provenance, SourceType


class RelatedEntity(BaseModel):
    id: str
    source_type: SourceType = Field(description="Trust level of the RELATIONSHIP (not of the entity)")
    type: str | None = None
    title: str | None = None


class KnowledgeItem(BaseModel):
    """One OKF item, generated from PostgreSQL."""

    id: str
    type: str
    title: str
    source_type: SourceType
    provenance: Provenance
    field_provenance: dict | None = None
    attributes: dict
    attribute_source_types: dict[str, SourceType] = Field(
        description="Attributes whose trust level differs from the record's source_type")
    relationships: dict[str, list[RelatedEntity]] = Field(
        description="Typed links, read from this entity's side, e.g. taught_by, offered_in")
    last_updated: str
