"""LLM call seam for pipeline modules: assigned bucket -> automatic fallback,
with every attempt logged to module_events (provider, latency, status — the
observability half of the free-tier strategy, principles 5 & 8).

Usage:  text = call_module(db, visit_id=..., module_code="M3", system=..., user=...)
Raises LLMCallError if the whole chain fails (an 'error' event is logged).
"""

from __future__ import annotations

import logging
import time

from openai import OpenAI
from sqlalchemy.orm import Session

from backend.app.core.llm_providers import ProviderConfig, provider_chain_for_module
from backend.app.db.models import ModuleEvent

logger = logging.getLogger(__name__)


class LLMCallError(RuntimeError):
    """Every provider in the module's chain failed (or none is configured)."""


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
    then the fallback chain (ADR-0026); logs one module_events row per outcome.
    """
    chain = provider_chain_for_module(module_code)
    if not chain:
        _log_event(
            db, visit_id=visit_id, module_code=module_code, status="error",
            provider=None, error="No LLM provider configured (set keys in backend/.env).",
        )
        raise LLMCallError(f"{module_code}: no LLM provider configured.")

    last_error: Exception | None = None
    for i, provider in enumerate(chain):
        start = time.monotonic()
        try:
            text = _attempt(provider, system=system, user=user, timeout=timeout)
            _log_event(
                db, visit_id=visit_id, module_code=module_code,
                status="ok" if i == 0 else "fallback",
                provider=provider.key,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
            return text
        except Exception as exc:  # noqa: BLE001 — any provider failure moves down the chain
            last_error = exc
            logger.warning("%s via %s failed: %s", module_code, provider.key, exc)

    _log_event(
        db, visit_id=visit_id, module_code=module_code, status="error",
        provider=chain[-1].key, error=str(last_error),
    )
    raise LLMCallError(f"{module_code}: all providers failed — {last_error}")
