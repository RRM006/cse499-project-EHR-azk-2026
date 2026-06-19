"""Local Whisper provider via faster-whisper (CTranslate2, int8, CPU).

Lazy-imports faster_whisper so the core app runs without requirements-local.txt;
until installed, this provider reports "not_configured". The model is loaded once
and cached on the class.
"""

from __future__ import annotations

import importlib.util

from backend.app.services.stt.base import ProviderInfo, STTProvider


def _installed() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


class LocalWhisperProvider(STTProvider):
    id = "local_whisper"
    label = "Local Whisper (faster-whisper, CPU)"
    kind = "server"

    _model = None  # cached WhisperModel across requests

    def info(self) -> ProviderInfo:
        if not _installed():
            return ProviderInfo(
                self.id, self.label, self.kind, "missing_package",
                installed=False, configured=False, ready=False,
                detail="Install requirements-whisper.txt (faster-whisper).",
            )
        # Model weights auto-download from Hugging Face on first use.
        return ProviderInfo(
            self.id, self.label, self.kind, "available",
            installed=True, configured=True, ready=True,
            detail=f"Local - model '{self._settings.whisper_model_size}' (int8 CPU); "
                   "auto-downloads on first run.",
        )

    def _get_model(self):
        if LocalWhisperProvider._model is None:
            from faster_whisper import WhisperModel

            LocalWhisperProvider._model = WhisperModel(
                self._settings.whisper_model_size, device="cpu", compute_type="int8"
            )
        return LocalWhisperProvider._model

    def transcribe(self, audio_bytes: bytes, mimetype: str, language: str = "bn") -> str:
        from backend.app.services.stt.audio import decode_to_mono16k

        samples, _ = decode_to_mono16k(audio_bytes)
        segments, _ = self._get_model().transcribe(
            samples, language=language or None, vad_filter=True
        )
        return "".join(segment.text for segment in segments).strip()
