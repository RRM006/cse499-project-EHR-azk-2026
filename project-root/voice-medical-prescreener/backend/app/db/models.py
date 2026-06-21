"""Database models.

CONSTITUTION RULE #1 — the raw transcript is permanent and is never modified.
``raw_text`` is written once at insert time. The correction lives in a SEPARATE
column (``corrected_text``) and never overwrites the raw words.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


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


class Document(Base):
    """A generated export artifact (.docx now, PDF later) for a completed session.

    The DB stays the source of truth (the Utterance holds the verbatim raw + the
    correction). A Document is a *derived* file, regenerable from the Utterance, so
    it never holds the canonical words — it just records what was exported and where.

    ``utterance_id`` is the session grain today. Future Patient/Visit tables can add
    their own columns/foreign keys here without disturbing this one.
    """

    __tablename__ = "documents"

    # Non-guessable string id (UUID). Doubles as the on-disk filename stem, so file
    # names leak nothing patient-identifying and are safe to expose in URLs.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)

    # Which session (utterance) this document was generated from.
    utterance_id: Mapped[int] = mapped_column(
        ForeignKey("utterances.id"), nullable=False, index=True
    )

    # Export format: "docx" today; "pdf" later — distinguishes multiple artifacts.
    format: Mapped[str] = mapped_column(String(8), nullable=False, default="docx")

    # Which transcript content this file holds: "raw" or "corrected" (raw and
    # corrected are exported as SEPARATE, independently downloadable files). Legacy
    # rows generated before this split are labelled "combined" via the server default.
    kind: Mapped[str] = mapped_column(String(16), nullable=False, server_default="combined")

    # Human-facing download name (e.g. "session-12-20260621.docx").
    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # Path RELATIVE to the configured documents_dir; resolved at read time so the
    # base directory can move (volume, object store) without rewriting rows.
    rel_path: Mapped[str] = mapped_column(String(512), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f"<Document id={self.id!r} utterance_id={self.utterance_id} format={self.format!r}>"
