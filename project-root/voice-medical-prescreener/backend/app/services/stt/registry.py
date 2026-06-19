"""STT provider registry.

The single place that knows the set of providers. Adding a provider = import its
class and add it to _PROVIDER_CLASSES; nothing else in the app changes.
"""

from __future__ import annotations

from functools import lru_cache

from backend.app.core.config import get_settings
from backend.app.services.stt.banglaspeech import BanglaSpeech2TextProvider
from backend.app.services.stt.base import ProviderInfo, STTProvider
from backend.app.services.stt.browser_webspeech import BrowserWebSpeechProvider
from backend.app.services.stt.groq_whisper import GroqWhisperProvider
from backend.app.services.stt.local_whisper import LocalWhisperProvider
from backend.app.services.stt.qwen_asr import QwenASRProvider

# Order here is the order shown in the frontend dropdown (default first).
_PROVIDER_CLASSES: list[type[STTProvider]] = [
    BrowserWebSpeechProvider,
    GroqWhisperProvider,
    LocalWhisperProvider,
    BanglaSpeech2TextProvider,
    QwenASRProvider,
]


@lru_cache
def _providers() -> dict[str, STTProvider]:
    settings = get_settings()
    return {cls.id: cls(settings) for cls in _PROVIDER_CLASSES}


def list_providers() -> list[ProviderInfo]:
    """Provider metadata + live status for the dropdown.

    A provider that throws while checking its own health is reported as an
    'error' rather than crashing the whole listing.
    """
    infos: list[ProviderInfo] = []
    for provider in _providers().values():
        try:
            infos.append(provider.info())
        except Exception as exc:  # never let one bad provider hide the rest
            infos.append(
                ProviderInfo(
                    id=getattr(provider, "id", "unknown"),
                    label=getattr(provider, "label", "unknown"),
                    kind=getattr(provider, "kind", "server"),
                    status="error",
                    installed=False,
                    configured=False,
                    ready=False,
                    detail=f"Initialization error: {exc}",
                )
            )
    return infos


def get_provider(provider_id: str) -> STTProvider:
    providers = _providers()
    if provider_id not in providers:
        raise KeyError(provider_id)
    return providers[provider_id]
