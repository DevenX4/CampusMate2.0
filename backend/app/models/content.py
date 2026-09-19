"""Policies, notices, FAQ and the academic calendar.

Their cross-references ("this notice mentions COURSE-2CEIT602 and LAB-IT-001") can point
at many entity types, so the *_links tables enforce the owner side with a foreign key and
store the target as a plain entity ID. Targets are validated by the seed process.
"""

from datetime import date

from sqlalchemy import CheckConstraint, Column, ForeignKey, Table, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base, ProvenanceMixin, TimestampMixin, in_list, provenance_constraints, status_constraint,
)

POLICY_STATUSES = ("active", "inactive", "superseded")
POLICY_RELATIONS = ("applies_to", "governs")


class Policy(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "policies"
    __table_args__ = (
        *provenance_constraints(),
        CheckConstraint(in_list("status", POLICY_STATUSES), name="status"),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="effective_range",
        ),
    )

    policy_id: Mapped[str] = mapped_column(primary_key=True)
    policy_number: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]
    category: Mapped[str | None]
    owner_faculty_id: Mapped[str | None] = mapped_column(ForeignKey("faculty.faculty_id"))
    summary: Mapped[str | None]
    clauses: Mapped[list[str] | None] = mapped_column(ARRAY(Text))  # ordered: clause 1, 2, ...
    effective_from: Mapped[date | None]
    effective_to: Mapped[date | None]
    status: Mapped[str] = mapped_column(server_default="active")
    academic_year: Mapped[str | None]


policy_links = Table(
    "policy_links",
    Base.metadata,
    Column("policy_id", ForeignKey("policies.policy_id", ondelete="CASCADE"), primary_key=True),
    Column("relation", Text, primary_key=True),
    Column("target_id", Text, primary_key=True),
    CheckConstraint(in_list("relation", POLICY_RELATIONS), name="relation"),
)


class Notice(ProvenanceMixin, TimestampMixin, Base):
    """A notice's active/expired status is NOT stored: it is computed from its dates.
    Only supersession is stored, because it is an event rather than a function of time."""

    __tablename__ = "notices"
    __table_args__ = (
        *provenance_constraints(),
        CheckConstraint(
            "expiry_date IS NULL OR effective_date IS NULL OR expiry_date >= effective_date",
            name="validity_range",
        ),
        CheckConstraint("supersedes_notice_id <> notice_id", name="not_self"),
    )

    notice_id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    notice_date: Mapped[date]
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.department_id"))
    category: Mapped[str | None]
    target_audience: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    content: Mapped[str]
    effective_date: Mapped[date | None]
    expiry_date: Mapped[date | None]
    # A notice can be replaced by at most one newer notice, hence unique.
    supersedes_notice_id: Mapped[str | None] = mapped_column(
        ForeignKey("notices.notice_id"), unique=True
    )
    academic_year: Mapped[str | None]


notice_links = Table(
    "notice_links",
    Base.metadata,
    Column("notice_id", ForeignKey("notices.notice_id", ondelete="CASCADE"), primary_key=True),
    Column("target_id", Text, primary_key=True),
)


class Faq(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "faq"
    __table_args__ = (*provenance_constraints(), status_constraint())

    faq_id: Mapped[str] = mapped_column(primary_key=True)
    category: Mapped[str | None]
    question: Mapped[str]
    answer: Mapped[str]
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.department_id"))
    status: Mapped[str] = mapped_column(server_default="active")
    academic_year: Mapped[str | None]


faq_links = Table(
    "faq_links",
    Base.metadata,
    Column("faq_id", ForeignKey("faq.faq_id", ondelete="CASCADE"), primary_key=True),
    Column("target_id", Text, primary_key=True),
)


class CalendarEvent(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "calendar_events"
    __table_args__ = (
        *provenance_constraints(),
        CheckConstraint("end_date >= start_date", name="date_range"),
    )

    event_id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    event_type: Mapped[str | None]
    start_date: Mapped[date]
    end_date: Mapped[date]
    term: Mapped[str | None]
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.department_id"))
    academic_year: Mapped[str | None]


# Which semesters an event applies to. Its programmes are those semesters' programmes.
calendar_event_semesters = Table(
    "calendar_event_semesters",
    Base.metadata,
    Column(
        "event_id", ForeignKey("calendar_events.event_id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "semester_id", ForeignKey("semesters.semester_id", ondelete="CASCADE"), primary_key=True
    ),
)
