"""BE-4 checks — M10 risk + red-flag rule + M11 XAI, fully offline.

The safety-critical part (TC-R1): every phrase on the red-flag list MUST force
tier 'critical' — including when the model call fails entirely, and including
phrases appearing only in RAW (uncorrected) text. Also: append-only assessments,
model-tier passthrough when no flags, medium-on-model-failure (never silently
low), every assessment carrying a stored reason, and route guard rails.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.main import app
from backend.app.services.red_flags import RED_FLAG_RULES, scan_text


# --- pure rule tests (no app needed) — TC-R1: zero misses on the fixed list ---

@pytest.mark.parametrize(
    "category,phrase",
    [(c, p) for c, phrases in RED_FLAG_RULES.items() for p in phrases],
)
def test_every_red_flag_phrase_triggers_its_category(category, phrase):
    assert category in scan_text(f"রোগী বললেন ... {phrase} ... আরো কথা")


def test_benign_text_triggers_nothing():
    assert scan_text("আমার হালকা মাথা ব্যথা আর সর্দি হয়েছে") == []
    assert scan_text("mild headache and runny nose since yesterday") == []


# --- route/pipeline tests ---

@pytest.fixture()
def env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    from backend.app.core import llm_providers as lp

    monkeypatch.setattr(
        "backend.app.services.llm_client.provider_chain_for_module",
        lambda code, settings=None: [lp.ProviderConfig("gemini_flash", "k", "http://fake", "m")],
    )

    state = {"model_tier": "low", "fail": False}

    def fake_attempt(provider, *, system, user, timeout):
        if state["fail"]:
            raise RuntimeError("simulated outage")
        if "classify the urgency" in system:
            return json.dumps({"tier": state["model_tier"], "drivers": ["cough for 2 days"]})
        if "explain, in 1-3 plain sentences" in system:
            return "Assigned due to the listed factors."
        raise AssertionError(f"Unexpected prompt: {system[:50]}")

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)
    yield TestClient(app), state
    app.dependency_overrides.clear()


def _visit_saying(client, text):
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances", json={"raw_text": text, "role": "patient"})
    return uuid


def test_red_flag_forces_critical_over_model_low(env):
    client, state = env
    state["model_tier"] = "low"  # model would reassure — the rule must win
    uuid = _visit_saying(client, "চার দিন ধরে বুকে ব্যথা, ঘাড় পর্যন্ত ওঠে")
    r = client.post(f"/api/visits/{uuid}/assess")
    assert r.status_code == 200
    body = r.json()
    assert body["tier"] == "critical"
    assert body["rule_overrode"] is True
    assert "chest pain" in body["red_flags"]
    assert body["explanation"]["reason_text"]  # a reason is always stored


def test_red_flag_survives_total_model_failure(env):
    client, state = env
    state["fail"] = True  # M10 and M11 both down
    uuid = _visit_saying(client, "hothat shash koshto hocche, dom bondho lagche")
    body = client.post(f"/api/visits/{uuid}/assess").json()
    assert body["tier"] == "critical"
    assert "severe breathing difficulty" in body["red_flags"]
    # deterministic fallback reason still cites the flag
    assert "red-flag" in body["explanation"]["reason_text"]


def test_no_flags_model_tier_passes_through_and_appends(env):
    client, state = env
    state["model_tier"] = "high"
    uuid = _visit_saying(client, "দুই দিন ধরে কাশি আর হালকা জ্বর")
    first = client.post(f"/api/visits/{uuid}/assess").json()
    assert first["tier"] == "high" and first["rule_overrode"] is False and first["red_flags"] == []

    # Re-assess with a different model tier -> a NEW row (append-only); GET = latest.
    state["model_tier"] = "medium"
    second = client.post(f"/api/visits/{uuid}/assess").json()
    assert second["id"] != first["id"]
    assert client.get(f"/api/visits/{uuid}/risk").json()["id"] == second["id"]


def test_model_failure_without_flags_degrades_to_medium(env):
    client, state = env
    state["fail"] = True
    uuid = _visit_saying(client, "হালকা সর্দি হয়েছে")
    body = client.post(f"/api/visits/{uuid}/assess").json()
    assert body["tier"] == "medium"  # never silently low (rule #3)
    assert body["red_flags"] == [] and body["rule_overrode"] is False


def test_guard_rails(env):
    client, _ = env
    assert client.post("/api/visits/nope/assess").status_code == 404
    assert client.get("/api/visits/nope/risk").status_code == 404
    r = client.post("/api/patients/verify-otp", json={"phone": "01712345678", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    assert client.post(f"/api/visits/{uuid}/assess").status_code == 400  # no patient speech
    assert client.get(f"/api/visits/{uuid}/risk").status_code == 404
