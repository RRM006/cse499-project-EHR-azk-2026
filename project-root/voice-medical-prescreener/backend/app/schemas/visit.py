"""API data contracts for visits (the aggregate root) and their utterances.

A visit is one pre-screening encounter; utterances hang off it in ``seq`` order.
``raw_text`` is carried verbatim in both directions (rule #1).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VisitCreate(BaseModel):
    """Start a visit. ``patient_id`` is optional (walk-in before a patient exists)."""

    patient_id: int | None = Field(None, description="Attach an existing patient, if known.")
    language: str = Field("bn-BD", description="BCP-47 language tag for the session.")


class VisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    clinic_id: int
    patient_id: int | None
    assigned_doctor_id: int | None
    status: str
    language: str
    started_at: datetime
    submitted_at: datetime | None = None
    completed_at: datetime | None


class StoreVisitUtteranceRequest(BaseModel):
    """Persist one raw turn of the conversation against a visit."""

    raw_text: str = Field(..., description="Exact recognized/typed text. Stored unchanged.")
    role: Literal["patient", "system"] = Field(
        "patient", description="'patient' = spoken/typed input; 'system' = a question spoken by TTS."
    )
    source: Literal["mic", "manual", "tts"] = Field("mic", description="Where the text came from.")
    stt_provider: str | None = Field(
        "browser_webspeech", description="Which STT engine produced it (null for system turns)."
    )


class VisitUtteranceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int | None
    role: str
    seq: int | None
    raw_text: str
    corrected_text: str | None
    source: str
    stt_provider: str | None
    created_at: datetime


class VisitDetailOut(VisitOut):
    """A visit plus its full conversation in turn order."""

    utterances: list[VisitUtteranceOut] = []
