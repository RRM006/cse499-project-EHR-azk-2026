"""Verify the configured LLM API keys work — WITHOUT ever printing one.

Written for the key rotation that has been pending since S25. Rotating a key is a
manual, credential-bound job only a human can do (log in to the provider, revoke the
old key, create a new one, paste it into ``backend/.env``). What a script *can* do
safely is the step after: prove the new key actually works, before a demo depends on it.

    .venv\\Scripts\\python.exe -m backend.scripts.check_api_keys          (Windows)
    .venv/bin/python -m backend.scripts.check_api_keys                   (Linux)

⚠ SAFETY PROPERTIES, which are the whole point of this file:

  * **A key value is never printed, logged, or written anywhere.** Only its presence,
    its length, and the provider's verdict are reported. A key is a credential; a
    terminal is a place screenshots come from.
  * It reads the SAME registry the application uses
    (``backend.app.core.llm_providers``), so it cannot drift from what the pipeline
    actually calls, and it needs no second copy of any base URL or model name.
  * It sends one tiny, cheap completion per provider — enough to prove authentication,
    not enough to matter against a free daily quota.
  * Nothing here touches the database or any patient data.

Exit code is 0 when every CONFIGURED provider authenticates, 1 otherwise, so it can gate
a demo checklist.
"""

from __future__ import annotations

import sys

from backend.app.core.config import get_settings
from backend.app.core.llm_providers import (
    CEREBRAS,
    GEMINI_FLASH,
    GEMINI_FLASH_LITE,
    GROQ,
    KEY_ENV_NAMES,
    MISTRAL,
    OPENROUTER,
    misconfigured_buckets,
    provider_api_keys,
    provider_variants,
)

# The three providers the project actually depends on (ADR-0026's independent buckets),
# followed by the two optional extras. Flash and Flash-Lite deliberately share the
# GEMINI credentials, so probing both would spend requests re-testing the same keys —
# Flash-Lite is listed for completeness and skipped when its key SET matches Flash's.
# ⚠ S44: the second element is the BASE env name. The bucket's real slots are that name
# plus `_1`, `_2`, `_3` — see slot_env_names() and llm_providers.provider_api_keys().
PROBE_ORDER = [
    (GEMINI_FLASH, "GEMINI_API_KEY", "https://aistudio.google.com/apikey"),
    (GROQ, "GROQ_API_KEY", "https://console.groq.com/keys"),
    (OPENROUTER, "OPENROUTER_API_KEY", "https://openrouter.ai/settings/keys"),
    (CEREBRAS, "CEREBRAS_API_KEY", "https://cloud.cerebras.ai"),
    (MISTRAL, "MISTRAL_API_KEY", "https://console.mistral.ai/api-keys"),
    (GEMINI_FLASH_LITE, "GEMINI_API_KEY", "https://aistudio.google.com/apikey"),
]


def _probe(provider) -> tuple[bool, str]:
    """One minimal completion. Returns (ok, short human-readable verdict)."""
    try:
        from openai import OpenAI
    except ImportError:  # pragma: no cover - the venv always has it
        return False, "the openai package is not installed in this environment"

    client = OpenAI(api_key=provider.api_key, base_url=provider.base_url, timeout=20.0)
    try:
        client.chat.completions.create(
            model=provider.model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        return True, "authenticated"
    except Exception as exc:  # noqa: BLE001 - every failure mode is reported, not raised
        text = str(exc)
        lowered = text.lower()
        # ⚠ Never echo the exception verbatim: a provider that rejects a key sometimes
        # quotes it back in the error body, and this function's contract is that no key
        # value reaches the terminal.
        # ⚠ S42 — ORDER IS LOAD-BEARING, and getting it wrong cost real trust. Groq's
        # reply for a decommissioned model is a 404 whose body reads
        # `'type': 'invalid_request_error'`. The old order tested "invalid" FIRST, so a
        # perfectly valid credential was reported as "REJECTED — the key is wrong,
        # revoked, or not yet active" and the human was sent to rotate it. A checker
        # that accuses a good key of being bad is worse than no checker. The model
        # verdict is therefore decided BEFORE the credential verdict, and the
        # credential test no longer keys on the bare word "invalid".
        if "404" in text or "model_not_found" in lowered or "does not exist" in lowered:
            return False, "key OK, but the configured MODEL was not found (rotate the MODEL, not the key)"
        if "401" in text or "unauthor" in lowered or "invalid api key" in lowered                 or "invalid_api_key" in lowered:
            return False, "REJECTED — the key is wrong, revoked, or not yet active"
        if "429" in text or "quota" in lowered or "rate limit" in lowered:
            # The key is valid; the free tier is simply spent for now.
            return True, "authenticated (free quota currently exhausted — 429)"
        if "timeout" in lowered or "connect" in lowered:
            return False, "network problem — could not reach the provider"
        return False, f"failed ({type(exc).__name__})"


def report_slots(bucket: str, settings) -> int:
    """Print which credential SLOTS this bucket holds, and return how many.

    ⚠ S44 — the report the human reads before a demo. It prints the slot NUMBER and
    whether it is filled, and never the key. A gap is stated plainly rather than
    alarmingly: sparse configuration is legal, and a bucket with two of three slots
    filled is a bucket with two working quotas, not a broken one.

    The env names come from the registry (``KEY_ENV_NAMES``), so this can never tell an
    operator to edit a variable nothing reads.
    """
    names = KEY_ENV_NAMES[bucket]
    configured = len(provider_api_keys(bucket, settings))
    # Which .env NAMES are empty — read from the settings field each name maps to
    # (pydantic-settings is case-insensitive, so the field is the lower-cased name).
    # ⚠ Only emptiness is read here; no value is ever held, compared or printed.
    empty = [n for n in names if not str(getattr(settings, n.lower(), "") or "").strip()]
    print(f"  {bucket}:")
    if not configured:
        print(f"      no key set in {' / '.join(names)} — bucket skipped")
        return 0
    for i in range(1, configured + 1):
        print(f"      key {i} configured")
    if empty:
        print(f"      empty slot(s): {', '.join(empty)} — each extra key is another "
              "free daily quota")
    return configured


def main() -> int:
    settings = get_settings()
    print("Checking configured API keys. No key value is ever printed.\n")

    seen_keys: set[tuple[str, ...]] = set()
    failures = 0
    checked = 0
    # S43: buckets holding a valid key that name no model at all. Reported as their own
    # verdict below, because the old code printed "not set" for them — blaming a key
    # that is present and fine, and hiding the .env line that actually needs attention.
    broken_config = set(misconfigured_buckets(settings))

    for key, env_name, console_url in PROBE_ORDER:
        if key in broken_config:
            checked += 1
            failures += 1
            print(f"  {key}: key(s) ARE set but this bucket names NO MODEL")
            print(f"      set {key.upper()}_MODEL in backend/.env (or leave it unset to "
                  "use the shipped default) — this bucket is currently skipped entirely")
            continue

        # S44: the slot inventory first, because it answers the question the human
        # actually has ("did all nine keys land?") without spending a single request.
        if report_slots(key, settings) == 0:
            continue
        variants = provider_variants(key, settings)
        fingerprint = tuple(sorted({p.api_key for p in variants}))
        if fingerprint in seen_keys:
            print("      same credential(s) as above — not re-probed")
            continue
        seen_keys.add(fingerprint)

        # S42: a bucket may name several models. S44: and several credentials. Probe
        # EVERY (slot, model) attempt — the whole point of both lists is that one dead
        # combination must not condemn the bucket, so the report has to say WHICH ones
        # work. ⚠ The bucket passes if ANY attempt answers: a missing or spent key 2
        # must never be reported as "the provider is unavailable" while key 1 works.
        checked += 1
        bucket_ok = False
        for provider in variants:
            ok, verdict = _probe(provider)
            bucket_ok = bucket_ok or ok
            mark = "PASS" if ok else "FAIL"
            print(f"      key {provider.key_index} [{provider.model}]  {mark} — {verdict}")
        if not bucket_ok:
            failures += 1
            print(f"      {env_name}: every configured key failed — rotate or fix at: {console_url}")

    print()
    if not checked:
        print("No provider keys are configured. Set them in backend/.env (never in git).")
        return 1
    if failures:
        print(f"{failures} of {checked} provider bucket(s) FAILED. See the URLs above.")
        return 1
    print(f"All {checked} configured credential(s) authenticated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
