import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# Tests must never touch the development database. Set before any app import, and
# real environment variables win over .env. Host, port, user and password still come
# from .env (or the environment), so tests run against the same server as the app.
os.environ["APP_ENV"] = "test"
os.environ["DB_NAME"] = "campusmate_test"

from app.core.config import get_settings  # noqa: E402
from app.core.db import ALEMBIC_INI  # noqa: E402


def alembic_config() -> Config:
    return Config(str(ALEMBIC_INI))


@pytest.fixture(scope="session")
def migrated_engine():
    """A freshly migrated campusmate_test database, shared by the whole test run."""
    settings = get_settings()
    assert settings.db_name.endswith("_test"), "refusing to reset a non-test database"
    engine = create_engine(settings.database_url)
    try:
        with engine.connect():
            pass
    except OperationalError as exc:
        reason = str(exc.orig).splitlines()[0]
        pytest.skip(
            f"test database {settings.db_host}:{settings.db_port}/{settings.db_name} "
            f"not reachable: {reason}. See README > Database setup."
        )
    # Rebuild the schema from scratch through the real migrations.
    command.downgrade(alembic_config(), "base")
    command.upgrade(alembic_config(), "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(migrated_engine):
    """A Session whose changes are rolled back after each test, so tests stay independent."""
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        # Commits inside the test only release a SAVEPOINT; the outer transaction is undone.
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
