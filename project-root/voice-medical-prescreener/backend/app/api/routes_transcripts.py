"""Transcript routes: store raw verbatim, correct into a separate field, list.

Flow for POST /api/correct (the core Phase 0 loop):
  1. persist the RAW text exactly as received (never lost, even if step 2 fails),
  2. run the swappable corrector,
  3. store the correction in a SEPARATE field and return both.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import repository as repo
from backend.app.db.database import get_db
from backend.app.schemas.transcript import CorrectRequest, TranscriptOut
from backend.app.services.correction import build_corrector

router = APIRouter(prefix="/api", tags=["transcripts"])


@router.post("/correct", response_model=TranscriptOut)
def correct_transcript(payload: CorrectRequest, db: Session = Depends(get_db)) -> TranscriptOut:
    # Fail fast on misconfiguration (missing key / bad provider) before storing.
    try:
        corrector = build_corrector()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=f"Corrector not configured: {exc}")

    # 1. RAW is persisted verbatim first — it survives even if correction fails.
    utterance = repo.create_raw(db, raw_text=payload.raw_text, source=payload.source)

    # 2. Correction (separate field).
    try:
        corrected = corrector.correct(payload.raw_text)
    except Exception as exc:  # network / quota / provider errors
        # Raw is already saved; surface the failure but don't lose the record.
        raise HTTPException(
            status_code=502,
            detail=f"Correction failed (raw saved as id={utterance.id}): {exc}",
        )

    # 3. Store the correction alongside the untouched raw.
    utterance = repo.set_correction(
        db,
        utterance_id=utterance.id,
        corrected_text=corrected,
        provider=corrector.provider,
        model=corrector.model,
    )
    return utterance


@router.get("/transcripts", response_model=list[TranscriptOut])
def list_transcripts(limit: int = 50, db: Session = Depends(get_db)) -> list[TranscriptOut]:
    return repo.get_recent(db, limit=limit)
