"""edge-tts provider — natural neural Bangla (ADR-0050, TTS-2).

WHY THIS EXISTS. The S29 live listen rejected espeak-ng on quality: *"Too robotic …
i want make it like human not too robotic"*. espeak-ng is a **formant synthesizer**, so
that is inherent, not tunable — no `.env` value makes it sound human. Microsoft's
`bn-BD` neural voices (`NabanitaNeural` female, `PradeepNeural` male) are genuinely
neural and are the only verified free option with a natural Dhaka accent.

⚠ THE TRADE-OFF, MADE EXPLICITLY (ADR-0050, the human's decision). M7 questions are
DERIVED from what the patient said, and this provider sends that text to Microsoft.
That is a real rule #4 cost and it is why espeak-ng was chosen first. It was accepted
knowingly, for a research prototype running on synthetic data, on the grounds that the
system ALREADY sends the patient's actual audio to Google via the Web Speech API — so
this adds a second processor of strictly less sensitive, derived text, rather than
crossing a new boundary. It still limits what the thesis may claim about privacy.
**Nothing here is stored, logged, or sent anywhere else**, and no transcript, raw_text
or patient identity ever reaches this module — it receives one question string.

For a fully offline/private demo, set `TTS_PROVIDER=espeak`: that path is untouched and
still the automatic fallback when this provider fails (see service.py).

Licensing: edge-tts is **LGPL-3.0**. Used as an ordinary pip-installed library it
imposes no copyleft on this project's own code and carries no non-commercial clause —
unlike `facebook/mms-tts-ben` (CC-BY-NC-4.0), which was rejected for that reason plus
its torch+transformers weight on these CPU-only machines.
"""

from __future__ import annotations

import asyncio

from .base import MAX_TEXT_CHARS, TtsProvider, TtsUnavailable

# Microsoft returns MP3, not WAV. The seam already carries `media_type` per provider
# through to the Response, and <audio> plays MP3 natively — so this needs no route or
# frontend change. (It is also ~8x smaller than espeak's WAV over the wire.)
MEDIA_TYPE = "audio/mpeg"

# The network call is the whole cost here. Long enough for a slow clinic link, short
# enough that a hung request cannot hold the kiosk's turn-taking hostage — the caller
# falls back to espeak-ng when this expires.
REQUEST_TIMEOUT_S = 12

# An MP3 frame header is 4 bytes; anything this small is not speech. Treated as a
# failure rather than played, for the same reason espeak.py rejects a bare WAV header:
# silence that looks like success would hide a broken kiosk from the clinic.
MIN_AUDIO_BYTES = 512


class EdgeTtsProvider(TtsProvider):
    name = "edge"
    media_type = MEDIA_TYPE

    def __init__(
        self,
        voice_bn: str = "bn-BD-NabanitaNeural",
        voice_en: str = "en-US-AriaNeural",
        rate: str = "+0%",
        timeout_s: int = REQUEST_TIMEOUT_S,
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> None:
        self._voices = {"bn": voice_bn, "en": voice_en}
        self._rate = rate
        # S35: edge-tts accepts pitch and volume alongside rate. Defaults are NEUTRAL on
        # purpose — the voice is already neural, and pushing prosody around is how a
        # synthesizer starts sounding like a cartoon rather than like a calm assistant.
        # These exist so a clinic can compensate for a noisy waiting room or a patient
        # who finds the default pitch hard to hear, not as a "naturalness" dial.
        self._pitch = pitch
        self._volume = volume
        self._timeout_s = timeout_s

    def available(self) -> bool:
        """Only that the library is importable — deliberately NOT a network check.

        This runs on every kiosk page load via /api/config. Probing Microsoft there
        would add latency to every load and still tell us nothing about the moment the
        question is actually asked, so reachability is proven the only honest way:
        by trying, and falling back to espeak-ng if it fails.
        """
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            return False
        return True

    def synthesize(self, text: str, lang: str) -> bytes:
        if not text or not text.strip():
            raise TtsUnavailable("Refusing to synthesize empty text.")
        if len(text) > MAX_TEXT_CHARS:
            raise TtsUnavailable(f"Text exceeds {MAX_TEXT_CHARS} characters.")
        voice = self._voices.get(lang)
        if not voice:
            raise TtsUnavailable(f"No edge-tts voice configured for language {lang!r}.")

        try:
            import edge_tts
        except ImportError as exc:   # dependency not installed for this deployment
            raise TtsUnavailable(
                "edge-tts is not installed. Run: pip install -r requirements.txt"
            ) from exc

        async def _render() -> bytes:
            communicate = edge_tts.Communicate(
                text, voice, rate=self._rate, pitch=self._pitch, volume=self._volume,
            )
            chunks: list[bytes] = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            return b"".join(chunks)

        try:
            # The /api/tts route is a sync `def`, so FastAPI runs it in a worker thread
            # with no event loop of its own — asyncio.run() is correct and safe here.
            # If a future async caller changes that, the RuntimeError below turns it
            # into a normal TtsUnavailable (and thus the espeak fallback) rather than a 500.
            audio = asyncio.run(asyncio.wait_for(_render(), timeout=self._timeout_s))
        except asyncio.TimeoutError as exc:
            raise TtsUnavailable(
                f"edge-tts timed out after {self._timeout_s}s (no internet?)."
            ) from exc
        except RuntimeError as exc:   # already inside a running loop
            raise TtsUnavailable(f"Could not run edge-tts: {exc}") from exc
        except Exception as exc:
            # Network errors, DNS failures, a Microsoft-side change, an unknown voice
            # name. Anything at all here means "no audio", which the seam's contract
            # says must be raised, never returned as silence.
            raise TtsUnavailable(f"edge-tts failed: {type(exc).__name__}: {exc}") from exc

        if len(audio) < MIN_AUDIO_BYTES:
            raise TtsUnavailable("edge-tts returned no audible audio.")
        return audio
