"""Provider selection for server-side TTS (mirrors services/otp/service.py).

One place decides which provider is live, driven by TTS_PROVIDER in backend/.env.
`browser` means "no server provider" — the pre-ADR-0040 behaviour, kept so the whole
seam can be switched off without deleting code (the ADR-0045 pattern).

ADR-0050 added a second provider (edge-tts) and, with it, a **local fallback**: a
network voice can fail at the worst possible moment, and for a clinic kiosk a robotic
question beats a silent one. So when the configured provider fails, espeak-ng is tried
before giving up. The failure is still LOUD if both fail — a 503, never silence.
"""

from __future__ import annotations

import logging

from ...core.config import get_settings
from .base import TtsProvider, TtsUnavailable
from .edge import EdgeTtsProvider
from .espeak import EspeakNgProvider
from .prosody import speech_text

logger = logging.getLogger(__name__)

# Languages the kiosk UI can be in. The wire value is always the short code; the actual
# voice names live in .env so a clinic can pick a different Bengali variant.
SUPPORTED_LANGS = ("bn", "en")

# The local, offline engine every other provider falls back to. Named once so the
# fallback rule below cannot drift from what the .env documentation promises.
LOCAL_PROVIDER = "espeak"


def _make_espeak() -> EspeakNgProvider:
    settings = get_settings()
    return EspeakNgProvider(
        binary=settings.tts_espeak_path,
        voice_bn=settings.tts_voice_bn,
        voice_en=settings.tts_voice_en,
        speed_wpm=settings.tts_speed_wpm,
    )


def _make_edge() -> EdgeTtsProvider:
    settings = get_settings()
    return EdgeTtsProvider(
        voice_bn=settings.tts_edge_voice_bn,
        voice_en=settings.tts_edge_voice_en,
        rate=settings.tts_edge_rate,
        timeout_s=settings.tts_edge_timeout_s,
        pitch=settings.tts_edge_pitch,
        volume=settings.tts_edge_volume,
    )


#: name -> factory. Adding a provider (e.g. the quantized on-device model of faculty
#: Requirement 2) is one entry here plus one TTS_PROVIDERS value — nothing else.
PROVIDER_FACTORIES = {
    LOCAL_PROVIDER: _make_espeak,
    "edge": _make_edge,
}


def get_provider() -> TtsProvider | None:
    """The configured provider, or None when server-side TTS is switched off."""
    factory = PROVIDER_FACTORIES.get(get_settings().resolved_tts_provider)
    return factory() if factory else None


def get_fallback_provider(primary: TtsProvider | None) -> TtsProvider | None:
    """The local engine to try when `primary` fails, or None if there is nothing to add.

    Returns None when the fallback is disabled, when nothing is configured, or when the
    primary IS the local engine (retrying espeak-ng after espeak-ng just failed would
    only slow down an honest error).
    """
    if primary is None or not get_settings().tts_local_fallback:
        return None
    if primary.name == LOCAL_PROVIDER:
        return None
    return _make_espeak()


def server_tts_available() -> bool:
    """True if a provider is configured AND it (or its fallback) could actually speak.

    Used by GET /api/config so the kiosk knows whether a server fallback exists before
    it tries one, and so the "no Bangla voice" banner can tell the patient the truth.
    Deliberately does NOT synthesize and never touches the network — it must stay cheap
    enough to call on every page load.
    """
    provider = get_provider()
    if provider is None:
        return False
    if provider.available():
        return True
    fallback = get_fallback_provider(provider)
    return bool(fallback and fallback.available())


def synthesize(text: str, lang: str) -> tuple[bytes, str]:
    """Render `text` and return (audio_bytes, media_type).

    Tries the configured provider, then the local fallback. Raises TtsUnavailable when
    NO provider can produce audio — the caller turns that into a 503 so the frontend
    falls back to on-screen text instead of pretending audio played.
    """
    if lang not in SUPPORTED_LANGS:
        raise TtsUnavailable(f"Unsupported language {lang!r}.")
    provider = get_provider()
    if provider is None:
        raise TtsUnavailable("Server-side TTS is disabled (TTS_PROVIDER=browser).")

    # S35: punctuate for speech ONCE, here, so every provider (and the fallback) reads
    # the identical line. Punctuation and whitespace only — never a word — because the
    # kiosk's read-back sends the PATIENT's own captured words down this same path.
    text = speech_text(text, lang)

    try:
        return provider.synthesize(text, lang), provider.media_type
    except TtsUnavailable as primary_error:
        fallback = get_fallback_provider(provider)
        if fallback is None:
            raise
        # WARNING, not debug: a clinic silently running on the robotic fallback for a
        # week is exactly the kind of quiet degradation this project keeps refusing to
        # ship. The message carries no question text — only the provider names.
        logger.warning(
            "TTS provider %r failed (%s); falling back to %r.",
            provider.name, primary_error, fallback.name,
        )
        try:
            return fallback.synthesize(text, lang), fallback.media_type
        except TtsUnavailable as fallback_error:
            raise TtsUnavailable(
                f"{provider.name} failed ({primary_error}); "
                f"{fallback.name} fallback also failed ({fallback_error})"
            ) from fallback_error
