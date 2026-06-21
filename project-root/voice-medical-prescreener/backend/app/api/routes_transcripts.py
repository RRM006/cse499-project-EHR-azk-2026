"""Transcript routes: store raw verbatim, correct into a separate field, list.

The pipeline is two explicit steps so raw is created once and never re-touched:
  1. transcription stores RAW (here via POST /api/transcripts for browser/manual
     text, or via POST /api/transcribe for server STT in routes_stt.py),
  2. POST /api/correct corrects an existing utterance by id, filling ONLY the
     separate corrected field.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import repository as repo
from backend.app.db.database import get_db
from backend.app.schemas.transcript import CorrectRequest, StoreRawRequest, TranscriptOut
from backend.app.services.correction import build_corrector
from backend.app.services.documents import generate_session_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["transcripts"])


@router.post("/transcripts", response_model=TranscriptOut)
def store_raw(payload: StoreRawRequest, db: Session = Depends(get_db)) -> TranscriptOut:
    """Persist a client-produced raw transcript (browser STT or manual typing)."""
    return repo.create_raw(
        db,
        raw_text=payload.raw_text,
        source=payload.source,
        stt_provider=payload.stt_provider,
    )


@router.post("/correct", response_model=TranscriptOut)
def correct_transcript(payload: CorrectRequest, db: Session = Depends(get_db)) -> TranscriptOut:
    utterance = repo.get_by_id(db, payload.utterance_id)
    if utterance is None:
        raise HTTPException(status_code=404, detail=f"Utterance {payload.utterance_id} not found")

    try:
        corrector = build_corrector()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=f"Corrector not configured: {exc}")

    try:
        corrected = corrector.correct(utterance.raw_text)  # raw is read-only here
    except Exception as exc:  # network / quota / provider errors
        raise HTTPException(status_code=502, detail=f"Correction failed: {exc}")

    updated = repo.set_correction(
        db,
        utterance_id=utterance.id,
        corrected_text=corrected,
        provider=corrector.provider,
        model=corrector.model,
    )

    # The session is now complete (raw + corrected) — save a .docx export.
    # Best-effort: a document failure must never fail the correction response, and
    # the file is always regenerable from the DB (the source of truth).
    try:
        generate_session_document(db, updated, doc_format="docx")
    except Exception:  # noqa: BLE001 - non-critical side effect
        logger.exception("Failed to generate session document for utterance %s", updated.id)

    return updated


@router.get("/transcripts", response_model=list[TranscriptOut])
def list_transcripts(limit: int = 50, db: Session = Depends(get_db)) -> list[TranscriptOut]:
    return repo.get_recent(db, limit=limit)
