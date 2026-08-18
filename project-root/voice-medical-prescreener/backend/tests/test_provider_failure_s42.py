"""S42 — the provider outage that broke the Patient Portal, pinned.

WHAT ACTUALLY HAPPENED, so these tests are read as a description of a real event
rather than a hypothetical:

  * Groq's ``llama-3.3-70b-versatile`` had been DECOMMISSIONED — the live model list no
    longer contains any Llama chat model. Groq is ``FALLBACK_ORDER[0]``, so the first
    bucket every module falls back to was answering 404 for every call.
  * OpenRouter's ``google/gemma-4-31b-it:free`` was answering 429 from its SHARED
    upstream pool. That was ADR-0026's universal fallback.
  * Which left Gemini as the only working provider. The moment its daily free quota hit
    429, ``POST /api/visits/<uuid>/intake`` answered **502** and the patient's screen
    showed the raw upstream body — model id, upstream provider name and a signup URL.

The tests below cover the nine scenarios the hardening brief named, plus the two
disclosure properties (no provider text, no secret) that make this a safety fix and not
only a reliability one.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.services.llm_client as lc
from backend.app.core import llm_providers as lp
from backend.app.db.models import Base, Clinic, ModuleEvent, Visit


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool, future=True,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine, autoflush=False, future=True)()
    clinic = Clinic(name="Test Clinic")
    db.add(clinic)
    db.flush()
    visit = Visit(clinic_id=clinic.id, uuid="s42-visit")
    db.add(visit)
    db.commit()
    yield db, visit.id
    db.close()


@pytest.fixture(autouse=True)
def _no_cooldown_bleed():
    """Cooldowns live in a module-level dict, so one test's 429 would otherwise change
    the next test's chain. Cleared on both sides."""
    lc.reset_cooldowns()
    yield
    lc.reset_cooldowns()


@pytest.fixture(autouse=True)
def _instant_retry(monkeypatch):
    """The retry backoff is real seconds in production and pointless waiting here."""
    monkeypatch.setattr(lc.time, "sleep", lambda _s: None)


def _chain(monkeypatch, *specs):
    """specs are (bucket, model) pairs — the S42 chain shape."""
    chain = [lp.ProviderConfig(k, "test-key", "http://fake", m) for k, m in specs]
    monkeypatch.setattr(lc, "provider_chain_for_module", lambda mc, settings=None: chain)
    return chain


def _call(db, visit_id, module_code="M4"):
    return lc.call_module(db, visit_id=visit_id, module_code=module_code, system="s", user="u")


# --- the provider-failure matrix ----------------------------------------------------
# Every message below is copied from a REAL provider body observed during the outage,
# so the classifier is tested against the wording it will actually meet.

RATE_LIMIT_429 = (
    "Error code: 429 - {'error': {'message': 'Provider returned error', 'code': 429, "
    "'metadata': {'raw': 'google/gemma-4-31b-it:free is temporarily rate-limited "
    "upstream. Please retry shortly, or add your own key to accumulate your rate "
    "limits: https://openrouter.ai/settings/integrations', 'provider_name': "
    "'Google AI Studio'}}}"
)
MODEL_GONE_404 = (
    "Error code: 404 - {'error': {'message': 'The model `llama-3.3-70b-versatile` does "
    "not exist or you do not have access to it.', 'type': 'invalid_request_error', "
    "'code': 'model_not_found'}}"
)
SERVICE_503 = "Error code: 503 - {'error': {'message': 'Service temporarily unavailable'}}"
TIMEOUT = "Request timed out."


def test_1_primary_provider_success_is_logged_as_ok_and_never_falls_back(db_session, monkeypatch):
    db, visit_id = db_session
    _chain(monkeypatch, ("gemini_flash", "gemini-flash-latest"), ("groq", "openai/gpt-oss-120b"))
    seen = []
    monkeypatch.setattr(lc, "_attempt",
                        lambda p, **kw: (seen.append(p.key), "answer")[1])
    assert _call(db, visit_id) == "answer"
    assert seen == ["gemini_flash"]                       # the fallback was never touched
    ev = db.query(ModuleEvent).all()
    assert [(e.provider, e.status) for e in ev] == [("gemini_flash", "ok")]


@pytest.mark.parametrize(
    "failure, label",
    [(RATE_LIMIT_429, "429 rate limit"),
     (SERVICE_503, "503 unavailable"),
     (TIMEOUT, "timeout"),
     (MODEL_GONE_404, "obsolete/unavailable model")],
)
def test_2345_primary_failure_of_every_kind_falls_back_and_succeeds(
    db_session, monkeypatch, failure, label
):
    """Scenarios 2-5: 429, 503, timeout and a retired model each fall through to the
    next bucket and the caller still gets its answer."""
    db, visit_id = db_session
    _chain(monkeypatch, ("gemini_flash", "gemini-flash-latest"), ("groq", "openai/gpt-oss-120b"))

    def attempt(provider, **kw):
        if provider.key == "gemini_flash":
            raise RuntimeError(failure)
        return "answer"

    monkeypatch.setattr(lc, "_attempt", attempt)
    assert _call(db, visit_id) == "answer", label
    last = db.query(ModuleEvent).order_by(ModuleEvent.id.desc()).first()
    assert (last.provider, last.status) == ("groq", "fallback")


def test_6_all_providers_unavailable_is_a_controlled_error_not_a_crash(db_session, monkeypatch):
    """Scenario 6. The failure is an LLMCallError — a named, expected outcome the
    routes already handle — never a bare provider exception escaping the seam."""
    db, visit_id = db_session
    _chain(monkeypatch, ("gemini_flash", "m1"), ("groq", "m2"), ("openrouter", "m3"))
    monkeypatch.setattr(lc, "_attempt",
                        lambda p, **kw: (_ for _ in ()).throw(RuntimeError(RATE_LIMIT_429)))
    with pytest.raises(lc.LLMCallError):
        _call(db, visit_id)
    # Every attempt is accounted for in module_events — that is the developer's trail.
    assert {e.provider for e in db.query(ModuleEvent).all()} == {
        "gemini_flash", "groq", "openrouter"}


def test_7_a_dead_chain_never_shows_the_patient_any_provider_text(db_session, monkeypatch):
    """Scenario 7 — the disclosure half of the outage, and the reason this is a safety
    fix. The patient's screen showed the model id, the upstream provider's name and a
    signup URL, because the route answered ``detail=str(exc)``."""
    db, visit_id = db_session
    _chain(monkeypatch, ("openrouter", "google/gemma-4-31b-it:free"))
    monkeypatch.setattr(lc, "_attempt",
                        lambda p, **kw: (_ for _ in ()).throw(RuntimeError(RATE_LIMIT_429)))
    with pytest.raises(lc.LLMCallError) as caught:
        _call(db, visit_id)

    # The exception itself still carries everything, for the log and module_events.
    assert "gemma-4-31b-it" in str(caught.value)

    # What a patient may be shown carries none of it.
    safe = caught.value.safe_detail
    for forbidden in ("gemma", "openrouter", "Google AI Studio", "http", "429",
                      "rate-limited", "quota", "api", "key", "provider"):
        assert forbidden.lower() not in safe.lower(), f"{forbidden!r} leaked into: {safe}"
    # …and it still tells the patient the two things they need.
    assert "saved" in safe.lower()          # their answers are not lost
    assert "again" in safe.lower()          # they may retry


def test_7b_every_llm_route_uses_the_safe_helper_and_none_returns_str_exc():
    """The guarantee above is only worth anything if EVERY route goes through it.
    Six call sites returned ``detail=str(exc)`` before S42."""
    import pathlib
    api = pathlib.Path(__file__).resolve().parents[1] / "app" / "api"
    offenders = []
    for f in api.glob("routes_*.py"):
        text = f.read_text(encoding="utf-8")
        if "LLMCallError" not in text:
            continue
        assert "llm_unavailable" in text, f"{f.name} handles LLMCallError without the helper"
        for i, line in enumerate(text.splitlines(), 1):
            if "detail=str(exc)" in line and "502" in line:
                offenders.append(f"{f.name}:{i}")
    assert not offenders, f"raw provider text still reachable from: {offenders}"


def test_8_a_transient_failure_is_retried_once_so_intake_is_not_lost_to_a_blip(
    db_session, monkeypatch
):
    """Scenario 8 — 'intake does not incorrectly remain stuck'. OpenRouter's own body
    says 'Please retry shortly', and it means it: the same model served the same
    request seconds later. One short retry pass turns that into a success."""
    db, visit_id = db_session
    _chain(monkeypatch, ("openrouter", "a:free"))
    calls = {"n": 0}

    def attempt(provider, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError(RATE_LIMIT_429)
        return "answer"

    monkeypatch.setattr(lc, "_attempt", attempt)
    assert _call(db, visit_id) == "answer"
    assert calls["n"] == 2


def test_8b_a_permanent_failure_is_NOT_retried(db_session, monkeypatch):
    """The other half, and the one that protects the patient's time: a retired model
    answers 404 identically however often it is asked. Retrying it would only make the
    patient wait longer for the same error."""
    db, visit_id = db_session
    _chain(monkeypatch, ("groq", "llama-3.3-70b-versatile"))
    calls = {"n": 0}

    def attempt(provider, **kw):
        calls["n"] += 1
        raise RuntimeError(MODEL_GONE_404)

    monkeypatch.setattr(lc, "_attempt", attempt)
    with pytest.raises(lc.LLMCallError):
        _call(db, visit_id)
    assert calls["n"] == 1, "a 404 model_not_found must not be retried"


def test_8c_the_retry_is_bounded_a_patient_is_waiting(db_session, monkeypatch):
    """A retry loop with no bound trades a visible error for an invisible hang."""
    db, visit_id = db_session
    _chain(monkeypatch, ("gemini_flash", "m1"), ("openrouter", "a:free"))
    calls = {"n": 0}

    def attempt(provider, **kw):
        calls["n"] += 1
        raise RuntimeError(RATE_LIMIT_429)

    monkeypatch.setattr(lc, "_attempt", attempt)
    with pytest.raises(lc.LLMCallError):
        _call(db, visit_id)
    # 2 attempts x (1 first pass + 1 retry pass). Never unbounded.
    assert calls["n"] == 4
    assert lc.TRANSIENT_RETRY_PASSES == 1


def test_9_no_api_key_ever_reaches_a_log_record(db_session, monkeypatch, caplog):
    """Scenario 9. Every failed attempt is logged with the provider, the model and the
    error — the model and provider are diagnostics, the credential never is."""
    db, visit_id = db_session
    secret = "sk-live-THIS-IS-THE-SECRET-VALUE-0123456789"
    chain = [lp.ProviderConfig("openrouter", secret, "http://fake", "a:free")]
    monkeypatch.setattr(lc, "provider_chain_for_module", lambda mc, settings=None: chain)
    monkeypatch.setattr(lc, "_attempt",
                        lambda p, **kw: (_ for _ in ()).throw(RuntimeError(RATE_LIMIT_429)))

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(lc.LLMCallError) as caught:
            _call(db, visit_id)

    assert secret not in caplog.text
    assert secret not in str(caught.value)
    assert secret not in caught.value.safe_detail
    for ev in db.query(ModuleEvent).all():
        assert secret not in (ev.error or "")
        assert secret not in (ev.provider or "")
    # The diagnostics that ARE wanted survived.
    assert "openrouter" in caplog.text and "a:free" in caplog.text


# --- the classifier itself ----------------------------------------------------------


@pytest.mark.parametrize("body", [RATE_LIMIT_429, SERVICE_503, TIMEOUT,
                                  "Error code: 502 Bad Gateway",
                                  "Error code: 504 gateway timeout",
                                  "The engine is currently overloaded"])
def test_transient_failures_are_recognised(body):
    assert lc.is_transient(RuntimeError(body)), body


@pytest.mark.parametrize("body", [MODEL_GONE_404,
                                  "Error code: 401 - invalid api key",
                                  "Error code: 400 - malformed request"])
def test_permanent_failures_are_not_treated_as_transient(body):
    assert not lc.is_transient(RuntimeError(body)), body


# --- the route, end to end ----------------------------------------------------------


def test_intake_route_answers_502_with_the_safe_message_and_a_retry_after_header(monkeypatch):
    """The Patient Portal's actual failure path, exercised through HTTP.

    ``Retry-After`` is the standards-compliant way to say 'this is temporary', and it
    is what makes the failure recoverable rather than terminal for any client.
    """
    from backend.app.api._llm_errors import RETRY_AFTER_SECONDS, llm_unavailable
    from fastapi import FastAPI

    app = FastAPI()

    @app.post("/boom")
    def boom():
        raise llm_unavailable(lc.LLMCallError(f"M4: all providers failed — {RATE_LIMIT_429}"))

    r = TestClient(app, raise_server_exceptions=False).post("/boom")
    assert r.status_code == 502
    assert r.headers["Retry-After"] == str(RETRY_AFTER_SECONDS)
    body = r.text.lower()
    for forbidden in ("gemma", "openrouter", "google ai studio", "http://", "https://"):
        assert forbidden not in body, f"{forbidden!r} reached the HTTP body: {r.text}"
    assert r.json()["detail"] == lc.LLM_UNAVAILABLE_DETAIL


# --- the whole call is time-bounded ---------------------------------------------------


def test_a_hanging_chain_cannot_keep_a_patient_waiting_indefinitely(db_session, monkeypatch):
    """The failure a bounded per-attempt timeout does NOT prevent.

    Each attempt is capped at 45 s, but the S42 chain makes up to five of them and the
    retry pass can repeat them — so providers that accept the connection and then hang
    would have held the patient on a spinner for minutes. A patient cannot tell that
    apart from a broken kiosk, and it is strictly worse than an error, which at least
    comes with the retry button.
    """
    db, visit_id = db_session
    _chain(monkeypatch, ("gemini_flash", "m1"), ("groq", "m2"),
           ("openrouter", "a:free"), ("openrouter", "b:free"), ("openrouter", "c:free"))

    clock = {"t": 0.0}
    monkeypatch.setattr(lc.time, "monotonic", lambda: clock["t"])
    seen_timeouts = []

    def hang(provider, *, system, user, timeout):
        seen_timeouts.append(timeout)
        clock["t"] += timeout                      # the provider hangs for its full timeout
        raise RuntimeError(TIMEOUT)

    monkeypatch.setattr(lc, "_attempt", hang)
    with pytest.raises(lc.LLMCallError):
        # 40 s per attempt divides the 90 s budget unevenly on purpose, so the CLAMP on
        # the last attempt is observable rather than coincidentally equal.
        lc.call_module(db, visit_id=visit_id, module_code="M4",
                       system="s", user="u", timeout=40.0)

    assert clock["t"] <= lc.CALL_DEADLINE_S + 0.01, (
        f"one module call burned {clock['t']:.0f}s against a {lc.CALL_DEADLINE_S:.0f}s budget")
    assert sum(seen_timeouts) <= lc.CALL_DEADLINE_S + 0.01
    # Unbounded, all five attempts plus a retry pass would have run: 40 x 5 x 2 = 400 s.
    assert len(seen_timeouts) < 5, "the chain was not cut short by the budget"
    # The final attempt gets only what is LEFT (90 - 40 - 40 = 10 s), never a fresh 40.
    assert seen_timeouts == [40.0, 40.0, 10.0]


def test_the_budget_is_far_larger_than_a_real_degraded_success(db_session, monkeypatch):
    """The bound must only ever cut off a genuine hang. MEASURED live: a healthy module
    call took ~2-10 s, and the slowest fully-degraded one (Gemini down, Groq down,
    answered by OpenRouter's free pool) took 14.1 s."""
    assert lc.CALL_DEADLINE_S >= 4 * 14.1

    db, visit_id = db_session
    _chain(monkeypatch, ("gemini_flash", "m1"), ("openrouter", "a:free"))
    clock = {"t": 0.0}
    monkeypatch.setattr(lc.time, "monotonic", lambda: clock["t"])

    def slow_but_working(provider, *, system, user, timeout):
        clock["t"] += 14.1                          # the measured worst real latency
        if provider.key == "gemini_flash":
            raise RuntimeError(RATE_LIMIT_429)
        return "answer"

    monkeypatch.setattr(lc, "_attempt", slow_but_working)
    assert _call(db, visit_id) == "answer", "the budget cut off a call that would have worked"
