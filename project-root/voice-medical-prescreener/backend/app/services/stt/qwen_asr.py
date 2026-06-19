"""Qwen3-ASR-1.7B provider (local, CPU).

API (from the QwenLM/Qwen3-ASR README):
    from qwen_asr import Qwen3ASRModel
    model = Qwen3ASRModel.from_pretrained("Qwen/Qwen3-ASR-1.7B", ...)
    results = model.transcribe(audio=(np.ndarray, sr), language=None)
    results[0].text
We run CPU/float32 and feed a (16 kHz mono numpy, sr) tuple. This is the heaviest,
riskiest provider — verify Bangla quality and CPU latency before relying on it.
Lazy-imported; model cached after first load.
"""

from __future__ import annotations

import importlib.util
import os

from backend.app.services.stt.base import ProviderInfo, STTProvider

# Qwen takes language *names*, not codes. Map the common ones; unknown -> auto-detect.
_LANG_NAMES = {"bn": "Bengali", "en": "English"}

# Default Hugging Face model id used when QWEN_ASR_MODEL_DIR is empty (auto-download).
DEFAULT_QWEN_MODEL = "Qwen/Qwen3-ASR-1.7B"


def _installed() -> bool:
    return importlib.util.find_spec("qwen_asr") is not None


class QwenASRProvider(STTProvider):
    id = "qwen_asr"
    label = "Qwen3-ASR-1.7B (local, CPU)"
    kind = "server"

    _model = None  # cached Qwen3ASRModel

    def info(self) -> ProviderInfo:
        if not _installed():
            return ProviderInfo(
                self.id, self.label, self.kind, "missing_package",
                installed=False, configured=False, ready=False,
                detail="Install requirements-qwen.txt (qwen-asr + onnxruntime).",
            )
        # If a model dir is explicitly set but doesn't exist, that's a missing model.
        model_dir = self._settings.qwen_asr_model_dir
        if model_dir and not os.path.isdir(model_dir):
            return ProviderInfo(
                self.id, self.label, self.kind, "missing_model",
                installed=True, configured=False, ready=False,
                detail=f"QWEN_ASR_MODEL_DIR='{model_dir}' does not exist.",
            )
        source = "local dir" if model_dir else DEFAULT_QWEN_MODEL
        return ProviderInfo(
            self.id, self.label, self.kind, "available",
            installed=True, configured=True, ready=True,
            detail=f"Local - {source} (CPU). Heavy - expect high latency; "
                   "auto-downloads if no dir is set.",
        )

    def _get_model(self):
        if QwenASRProvider._model is None:
            import torch
            from qwen_asr import Qwen3ASRModel

            source = self._settings.qwen_asr_model_dir or DEFAULT_QWEN_MODEL
            QwenASRProvider._model = Qwen3ASRModel.from_pretrained(
                source, dtype=torch.float32, device_map="cpu", max_new_tokens=256
            )
        return QwenASRProvider._model

    def transcribe(self, audio_bytes: bytes, mimetype: str, language: str = "bn") -> str:
        from backend.app.services.stt.audio import decode_to_mono16k

        samples, sr = decode_to_mono16k(audio_bytes)
        results = self._get_model().transcribe(
            audio=(samples, sr), language=_LANG_NAMES.get(language or "", None)
        )
        return (results[0].text or "").strip()
