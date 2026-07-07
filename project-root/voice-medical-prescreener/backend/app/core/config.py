"""Application configuration.

All settings are loaded from ``backend/.env`` (gitignored) via pydantic-settings.
Environment variables override file values, which makes this safe for future
deployment (Docker/host env) without code changes. Nothing here is hardcoded.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# This file is backend/app/core/config.py -> parents[2] == the `backend/` dir.
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"
DEFAULT_SQLITE_PATH = BACKEND_DIR / "prescreener.db"
DEFAULT_DOCUMENTS_DIR = BACKEND_DIR / "data" / "documents"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- speech-to-text source (Module 1 = browser Web Speech API; future-swappable) ---
    stt_provider: str = "browser_webspeech"

    # --- correction provider (swappable: gemini | groq | openrouter) ---
    correction_provider: str = "gemini"
    correction_model: str = "gemini-flash-latest"

    # --- Gemini (OpenAI-compatible endpoint) ---
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # --- correction fallback providers (optional, wired up later) ---
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # --- extra free fallback buckets (optional; blank key = bucket skipped) ---
    # Cerebras: free tier ~1M tokens/day, OpenAI-compatible, very fast.
    # Mistral "Experiment" tier: ~1B tokens/month BUT trains on inputs — rule #4:
    # synthetic/consented data ONLY; leave blank unless you accept that.
    cerebras_api_key: str = ""
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    cerebras_model: str = "llama-3.3-70b"
    mistral_api_key: str = ""
    mistral_base_url: str = "https://api.mistral.ai/v1"
    mistral_model: str = "mistral-small-latest"

    # --- per-bucket model names (ADR-0026: three independent free quota buckets) ---
    gemini_flash_model: str = "gemini-flash-latest"
    gemini_flash_lite_model: str = "gemini-flash-lite-latest"
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # --- follow-up loop (M7–M9) ---
    # Loop guardrails from the capstone brief: stop on completeness OR max turns
    # (avoids patient fatigue). Both tunable without code changes.
    followup_max_questions: int = 5
    completeness_threshold: float = 0.7

    # --- patient identification (kiosk phone + OTP; ADR-0030) ---
    # The OTP flow is a STUB for the capstone demo: no SMS is sent; the kiosk accepts
    # exactly this code. Swap in a real gateway later behind the same verify endpoint.
    dev_otp: str = "000000"

    # --- persistence ---
    # Leave empty to use the default local SQLite file. Set a full SQLAlchemy URL
    # (e.g. postgresql+psycopg://...) later to move to Postgres without code changes.
    database_url: str = ""

    # Where generated .docx (and later PDF) session exports are written. Leave empty
    # to use the default under backend/data/documents. Point this at any path (or a
    # mounted volume) in deployment without code changes — never hardcoded.
    # Accepts either env var: DOCUMENT_OUTPUT_PATH (canonical) or DOCUMENTS_DIR (legacy).
    documents_dir: str = Field(
        "", validation_alias=AliasChoices("document_output_path", "documents_dir")
    )

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        # as_posix() keeps the URL valid on Windows (forward slashes).
        return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

    @property
    def resolved_documents_dir(self) -> Path:
        return Path(self.documents_dir) if self.documents_dir else DEFAULT_DOCUMENTS_DIR


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the .env file is parsed only once per process."""
    return Settings()
