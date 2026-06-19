"""Groq Whisper-large-v3 provider (cloud, server-side).

Reuses the OpenAI-compatible `openai` SDK (already a core dependency) pointed at
Groq's base URL. No heavy local install needed — only a GROQ_API_KEY.
"""

from __future__ import annotations

from backend.app.services.stt.base import ProviderInfo, STTProvider

# MediaRecorder mimetype -> a filename extension Groq/Whisper recognizes.
_MIME_EXT = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp4": "mp4",
    "audio/m4a": "m4a",
}


def _ext_for(mimetype: str) -> str:
    return _MIME_EXT.get((mimetype or "").split(";")[0].strip(), "webm")


class GroqWhisperProvider(STTProvider):
    id = "groq_whisper"
    label = "Groq · Whisper Large v3 (cloud)"
    kind = "server"

    def info(self) -> ProviderInfo:
        # Uses the core `openai` SDK, so it is always "installed".
        has_key = bool(self._settings.groq_api_key)
        if not has_key:
            return ProviderInfo(
                self.id, self.label, self.kind, "missing_api_key",
                installed=True, configured=False, ready=False,
                detail="Set GROQ_API_KEY in backend/.env (then restart the server).",
            )
        return ProviderInfo(
            self.id, self.label, self.kind, "available",
            installed=True, configured=True, ready=True,
            detail=f"Cloud - model {self._settings.groq_stt_model}.",
        )

    def transcribe(self, audio_bytes: bytes, mimetype: str, language: str = "bn") -> str:
        if not self._settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not set in backend/.env")

        from openai import OpenAI

        client = OpenAI(
            api_key=self._settings.groq_api_key,
            base_url=self._settings.groq_base_url,
            timeout=60.0,
        )
        result = client.audio.transcriptions.create(
            model=self._settings.groq_stt_model,
            file=(f"audio.{_ext_for(mimetype)}", audio_bytes, mimetype),
            language=language or None,
        )
        return (result.text or "").strip()
