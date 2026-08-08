"""API data contracts for the M7–M9 follow-up loop."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FollowupQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    target_gap: str | None
    question_text: str  # shown on screen AND spoken via TTS (ADR-0028)
    priority: int | None
    answer_utterance_id: int | None
    asked_at: datetime
    answered_at: datetime | None


class NextQuestionOut(BaseModel):
    """Result of /followup/next: either a question to ask, or the loop is complete."""

    complete: bool
    completeness_score: float
    question: FollowupQuestionOut | None = None


class AnswerRequest(BaseModel):
    """The patient's answer to a follow-up question (stored verbatim as an utterance
    — the answer is never a free-text profile field, ADR-0027).

    ONE pipeline serves both input modes (ADR-0048): `source="mic"` for speech and
    `source="manual"` for typing. Voice is the primary route; typing is the always-
    available fallback. Nothing else differs — the merge/extraction path is identical.
    """

    question_id: int
    raw_text: str = Field(
        ..., min_length=1, description="Exact recognized/typed text. Stored unchanged."
    )
    source: Literal["mic", "manual"] = "mic"
    stt_provider: str | None = "browser_webspeech"

    @field_validator("raw_text")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        """S1 (ADR-0048): 'never silently submit an empty answer' is enforced on the
        SERVER, not only in the browser — an auto-endpointing kiosk must not be able
        to store a blank turn when a patient never actually spoke.

        ⚠ Rule #1: the value is returned COMPLETELY UNCHANGED. `.strip()` is used to
        test emptiness only — never to rewrite the patient's words. Padding, casing
        and punctuation are part of the verbatim record.
        """
        if not value.strip():
            raise ValueError("raw_text must not be blank — an empty answer is never submitted.")
        return value


class AnswerOut(BaseModel):
    """Updated loop state after M8 + M9; carries the next question when not complete
    so the voice-only frontend needs no second round-trip (architecture.md §4)."""

    complete: bool
    completeness_score: float
    next_question: FollowupQuestionOut | None = None
