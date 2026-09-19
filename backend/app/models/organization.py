"""University hierarchy: university -> org units (school, college) -> departments."""

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base, ProvenanceMixin, TimestampMixin, provenance_constraints, status_constraint,
)


class University(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "universities"
    __table_args__ = provenance_constraints()

    university_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    short_name: Mapped[str | None]
    address: Mapped[str | None]
    phone: Mapped[str | None]
    fax: Mapped[str | None]
    toll_free: Mapped[str | None]
    email: Mapped[str | None]
    website: Mapped[str | None]
    note: Mapped[str | None]


class OrgUnit(ProvenanceMixin, TimestampMixin, Base):
    """A school/faculty or college inside the university (e.g. SCHOOL-FET-001)."""

    __tablename__ = "org_units"
    __table_args__ = provenance_constraints()

    org_unit_id: Mapped[str] = mapped_column(primary_key=True)
    unit_type: Mapped[str]
    name: Mapped[str]
    university_id: Mapped[str] = mapped_column(ForeignKey("universities.university_id"))
    # NULL for a top-level unit directly under the university.
    parent_org_unit_id: Mapped[str | None] = mapped_column(ForeignKey("org_units.org_unit_id"))


class Department(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (*provenance_constraints(), status_constraint())

    department_id: Mapped[str] = mapped_column(primary_key=True)
    department_name: Mapped[str] = mapped_column(unique=True)
    short_name: Mapped[str | None]
    university_id: Mapped[str] = mapped_column(ForeignKey("universities.university_id"))
    parent_org_unit_id: Mapped[str | None] = mapped_column(ForeignKey("org_units.org_unit_id"))
    parent_link_note: Mapped[str | None]
    # departments -> faculty -> departments is a cycle. The constraint is created after
    # both tables exist (use_alter) and checked at COMMIT (deferred), so a department and
    # its head can be inserted in the same transaction in either order.
    head_faculty_id: Mapped[str | None] = mapped_column(
        ForeignKey("faculty.faculty_id", use_alter=True, deferrable=True, initially="DEFERRED")
    )
    office_room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.room_id"))
    overview: Mapped[str | None]
    vision: Mapped[str | None]
    mission: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    focus_areas: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    contact: Mapped[dict | None]  # small free-form contact block (emails, phone, hours)
    status: Mapped[str] = mapped_column(server_default="active")


class ResearchArea(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "research_areas"
    __table_args__ = (*provenance_constraints(), UniqueConstraint("department_id", "name"))

    research_area_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.department_id"))
