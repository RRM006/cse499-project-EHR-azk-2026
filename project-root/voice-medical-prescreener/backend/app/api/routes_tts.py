"""Public server-side TTS route — the Bangla audio fallback.

GET /api/tts?text=...&lang=bn  ->  audio/wav

No DB, no auth: like /api/config, the kiosk needs this before the patient has
identified themselves, and it is the SAME question text that is already displayed on
screen. Nothing is stored and nothing is read from the database.

⚠ Deliberately NOT a patient-data endpoint. It renders whatever text it is handed;
the kiosk only ever hands it the assistant's own question. No `raw_text`, no
utterances, no transcript ever passes through here (rule #1 is untouched).

503 on failure — never silence. A silent 200 is indistinguishable from working audio
at the UI, which would hide a broken kiosk from the clinic.
"""

from fastapi import APIRouter, HTTPException, Query, Response

from backend.app.services.tts import TtsUnavailable, synthesize
from backend.app.services.tts.espeak import MAX_TEXT_CHARS
from backend.app.services.tts.service import SUPPORTED_LANGS

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/tts")
def speak(
    text: str = Query(..., min_length=1, max_length=MAX_TEXT_CHARS),
    lang: str = Query("bn"),
) -> Response:
    """Render one question aloud. Used only when the browser has no `bn*` voice."""
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=422, detail=f"Unsupported lang {lang!r}.")
    try:
        audio, media_type = synthesize(text, lang)
    except TtsUnavailable as exc:
        # 503, not 500: the request was valid, the engine just is not available. The
        # kiosk treats this as "no audio" and keeps the on-screen text (ADR-0028).
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=audio,
        media_type=media_type,
        # Same question is often replayed (🔊 button, Repeat question) — let the browser
        # reuse it rather than re-running the engine. Private: never a shared cache.
        headers={"Cache-Control": "private, max-age=300"},
    )
