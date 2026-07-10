"""P1-5 (2.0 build, ADR-0042b) — Confirm & Submit returns instantly.

The M10/M11/M10C work now runs in a FastAPI background task on its OWN session
bound to the same engine as the request (so these tests exercise the real job).
Proves: (1) the assessment + C1 suggestion still land after submit; (2) a crash
inside the background job can never block or undo the submission; (3) the LOCAL
red-flag rule still forces Critical from the background job even when the model
call fails (rule #3). TestClient runs BackgroundTasks before returning, so the
"after submit" state here is exactly what the medic's queue refresh would see.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import CaseProfile, RiskAssessment, Visit, XaiExplanation
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS


@pytest.fixture()
def env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db

    from backend.app.core import llm_providers as lp

    monkeypatch.setattr(
        "backend.app.services.llm_client.provider_chain_for_module",
        lambda code, settings=None: [lp.ProviderConfig("gemini_flash", "k", "http://fake", "m")],
    )

    state = {"m10_fails": False}

    def fake_attempt(provider, *, system, user, timeout):
        if "classify the urgency" in system:
            if state["m10_fails"]:
                raise RuntimeError("model down")
            return json.dumps({"tier": "high", "drivers": ["fever 3 days"]})
        if "explain, in 1-3 plain sentences" in system:
            return "High due to fever duration."
        if '"condition_en"' in system:
            return json.dumps({"condition_en": "Viral fever (possible)",
                               "condition_bn": "ভাইরাল জ্বর (সম্ভাব্য)",
                               "reasoning_en": "Fever reported for three days.",
                               "reasoning_bn": "তিন দিনের জ্বর।"})
        if "extract structured" in system:
            data = {k: f"<{k}>" for k in SUMMARY_FIELD_KEYS}
            data["symptom_details_structured"] = {}
            return json.dumps(data)
        if "chief-complaint summary" in system:
            return "Fever for three days."
        if "completeness checker" in system:
            return json.dumps({"present": [], "missing": ["temperature"]})
        raise AssertionError(system[:50])

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)
    yield TestClient(app), TestSession, state
    app.dependency_overrides.clear()


def _visit_ready_to_submit(client, text="তিন দিন ধরে জ্বর"):
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances", json={"raw_text": text, "role": "patient"})
    client.post(f"/api/visits/{uuid}/intake")
    return uuid


def test_background_assessment_and_suggestion_land_after_submit(env):
    client, TestSession, _ = env
    uuid = _visit_ready_to_submit(client)

    r = client.post(f"/api/visits/{uuid}/submit")
    assert r.status_code == 200 and r.json()["status"] == "awaiting_review"

    # The background job ran on its own session bound to the SAME engine: the
    # assessment (+ stored reason) and the C1 suggestion are all there.
    db = TestSession()
    assessment = db.query(RiskAssessment).one()
    assert assessment.tier == "high"
    assert db.query(XaiExplanation).count() == 1
    suggestion = db.query(CaseProfile).one().entities["suggested_condition"]
    assert suggestion["condition_en"] == "Viral fever (possible)"
    db.close()

    # And the medic queue sees the tier (what the 15s refresh would show).
    item = client.get("/api/dashboard", params={"role": "medic"}).json()[0]
    assert item["visit_uuid"] == uuid and item["tier"] == "high"


def test_background_crash_never_blocks_submission(env, monkeypatch):
    client, TestSession, _ = env
    uuid = _visit_ready_to_submit(client)

    def boom(db, visit, profile):
        raise RuntimeError("assessment exploded")

    monkeypatch.setattr("backend.app.api.routes_dashboard.assess_visit", boom)
    r = client.post(f"/api/visits/{uuid}/submit")
    assert r.status_code == 200 and r.json()["status"] == "awaiting_review"

    # Submission survived; the case is queued (tier just not there yet) and the
    # visit status was NOT rolled back by the failed background job.
    db = TestSession()
    assert db.query(Visit).one().status == "awaiting_review"
    assert db.query(RiskAssessment).count() == 0
    db.close()
    item = client.get("/api/dashboard", params={"role": "medic"}).json()[0]
    assert item["visit_uuid"] == uuid and item["tier"] is None


def test_red_flag_forces_critical_from_background_even_with_model_down(env):
    client, TestSession, state = env
    # "বুকে ব্যথা" is a red-flag phrase; the M10 model call itself fails.
    uuid = _visit_ready_to_submit(client, text="হঠাৎ বুকে ব্যথা হচ্ছে")
    state["m10_fails"] = True

    r = client.post(f"/api/visits/{uuid}/submit")
    assert r.status_code == 200

    # Rule #3 survives the move to the background: LOCAL rule -> critical, with a
    # stored deterministic reason, despite the dead model.
    db = TestSession()
    assessment = db.query(RiskAssessment).one()
    assert assessment.tier == "critical"
    assert assessment.red_flags and assessment.rule_overrode is True
    assert db.query(XaiExplanation).count() == 1
    db.close()
