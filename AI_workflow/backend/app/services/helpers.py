"""Small building blocks shared by the catalog services."""

from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import Session

from app.schemas.common import FromORM, Page

S = TypeVar("S", bound=BaseModel)


def build(schema: type[S], obj: object, **computed) -> S:
    """Create a response object: every schema field is copied from the same-named attribute of
    `obj` (a database row), except the fields passed in `computed` (related or derived values)."""
    copied = {
        name: getattr(obj, name)
        for name in schema.model_fields
        if name not in computed and hasattr(obj, name)
    }
    return schema.model_validate({**copied, **computed})


def contains(column, text: str) -> ColumnElement[bool]:
    """Case-insensitive "column contains text". The user's % and _ are escaped so they are
    matched literally instead of acting as wildcards. (The value itself is always sent as a
    bound parameter, so this is about correct matching, not SQL injection.)"""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.ilike(f"%{escaped}%", escape="\\")


def paginate(db: Session, query: Select, schema: type[FromORM], limit: int, offset: int) -> Page:
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.scalars(query.limit(limit).offset(offset)).all()
    return Page(items=[schema.model_validate(r) for r in rows], total=total, limit=limit, offset=offset)
