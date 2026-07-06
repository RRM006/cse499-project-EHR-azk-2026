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
}
FALLBACK_PROVIDER = OPENROUTER


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
    }
    if key not in registry:
        raise ValueError(f"Unknown LLM provider key '{key}'. Expected one of: {sorted(registry)}")
    return registry[key]


def provider_chain_for_module(module_code: str, settings: Settings | None = None) -> list[ProviderConfig]:
    """The providers to try for a module, in order: its assigned bucket, then the
    universal fallback — skipping any without a configured key. Unknown module codes
    (future M16+) get whatever is configured, fallback-first-last ordering preserved.
    """
    s = settings or get_settings()
    keys = []
    assigned = MODULE_PROVIDERS.get(module_code)
    if assigned:
        keys.append(assigned)
    if FALLBACK_PROVIDER not in keys:
        keys.append(FALLBACK_PROVIDER)
    if not assigned:
        # No assignment: try every configured bucket before the fallback.
        keys = [GEMINI_FLASH, GROQ, FALLBACK_PROVIDER]
    chain = [get_provider(k, s) for k in keys]
    return [p for p in chain if p.configured]
