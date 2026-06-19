"""Speech-to-text service: swappable STT providers behind one interface."""

from backend.app.services.stt.base import ProviderInfo, STTProvider
from backend.app.services.stt.registry import get_provider, list_providers

__all__ = ["ProviderInfo", "STTProvider", "get_provider", "list_providers"]
