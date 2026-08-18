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

    @property
    def cooldown_key(self) -> str:
        """The identity a rate-limit cooldown applies to: the bucket AND the model.

        S42: a shared-pool 429 on OpenRouter is reported PER MODEL — the provider's own
        message says so ("<model> is temporarily rate-limited upstream"). Cooling down
        the whole bucket on that answer would skip sibling models that are perfectly
        available, which is how one busy free model used to take the entire universal
        fallback down with it. ``module_events.provider`` still records the bucket key,
        so the stored shape is unchanged.
        """
        return f"{self.key}|{self.model}"


def split_models(value: str) -> list[str]:
    """One model setting -> the ordered list of model ids it names.

    S42: a bucket may name SEVERAL models, comma-separated. This exists because of a
    measured failure: ``google/gemma-4-31b-it:free`` answered 429 from OpenRouter's
    shared upstream pool while three sibling ``:free`` models answered the identical
    request correctly in the same minute. A bucket pinned to exactly one id therefore
    inherits that one id's luck, and the bucket in question is ADR-0026's UNIVERSAL
    FALLBACK — the last thing that should be fragile. A single id (no comma) keeps
    behaving exactly as before, so every existing configuration is unaffected.
    """
    return [m.strip() for m in (value or "").split(",") if m.strip()]


def get_provider(key: str, settings: Settings | None = None) -> ProviderConfig:
    """The bucket's PRIMARY entry (its first model). Kept for callers that want one
    ProviderConfig per bucket — the key checker and the tests."""
    variants = provider_variants(key, settings)
    if not variants:
        raise ValueError(f"Provider '{key}' names no model.")
    return variants[0]


def provider_variants(key: str, settings: Settings | None = None) -> list[ProviderConfig]:
    """Every (bucket, model) attempt this bucket offers, in configured order."""
    s = settings or get_settings()
    registry: dict[str, tuple[str, str, str]] = {
        GEMINI_FLASH: (s.gemini_api_key, s.gemini_base_url, s.gemini_flash_model),
        GEMINI_FLASH_LITE: (s.gemini_api_key, s.gemini_base_url, s.gemini_flash_lite_model),
        GROQ: (s.groq_api_key, "https://api.groq.com/openai/v1", s.groq_model),
        OPENROUTER: (s.openrouter_api_key, "https://openrouter.ai/api/v1", s.openrouter_model),
        CEREBRAS: (s.cerebras_api_key, s.cerebras_base_url, s.cerebras_model),
        MISTRAL: (s.mistral_api_key, s.mistral_base_url, s.mistral_model),
    }
    if key not in registry:
        raise ValueError(f"Unknown LLM provider key '{key}'. Expected one of: {sorted(registry)}")
    api_key, base_url, models = registry[key]
    return [ProviderConfig(key, api_key, base_url, m) for m in split_models(models)]


def provider_chain_for_module(module_code: str, settings: Settings | None = None) -> list[ProviderConfig]:
    """The attempts to make for a module, in order: its assigned bucket, then every
    provider in FALLBACK_ORDER — skipping any without a configured key. Unknown
    module codes (future M16+) start from Gemini Flash then the same fallbacks.

    S42: a bucket that names several models contributes one attempt PER MODEL, so the
    chain is a list of (bucket, model) attempts rather than one entry per bucket.
    A bucket naming a single model contributes exactly one entry, as it always did.
    """
    s = settings or get_settings()
    assigned = MODULE_PROVIDERS.get(module_code) or GEMINI_FLASH
    keys = [assigned] + [k for k in FALLBACK_ORDER if k != assigned]
    chain: list[ProviderConfig] = []
    for k in keys:
        chain.extend(p for p in provider_variants(k, s) if p.configured)
    return chain
