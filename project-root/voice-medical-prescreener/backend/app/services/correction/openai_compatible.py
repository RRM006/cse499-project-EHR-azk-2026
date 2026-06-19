"""OpenAI-compatible Corrector.

One implementation covers Gemini (now) and Groq / OpenRouter (later), because all
three speak the OpenAI Chat Completions protocol. Choosing a provider is purely a
config change (CORRECTION_PROVIDER + the matching key/base_url) — no code change.

Run a manual live check (needs a real key in backend/.env), from the project root:

    python -m backend.app.services.correction.openai_compatible "ami onek jor onuvob korchi"
"""

from __future__ import annotations

from openai import OpenAI

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

# OpenAI-compatible base URLs for the providers we may use.
_PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    # gemini uses settings.gemini_base_url (configurable), handled below.
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

    if provider == "gemini":
        api_key = settings.gemini_api_key
        base_url = settings.gemini_base_url
    elif provider == "groq":
        api_key = settings.groq_api_key
        base_url = _PROVIDER_BASE_URLS["groq"]
    elif provider == "openrouter":
        api_key = settings.openrouter_api_key
        base_url = _PROVIDER_BASE_URLS["openrouter"]
    else:
        raise ValueError(
            f"Unknown CORRECTION_PROVIDER '{settings.correction_provider}'. "
            "Expected one of: gemini, groq, openrouter."
        )

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
