"""Public kiosk runtime configuration (faculty Requirement 3 + 3b, ADR-0048).

The patient kiosk reads these at load so the voice-loop timings can be tuned per
clinic from `backend/.env` WITHOUT editing JavaScript (e.g. a longer countdown for
an elderly-heavy waiting room).

⚠ This payload is served to an UNAUTHENTICATED browser. It must carry only
behavioural knobs — never a key, URL, path, provider name or any patient data. The
exact field set is asserted by `backend/tests/test_kiosk_config.py`.
"""

from typing import Literal

from pydantic import BaseModel


class KioskConfigOut(BaseModel):
    """Kiosk turn-taking behaviour. All durations are milliseconds."""

    # "auto" = voice-first: the mic opens itself after TTS and a visible countdown
    # submits. "manual" = the original tap-to-talk path (kept, never deleted).
    voice_loop: Literal["auto", "manual"]
    # The visible 3-2-1 countdown IS the silence window: it is a CONFIRMATION
    # window, cancelled by any resumed speech — never a hard cutoff (rule #1).
    countdown_ms: int
    # Delay after TTS ends before the mic may open (echo guard — the AI's own words
    # must never land in the patient's verbatim record).
    tts_guard_ms: int
    # Total silence before the question is repeated once, then typing is offered.
    no_speech_ms: int
    # Hard cap on a single answer before what was captured is submitted.
    max_answer_ms: int
