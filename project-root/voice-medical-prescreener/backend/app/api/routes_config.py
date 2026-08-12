"""Public kiosk configuration route (S1 of faculty Requirement 3 + 3b, ADR-0048).

GET /api/config — the patient kiosk's voice-loop mode and timings.

No DB, no auth: the kiosk fetches this before a patient has identified themselves.
It therefore exposes ONLY behavioural knobs (see `schemas/kiosk_config.py`) — the
response is built field-by-field from `Settings` rather than dumping it, so a new
secret added to config.py can never leak here by accident.
"""

from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.schemas.kiosk_config import KioskConfigOut
from backend.app.services.tts import server_tts_available

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/config", response_model=KioskConfigOut)
def kiosk_config() -> KioskConfigOut:
    settings = get_settings()
    return KioskConfigOut(
        voice_loop=settings.resolved_voice_loop,  # normalized; bad .env value -> "auto"
        countdown_ms=settings.voice_countdown_ms,
        tts_guard_ms=settings.voice_tts_guard_ms,
        no_speech_ms=settings.voice_no_speech_ms,
        max_answer_ms=settings.voice_max_answer_ms,
        # S34 (ADR-0055): the spoken-answer read-back gate and the review auto-submit.
        answer_confirm=settings.voice_answer_confirm,
        review_timeout_ms=max(0, settings.voice_review_timeout_ms),
        # Capability, not configuration: reports whether the engine is really installed.
        server_tts=server_tts_available(),
    )
