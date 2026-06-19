"""API data contracts for utterances.

These are deliberately separate from the SQLAlchemy model so the wire format and
the storage format can evolve independently. ``raw_text`` is carried verbatim.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CorrectRequest(BaseModel):
    """Incoming raw text to store verbatim and then correct (separately)."""

    raw_text: str = Field(
        ...,
        description="Exact recognized (mic) or typed (manual) text. Stored unchanged.",
    )
    source: Literal["mic", "manual"] = Field(
        "mic", description="Where the raw text came from."
    )


class TranscriptOut(BaseModel):
    """An utterance as returned by the API: raw + the separate correction."""

    model_config = ConfigDict(from_attributes=True)  # allow building from ORM objects

    id: int
    raw_text: str
    corrected_text: str | None
    source: str
    correction_provider: str | None
    correction_model: str | None
    created_at: datetime
    corrected_at: datetime | None
