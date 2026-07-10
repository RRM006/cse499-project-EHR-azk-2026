"""P3-1 (2.0 build) — Visit.submitted_at: the patient's "Confirm & Submit" moment.

The doctor portal must show WHEN the patient submitted (rendered as Dhaka time in
the browser), which is distinct from started_at (kiosk session start). Proves:
(1) submit stamps submitted_at exactly once and returns it; (2) the staff queues
and the visit detail expose it; (3) later status transitions (assign / review)
never clobber the original submission moment. Offline — LLM boundary faked.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import Clinic, User, Visit
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
    medic = User(clinic_id=clinic.id, name="Medic Rahman", role="medic")
    doctor = User(clinic_id=clinic.id, name="Dr. Yasmin", role="doctor")
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
    yield TestClient(app), TestSession, ids
    app.dependency_overrides.clear()


def _visit_ready_to_submit(client):
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances",
                json={"raw_text": "তিন দিন ধরে জ্বর", "role": "patient"})
    client.post(f"/api/visits/{uuid}/intake")
    return uuid


def test_submit_stamps_submitted_at_once(env):
    client, TestSession, _ = env
    uuid = _visit_ready_to_submit(client)

    # Not submitted yet -> no submission moment anywhere.
    assert client.get(f"/api/visits/{uuid}").json()["submitted_at"] is None

    r = client.post(f"/api/visits/{uuid}/submit")
    assert r.status_code == 200
    stamped = r.json()["submitted_at"]
    assert stamped is not None

    # Stored on the row itself (what migration 0011 persists), and started_at
    # is untouched — they are different facts about the visit.
    db = TestSession()
    visit = db.query(Visit).one()
    assert visit.submitted_at is not None
    assert visit.started_at is not None
    db.close()

    # A second submit is a 409 (already awaiting_review) — the stamp can't move.
    assert client.post(f"/api/visits/{uuid}/submit").status_code == 409
    assert client.get(f"/api/visits/{uuid}").json()["submitted_at"] == stamped


def test_queue_and_detail_expose_submitted_at(env):
    client, _, _ = env
    uuid = _visit_ready_to_submit(client)
    stamped = client.post(f"/api/visits/{uuid}/submit").json()["submitted_at"]

    # Medic queue row (what staff.js renders as Dhaka time) carries it.
    item = client.get("/api/dashboard", params={"role": "medic"}).json()[0]
    assert item["visit_uuid"] == uuid and item["submitted_at"] == stamped

    # Visit detail (what the doctor's patient-details card reads) carries it too.
    assert client.get(f"/api/visits/{uuid}").json()["submitted_at"] == stamped


def test_later_transitions_never_clobber_submitted_at(env):
    client, _, ids = env
    uuid = _visit_ready_to_submit(client)
    stamped = client.post(f"/api/visits/{uuid}/submit").json()["submitted_at"]

    # Medic forwards to the doctor (awaiting_review -> awaiting_doctor)…
    r = client.post(f"/api/visits/{uuid}/assign", json={"doctor_id": ids["doctor"]})
    assert r.status_code == 200

    # …and the doctor-queue row + detail still show the ORIGINAL submission moment.
    item = client.get("/api/dashboard", params={"role": "doctor"}).json()[0]
    assert item["visit_uuid"] == uuid and item["submitted_at"] == stamped
    assert client.get(f"/api/visits/{uuid}").json()["submitted_at"] == stamped
