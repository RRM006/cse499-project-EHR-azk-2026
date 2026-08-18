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
    MISTRAL,
    OPENROUTER,
    provider_variants,
)

# The three keys the project actually depends on (ADR-0026's independent buckets),
# followed by the two optional extras. Flash and Flash-Lite deliberately share
# GEMINI_API_KEY, so probing both would spend two requests to test one credential —
# Flash-Lite is listed for completeness and skipped when its key matches Flash's.
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


def main() -> int:
    settings = get_settings()
    print("Checking configured API keys. No key value is ever printed.\n")

    seen_keys: set[str] = set()
    failures = 0
    checked = 0

    for key, env_name, console_url in PROBE_ORDER:
        variants = provider_variants(key, settings)
        if not variants or not variants[0].configured:
            print(f"  {key:<18} {env_name:<20} not set — skipped")
            continue
        if variants[0].api_key in seen_keys:
            print(f"  {key:<18} {env_name:<20} same credential as above — not re-probed")
            continue
        seen_keys.add(variants[0].api_key)

        # S42: a bucket may name several models. Probe EACH — the whole point of the
        # list is that one model being unusable must not condemn the bucket, so the
        # report has to say which models work, not just whether the first one does.
        # The credential passes if ANY of its models answers.
        checked += 1
        bucket_ok = False
        for provider in variants:
            ok, verdict = _probe(provider)
            bucket_ok = bucket_ok or ok
            mark = "PASS" if ok else "FAIL"
            label = f"{key} [{provider.model}]"
            print(f"  {label:<62} {mark} — {verdict}")
        if not bucket_ok:
            failures += 1
            print(f"       {env_name}: rotate or fix at: {console_url}")

    print()
    if not checked:
        print("No provider keys are configured. Set them in backend/.env (never in git).")
        return 1
    if failures:
        print(f"{failures} of {checked} credential(s) FAILED. See the URLs above.")
        return 1
    print(f"All {checked} configured credential(s) authenticated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
