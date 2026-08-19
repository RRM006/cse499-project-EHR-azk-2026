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

# S42 — ONE bounded second pass, and only over attempts whose failure looked TEMPORARY.
# OpenRouter's own 429 body says "temporarily rate-limited upstream. Please retry
# shortly", and that is literally true: the same model answered correctly seconds later.
# The pass is deliberately small because a patient is waiting on the other end of this
# call — a retry storm would trade a visible error for an invisible hang, which is worse.
TRANSIENT_RETRY_PASSES = 1
TRANSIENT_RETRY_BACKOFF_S = 1.5

# ⚠ THE WHOLE CALL IS BOUNDED, not just each attempt.
# The per-attempt `timeout` only bounds ONE request. With the S42 chain that is up to
# five (bucket, model) attempts, and the retry pass can repeat them — so a chain of
# providers that ACCEPT the connection and then hang would have kept a patient watching
# a spinner for 45 s x 5 x 2 = 7.5 minutes before being told anything. "Stuck loading"
# is the failure mode a waiting patient cannot distinguish from a broken kiosk, and it
# is worse than an honest error, because an error at least offers the retry button.
#
# 90 s is chosen from MEASURED runs, not guessed: a healthy intake module call took
# ~2-10 s, and the worst fully-degraded one (Gemini down, Groq down, served by
# OpenRouter's free pool) took 14.1 s. The budget is therefore several times the
# slowest real success, so it can only ever cut off a genuine hang.
CALL_DEADLINE_S = 90.0

# Substrings that mark a failure as worth one more try. Everything else (a bad key, a
# retired model, a malformed request) is PERMANENT for this call and is never retried —
# retrying a 404 model_not_found just spends the patient's time to get the same answer.
_TRANSIENT_HINTS = (
    "429", "rate limit", "rate-limited", "quota", "overloaded", "capacity",
    "500", "502", "503", "504", "timeout", "timed out", "temporarily",
    "unavailable", "connection", "connect", "read error",
)

# The ONE sentence any patient-facing route may show when the whole chain is down.
# ⚠ It names no provider, no model, no quota and no URL — see _safe_message(). The
# technical text lives in the server log and in module_events, where the developer is.
LLM_UNAVAILABLE_DETAIL = (
    "The AI assistant is temporarily unavailable. Your answers are saved — "
    "please try again in a moment."
)

# (bucket|model) -> monotonic timestamp until which that attempt should be skipped.
_cooldowns: dict[str, float] = {}


class LLMCallError(RuntimeError):
    """Every provider in the module's chain failed (or none is configured).

    ⚠ S42: ``str(exc)`` on this exception CONTAINS THE RAW UPSTREAM PROVIDER BODY, and
    that body has been measured to include the model id, the upstream provider's name
    and a signup URL. It is for logs and module_events ONLY. Anything that answers a
    patient must use ``safe_detail`` instead — the route helpers in
    ``api/_llm_errors.py`` are the single place that conversion happens.
    """

    @property
    def safe_detail(self) -> str:
        return LLM_UNAVAILABLE_DETAIL


def is_transient(exc: Exception) -> bool:
    """Is this failure worth exactly one more attempt? (429 / 5xx / timeout / network)"""
    msg = str(exc).lower()
    return any(hint in msg for hint in _TRANSIENT_HINTS)


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
    then the fallback chain (ADR-0026), skipping attempts on quota cooldown;
    logs one module_events row per attempt (ok / fallback / error).

    S42: the chain is a list of (bucket, model) ATTEMPTS — a bucket configured with
    several models contributes one attempt each — and a failed pass whose failures all
    looked temporary is retried once, briefly, before the caller is told it failed.
    """
    chain = provider_chain_for_module(module_code)
    if not chain:
        _log_event(
            db, visit_id=visit_id, module_code=module_code, status="error",
            provider=None, error="No LLM provider configured (set keys in backend/.env).",
        )
        raise LLMCallError(f"{module_code}: no LLM provider configured.")

    assigned_key = chain[0].key
    active = [p for p in chain if not _on_cooldown(p.cooldown_key)]
    if not active:  # every bucket cooling down — fail-open and try them all
        active = chain

    state: dict = {"last_error": None}
    deadline = time.monotonic() + CALL_DEADLINE_S

    def run(provider: ProviderConfig) -> str | None:
        """One attempt. Returns the text, or None after logging the failure.

        The per-attempt timeout is clamped to whatever is LEFT of the whole call's
        budget, so the last provider in a slow chain cannot extend the wait past it."""
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            state["last_error"] = state["last_error"] or TimeoutError(
                f"exceeded the {CALL_DEADLINE_S:.0f}s budget for one module call"
            )
            return None
        start = time.monotonic()
        try:
            text = _attempt(provider, system=system, user=user,
                            timeout=min(timeout, remaining))
            _log_event(
                db, visit_id=visit_id, module_code=module_code,
                status="ok" if provider.key == assigned_key else "fallback",
                provider=provider.key,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
            return text
        except Exception as exc:  # noqa: BLE001 — any provider failure moves down the chain
            state["last_error"] = exc
            _classify_and_cooldown(provider.cooldown_key, exc)
            _log_event(
                db, visit_id=visit_id, module_code=module_code, status="error",
                provider=provider.key,
                latency_ms=int((time.monotonic() - start) * 1000),
                error=str(exc)[:500],
            )
            # ⚠ `provider.label` is bucket + credential SLOT NUMBER + model id. It never
            # contains a key value — which is what makes "Gemini key 2 is the one that
            # is exhausted" a diagnosable fact without a credential reaching a log file.
            logger.warning("%s via %s failed: %s", module_code, provider.label, exc)
            return None

    retryable: list[ProviderConfig] = []
    for provider in active:
        text = run(provider)
        if text is not None:
            return text
        if is_transient(state["last_error"]):
            retryable.append(provider)

    # S42 — the whole chain failed. If the failures were the "please retry shortly"
    # kind, give them exactly one more short pass rather than handing the patient an
    # error for a queue that had already cleared.
    for _ in range(TRANSIENT_RETRY_PASSES):
        if not retryable or time.monotonic() >= deadline:
            break
        time.sleep(TRANSIENT_RETRY_BACKOFF_S)
        logger.info("%s: retrying %d transient provider attempt(s)", module_code, len(retryable))
        still: list[ProviderConfig] = []
        for provider in retryable:
            text = run(provider)
            if text is not None:
                return text
            if is_transient(state["last_error"]):
                still.append(provider)
        retryable = still

    raise LLMCallError(f"{module_code}: all providers failed — {state['last_error']}")
