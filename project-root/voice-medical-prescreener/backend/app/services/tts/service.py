"""Provider selection for server-side TTS (mirrors services/otp/service.py).

One place decides which provider is live, driven by TTS_PROVIDER in backend/.env.
`browser` means "no server provider" — the pre-ADR-0040 behaviour, kept so the whole
seam can be switched off without deleting code (the ADR-0045 pattern).
"""

from __future__ import annotations

from ...core.config import get_settings
from .base import TtsProvider, TtsUnavailable
from .espeak import EspeakNgProvider

# Languages the kiosk UI can be in. The wire value is always the short code; espeak
# voice names live in .env so a clinic can pick a different Bengali variant.
SUPPORTED_LANGS = ("bn", "en")


def get_provider() -> TtsProvider | None:
    """The configured provider, or None when server-side TTS is switched off."""
    settings = get_settings()
    if settings.resolved_tts_provider != "espeak":
        return None
    return EspeakNgProvider(
        binary=settings.tts_espeak_path,
        voice_bn=settings.tts_voice_bn,
        voice_en=settings.tts_voice_en,
        speed_wpm=settings.tts_speed_wpm,
    )


def server_tts_available() -> bool:
    """True only if a provider is configured AND its engine is actually present.

    Used by GET /api/config so the kiosk knows whether a server fallback exists before
    it tries one, and so the "no Bangla voice" banner can tell the patient the truth.
    Deliberately does NOT synthesize — it must stay cheap enough to call on page load.
    """
    provider = get_provider()
    if provider is None:
        return False
    resolve = getattr(provider, "resolve_binary", None)
    return bool(resolve()) if callable(resolve) else True


def synthesize(text: str, lang: str) -> tuple[bytes, str]:
    """Render `text` and return (audio_bytes, media_type).

    Raises TtsUnavailable when no audio can be produced — the caller turns that into a
    503 so the frontend falls back to text instead of pretending audio played.
    """
    if lang not in SUPPORTED_LANGS:
        raise TtsUnavailable(f"Unsupported language {lang!r}.")
    provider = get_provider()
    if provider is None:
        raise TtsUnavailable("Server-side TTS is disabled (TTS_PROVIDER=browser).")
    return provider.synthesize(text, lang), provider.media_type
