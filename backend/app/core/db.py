"""Database access: one engine for the process, one Session per request.

- Engine: a pool of reusable connections to PostgreSQL (psycopg driver). Creating it does
  not connect; the first query does.
- Session: a unit of work. Changes are sent inside a transaction and made permanent by
  session.commit(), or undone by session.rollback().
"""

from collections.abc import Iterator
from functools import lru_cache

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import REPO_ROOT, get_settings

ALEMBIC_INI = REPO_ROOT / "backend" / "alembic.ini"

# pool_pre_ping: test a pooled connection before use, so a restarted PostgreSQL
# does not surface as an error on the next request.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: opens a Session for one request and always closes it."""
    with SessionLocal() as session:
        yield session


@lru_cache
def expected_schema_revision() -> str | None:
    """The newest migration in the code (Alembic 'head')."""
    return ScriptDirectory.from_config(Config(str(ALEMBIC_INI))).get_current_head()


def current_schema_revision(session: Session) -> str | None:
    """The migration the database is at, or None if it has never been migrated."""
    if session.execute(text("SELECT to_regclass('alembic_version')")).scalar() is None:
        return None
    return session.execute(text("SELECT version_num FROM alembic_version")).scalar()
