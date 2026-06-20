"""API data contracts for utterances.

These are deliberately separate from the SQLAlchemy model so the wire format and
the storage format can evolve independently. ``raw_text`` is carried verbatim.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StoreRawRequest(BaseModel):
    """Persist a raw transcript produced client-side (browser STT or manual typing)."""

    raw_text: str = Field(..., description="Exact recognized/typed text. Stored unchanged.")
    stt_provider: str = Field(
        "browser_webspeech",
        description="Which source produced it (browser_webspeech | manual).",
    )
    source: Literal["mic", "manual"] = Field("mic", description="Where the raw text came from.")


class CorrectRequest(BaseModel):
    """Correct an already-stored raw utterance (raw stays immutable)."""

    utterance_id: int = Field(..., description="ID of the stored raw utterance to correct.")


class TranscriptOut(BaseModel):
    """An utterance as returned by the API: raw + the separate correction."""

    model_config = ConfigDict(from_attributes=True)  # allow building from ORM objects

    id: int
    raw_text: str
    corrected_text: str | None
    source: str
    stt_provider: str | None
    correction_provider: str | None
    correction_model: str | None
    created_at: datetime
    corrected_at: datetime | None
