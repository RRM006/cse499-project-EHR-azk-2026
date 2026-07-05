"""BE-2 checks — intake pipeline (M3/M4/M6) + profile route, fully offline.

The LLM boundary (_attempt) is faked per-module, so this proves the plumbing:
prompts route to the right buckets with fallback, the 10-field shape is enforced,
module_events rows are logged with provider + status, and the profile upserts.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import ModuleEvent
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS

# The bilingual reply shape the Session-9 prompt asks for: {"en", "bn"} per key.
_FAKE_EXTRACTION = {
    key: {"en": f"<{key}>", "bn": f"<bn:{key}>"} for key in SUMMARY_FIELD_KEYS
}
_FAKE_EXTRACTION["symptom_details_structured"] = {
    "location": "retrosternal", "character": "burning",
    "worse": "lying down", "better": "sitting", "pain_severity_0_10": 7,
}
_FAKE_GAPS = {"present": ["chest pain duration"], "missing": ["temperature measurement"]}


@pytest.fixture()
def client_and_session(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool, future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Fake the provider chain (pretend all keys are configured)...
    from backend.app.core import llm_providers as lp

    def fake_chain(module_code, settings=None):
        key = lp.MODULE_PROVIDERS.get(module_code, lp.GEMINI_FLASH)
        return [lp.ProviderConfig(key, "k", "http://fake", "m"),
                lp.ProviderConfig(lp.OPENROUTER, "k", "http://fake", "m")]

    monkeypatch.setattr("backend.app.services.llm_client.provider_chain_for_module", fake_chain)

    # ...and the network call itself, keyed by which system prompt arrives.
    def fake_attempt(provider, *, system, user, timeout):
        if "extract structured" in system:
            return "```json\n" + json.dumps(_FAKE_EXTRACTION) + "\n```"  # fences tolerated
        if "chief-complaint summary" in system:
            return "Patient reports burning chest pain for 4 days, worse after meals."
        return json.dumps(_FAKE_GAPS)

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)

    yield TestClient(app), TestSession
    app.dependency_overrides.clear()


def _make_visit_with_turns(client):
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances",
                json={"raw_text": "আপনার সমস্যা বলুন", "role": "system", "source": "tts"})
    client.post(f"/api/visits/{uuid}/utterances",
                json={"raw_text": "চার দিন ধরে বুকে জ্বালাপোড়া", "role": "patient"})
    return uuid


def test_intake_builds_profile_and_logs_module_events(client_and_session):
    client, TestSession = client_and_session
    uuid = _make_visit_with_turns(client)

    r = client.post(f"/api/visits/{uuid}/intake")
    assert r.status_code == 200
    profile = r.json()

    # 10-field shape enforced (bilingual since S9; `value` mirrors value_en for
    # back-compat), AI provenance set, structured sub-shape carried.
    fields = profile["entities"]["summary_fields"]
    for key in SUMMARY_FIELD_KEYS:
        assert fields[key] == {"value": f"<{key}>", "value_en": f"<{key}>",
                               "value_bn": f"<bn:{key}>", "source": "ai",
                               "edited_by": None, "edited_at": None}
    assert fields["symptom_details_structured"]["pain_severity_0_10"] == 7
    assert "burning chest pain" in profile["summary"]
    assert profile["gaps"] == _FAKE_GAPS

    # module_events: one 'ok' row per module, right buckets (ADR-0026).
    db = TestSession()
    events = {e.module_code: e for e in db.query(ModuleEvent).all()}
    db.close()
    assert set(events) == {"M3", "M4", "M6"}
    assert all(e.status == "ok" and e.latency_ms is not None for e in events.values())
    assert events["M3"].provider == "gemini_flash_lite"
    assert events["M4"].provider == "gemini_flash"
    assert events["M6"].provider == "groq"

    # GET /profile returns the same; re-running intake UPSERTS (still one profile).
    assert client.get(f"/api/visits/{uuid}/profile").json()["id"] == profile["id"]
    assert client.post(f"/api/visits/{uuid}/intake").json()["id"] == profile["id"]


def test_intake_guard_rails(client_and_session):
    client, _ = client_and_session
    assert client.post("/api/visits/nope/intake").status_code == 404
    assert client.get("/api/visits/nope/profile").status_code == 404

    # Visit with no utterances -> 400, and no profile yet -> 404.
    r = client.post("/api/patients/verify-otp", json={"phone": "01712345678", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    assert client.post(f"/api/visits/{uuid}/intake").status_code == 400
    assert client.get(f"/api/visits/{uuid}/profile").status_code == 404


def test_fallback_is_used_and_logged(client_and_session, monkeypatch):
    client, TestSession = client_and_session
    uuid = _make_visit_with_turns(client)

    # First provider in every chain now fails -> fallback must serve and be logged.
    calls = {"n": 0}
    import backend.app.services.llm_client as lc
    real_attempt = lc._attempt

    def flaky_attempt(provider, **kw):
        if provider.key != "openrouter":
            raise RuntimeError("simulated 429")
        return real_attempt(provider, **kw)

    monkeypatch.setattr("backend.app.services.llm_client._attempt", flaky_attempt)

    assert client.post(f"/api/visits/{uuid}/intake").status_code == 200
    db = TestSession()
    statuses = {e.module_code: e for e in db.query(ModuleEvent).all()}
    db.close()
    assert all(e.status == "fallback" and e.provider == "openrouter" for e in statuses.values())
