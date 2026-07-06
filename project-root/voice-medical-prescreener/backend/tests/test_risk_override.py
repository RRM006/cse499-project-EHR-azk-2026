"""MEDIC-3 — staff risk override (POST /risk/override), fully offline.

Must: append a model_provider='human' row (AI rows never edited), carry red
flags + rule_overrode forward, store a reason (constitution), land in audit_log
with from/to, drive GET /risk and the dashboard tier, reject bad tiers, and
REFUSE to downgrade a red-flag Critical (rule #3 — only the doctor decides).
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import AuditLog, RiskAssessment
from backend.app.main import app


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

    state = {"model_tier": "medium"}

    def fake_attempt(provider, *, system, user, timeout):
        if "classify the urgency" in system:
            return json.dumps({"tier": state["model_tier"], "drivers": ["fever 3 days"]})
        if "explain, in 1-3 plain sentences" in system:
            return "Assigned due to the listed factors."
        raise AssertionError(f"Unexpected prompt: {system[:50]}")

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)
    yield TestClient(app), TestSession, state
    app.dependency_overrides.clear()


def _assessed_visit(client, text="তিন দিন ধরে জ্বর আর মাথা ব্যথা"):
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances", json={"raw_text": text, "role": "patient"})
    assert client.post(f"/api/visits/{uuid}/assess").status_code == 200
    return uuid


def test_override_appends_human_row_and_audits(env):
    client, TestSession, state = env
    uuid = _assessed_visit(client)  # benign text -> tier medium, no flags

    r = client.post(f"/api/visits/{uuid}/risk/override",
                    json={"tier": "high", "editor_id": 7, "reason": "patient looks unwell"})
    assert r.status_code == 200
    body = r.json()
    assert body["tier"] == "high"
    assert body["model_provider"] == "human"
    assert "staff override" in body["explanation"]["reason_text"]
    assert "patient looks unwell" in body["explanation"]["reason_text"]

    # GET /risk and the medic dashboard now serve the human tier.
    assert client.get(f"/api/visits/{uuid}/risk").json()["tier"] == "high"
    client.post(f"/api/visits/{uuid}/submit")
    items = client.get("/api/dashboard?role=medic").json()
    assert [i["tier"] for i in items if i["visit_uuid"] == uuid] == ["high"]

    db = TestSession()
    rows = db.query(RiskAssessment).order_by(RiskAssessment.id).all()
    assert [a.model_provider for a in rows][-1] == "human"
    assert len(rows) == 2  # AI row untouched, human row appended
    log = db.query(AuditLog).filter(AuditLog.action == "risk_override").one()
    assert log.actor_id == 7
    assert log.detail == {"from": "medium", "to": "high", "reason": "patient looks unwell"}
    db.close()


def test_red_flag_critical_cannot_be_downgraded(env):
    client, TestSession, state = env
    state["model_tier"] = "low"
    uuid = _assessed_visit(client, "বুকে ব্যথা, ঘাড় পর্যন্ত ওঠে")  # red flag -> critical

    r = client.post(f"/api/visits/{uuid}/risk/override",
                    json={"tier": "medium", "editor_id": 7})
    assert r.status_code == 409

    # Re-affirming critical IS allowed, and the red flags survive on the human row.
    r = client.post(f"/api/visits/{uuid}/risk/override",
                    json={"tier": "critical", "editor_id": 7})
    assert r.status_code == 200
    body = r.json()
    assert body["tier"] == "critical" and "chest pain" in body["red_flags"]
    assert body["rule_overrode"] is True  # safety story carried forward

    # ...and the carried-forward flags keep guarding future downgrades too.
    assert client.post(f"/api/visits/{uuid}/risk/override",
                       json={"tier": "low", "editor_id": 7}).status_code == 409


def test_override_guard_rails(env):
    client, _, _ = env

    # Unknown visit -> 404.
    assert client.post("/api/visits/nope/risk/override",
                       json={"tier": "high"}).status_code == 404

    # Assessed-visit needed: a fresh visit without /assess -> 404.
    r = client.post("/api/patients/verify-otp", json={"phone": "01712345678", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    assert client.post(f"/api/visits/{uuid}/risk/override",
                       json={"tier": "high"}).status_code == 404

    # Bad tier code -> 422 (schema-validated; C2: no numeric scores on the wire).
    uuid2 = _assessed_visit(client)
    assert client.post(f"/api/visits/{uuid2}/risk/override",
                       json={"tier": "85%"}).status_code == 422
