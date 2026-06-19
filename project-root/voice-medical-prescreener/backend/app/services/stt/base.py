"""The STT provider interface — mirrors the Corrector pattern in ../correction.

Every speech-to-text engine (browser or server-side) implements this same small
interface, so the rest of the app treats them identically. Adding a new engine
later means writing one new subclass and registering it — no other code changes.

CONSTITUTION RULE #1: a provider only PRODUCES raw text. Storing it (verbatim,
write-once) and correcting it (separately) happen elsewhere.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Literal

from backend.app.core.config import Settings, get_settings

ProviderKind = Literal["browser", "server"]

# Machine-readable status codes. The frontend maps these to friendly labels.
#   available             -> ✅ ready to use
#   missing_api_key       -> ❌ a cloud provider has no key configured
#   missing_package       -> ❌ the Python package isn't installed
#   missing_model         -> ❌ the package is installed but model files are missing
#   unsupported_platform  -> ❌ can't run on this OS/arch
#   error                 -> ❌ something threw while checking (detail has the message)
ProviderStatus = Literal[
    "available",
    "missing_api_key",
    "missing_package",
    "missing_model",
    "unsupported_platform",
    "error",
]


@dataclass(frozen=True)
class ProviderInfo:
    """Health + metadata for one provider — drives the dropdown and debugging."""

    id: str
    label: str
    kind: ProviderKind
    status: ProviderStatus
    installed: bool   # is the required Python package importable?
    configured: bool  # is the key / model path that it needs present?
    ready: bool       # can it actually transcribe right now? (status == "available")
    detail: str = ""  # human-readable reason / extra info


class STTProvider(ABC):
    id: ClassVar[str]
    label: ClassVar[str]
    kind: ClassVar[ProviderKind]

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @abstractmethod
    def info(self) -> ProviderInfo:
        """Report id/label/kind and current availability for the dropdown."""
        raise NotImplementedError

    def transcribe(self, audio_bytes: bytes, mimetype: str, language: str = "bn") -> str:
        """Turn recorded audio into raw text (server providers only).

        Browser providers transcribe client-side and never call this.
        """
        raise NotImplementedError(f"Provider '{self.id}' does not transcribe server-side")
