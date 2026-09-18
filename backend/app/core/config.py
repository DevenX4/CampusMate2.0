"""Application configuration, loaded from environment variables and the repo-root .env file.

Precedence (highest first): real environment variables > .env file > defaults below.
Fields without a default (DB_PASSWORD) must be provided, so a misconfigured app fails at startup.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[3] is the CampusMate repo root.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # tolerate variables meant for later phases
    )

    app_name: str = "CampusMate AI"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # PostgreSQL. Only the settings live here; the database layer arrives in Phase 2.
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "campusmate"
    db_user: str = "campusmate_app"
    db_password: SecretStr  # SecretStr prints as '**********' in logs and reprs

    @property
    def database_url(self) -> str:
        """SQLAlchemy URL for the psycopg (v3) driver. Contains the password: never log it."""
        password = quote_plus(self.db_password.get_secret_value())
        return (
            f"postgresql+psycopg://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    """Read the environment once and reuse the same Settings object everywhere."""
    return Settings()
