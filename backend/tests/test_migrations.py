from alembic import command
from sqlalchemy import inspect, text

from app.models import Base
from tests.conftest import alembic_config


def test_models_and_migrations_agree(migrated_engine):
    # Fails if a model was changed without generating a migration for it.
    command.check(alembic_config())


def test_every_model_table_exists(migrated_engine):
    tables = set(inspect(migrated_engine).get_table_names())
    assert set(Base.metadata.tables) <= tables


def test_downgrade_to_base_and_upgrade_again(migrated_engine):
    command.downgrade(alembic_config(), "base")
    assert inspect(migrated_engine).get_table_names() == ["alembic_version"]
    command.upgrade(alembic_config(), "head")
    assert set(Base.metadata.tables) <= set(inspect(migrated_engine).get_table_names())


def test_hand_written_parts_exist(migrated_engine):
    with migrated_engine.connect() as conn:
        deferred_fks = conn.execute(text(
            "SELECT conname FROM pg_constraint WHERE condeferrable AND condeferred ORDER BY 1"
        )).scalars().all()
        triggers = conn.execute(text(
            "SELECT tgname FROM pg_trigger "
            "WHERE tgrelid = 'audit_logs'::regclass AND NOT tgisinternal ORDER BY 1"
        )).scalars().all()
    assert deferred_fks == ["fk_departments_head_faculty_id", "fk_documents_department_id"]
    assert triggers == ["audit_logs_no_truncate", "audit_logs_no_update_delete"]
