"""Declarative base, constraint naming, and the column groups shared by many tables."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKeyConstraint, MetaData, Numeric, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Every constraint gets a predictable name. Alembic needs names to alter or drop
# constraints in later migrations; without a convention PostgreSQL invents them.
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}

SOURCE_TYPES = ("official", "derived_official", "synthetic")
RECORD_STATUSES = ("active", "inactive")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Python type -> PostgreSQL type used when a column does not name one explicitly.
    type_annotation_map = {
        str: Text,                                   # PostgreSQL TEXT: no arbitrary length limits
        datetime: DateTime(timezone=True),           # TIMESTAMPTZ
        date: Date,
        Decimal: Numeric(6, 2),                      # credits / hours: exact, never float rounding
        dict: JSONB,
    }


def in_list(column: str, values: tuple[str, ...]) -> str:
    """SQL for a CHECK constraint such as: status IN ('active', 'inactive')."""
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class TimestampMixin:
    # sort_order keeps these columns at the end of every table.
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), sort_order=900)
    # onupdate is applied by SQLAlchemy when a row is changed through the ORM.
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), sort_order=901
    )


class ProvenanceMixin:
    """Where a fact came from: its trust level and the exact document version and page."""

    source_type: Mapped[str] = mapped_column(sort_order=800)
    source_document_id: Mapped[str] = mapped_column(sort_order=801)
    source_version_no: Mapped[int] = mapped_column(sort_order=802)
    source_page: Mapped[int | None] = mapped_column(sort_order=803)
    source_section: Mapped[str | None] = mapped_column(sort_order=804)


def provenance_constraints() -> tuple:
    """Constraints every ProvenanceMixin table must include in its __table_args__."""
    return (
        CheckConstraint(in_list("source_type", SOURCE_TYPES), name="source_type"),
        CheckConstraint("source_page IS NULL OR source_page > 0", name="source_page_positive"),
        # A fact must cite a document version that actually exists.
        ForeignKeyConstraint(
            ["source_document_id", "source_version_no"],
            ["document_versions.document_id", "document_versions.version_no"],
        ),
    )


def status_constraint() -> CheckConstraint:
    return CheckConstraint(in_list("status", RECORD_STATUSES), name="status")
