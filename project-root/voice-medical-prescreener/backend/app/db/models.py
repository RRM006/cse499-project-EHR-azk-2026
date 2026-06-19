"""Database models.

CONSTITUTION RULE #1 — the raw transcript is permanent and is never modified.
``raw_text`` is written once at insert time. The correction lives in a SEPARATE
column (``corrected_text``) and never overwrites the raw words.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Utterance(Base):
    __tablename__ = "utterances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # RAW — exactly what was recognized (mic) or typed (manual). Write-once, never edited.
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    # CORRECTED — a SEPARATE field, filled in later by the correction service. May be null.
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Where the raw text came from: 'mic' or 'manual' (typed fallback).
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="mic")

    # Which STT engine produced the raw text (e.g. browser_webspeech, groq_whisper).
    stt_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Audit trail: which provider/model produced the correction.
    correction_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    correction_model: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f"<Utterance id={self.id} source={self.source!r} corrected={self.corrected_text is not None}>"
