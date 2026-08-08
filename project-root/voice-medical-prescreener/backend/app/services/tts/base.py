"""The pluggable server-side TTS provider seam (mirrors the ADR-0045 OTP seam).

WHY THIS EXISTS. ADR-0027 chose the browser's own `speechSynthesis` for M7 audio —
free, key-less, no server. On Arch that works for Bangla once espeak-ng is installed
(ADR-0040). On **Windows it can never work**: Microsoft ships no Bengali voice at all,
so `getVoices()` has nothing `bn*` to pick and a Bangla question is either silent or
mangled by an en-US voice. This seam is the fallback for exactly that case.

A provider's ONLY job is: text + language in, playable audio bytes out. It knows
nothing about visits, patients or the kiosk flow. Swapping in the quantized on-device
Bangla model (faculty Requirement 2) is one new subclass plus a TTS_PROVIDER value —
no route change, no frontend change.

⚠ The browser voice stays PREFERRED. This is a fallback, not a replacement: the
frontend only calls the server when it has no `bn*` voice of its own.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

# A single question, not an audiobook. `/api/tts` is unauthenticated, so this also
# bounds how much work one caller can ask for. It lives HERE, not in a provider
# module, because the cap is a property of the endpoint's contract — every provider
# and the route itself must agree on it (ADR-0050: it used to be imported from
# espeak.py, which made a local engine's constant the API's limit by accident).
MAX_TEXT_CHARS = 600


class TtsUnavailable(RuntimeError):
    """No audio could be produced (engine missing, unsupported language, crash).

    Raised rather than returning silence, so the caller can be HONEST with the
    patient instead of pretending Bangla audio played. The kiosk keeps showing the
    question as text, which is the ADR-0028 fallback.
    """


class TtsProvider(ABC):
    name: str = "abstract"
    #: MIME type of the bytes `synthesize` returns.
    media_type: str = "audio/wav"

    def available(self) -> bool:
        """Cheap, NON-network check that this provider could plausibly work.

        Called on every page load via GET /api/config, so it must never synthesize
        and never make a request. A provider that cannot know without trying (any
        network provider) should report True and fail loudly at synthesize() time.
        """
        return True

    @abstractmethod
    def synthesize(self, text: str, lang: str) -> bytes:
        """Render ``text`` in ``lang`` ('bn' or 'en') and return audio bytes.

        Must raise :class:`TtsUnavailable` on any failure — never return b"" and
        never return silence, because a silent success is indistinguishable from
        working audio at the UI and would hide a broken clinic kiosk.
        """
