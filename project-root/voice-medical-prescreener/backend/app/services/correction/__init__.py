"""Text-correction service (Module 2, Phase 0: one swappable LLM corrector)."""

from backend.app.services.correction.base import Corrector
from backend.app.services.correction.openai_compatible import (
    OpenAICompatibleCorrector,
    build_corrector,
)

__all__ = ["Corrector", "OpenAICompatibleCorrector", "build_corrector"]
