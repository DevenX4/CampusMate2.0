"""Programmes, semesters, courses and how courses are offered (official GUNI curriculum)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Column, ForeignKey, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base, ProvenanceMixin, TimestampMixin, in_list, provenance_constraints,
)

OFFERING_TYPES = ("regular", "elective", "audit", "open")
SLOT_KINDS = ("elective", "audit", "open")
PREREQUISITE_STRENGTHS = ("recommended", "required")


class Program(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "programs"
    __table_args__ = provenance_constraints()

    program_id: Mapped[str] = mapped_column(primary_key=True)
    program_name: Mapped[str]
    short_name: Mapped[str] = mapped_column(unique=True)
    degree_type: Mapped[str | None]
    university_id: Mapped[str] = mapped_column(ForeignKey("universities.university_id"))
    org_unit_id: Mapped[str | None] = mapped_column(ForeignKey("org_units.org_unit_id"))
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.department_id"))
    effective_year: Mapped[str | None]
    catalog_program_code: Mapped[str | None]
    catalog_program_name: Mapped[str | None]
    description: Mapped[str | None]  # official description: not present in the sources (NULL)
    synthetic_description: Mapped[str | None]
    coordinator_faculty_id: Mapped[str | None] = mapped_column(ForeignKey("faculty.faculty_id"))
    # Mixed-provenance record: which fields are official, derived or synthetic.
    field_provenance: Mapped[dict | None]
    additional_sources: Mapped[list | None] = mapped_column(JSONB)

    # Number of semesters and total credits are not stored: they are computed from `semesters`.
    semesters: Mapped[list["Semester"]] = relationship(
        back_populates="program", order_by="Semester.semester_number"
    )


class Semester(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "semesters"
    __table_args__ = (
        *provenance_constraints(),
        UniqueConstraint("program_id", "semester_number"),
        CheckConstraint("semester_number > 0", name="semester_number_positive"),
        CheckConstraint(
            "source_page_end IS NULL OR source_page_end >= source_page", name="page_range"
        ),
    )

    semester_id: Mapped[str] = mapped_column(primary_key=True)
    program_id: Mapped[str] = mapped_column(ForeignKey("programs.program_id"))
    semester_number: Mapped[int]
    semester_name: Mapped[str]
    # Totals exactly as printed on the official semester page.
    total_course: Mapped[int | None]
    total_regular_course: Mapped[int | None]
    total_elective_course: Mapped[int | None]
    total_open_course: Mapped[int | None]
    total_audit_course: Mapped[int | None]
    total_credits_th: Mapped[Decimal | None]
    total_credits_pr: Mapped[Decimal | None]
    total_credits: Mapped[Decimal | None]
    total_contact_hours: Mapped[Decimal | None]
    total_marks: Mapped[int | None]
    effective_year: Mapped[str | None]
    syllabus_date: Mapped[date | None]
    source_page_end: Mapped[int | None]  # some semester tables continue onto a second page

    program: Mapped[Program] = relationship(back_populates="semesters")
    offerings: Mapped[list["CourseOffering"]] = relationship(back_populates="semester")


class Course(ProvenanceMixin, TimestampMixin, Base):
    """A course identity. Its programme, semester and credits live in `course_offerings`."""

    __tablename__ = "courses"
    __table_args__ = provenance_constraints()

    course_id: Mapped[str] = mapped_column(primary_key=True)
    # Unique within this dataset. Codes are NOT globally unique across all GUNI programmes
    # (see data_quality_conflicts), so this must be revisited if other programmes are added.
    course_code: Mapped[str] = mapped_column(unique=True)
    course_name: Mapped[str]
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.department_id"))
    curriculum_status: Mapped[str]
    description: Mapped[str | None]  # official description: not present in the sources (NULL)
    synthetic_description: Mapped[str | None]
    delivered_by_note: Mapped[str | None]
    curriculum_note: Mapped[str | None]
    field_provenance: Mapped[dict | None]

    offerings: Mapped[list["CourseOffering"]] = relationship(back_populates="course")


class CreditSchemeMixin:
    """Teaching and examination scheme of one course row (or one elective slot)."""

    credit_th: Mapped[Decimal | None]
    credit_pr: Mapped[Decimal | None]
    credit_total: Mapped[Decimal | None]
    contact_hours: Mapped[Decimal | None]
    th_internal_max: Mapped[int | None]
    th_external_max: Mapped[int | None]
    pr_internal_max: Mapped[int | None]
    pr_external_max: Mapped[int | None]
    total_marks: Mapped[int | None]
    # Marks exactly as printed (e.g. "0/40"); kept verbatim for audit, never queried.
    exam_raw: Mapped[dict | None]


class ElectiveGroup(CreditSchemeMixin, ProvenanceMixin, TimestampMixin, Base):
    """An elective/audit/open slot in a semester; students pick one of its option courses.
    The options are the course_offerings whose elective_group_id points here (not stored twice)."""

    __tablename__ = "elective_groups"
    __table_args__ = (
        *provenance_constraints(),
        CheckConstraint(in_list("slot_kind", SLOT_KINDS), name="slot_kind"),
    )

    elective_group_id: Mapped[str] = mapped_column(primary_key=True)
    semester_id: Mapped[str] = mapped_column(ForeignKey("semesters.semester_id"))
    group_name: Mapped[str]
    slot_kind: Mapped[str]
    slot_title: Mapped[str | None]
    slot_no: Mapped[int | None]


class CourseOffering(CreditSchemeMixin, ProvenanceMixin, TimestampMixin, Base):
    """Course X is offered in semester Y (and therefore in that semester's programme)."""

    __tablename__ = "course_offerings"
    __table_args__ = (
        *provenance_constraints(),
        UniqueConstraint("course_id", "semester_id"),
        CheckConstraint(in_list("course_type", OFFERING_TYPES), name="course_type"),
        # Regular courses have no slot; elective/audit/open offerings always belong to one.
        CheckConstraint(
            "(course_type = 'regular') = (elective_group_id IS NULL)", name="slot_matches_type"
        ),
    )

    offering_id: Mapped[str] = mapped_column(primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id"))
    # The programme is not stored: it is the semester's programme.
    semester_id: Mapped[str] = mapped_column(ForeignKey("semesters.semester_id"))
    course_type: Mapped[str]
    elective_group_id: Mapped[str | None] = mapped_column(
        ForeignKey("elective_groups.elective_group_id")
    )
    credit_basis: Mapped[str | None]

    course: Mapped[Course] = relationship(back_populates="offerings")
    semester: Mapped[Semester] = relationship(back_populates="offerings")


class CoursePrerequisite(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "course_prerequisites"
    __table_args__ = (
        *provenance_constraints(),
        UniqueConstraint("course_id", "requires_course_id"),
        CheckConstraint("course_id <> requires_course_id", name="not_self"),
        CheckConstraint(in_list("strength", PREREQUISITE_STRENGTHS), name="strength"),
    )

    prerequisite_id: Mapped[str] = mapped_column(primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id"))
    requires_course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id"))
    strength: Mapped[str]
    academic_year: Mapped[str | None]


class CatalogListing(ProvenanceMixin, TimestampMixin, Base):
    """A course's appearance in the official 1.1.3 employability course list, per year."""

    __tablename__ = "catalog_listings"
    __table_args__ = provenance_constraints()

    course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id"), primary_key=True)
    academic_year: Mapped[str] = mapped_column(primary_key=True)
    catalog_program_code: Mapped[str] = mapped_column(primary_key=True)
    catalog_program_name: Mapped[str | None]
    listed_course_name: Mapped[str]
    catalog_sr_no: Mapped[int | None]


class CourseSharedListing(ProvenanceMixin, TimestampMixin, Base):
    """Another programme's syllabus page that lists the same course code."""

    __tablename__ = "course_shared_listings"
    __table_args__ = provenance_constraints()

    course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id"), primary_key=True)
    program_short_name: Mapped[str] = mapped_column(primary_key=True)
    listed_line: Mapped[str | None]
    title_matches: Mapped[bool | None]


class GradeBand(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "grade_bands"
    __table_args__ = provenance_constraints()

    grade_band_id: Mapped[str] = mapped_column(primary_key=True)
    marks_range: Mapped[str]
    grade_regular: Mapped[str]
    grade_point_regular: Mapped[int]
    grade_remedial: Mapped[str | None]
    grade_point_remedial: Mapped[int | None]


grade_band_programs = Table(
    "grade_band_programs",
    Base.metadata,
    Column(
        "grade_band_id", ForeignKey("grade_bands.grade_band_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("program_id", ForeignKey("programs.program_id", ondelete="CASCADE"), primary_key=True),
)


class DataQualityConflict(ProvenanceMixin, TimestampMixin, Base):
    """The same course code printed with different names in different official sources."""

    __tablename__ = "data_quality_conflicts"
    __table_args__ = provenance_constraints()

    conflict_id: Mapped[str] = mapped_column(primary_key=True)
    course_code: Mapped[str]
    syllabus_course_name: Mapped[str]
    catalog_course_name: Mapped[str]
    academic_year: Mapped[str | None]
    catalog_program_code: Mapped[str | None]
    catalog_program_name: Mapped[str | None]
    interpretation: Mapped[str | None]
