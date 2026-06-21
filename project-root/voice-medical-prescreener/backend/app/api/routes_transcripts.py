"""Transcript routes: store raw verbatim, correct into a separate field, and export
the raw and corrected transcripts as SEPARATE, independently downloadable .docx files.

The pipeline keeps raw immutable (constitution rule #1):
  1. POST /api/transcripts            — store RAW once (browser STT or manual text).
  2. POST /api/transcripts/{id}/documents/raw       — render the RAW .docx.
  3. POST /api/correct                — fill ONLY the separate corrected field, and
     best-effort render the corrected .docx.
  4. POST /api/transcripts/{id}/documents/corrected — (re)render the corrected .docx.
  5. GET  /api/transcripts/{id}       — raw + corrected text + both document links.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import repository as repo
from backend.app.db.models import Utterance
from backend.app.db.database import get_db
from backend.app.schemas.document import DocumentOut
from backend.app.schemas.transcript import (
    CorrectRequest,
    StoreRawRequest,
    TranscriptDetailOut,
    TranscriptOut,
)
from backend.app.services.correction import build_corrector
from backend.app.services.documents import generate_session_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["transcripts"])


def _to_detail(db: Session, utterance: Utterance) -> TranscriptDetailOut:
    """Build the detail response: the utterance plus its latest raw/corrected docs."""
    raw_doc = repo.get_latest_document(db, utterance_id=utterance.id, kind="raw")
    cor_doc = repo.get_latest_document(db, utterance_id=utterance.id, kind="corrected")
    detail = TranscriptDetailOut.model_validate(utterance)
    detail.raw_document = DocumentOut.model_validate(raw_doc) if raw_doc else None
    detail.corrected_document = DocumentOut.model_validate(cor_doc) if cor_doc else None
    return detail


@router.post("/transcripts", response_model=TranscriptOut)
def store_raw(payload: StoreRawRequest, db: Session = Depends(get_db)) -> TranscriptOut:
    """Persist a client-produced raw transcript (browser STT or manual typing)."""
    return repo.create_raw(
        db,
        raw_text=payload.raw_text,
        source=payload.source,
        stt_provider=payload.stt_provider,
    )


@router.get("/transcripts", response_model=list[TranscriptOut])
def list_transcripts(limit: int = 50, db: Session = Depends(get_db)) -> list[TranscriptOut]:
    return repo.get_recent(db, limit=limit)


@router.get("/transcripts/{utterance_id}", response_model=TranscriptDetailOut)
def get_transcript(utterance_id: int, db: Session = Depends(get_db)) -> TranscriptDetailOut:
    utterance = repo.get_by_id(db, utterance_id)
    if utterance is None:
        raise HTTPException(status_code=404, detail=f"Transcript {utterance_id} not found")
    return _to_detail(db, utterance)


@router.post("/transcripts/{utterance_id}/documents/raw", response_model=DocumentOut)
def generate_raw_document(utterance_id: int, db: Session = Depends(get_db)) -> DocumentOut:
    """Generate (or regenerate) the RAW transcript .docx for a session."""
    utterance = repo.get_by_id(db, utterance_id)
    if utterance is None:
        raise HTTPException(status_code=404, detail=f"Transcript {utterance_id} not found")
    try:
        return generate_session_document(db, utterance, kind="raw")
    except Exception as exc:  # noqa: BLE001 - surface as a clean 500
        logger.exception("Failed to generate RAW document for utterance %s", utterance_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {exc}")


@router.post("/transcripts/{utterance_id}/documents/corrected", response_model=DocumentOut)
def generate_corrected_document(utterance_id: int, db: Session = Depends(get_db)) -> DocumentOut:
    """Generate (or regenerate) the corrected transcript .docx for a session."""
    utterance = repo.get_by_id(db, utterance_id)
    if utterance is None:
        raise HTTPException(status_code=404, detail=f"Transcript {utterance_id} not found")
    if not (utterance.corrected_text and utterance.corrected_text.strip()):
        raise HTTPException(
            status_code=400,
            detail="No corrected text yet — run correction before exporting it.",
        )
    try:
        return generate_session_document(db, utterance, kind="corrected")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to generate corrected document for utterance %s", utterance_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {exc}")


@router.post("/correct", response_model=TranscriptDetailOut)
def correct_transcript(
    payload: CorrectRequest, db: Session = Depends(get_db)
) -> TranscriptDetailOut:
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

    # Best-effort: render the corrected .docx now so the UI gets its link back. A
    # document failure must never fail the correction — the file is regenerable from
    # the DB (the source of truth) via the /documents/corrected route.
    try:
        generate_session_document(db, updated, kind="corrected")
    except Exception:  # noqa: BLE001 - non-critical side effect
        logger.exception("Failed to generate corrected document for utterance %s", updated.id)

    return _to_detail(db, updated)
