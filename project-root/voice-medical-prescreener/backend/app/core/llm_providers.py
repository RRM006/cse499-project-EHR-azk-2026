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
    # S44: which credential slot of the bucket this attempt uses, 1-based. It is an
    # INDEX, never the key itself — nothing anywhere prints or logs `api_key`.
    key_index: int = 1

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def label(self) -> str:
        """How this attempt is named in a log line. Safe by construction: bucket, slot
        number and model id only."""
        return f"{self.key} key {self.key_index} [{self.model}]"

    @property
    def cooldown_key(self) -> str:
        """The identity a rate-limit cooldown applies to: the bucket, the CREDENTIAL and
        the model.

        S42: a shared-pool 429 on OpenRouter is reported PER MODEL — the provider's own
        message says so ("<model> is temporarily rate-limited upstream"). Cooling down
        the whole bucket on that answer would skip sibling models that are perfectly
        available, which is how one busy free model used to take the entire universal
        fallback down with it.

        ⚠ S44 adds the credential slot, and it is the crux of the multi-key change: a
        free-tier quota belongs to an ACCOUNT. Key 1 hitting its daily 429 says nothing
        whatsoever about key 2, so a cooldown that did not distinguish them would put
        two perfectly good quotas to sleep on the evidence of a third. Cooldowns stay
        time-based and in-process, so a key is never permanently abandoned.

        ``module_events.provider`` still records the bucket key alone, so the stored
        shape is unchanged and no credential slot reaches the database.
        """
        return f"{self.key}#{self.key_index}|{self.model}"


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
    """The bucket's PRIMARY entry — its first credential and first model. Kept for
    callers that want one ProviderConfig per bucket (the tests, and anything that only
    needs the endpoint)."""
    variants = provider_variants(key, settings)
    if not variants:
        raise ValueError(f"Provider '{key}' names no model.")
    return variants[0]


def dedup_keys(values: list[str]) -> list[str]:
    """An ordered credential list from raw settings values: blanks dropped, whitespace
    stripped, duplicates removed while keeping the first position.

    S44. Duplicates are removed because the same key pasted into two slots is not two
    quotas — trying it twice would spend the patient's time proving the same 429 again,
    and would make the "3 keys configured" report a lie about the redundancy actually
    available. Order is preserved because slot order IS the fallback order.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        v = (raw or "").strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _registry(s: Settings) -> dict[str, tuple[list[str], str, str]]:
    """bucket key -> (ordered api keys, base_url, model setting). The ONE place a
    provider's endpoint and credentials are written down; everything that needs to reach
    a provider reads it here.

    ⚠ S44 — the first element is a LIST. A free tier is metered per ACCOUNT, so three
    keys for one provider are three independent quotas, and the natural place to try
    them is inside the bucket that already owns that provider's endpoint and models.
    The slot order is ``[<BARE>, _1, _2, _3]``: an existing .env that sets only
    ``GEMINI_API_KEY`` is a one-element list and behaves exactly as it always did, and a
    new .env may use the numbered slots alone.

    Cerebras and Mistral keep a single slot each — they are optional extra BUCKETS
    (ADR-0026), and nothing has asked them to hold several accounts.
    """
    return {
        GEMINI_FLASH: (
            dedup_keys([s.gemini_api_key, s.gemini_api_key_1, s.gemini_api_key_2,
                        s.gemini_api_key_3]),
            s.gemini_base_url, s.gemini_flash_model),
        GEMINI_FLASH_LITE: (
            dedup_keys([s.gemini_api_key, s.gemini_api_key_1, s.gemini_api_key_2,
                        s.gemini_api_key_3]),
            s.gemini_base_url, s.gemini_flash_lite_model),
        GROQ: (
            dedup_keys([s.groq_api_key, s.groq_api_key_1, s.groq_api_key_2, s.groq_api_key_3]),
            "https://api.groq.com/openai/v1", s.groq_model),
        OPENROUTER: (
            dedup_keys([s.openrouter_api_key, s.openrouter_api_key_1, s.openrouter_api_key_2,
                        s.openrouter_api_key_3]),
            "https://openrouter.ai/api/v1", s.openrouter_model),
        CEREBRAS: (dedup_keys([s.cerebras_api_key]), s.cerebras_base_url, s.cerebras_model),
        MISTRAL: (dedup_keys([s.mistral_api_key]), s.mistral_base_url, s.mistral_model),
    }


# The .env variable names each bucket reads for its credentials, IN SLOT ORDER.
# ⚠ This lives beside _registry because it is the registry's other half: the names a
# human types and the values the code reads have to describe the same slots, or a
# report tells the operator to edit a line that nothing reads. A test asserts every
# name here maps to a real Settings field, so the two cannot drift apart.
# Cerebras and Mistral have ONE slot each — they are optional extra buckets, not
# accounts anyone has three of.
_GEMINI_KEY_ENVS = ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]
KEY_ENV_NAMES: dict[str, list[str]] = {
    GEMINI_FLASH: _GEMINI_KEY_ENVS,
    GEMINI_FLASH_LITE: _GEMINI_KEY_ENVS,
    GROQ: ["GROQ_API_KEY", "GROQ_API_KEY_1", "GROQ_API_KEY_2", "GROQ_API_KEY_3"],
    OPENROUTER: ["OPENROUTER_API_KEY", "OPENROUTER_API_KEY_1", "OPENROUTER_API_KEY_2",
                 "OPENROUTER_API_KEY_3"],
    CEREBRAS: ["CEREBRAS_API_KEY"],
    MISTRAL: ["MISTRAL_API_KEY"],
}


def _bucket(key: str, s: Settings) -> tuple[list[str], str, str]:
    registry = _registry(s)
    if key not in registry:
        raise ValueError(f"Unknown LLM provider key '{key}'. Expected one of: {sorted(registry)}")
    return registry[key]


def provider_api_keys(key: str, settings: Settings | None = None) -> list[str]:
    """The bucket's configured credentials, in the order they will be tried.

    ⚠ Returns SECRET VALUES. Callers may count them, compare them and pass them to a
    client; nothing may print, log or persist them. ``check_api_keys`` uses this to
    report how many slots are filled and reports only the count and the slot number.
    """
    return _bucket(key, settings or get_settings())[0]


def provider_credentials(key: str, settings: Settings | None = None) -> tuple[str, str]:
    """(first api_key, base_url) for a bucket, independent of which model it names.

    S43: the Module-2 ``Corrector`` seam picks its own model (CORRECTION_MODEL) but
    still has to reach a real endpoint, and it used to keep a private copy of Groq's
    and OpenRouter's base URLs to do so. This exists so it can read the registry
    instead — one place where a provider's address is recorded.

    S44: with several credentials configured this returns the FIRST. That is a
    deliberate limit rather than an oversight — the corrector is a single-shot seam with
    no chain of its own (see ADR-0069), so it uses slot 1 and fails honestly, exactly as
    it did before. The empty string is returned when the bucket has no key at all, which
    is what ``build_corrector`` already turns into a RuntimeError naming backend/.env.
    """
    keys, base_url, _ = _bucket(key, settings or get_settings())
    return (keys[0] if keys else ""), base_url


def provider_variants(key: str, settings: Settings | None = None) -> list[ProviderConfig]:
    """Every attempt this bucket offers, in order: for each CREDENTIAL, each MODEL.

    ⚠ S44 — key-major, and the nesting is the decision. Trying every model of key 1
    before moving to key 2 is right for both failure modes this project has actually
    measured: an OpenRouter ``:free`` 429 comes from a shared per-model queue, where a
    sibling model on the SAME key is the thing likely to answer; a daily-quota 429 is
    per account, where only another key helps, and by then every model of the exhausted
    key has been ruled out anyway. Model-major would interleave the two and make the
    order impossible to state in one sentence.

    A bucket with one key and one model yields exactly one attempt, as it always did.

    ⚠ An empty list means the bucket names NO model, or holds no key. Those are not the
    same thing — see ``misconfigured_buckets()``, which exists because the two used to
    be reported identically and the report was wrong.
    """
    keys, base_url, models = _bucket(key, settings or get_settings())
    model_ids = split_models(models)
    return [
        ProviderConfig(key, api_key, base_url, model, index)
        for index, api_key in enumerate(keys, start=1)
        for model in model_ids
    ]


def misconfigured_buckets(settings: Settings | None = None) -> list[str]:
    """Buckets that hold at least one KEY but whose model setting is blank, in registry
    order.

    ⚠ S43 — a silent configuration error, and the demo-relevant kind. Blanking
    ``GROQ_MODEL=`` or ``OPENROUTER_MODEL=`` in .env makes ``split_models`` return an
    empty list, which makes ``provider_variants`` return nothing, which makes
    ``provider_chain_for_module`` skip the bucket entirely — with perfectly good keys
    sitting in .env and nothing anywhere saying so. The universal fallback can be
    deleted by one blank line. ``check_api_keys`` was reporting exactly this case as
    "not set", i.e. blaming the key.

    A bucket with no key at all is NOT listed: that is a bucket the operator simply did
    not configure, which is the normal, intended state for the optional ones.
    """
    s = settings or get_settings()
    return [
        key for key, (keys, _base, models) in _registry(s).items()
        if keys and not split_models(models)
    ]


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
