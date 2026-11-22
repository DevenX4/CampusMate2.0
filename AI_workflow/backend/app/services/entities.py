"""The global set of entity IDs (COURSE-2CEIT602, FAC-IT-003, DOC-FAQ-001, ...).

Dataset IDs are unique across all tables (dataset audit check 1), so one set of IDs answers
"is this string a real entity?" for any type.
"""

from sqlalchemy import Select, select, union_all
from sqlalchemy.orm import Session

from app.models import Base


def entity_tables() -> list:
    """Tables whose rows are entities: they carry provenance and a single-column ID."""
    return [t for t in Base.metadata.sorted_tables
            if "source_document_id" in t.c and len(t.primary_key.columns) == 1]


def entity_id_query() -> Select:
    documents = Base.metadata.tables["documents"]
    return union_all(
        *(select(next(iter(t.primary_key.columns)).label("id")) for t in entity_tables()),
        select(documents.c.document_id.label("id")),
    )


def known_entity_ids(db: Session) -> set[str]:
    return set(db.scalars(entity_id_query()))
