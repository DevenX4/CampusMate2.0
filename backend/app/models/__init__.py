"""All ORM models. Importing this package registers every table on Base.metadata,
which is what Alembic compares against the database."""

from app.models import auth, campus, content, curriculum, documents, operations, organization, people
from app.models.base import Base

__all__ = [
    "Base", "auth", "campus", "content", "curriculum", "documents", "operations",
    "organization", "people",
]
