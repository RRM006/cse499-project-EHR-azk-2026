"""BE-5 checks — submit -> medic queue -> field edit -> assign -> doctor queue.

Offline: the LLM boundary is faked (assessment tier 'high'; red flag path covered
in test_risk.py). Proves the whole staff workflow across the ADR-0030 status flow,
human field edits (provenance + M8 protection is covered in test_followup_loop),
role validation, and the phone search box.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import Clinic, User
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS


@pytest.fixture()
def env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    # Seed the staff the routes validate against (0003's seed, in miniature).
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
    yield TestClient(app), ids
    app.dependency_overrides.clear()


def _submitted_visit(client):
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances",
                json={"raw_text": "তিন দিন ধরে জ্বর", "role": "patient"})
    client.post(f"/api/visits/{uuid}/intake")
    r = client.post(f"/api/visits/{uuid}/submit")
    assert r.status_code == 200 and r.json()["status"] == "awaiting_review"
    return uuid


def test_full_staff_workflow(env):
    client, ids = env
    uuid = _submitted_visit(client)

    # submit auto-ran the assessment -> medic queue shows the tier + main problem
    queue = client.get("/api/dashboard", params={"role": "medic"}).json()
    assert len(queue) == 1
    item = queue[0]
    assert item["visit_uuid"] == uuid and item["tier"] == "high"
    assert item["main_problem"] == "<main_problem>"
    assert item["patient_phone"] == "+8801715984632"

    # doctor queue is still empty; phone search finds the case regardless of status
    assert client.get("/api/dashboard", params={"role": "doctor"}).json() == []
    assert client.get("/api/dashboard", params={"phone": "01715984632"}).json()[0]["visit_uuid"] == uuid

    # medic edits field 1 -> human provenance
    r = client.patch(
        f"/api/visits/{uuid}/profile/fields/main_problem",
        json={"value": "Fever with chills, 3 days", "editor_id": ids["medic"]},
    )
    assert r.status_code == 200
    field = r.json()["entities"]["summary_fields"]["main_problem"]
    assert field["source"] == "human" and field["edited_by"] == ids["medic"]
    # S9: the staff edit is authoritative for BOTH languages — typed text lands in
    # every slot, untranslated (no quota spent on edits).
    assert (field["value"] == field["value_en"] == field["value_bn"]
            == "Fever with chills, 3 days")

    # medic forwards to the doctor -> awaiting_doctor + assignment recorded
    r = client.post(f"/api/visits/{uuid}/assign", json={"doctor_id": ids["doctor"]})
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_doctor"
    assert r.json()["assigned_doctor_id"] == ids["doctor"]

    # queues moved: medic empty, doctor (filtered by id) has it
    assert client.get("/api/dashboard", params={"role": "medic"}).json() == []
    dq = client.get("/api/dashboard", params={"role": "doctor", "doctor_id": ids["doctor"]}).json()
    assert [i["visit_uuid"] for i in dq] == [uuid]

    # forwarding twice is a 409; submitting again is a 409
    assert client.post(f"/api/visits/{uuid}/assign", json={"doctor_id": ids["doctor"]}).status_code == 409
    assert client.post(f"/api/visits/{uuid}/submit").status_code == 409


def test_guard_rails(env):
    client, ids = env
    uuid = _submitted_visit(client)

    # unknown field / non-staff editor / bad role / bad phone / assign non-doctor
    assert client.patch(f"/api/visits/{uuid}/profile/fields/bogus",
                        json={"value": "x", "editor_id": ids["medic"]}).status_code == 400
    assert client.patch(f"/api/visits/{uuid}/profile/fields/main_problem",
                        json={"value": "x", "editor_id": 9999}).status_code == 403
    assert client.get("/api/dashboard", params={"role": "nurse"}).status_code == 400
    assert client.get("/api/dashboard", params={"phone": "123"}).status_code == 400
    assert client.get("/api/dashboard", params={"phone": "01999999999"}).json() == []
    assert client.post(f"/api/visits/{uuid}/assign",
                       json={"doctor_id": ids["medic"]}).status_code == 400

    # empty visit can't be submitted
    r = client.post("/api/patients/verify-otp", json={"phone": "01712345678", "otp": "000000"})
    empty_uuid = r.json()["visit"]["uuid"]
    assert client.post(f"/api/visits/{empty_uuid}/submit").status_code == 400
