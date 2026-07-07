"""LLM call seam for pipeline modules: assigned bucket -> automatic fallback,
with every attempt logged to module_events (provider, latency, status — the
observability half of the free-tier strategy, principles 5 & 8).

Quota-aware switching: when a provider answers 429 / quota-exceeded it is put on a
short in-process cooldown, so subsequent calls skip straight to a bucket that still
has free quota instead of burning requests on a known-dead provider. Fail-open: if
every provider is cooling down, the full chain is tried anyway.

Usage:  text = call_module(db, visit_id=..., module_code="M3", system=..., user=...)
Raises LLMCallError if the whole chain fails (an 'error' event is logged per attempt).
"""

from __future__ import annotations

import logging
import time

from openai import OpenAI
from sqlalchemy.orm import Session

from backend.app.core.llm_providers import ProviderConfig, provider_chain_for_module
from backend.app.db.models import ModuleEvent

logger = logging.getLogger(__name__)

# Cooldown lengths chosen from the providers' documented limit types: a plain RPM
# 429 clears within a minute; a daily-quota hit won't clear until the reset, so we
# back off much longer (still re-probing a few times an hour in case it was wrong).
RATE_LIMIT_COOLDOWN_S = 60.0
DAILY_QUOTA_COOLDOWN_S = 15 * 60.0

# provider key -> monotonic timestamp until which it should be skipped.
_cooldowns: dict[str, float] = {}


class LLMCallError(RuntimeError):
    """Every provider in the module's chain failed (or none is configured)."""


def reset_cooldowns() -> None:
    """Clear all provider cooldowns (used by tests and manual recovery)."""
    _cooldowns.clear()


def _on_cooldown(key: str) -> bool:
    until = _cooldowns.get(key)
    return until is not None and time.monotonic() < until


def _classify_and_cooldown(key: str, exc: Exception) -> None:
    """If the failure is a rate/quota limit, put the provider on cooldown."""
    msg = str(exc).lower()
    if "429" not in msg and "rate limit" not in msg and "quota" not in msg:
        return  # a non-quota failure (timeout, 5xx, bad key) — no cooldown
    daily = any(hint in msg for hint in ("per day", "daily", "rpd", "quota"))
    seconds = DAILY_QUOTA_COOLDOWN_S if daily else RATE_LIMIT_COOLDOWN_S
    _cooldowns[key] = time.monotonic() + seconds
    logger.warning("provider %s on cooldown for %.0fs (%s)", key, seconds, msg[:120])


def _log_event(
    db: Session,
    *,
    visit_id: int,
    module_code: str,
    status: str,
    provider: str | None,
    latency_ms: int | None = None,
    error: str | None = None,
) -> None:
    db.add(
        ModuleEvent(
            visit_id=visit_id,
            module_code=module_code,
            status=status,
            provider=provider,
            latency_ms=latency_ms,
            error=error,
        )
    )
    db.commit()


def _attempt(provider: ProviderConfig, *, system: str, user: str, timeout: float) -> str:
    client = OpenAI(api_key=provider.api_key, base_url=provider.base_url, timeout=timeout)
    response = client.chat.completions.create(
        model=provider.model,
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def call_module(
    db: Session,
    *,
    visit_id: int,
    module_code: str,
    system: str,
    user: str,
    timeout: float = 45.0,
) -> str:
    """Run one LLM task for a module. Tries the module's assigned provider first,
    then the fallback chain (ADR-0026), skipping providers on quota cooldown;
    logs one module_events row per attempt (ok / fallback / error).
    """
    chain = provider_chain_for_module(module_code)
    if not chain:
        _log_event(
            db, visit_id=visit_id, module_code=module_code, status="error",
            provider=None, error="No LLM provider configured (set keys in backend/.env).",
        )
        raise LLMCallError(f"{module_code}: no LLM provider configured.")

    assigned_key = chain[0].key
    active = [p for p in chain if not _on_cooldown(p.key)]
    if not active:  # every bucket cooling down — fail-open and try them all
        active = chain

    last_error: Exception | None = None
    for provider in active:
        start = time.monotonic()
        try:
            text = _attempt(provider, system=system, user=user, timeout=timeout)
            _log_event(
                db, visit_id=visit_id, module_code=module_code,
                status="ok" if provider.key == assigned_key else "fallback",
                provider=provider.key,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
            return text
        except Exception as exc:  # noqa: BLE001 — any provider failure moves down the chain
            last_error = exc
            _classify_and_cooldown(provider.key, exc)
            _log_event(
                db, visit_id=visit_id, module_code=module_code, status="error",
                provider=provider.key,
                latency_ms=int((time.monotonic() - start) * 1000),
                error=str(exc)[:500],
            )
            logger.warning("%s via %s failed: %s", module_code, provider.key, exc)

    raise LLMCallError(f"{module_code}: all providers failed — {last_error}")
