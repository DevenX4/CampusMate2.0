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


def _pdfs_present() -> bool:
    """The dataset PDFs are not in Git; tests that load the dataset need them locally."""
    data_dir = get_settings().data_dir
    manifest = data_dir / "pdfs.sha256"
    return manifest.is_file() and all(
        (data_dir / "pdfs" / line.split("*", 1)[1].strip()).is_file()
        for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()
    )


requires_dataset = pytest.mark.skipif(
    not _pdfs_present(), reason="dataset PDFs missing from data/pdfs (see README > PDFs)"
)


@pytest.fixture(scope="module")
def seeded_session(migrated_engine):
    """campusmate_test with the whole dataset loaded, inside a transaction that is rolled
    back when the test module finishes (so other modules still see an empty schema)."""
    if not _pdfs_present():
        pytest.skip("dataset PDFs missing from data/pdfs (see README > PDFs)")
    from app.seed.run import seed

    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        report = seed(session, get_settings().data_dir, storage_dir=None)
        assert report.problems == [], report.problems
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


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
