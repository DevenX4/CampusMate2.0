"""Step 4 of seeding: integrity checks, run inside the seed transaction.
Every check returns a list of problems; any problem means the whole seed is rolled back."""

from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import Base
from app.seed.source import SourceData, has_mojibake
from app.seed.transform import Rows
from app.services.entities import entity_id_query

TABLES = Base.metadata.tables
DOCUMENT_TABLES = ("documents", "document_versions", "document_entities")
# Columns holding an entity ID of any type (no foreign key possible, see models/content.py).
POLYMORPHIC_REFERENCES = {
    "policy_links": "target_id",
    "notice_links": "target_id",
    "faq_links": "target_id",
    "document_entities": "entity_id",
}


def validate(session: Session, src: SourceData, rows: Rows) -> list[str]:
    return [
        *check_row_counts(session, rows),
        *check_provenance(session),
        *check_references(session),
        *check_version_labels(src),
        *check_no_mojibake(rows),
    ]


def check_row_counts(session: Session, rows: Rows) -> list[str]:
    """The database holds exactly the dataset's rows: nothing missing, nothing stale."""
    seeded_docs = [d["document_id"] for d in rows["documents"]]
    problems = []
    for name, wanted in rows.items():
        table = TABLES[name]
        query = select(func.count()).select_from(table)
        if name in DOCUMENT_TABLES:  # admins may add other documents later; count only ours
            query = query.where(table.c.document_id.in_(seeded_docs))
        actual = session.scalar(query)
        if actual != len(wanted):
            problems.append(f"{name}: {actual} rows in the database, dataset has {len(wanted)}")
    return problems


def provenance_tables() -> list:
    return [t for t in Base.metadata.sorted_tables if "source_document_id" in t.c]


def check_provenance(session: Session) -> list[str]:
    """Official and derived-official facts must cite an OFFICIAL document and a page.
    Synthetic facts must cite a SYNTHETIC document, never an official one."""
    documents = TABLES["documents"]
    problems = []
    for table in provenance_tables():
        wrong = or_(
            and_(table.c.source_type.in_(["official", "derived_official"]),
                 or_(documents.c.source_type != "official", table.c.source_page.is_(None))),
            and_(table.c.source_type == "synthetic", documents.c.source_type != "synthetic"),
        )
        joined = table.join(documents, documents.c.document_id == table.c.source_document_id)
        bad = session.scalar(select(func.count()).select_from(joined).where(wrong))
        if bad:
            problems.append(f"{table.name}: {bad} rows whose source_type does not match the cited document")
    return problems


def check_references(session: Session) -> list[str]:
    """Every entity ID used in a polymorphic link must exist in some entity table."""
    known_ids = entity_id_query().subquery()
    problems = []
    for name, column in POLYMORPHIC_REFERENCES.items():
        col = TABLES[name].c[column]
        missing = session.scalars(select(col).where(col.not_in(select(known_ids.c.id))).distinct()).all()
        if missing:
            problems.append(f"{name}.{column}: unknown entity IDs {sorted(missing)[:5]}")
    return problems


def check_version_labels(src: SourceData) -> list[str]:
    """Records name the document version they came from; it must be version 1's label,
    which is the version every seeded record is linked to."""
    labels = {d["document_id"]: d["version"] for d in src.registry}
    problems = []
    for name, records in src.tables.items():
        bad = [r for r in records
               if "document_version" in r and r["document_version"] != labels[r["source_document"]]]
        if bad:
            problems.append(f"{name}: {len(bad)} records cite a version label that is not version 1")
    return problems


def check_no_mojibake(rows: Rows) -> list[str]:
    def strings(value: Any):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for v in value.values():
                yield from strings(v)
        elif isinstance(value, list):
            for v in value:
                yield from strings(v)

    return [
        f"{name}: garbled text remains: {s[:60]!r}"
        for name, table_rows in rows.items() for row in table_rows
        for s in strings(row) if has_mojibake(s)
    ]
