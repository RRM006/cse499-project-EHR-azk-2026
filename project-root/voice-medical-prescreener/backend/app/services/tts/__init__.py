"""Server-side TTS fallback for Bangla (see base.py for why this exists)."""

from .base import TtsProvider, TtsUnavailable
from .service import get_provider, server_tts_available, synthesize

__all__ = [
    "TtsProvider",
    "TtsUnavailable",
    "get_provider",
    "server_tts_available",
    "synthesize",
]
