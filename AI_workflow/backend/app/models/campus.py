"""Physical campus: buildings, rooms, laboratories and facilities."""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Table, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base, ProvenanceMixin, TimestampMixin, provenance_constraints, status_constraint,
)


class Building(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "buildings"
    __table_args__ = provenance_constraints()

    building_id: Mapped[str] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    floors: Mapped[int | None]
    description: Mapped[str | None]


class Room(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "rooms"
    __table_args__ = provenance_constraints()

    room_id: Mapped[str] = mapped_column(primary_key=True)
    room_number: Mapped[str] = mapped_column(unique=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.building_id"))
    floor: Mapped[int | None]
    room_type: Mapped[str | None]
    label: Mapped[str | None]


class Laboratory(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "laboratories"
    __table_args__ = (
        *provenance_constraints(),
        status_constraint(),
        CheckConstraint("capacity IS NULL OR capacity > 0", name="capacity_positive"),
    )

    lab_id: Mapped[str] = mapped_column(primary_key=True)
    lab_name: Mapped[str] = mapped_column(unique=True)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.department_id"))
    # Building and floor are not stored here: they follow from the room.
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.room_id"))
    capacity: Mapped[int | None]
    equipment: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    responsible_faculty_id: Mapped[str | None] = mapped_column(ForeignKey("faculty.faculty_id"))
    opening_hours: Mapped[str | None]
    booking_contact: Mapped[str | None]
    status: Mapped[str] = mapped_column(server_default="active")


# Which courses hold their practicals in which lab (many-to-many).
lab_courses = Table(
    "lab_courses",
    Base.metadata,
    Column("lab_id", ForeignKey("laboratories.lab_id", ondelete="CASCADE"), primary_key=True),
    Column("course_id", ForeignKey("courses.course_id", ondelete="CASCADE"), primary_key=True),
)


class Facility(ProvenanceMixin, TimestampMixin, Base):
    __tablename__ = "facilities"
    __table_args__ = (
        *provenance_constraints(),
        status_constraint(),
        CheckConstraint("capacity IS NULL OR capacity > 0", name="capacity_positive"),
    )

    facility_id: Mapped[str] = mapped_column(primary_key=True)
    facility_name: Mapped[str] = mapped_column(unique=True)
    facility_type: Mapped[str | None]
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.department_id"))
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.room_id"))
    description: Mapped[str | None]
    capacity: Mapped[int | None]
    availability: Mapped[str | None]
    status: Mapped[str] = mapped_column(server_default="active")
