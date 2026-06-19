"""Browser Web Speech API provider (the default, quick-start path).

Transcription happens entirely in the browser (Chrome/Edge, Google's engine),
so there is no server-side audio or transcribe() call. This class exists only so
the provider appears in the dropdown with a consistent interface; the frontend
additionally checks `window.SpeechRecognition` before enabling it.
"""

from __future__ import annotations

from backend.app.services.stt.base import ProviderInfo, STTProvider


class BrowserWebSpeechProvider(STTProvider):
    id = "browser_webspeech"
    label = "Browser Web Speech API (live)"
    kind = "browser"

    def info(self) -> ProviderInfo:
        # Server-side it is always "available"; the frontend additionally checks
        # window.SpeechRecognition and marks it unsupported if the browser lacks it.
        return ProviderInfo(
            id=self.id,
            label=self.label,
            kind=self.kind,
            status="available",
            installed=True,
            configured=True,
            ready=True,
            detail="Live, in-browser (Chrome/Edge). Requires internet.",
        )
