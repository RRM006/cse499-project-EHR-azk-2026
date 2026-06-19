"""BanglaSpeech2Text provider — offline Bangla-finetuned Whisper.

IMPORTANT: we do NOT use the `banglaspeech2text` PyPI package. It is unmaintained
and pins `huggingface-hub==0.11.1`, which conflicts with faster-whisper and breaks
installation. Instead we run the SAME underlying models (shhossain/whisper-*-bn,
the ones that package wraps) directly through `transformers`, which is maintained
and shares a modern huggingface-hub with the other engines.

Install: requirements-banglaspeech.txt (transformers + torch). Lazy-imported and
cached after first load.
"""

from __future__ import annotations

import importlib.util

from backend.app.services.stt.base import ProviderInfo, STTProvider


def _installed() -> bool:
    return (
        importlib.util.find_spec("transformers") is not None
        and importlib.util.find_spec("torch") is not None
    )


class BanglaSpeech2TextProvider(STTProvider):
    id = "banglaspeech2text"
    label = "BanglaSpeech2Text (offline Bangla, via transformers)"
    kind = "server"

    _pipe = None  # cached transformers ASR pipeline

    def _model_id(self) -> str:
        # Explicit override wins; otherwise derive from the size (tiny|base|small).
        return self._settings.banglaspeech_model or f"shhossain/whisper-{self._settings.banglaspeech_model_size}-bn"

    def info(self) -> ProviderInfo:
        if not _installed():
            return ProviderInfo(
                self.id, self.label, self.kind, "missing_package",
                installed=False, configured=False, ready=False,
                detail="Install requirements-banglaspeech.txt (transformers + torch).",
            )
        return ProviderInfo(
            self.id, self.label, self.kind, "available",
            installed=True, configured=True, ready=True,
            detail=f"Local - model '{self._model_id()}'; auto-downloads on first run.",
        )

    def _get_pipe(self):
        if BanglaSpeech2TextProvider._pipe is None:
            from transformers import pipeline

            BanglaSpeech2TextProvider._pipe = pipeline(
                "automatic-speech-recognition", model=self._model_id(), device="cpu"
            )
        return BanglaSpeech2TextProvider._pipe

    def transcribe(self, audio_bytes: bytes, mimetype: str, language: str = "bn") -> str:
        from backend.app.services.stt.audio import decode_to_mono16k

        samples, sr = decode_to_mono16k(audio_bytes)
        result = self._get_pipe()({"raw": samples, "sampling_rate": sr})
        return str(result.get("text", "")).strip()
