"""Alembic environment: connects to the database from app settings and compares the
database against the SQLAlchemy models (Base.metadata) for `alembic revision --autogenerate`."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    # disable_existing_loggers=False: don't silence the application's own loggers.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata
DATABASE_URL = get_settings().database_url

COMPARE_OPTIONS = {
    "target_metadata": target_metadata,
    "compare_type": True,  # also detect column type changes
}


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of executing it (`alembic upgrade head --sql`)."""
    context.configure(
        url=DATABASE_URL, literal_binds=True, dialect_opts={"paramstyle": "named"},
        **COMPARE_OPTIONS,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, **COMPARE_OPTIONS)
        # PostgreSQL DDL is transactional: if any step fails, the whole migration rolls back.
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
