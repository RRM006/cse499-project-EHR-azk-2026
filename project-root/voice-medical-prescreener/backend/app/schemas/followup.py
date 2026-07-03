"""API data contracts for the M7–M9 follow-up loop."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    """The patient's VOICE answer to a follow-up question (stored verbatim as an
    utterance — the answer is never a free-text profile field, ADR-0027)."""

    question_id: int
    raw_text: str = Field(..., description="Exact recognized text. Stored unchanged.")
    source: Literal["mic", "manual"] = "mic"
    stt_provider: str | None = "browser_webspeech"


class AnswerOut(BaseModel):
    """Updated loop state after M8 + M9; carries the next question when not complete
    so the voice-only frontend needs no second round-trip (architecture.md §4)."""

    complete: bool
    completeness_score: float
    next_question: FollowupQuestionOut | None = None
