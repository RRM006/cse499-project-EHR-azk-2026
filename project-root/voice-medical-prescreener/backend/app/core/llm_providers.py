"""LLM provider registry (ADR-0026): three independent free quota buckets + fallback.

Every provider is OpenAI-compatible, so one client covers all of them; which bucket
serves which module is DATA here, not branching in pipeline code (principle 8).
Everything resolves from settings/.env — nothing hardcoded.
"""

from dataclasses import dataclass

from backend.app.core.config import Settings, get_settings

GEMINI_FLASH = "gemini_flash"
GEMINI_FLASH_LITE = "gemini_flash_lite"
GROQ = "groq"
OPENROUTER = "openrouter"
CEREBRAS = "cerebras"
MISTRAL = "mistral"

# ADR-0026: quality tasks -> Flash; cheap structured extraction -> Flash-Lite;
# live-loop tasks -> Groq; OpenRouter :free is the universal fallback for all.
MODULE_PROVIDERS: dict[str, str] = {
    "M2": GEMINI_FLASH,
    "M3": GEMINI_FLASH_LITE,
    "M4": GEMINI_FLASH,
    "M6": GROQ,
    "M7": GROQ,
    "M8": GEMINI_FLASH_LITE,
    "M10": GEMINI_FLASH,  # base classification only — the red-flag RULE is local
    "M10C": GEMINI_FLASH,  # C1 suggested condition — separate call, never mixed into M10
    "M11": GEMINI_FLASH,
    "M12": GEMINI_FLASH,
    "M16": GEMINI_FLASH,  # P3-3 doctor drug-info assistant — quality/safety task
}
FALLBACK_PROVIDER = OPENROUTER

# Universal fallback order when the assigned bucket fails or is cooling down after
# a rate-limit hit. Groq first (largest barely-used free quota, fastest), then the
# optional extra buckets (skipped automatically while their keys are blank), then
# OpenRouter LAST (only ~50 free req/day — too small to burn early). The Gemini
# buckets are deliberately NOT cross-fallbacks: they hold the quality-task quota.
FALLBACK_ORDER: list[str] = [GROQ, CEREBRAS, MISTRAL, OPENROUTER]


@dataclass(frozen=True)
class ProviderConfig:
    key: str
    api_key: str
    base_url: str
    model: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def get_provider(key: str, settings: Settings | None = None) -> ProviderConfig:
    s = settings or get_settings()
    registry = {
        GEMINI_FLASH: ProviderConfig(
            GEMINI_FLASH, s.gemini_api_key, s.gemini_base_url, s.gemini_flash_model
        ),
        GEMINI_FLASH_LITE: ProviderConfig(
            GEMINI_FLASH_LITE, s.gemini_api_key, s.gemini_base_url, s.gemini_flash_lite_model
        ),
        GROQ: ProviderConfig(
            GROQ, s.groq_api_key, "https://api.groq.com/openai/v1", s.groq_model
        ),
        OPENROUTER: ProviderConfig(
            OPENROUTER, s.openrouter_api_key, "https://openrouter.ai/api/v1", s.openrouter_model
        ),
        CEREBRAS: ProviderConfig(
            CEREBRAS, s.cerebras_api_key, s.cerebras_base_url, s.cerebras_model
        ),
        MISTRAL: ProviderConfig(
            MISTRAL, s.mistral_api_key, s.mistral_base_url, s.mistral_model
        ),
    }
    if key not in registry:
        raise ValueError(f"Unknown LLM provider key '{key}'. Expected one of: {sorted(registry)}")
    return registry[key]


def provider_chain_for_module(module_code: str, settings: Settings | None = None) -> list[ProviderConfig]:
    """The providers to try for a module, in order: its assigned bucket, then every
    provider in FALLBACK_ORDER — skipping any without a configured key. Unknown
    module codes (future M16+) start from Gemini Flash then the same fallbacks.
    """
    s = settings or get_settings()
    assigned = MODULE_PROVIDERS.get(module_code) or GEMINI_FLASH
    keys = [assigned] + [k for k in FALLBACK_ORDER if k != assigned]
    chain = [get_provider(k, s) for k in keys]
    return [p for p in chain if p.configured]
