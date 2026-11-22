"""Faculty members and what they teach (synthetic demo data in this dataset)."""

from sqlalchemy import CheckConstraint, Column, ForeignKey, ForeignKeyConstraint, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base, ProvenanceMixin, TimestampMixin, in_list, provenance_constraints, status_constraint,
)

TEACHING_ROLES = ("instructor", "coordinator", "lab_instructor")


class Faculty(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "faculty"
    __table_args__ = (*provenance_constraints(), status_constraint())

    faculty_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    designation: Mapped[str | None]
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.department_id"))
    qualification: Mapped[str | None]
    specialization: Mapped[str | None]
    email: Mapped[str | None] = mapped_column(unique=True)
    office_room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.room_id"))
    consultation_hours: Mapped[str | None]
    joining_year: Mapped[int | None]
    status: Mapped[str] = mapped_column(server_default="active")
    # "Is head of department" is not stored: it is departments.head_faculty_id.

    teaching_assignments: Mapped[list["TeachingAssignment"]] = relationship(
        back_populates="faculty"
    )


faculty_research_areas = Table(
    "faculty_research_areas",
    Base.metadata,
    Column("faculty_id", ForeignKey("faculty.faculty_id", ondelete="CASCADE"), primary_key=True),
    Column(
        "research_area_id", ForeignKey("research_areas.research_area_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class TeachingAssignment(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "teaching_assignments"
    __table_args__ = (
        *provenance_constraints(),
        # Explicit name: the generated one would exceed PostgreSQL's 63-character limit.
        UniqueConstraint(
            "faculty_id", "course_id", "semester_id", "academic_year",
            name="uq_teaching_assignments_faculty_offering_year",
        ),
        CheckConstraint(in_list("role", TEACHING_ROLES), name="role"),
        # A faculty member can only teach a course in a semester where it is actually offered.
        ForeignKeyConstraint(
            ["course_id", "semester_id"],
            ["course_offerings.course_id", "course_offerings.semester_id"],
        ),
    )

    assignment_id: Mapped[str] = mapped_column(primary_key=True)
    faculty_id: Mapped[str] = mapped_column(ForeignKey("faculty.faculty_id"))
    course_id: Mapped[str]
    semester_id: Mapped[str]
    role: Mapped[str]
    academic_year: Mapped[str | None]

    faculty: Mapped[Faculty] = relationship(back_populates="teaching_assignments")
