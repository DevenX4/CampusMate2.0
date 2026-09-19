"""Application configuration, loaded from environment variables and the repo-root .env file.

Precedence (highest first): real environment variables > .env file > defaults below.
Fields without a default (DB_PASSWORD) must be provided, so a misconfigured app fails at startup.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, ValidationInfo, field_validator
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

    # Login sessions. COOKIE_SECURE must be true in production (cookie only sent over HTTPS).
    session_ttl_hours: int = 12
    cookie_secure: bool = False

    # Largest accepted upload. The official syllabus PDF is 37 MB.
    max_upload_mb: int = 50

    # Ingestion: largest chunk (characters); a job 'processing' longer than the lease is
    # assumed to belong to a crashed worker and is picked up again.
    chunk_max_chars: int = 1200
    ingestion_lease_minutes: int = 30
    worker_poll_seconds: int = 5

    # Retrieval. Models are downloaded once into MODEL_CACHE_DIR (ignored by Git).
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chroma_collection: str = "campusmate_chunks"
    # A Chroma server shared by the API and the ingestion worker, e.g. http://127.0.0.1:8001
    # (start it with: chroma run --path storage/chroma --port 8001). Empty: an embedded store in
    # STORAGE_DIR/chroma, safe only while a single process uses it.
    chroma_url: str | None = None
    retrieval_top_k: int = 8
    # Opt-in reranking (search mode hybrid_rerank). Best measured configuration; it did NOT
    # reliably beat plain hybrid on the evaluation set and costs ~5 s/query on CPU, so the
    # default mode stays hybrid. See evaluation/results/RETRIEVAL.md.
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-12-v2"
    rerank_candidates: int = 30  # hybrid candidates the cross-encoder rescores
    rerank_max_chars: int | None = None  # passage prefix the cross-encoder reads (None = all)

    # Answer generation. "extractive" needs no model (copies cited sentences); "openai_compatible"
    # talks to any server speaking the OpenAI chat API: a local Ollama / llama.cpp / LM Studio
    # server, or a hosted API. A non-local URL sends questions and evidence off this machine.
    generation_provider: Literal["extractive", "openai_compatible"] = "extractive"
    generation_base_url: str = "http://127.0.0.1:11434/v1"  # Ollama's default address
    generation_model: str | None = Field(default=None, validate_default=True)
    generation_api_key: SecretStr | None = None  # only for hosted APIs; local servers need none
    generation_timeout_seconds: float = 120.0
    generation_max_tokens: int = 400
    generation_temperature: float = 0.0  # deterministic: the same evidence gives the same answer

    # Local folders. Overridable so a container can mount them elsewhere later.
    data_dir: Path = REPO_ROOT / "data"  # the canonical dataset (read-only input)
    storage_dir: Path = REPO_ROOT / "storage"  # uploaded/original documents and indexes
    model_cache_dir: Path = REPO_ROOT / "model_cache"  # downloaded ML models

    @field_validator("data_dir", "storage_dir", "model_cache_dir")
    @classmethod
    def _relative_to_repo_root(cls, value: Path) -> Path:
        # "data" means <repo>/data regardless of the folder the app is started from.
        return value if value.is_absolute() else REPO_ROOT / value

    # A field validator, not a model validator: a model validator's error message would print
    # the whole input, secrets included.
    @field_validator("generation_model")
    @classmethod
    def _generation_model_required(cls, value: str | None, info: ValidationInfo) -> str | None:
        if info.data.get("generation_provider") == "openai_compatible" and not value:
            raise ValueError("GENERATION_MODEL is required when GENERATION_PROVIDER=openai_compatible")
        return value

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
