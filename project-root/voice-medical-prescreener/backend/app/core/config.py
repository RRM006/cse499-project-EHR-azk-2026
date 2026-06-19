"""Application configuration.

All settings are loaded from ``backend/.env`` (gitignored) via pydantic-settings.
Environment variables override file values, which makes this safe for future
deployment (Docker/host env) without code changes. Nothing here is hardcoded.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# This file is backend/app/core/config.py -> parents[2] == the `backend/` dir.
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"
DEFAULT_SQLITE_PATH = BACKEND_DIR / "prescreener.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- correction provider (swappable: gemini | groq | openrouter) ---
    correction_provider: str = "gemini"
    correction_model: str = "gemini-flash-latest"

    # --- Gemini (OpenAI-compatible endpoint) ---
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # --- fallback providers (Phase 0: unused, wired up later) ---
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # --- persistence ---
    # Leave empty to use the default local SQLite file. Set a full SQLAlchemy URL
    # (e.g. postgresql+psycopg://...) later to move to Postgres without code changes.
    database_url: str = ""

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        # as_posix() keeps the URL valid on Windows (forward slashes).
        return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the .env file is parsed only once per process."""
    return Settings()
