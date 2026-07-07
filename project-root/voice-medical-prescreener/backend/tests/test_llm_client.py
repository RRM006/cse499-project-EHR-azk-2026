"""Quota-aware provider switching in the llm_client seam:
- every failed attempt is logged to module_events (no more silent first-provider failures),
- a 429/quota failure puts that provider on cooldown so the NEXT call skips it,
- fail-open: if every provider is cooling down, the chain is tried anyway,
- the extended free-bucket fallback chain (ADR-0026 + Groq/Cerebras/Mistral) is ordered.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.services.llm_client as lc
from backend.app.core import llm_providers as lp
from backend.app.core.config import Settings
from backend.app.db.models import Base, Clinic, ModuleEvent, Visit


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool, future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)
    db = TestSession()
    clinic = Clinic(name="Test Clinic")
    db.add(clinic)
    db.flush()
    visit = Visit(clinic_id=clinic.id, uuid="t-visit")
    db.add(visit)
    db.commit()
    yield db, visit.id
    db.close()


def _chain(*keys):
    return [lp.ProviderConfig(k, "k", "http://fake", "m") for k in keys]


def _call(db, visit_id, module_code="M4"):
    return lc.call_module(db, visit_id=visit_id, module_code=module_code,
                          system="s", user="u")


def test_every_failed_attempt_is_logged(db_session, monkeypatch):
    db, visit_id = db_session
    monkeypatch.setattr(lc, "provider_chain_for_module",
                        lambda mc, settings=None: _chain("gemini_flash", "groq", "openrouter"))

    def attempt(provider, **kw):
        if provider.key != "openrouter":
            raise RuntimeError(f"{provider.key} boom")
        return "answer"

    monkeypatch.setattr(lc, "_attempt", attempt)
    assert _call(db, visit_id) == "answer"

    events = db.query(ModuleEvent).order_by(ModuleEvent.id).all()
    assert [(e.provider, e.status) for e in events] == [
        ("gemini_flash", "error"), ("groq", "error"), ("openrouter", "fallback"),
    ]
    assert "gemini_flash boom" in events[0].error
    assert all(e.latency_ms is not None for e in events)


def test_429_puts_provider_on_cooldown_and_next_call_skips_it(db_session, monkeypatch):
    db, visit_id = db_session
    monkeypatch.setattr(lc, "provider_chain_for_module",
                        lambda mc, settings=None: _chain("gemini_flash", "groq"))
    calls = []

    def attempt(provider, **kw):
        calls.append(provider.key)
        if provider.key == "gemini_flash":
            raise RuntimeError("Error code: 429 - rate limit exceeded")
        return "answer"

    monkeypatch.setattr(lc, "_attempt", attempt)

    assert _call(db, visit_id) == "answer"          # tries gemini, 429s, falls to groq
    assert calls == ["gemini_flash", "groq"]
    assert _call(db, visit_id) == "answer"          # gemini now skipped entirely
    assert calls == ["gemini_flash", "groq", "groq"]

    # The serving row for the second call is a fallback (assigned bucket was skipped).
    last = db.query(ModuleEvent).order_by(ModuleEvent.id.desc()).first()
    assert (last.provider, last.status) == ("groq", "fallback")


def test_non_quota_failure_does_not_cooldown(db_session, monkeypatch):
    db, visit_id = db_session
    monkeypatch.setattr(lc, "provider_chain_for_module",
                        lambda mc, settings=None: _chain("gemini_flash", "groq"))
    calls = []
    fail_first = {"on": True}

    def attempt(provider, **kw):
        calls.append(provider.key)
        if provider.key == "gemini_flash" and fail_first["on"]:
            raise RuntimeError("connection timeout")  # not a quota error
        return "answer"

    monkeypatch.setattr(lc, "_attempt", attempt)
    assert _call(db, visit_id) == "answer"
    fail_first["on"] = False
    assert _call(db, visit_id) == "answer"
    # gemini was retried on the second call (no cooldown for non-quota errors).
    assert calls == ["gemini_flash", "groq", "gemini_flash"]


def test_fail_open_when_everything_is_cooling_down(db_session, monkeypatch):
    db, visit_id = db_session
    monkeypatch.setattr(lc, "provider_chain_for_module",
                        lambda mc, settings=None: _chain("gemini_flash", "groq"))
    flaky = {"fail": True}

    def attempt(provider, **kw):
        if flaky["fail"]:
            raise RuntimeError("429 quota exceeded")
        return "answer"

    monkeypatch.setattr(lc, "_attempt", attempt)
    with pytest.raises(lc.LLMCallError):
        _call(db, visit_id)                          # both providers 429 -> both cool down
    flaky["fail"] = False
    assert _call(db, visit_id) == "answer"           # fail-open: chain tried anyway


def test_all_failed_raises_and_logs_each(db_session, monkeypatch):
    db, visit_id = db_session
    monkeypatch.setattr(lc, "provider_chain_for_module",
                        lambda mc, settings=None: _chain("gemini_flash", "openrouter"))
    monkeypatch.setattr(lc, "_attempt",
                        lambda provider, **kw: (_ for _ in ()).throw(RuntimeError("down")))
    with pytest.raises(lc.LLMCallError):
        _call(db, visit_id)
    events = db.query(ModuleEvent).all()
    assert [(e.provider, e.status) for e in events] == [
        ("gemini_flash", "error"), ("openrouter", "error"),
    ]


def test_extended_fallback_chain_order_and_key_gating():
    # All keys set: assigned bucket first, then Groq -> Cerebras -> Mistral -> OpenRouter.
    s = Settings(_env_file=None, gemini_api_key="g", groq_api_key="q",
                 openrouter_api_key="o", cerebras_api_key="c", mistral_api_key="m")
    keys = [p.key for p in lp.provider_chain_for_module("M4", s)]
    assert keys == ["gemini_flash", "groq", "cerebras", "mistral", "openrouter"]

    # Groq-assigned module: no duplicate groq entry.
    keys = [p.key for p in lp.provider_chain_for_module("M7", s)]
    assert keys == ["groq", "cerebras", "mistral", "openrouter"]

    # Blank keys are skipped (original three-bucket setup keeps working unchanged).
    s3 = Settings(_env_file=None, gemini_api_key="g", groq_api_key="q",
                  openrouter_api_key="o", cerebras_api_key="", mistral_api_key="")
    keys = [p.key for p in lp.provider_chain_for_module("M4", s3)]
    assert keys == ["gemini_flash", "groq", "openrouter"]

    # Unknown future module: Gemini Flash first, same fallbacks.
    keys = [p.key for p in lp.provider_chain_for_module("M99", s3)]
    assert keys == ["gemini_flash", "groq", "openrouter"]
