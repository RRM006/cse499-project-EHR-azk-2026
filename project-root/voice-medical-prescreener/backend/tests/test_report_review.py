"""BE-6/BE-7 checks — report assembly (local M12), doctor review, feedback, audit.

Offline. Proves: the report carries every section from stored data (incl. the
verbatim follow-up answers and the Red Flags section), the disclaimer/no-diagnosis
guarantee, doctor accept vs override -> 'reviewed', feedback storage, and that the
state-changing routes each leave an audit_log row.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import AuditLog, Clinic, User
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS


@pytest.fixture()
def env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    db = TestSession()
    clinic = Clinic(name="Demo Clinic")
    db.add(clinic)
    db.flush()
    medic = User(clinic_id=clinic.id, name="Medic", role="medic")
    doctor = User(clinic_id=clinic.id, name="Doctor", role="doctor")
    db.add_all([medic, doctor])
    db.commit()
    ids = {"medic": medic.id, "doctor": doctor.id}
    db.close()

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

    def fake_attempt(provider, *, system, user, timeout):
        if "classify the urgency" in system:
            return json.dumps({"tier": "high", "drivers": ["chest pain 4 days"]})
        if "explain, in 1-3 plain sentences" in system:
            return "High tier due to symptom duration and severity."
        if "extract structured" in system:
            # Sparse (3/10 filled) so the follow-up loop still has work to do.
            data = {k: (f"<{k}>" if i < 3 else "") for i, k in enumerate(SUMMARY_FIELD_KEYS)}
            data["symptom_details_structured"] = {}
            return json.dumps(data)
        if "chief-complaint summary" in system:
            return "Burning chest pain for four days."
        if "completeness checker" in system:
            return json.dumps({"present": ["duration"], "missing": ["temperature"]})
        if "ONE follow-up question" in system:
            return json.dumps({"target_gap": "temperature", "priority": 1,
                               "question": "জ্বর মেপেছেন? (Did you measure your temperature?)"})
        raise AssertionError(system[:50])

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)
    yield TestClient(app), ids, TestSession
    app.dependency_overrides.clear()


def _prepared_case(client):
    """Full patient journey: OTP -> speech (with a red flag) -> intake -> Q&A -> submit."""
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances",
                json={"raw_text": "চার দিন ধরে বুকে ব্যথা", "role": "patient"})
    client.post(f"/api/visits/{uuid}/intake")
    q = client.post(f"/api/visits/{uuid}/followup/next").json()["question"]
    client.post(f"/api/visits/{uuid}/followup/answer",
                json={"question_id": q["id"], "raw_text": "না, মাপা হয়নি"})
    assert client.post(f"/api/visits/{uuid}/submit").status_code == 200
    return uuid


def test_report_sections_review_feedback_and_audit(env):
    client, ids, TestSession = env
    uuid = _prepared_case(client)

    # --- report (M12, local) ---
    r = client.post(f"/api/visits/{uuid}/report")
    assert r.status_code == 200
    s = r.json()["sections"]
    assert s["chief_complaint"] == "Burning chest pain for four days."
    assert s["summary_fields"]["main_problem"]["value"] == "<main_problem>"
    assert s["risk"]["tier"] == "critical"          # red flag forced it
    assert "chest pain" in s["red_flags"]           # Red Flags section (ADR-0024)
    assert s["followup_qa"][0]["answer_raw"] == "না, মাপা হয়নি"  # verbatim
    assert "NOT a diagnosis" in s["disclaimer"]     # rule #2
    assert client.get(f"/api/visits/{uuid}/report").json()["id"] == r.json()["id"]

    # --- medic forwards, doctor overrides to low ---
    client.post(f"/api/visits/{uuid}/assign", json={"doctor_id": ids["doctor"]})
    r = client.post(f"/api/visits/{uuid}/review",
                    json={"reviewer_id": ids["doctor"], "override_tier": "low",
                          "disposition": "accept", "notes": "Reflux picture; not cardiac."})
    assert r.status_code == 200 and r.json()["override_tier"] == "low"
    visits = client.get("/api/visits", params={"status": "reviewed"}).json()
    assert [v["uuid"] for v in visits] == [uuid]
    assert visits[0]["completed_at"] is not None

    # reviewing again is a 409; medic can't review (403)
    assert client.post(f"/api/visits/{uuid}/review",
                       json={"reviewer_id": ids["doctor"]}).status_code == 409

    # --- feedback ---
    r = client.post(f"/api/visits/{uuid}/feedback",
                    json={"author_id": ids["doctor"], "rating": 4, "correct": False,
                          "comment": "Tier too high."})
    assert r.status_code == 200 and r.json()["rating"] == 4

    # --- audit trail: each state change left a row ---
    db = TestSession()
    actions = [a.action for a in db.query(AuditLog).all()]
    db.close()
    for expected in ("visit.submit", "report.generate", "visit.assign",
                     "visit.review", "feedback.create"):
        assert expected in actions, f"missing audit row: {expected}"


def test_review_guard_rails(env):
    client, ids, _ = env
    uuid = _prepared_case(client)
    # non-doctor reviewer / bad tier / feedback from unknown user
    assert client.post(f"/api/visits/{uuid}/review",
                       json={"reviewer_id": ids["medic"]}).status_code == 403
    assert client.post(f"/api/visits/{uuid}/review",
                       json={"reviewer_id": ids["doctor"], "override_tier": "moderate"}
                       ).status_code == 400  # schema code is 'medium', not 'moderate'
    assert client.post(f"/api/visits/{uuid}/feedback",
                       json={"author_id": 999}).status_code == 403
    assert client.get(f"/api/visits/{uuid}/report").status_code == 404  # none generated yet
