"""The command line (`python -m app.seed`) owns the transaction: it commits only when
validation passes, and a dry run never writes."""

from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models.documents import Document
from app.seed import __main__ as cli
from app.seed import run
from tests.conftest import requires_dataset


def document_count() -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(Document))


@requires_dataset
def test_dry_run_validates_but_writes_nothing(migrated_engine, capsys):
    assert cli.main(["--dry-run"]) == 0
    assert "validation: OK" in capsys.readouterr().out
    assert document_count() == 0


@requires_dataset
def test_failed_validation_rolls_everything_back(migrated_engine, monkeypatch, capsys):
    monkeypatch.setattr(run, "check_consistency", lambda session, src: ["forced problem for the test"])
    assert cli.main([]) == 1
    assert "ROLLED BACK" in capsys.readouterr().out
    assert document_count() == 0
