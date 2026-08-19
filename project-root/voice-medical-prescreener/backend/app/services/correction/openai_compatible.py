"""OpenAI-compatible Corrector.

One implementation covers Gemini (now) and Groq / OpenRouter (later), because all
three speak the OpenAI Chat Completions protocol. Choosing a provider is purely a
config change (CORRECTION_PROVIDER + the matching key/base_url) — no code change.

Run a manual live check (needs a real key in backend/.env), from the project root:

    python -m backend.app.services.correction.openai_compatible "ami onek jor onuvob korchi"
"""

from __future__ import annotations

from openai import OpenAI

from backend.app.core import llm_providers
from backend.app.core.config import Settings, get_settings
from backend.app.services.correction.base import Corrector

# Strict, correction-only instruction. The model fixes spelling/grammar of the
# utterance and returns ONLY the corrected text — it must not diagnose, translate,
# summarize, or invent symptoms (constitution rules #1 and #2).
SYSTEM_PROMPT = (
    "You are a careful text corrector for a medical pre-screening system in "
    "Bangladesh. The input is one patient utterance in Bangla, Banglish "
    "(Bangla-English mixed), Roman/phonetic Bangla, or a regional dialect.\n"
    "Your ONLY job is to fix obvious spelling and grammar mistakes so the text "
    "reads cleanly in its original language/script.\n"
    "Strict rules:\n"
    "- Do NOT add, remove, translate, summarize, reorder, or infer any symptom, "
    "meaning, or medical detail.\n"
    "- Do NOT diagnose or comment.\n"
    "- Keep the same language and script as the input (do not convert Banglish or "
    "Roman Bangla into Bangla script unless it already is Bangla).\n"
    "- If the text is already fine, return it unchanged.\n"
    "- Return ONLY the corrected text, with no quotes, labels, or explanation."
)

# ⚠ S43 — CORRECTION_PROVIDER names one of the buckets in the ONE provider registry.
# Until now this file carried its own copy of Groq's and OpenRouter's base URLs, so the
# project had two places that had to agree about where a provider lives. They are
# published endpoints and they do move (S41 and S42 both had to chase a provider's
# changed configuration), and a second copy is a thing that gets updated once.
# `backend.app.core.llm_providers` is the registry the whole pipeline resolves through;
# this now reads the same rows instead of restating them.
_CORRECTION_BUCKETS = {
    "gemini": llm_providers.GEMINI_FLASH,     # uses the configurable gemini_base_url
    "groq": llm_providers.GROQ,
    "openrouter": llm_providers.OPENROUTER,
}


class OpenAICompatibleCorrector(Corrector):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        provider: str = "gemini",
        timeout: float = 30.0,
    ) -> None:
        self.provider = provider
        self.model = model
        # Constructing the client does NOT make a network call.
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def correct(self, raw_text: str) -> str:
        # Nothing to correct (and don't waste an API call / quota on whitespace).
        if not raw_text.strip():
            return raw_text

        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0,  # deterministic: we want correction, not creativity
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
        )
        corrected = response.choices[0].message.content or ""
        # Strip only the *corrected* string's surrounding whitespace. The raw text
        # is handled by the caller and is never touched here.
        return corrected.strip()


def build_corrector(settings: Settings | None = None) -> OpenAICompatibleCorrector:
    """Build the corrector for the configured provider.

    Raises ValueError for an unknown provider and RuntimeError if its key is missing.
    """
    settings = settings or get_settings()
    provider = settings.correction_provider.lower().strip()

    bucket = _CORRECTION_BUCKETS.get(provider)
    if bucket is None:
        raise ValueError(
            f"Unknown CORRECTION_PROVIDER '{settings.correction_provider}'. "
            f"Expected one of: {', '.join(_CORRECTION_BUCKETS)}."
        )
    api_key, base_url = llm_providers.provider_credentials(bucket, settings)

    if not api_key:
        raise RuntimeError(
            f"No API key configured for provider '{provider}'. "
            "Set the matching key in backend/.env."
        )

    return OpenAICompatibleCorrector(
        api_key=api_key,
        base_url=base_url,
        model=settings.correction_model,
        provider=provider,
    )


if __name__ == "__main__":  # pragma: no cover - manual live check, run by a human
    import sys

    sample = " ".join(sys.argv[1:]) or "ami onek jor onuvob korchi ar mathao betha korche"
    corrector = build_corrector()
    print(f"provider/model : {corrector.provider} / {corrector.model}")
    print(f"RAW            : {sample}")
    print(f"CORRECTED      : {corrector.correct(sample)}")
