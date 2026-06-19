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

    # --- correction fallback providers (Phase 0: unused, wired up later) ---
    openrouter_api_key: str = ""

    # --- STT (speech-to-text) providers ---
    # Which provider the frontend dropdown selects by default.
    stt_default_provider: str = "browser_webspeech"
    # Language hint passed to server-side STT engines.
    stt_language: str = "bn"

    # Groq Whisper (OpenAI-compatible audio/transcriptions endpoint).
    # groq_api_key is shared with correction fallback above.
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_stt_model: str = "whisper-large-v3"

    # Local engines (installed via the optional requirements-*.txt files).
    whisper_model_size: str = "base"          # faster-whisper: tiny|base|small|medium
    banglaspeech_model_size: str = "base"     # shhossain/whisper-{size}-bn: tiny|base|small
    banglaspeech_model: str = ""              # full HF id override; empty -> derive from size
    qwen_asr_model_dir: str = ""              # local Qwen3-ASR dir; empty -> auto-download from HF

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
