import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make_settings(**env) -> Settings:
    # _env_file=None: ignore the repo .env so the test depends only on what it sets.
    return Settings(_env_file=None, **env)


def test_reads_environment_variables(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "test-password")
    monkeypatch.setenv("DB_HOST", "db.example.internal")
    monkeypatch.setenv("DB_PORT", "6543")
    settings = make_settings()
    assert settings.db_host == "db.example.internal"
    assert settings.db_port == 6543  # converted from the string "6543"


def test_password_is_required(monkeypatch):
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    with pytest.raises(ValidationError):
        make_settings()


def test_invalid_port_is_rejected(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "test-password")  # so the port is the only problem
    monkeypatch.setenv("DB_PORT", "not-a-number")
    with pytest.raises(ValidationError):
        make_settings()


def test_password_hidden_in_repr_but_present_in_url(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "p@ss:word/1")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    settings = make_settings()
    assert "p@ss" not in repr(settings)
    # Special characters are URL-encoded so the connection URL stays valid.
    assert settings.database_url.endswith(":p%40ss%3Aword%2F1@localhost:5432/campusmate_test")
