"""STT routes: list providers (for the dropdown) and transcribe uploaded audio.

Browser providers transcribe client-side and are persisted via
POST /api/transcripts instead; this transcribe endpoint is for server providers.
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db import repository as repo
from backend.app.db.database import get_db
from backend.app.schemas.transcript import ProviderOut, TranscriptOut
from backend.app.services.stt import get_provider, list_providers

router = APIRouter(prefix="/api", tags=["stt"])


@router.get("/stt/providers", response_model=list[ProviderOut])
def stt_providers() -> list[ProviderOut]:
    return [asdict(info) for info in list_providers()]


@router.post("/transcribe", response_model=TranscriptOut)
async def transcribe(
    provider: str = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> TranscriptOut:
    try:
        prov = get_provider(provider)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown STT provider '{provider}'")

    info = prov.info()
    if prov.kind == "browser":
        raise HTTPException(
            status_code=400,
            detail="Browser providers transcribe client-side; use POST /api/transcripts.",
        )
    if info.status != "available":
        raise HTTPException(
            status_code=409, detail=f"Provider '{provider}' is {info.status}: {info.detail}"
        )

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio upload.")

    try:
        raw_text = prov.transcribe(
            audio_bytes,
            audio.content_type or "audio/webm",
            language=get_settings().stt_language,
        )
    except Exception as exc:  # decode / model / provider errors
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}")

    # RAW persisted verbatim, tagged with the engine that produced it.
    return repo.create_raw(db, raw_text=raw_text, source="mic", stt_provider=provider)
