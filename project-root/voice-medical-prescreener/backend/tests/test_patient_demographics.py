"""P2-2 (2.0 build) — patient demographics: auto-fill + staff edit.

The M3/M8 extraction now also returns ``patient_demographics`` (name exactly as
stated, age_years, sex) and ``apply_demographics`` writes them onto the patients
row FILL-ONLY-WHEN-EMPTY — so a staff edit (extended vitals PATCH) is final and
the AI can never overwrite it. All offline (faked LLM, rule #4).
"""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import Clinic, Patient, User
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS


def _extraction(demo: dict | None) -> str:
    data = {k: {"en": f"<{k}>", "bn": f"<bn:{k}>"} for k in SUMMARY_FIELD_KEYS}
    data["symptom_details_structured"] = {}
    if demo is not None:
        data["patient_demographics"] = demo
    return json.dumps(data)


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
    db.add(medic)
    db.commit()
    ids = {"medic": medic.id}
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

    # Mutable demographics the fake extractor returns; None = key absent.
    state = {"demo": {"name": "রহিম উদ্দিন", "age_years": 45, "sex": "male"}}

    def fake_attempt(provider, *, system, user, timeout):
        if "extract structured" in system:
            return _extraction(state["demo"])
        if "chief-complaint summary" in system:
            return "Short summary."
        if "completeness checker" in system:
            return json.dumps({"present": [], "missing": ["temperature"]})
        raise AssertionError(system[:50])

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)
    yield TestClient(app), TestSession, state, ids
    app.dependency_overrides.clear()


def _visit_with_intake(client):
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances",
                json={"raw_text": "আমার নাম রহিম উদ্দিন, বয়স ৪৫", "role": "patient"})
    assert client.post(f"/api/visits/{uuid}/intake").status_code == 200
    return uuid


def test_demographics_autofill_from_intake(env):
    client, TestSession, state, ids = env
    _visit_with_intake(client)

    db = TestSession()
    p = db.query(Patient).one()
    db.close()
    assert p.display_name == "রহিম উদ্দিন"      # exactly as stated
    assert p.sex == "male"
    assert p.birth_year == datetime.now(timezone.utc).year - 45


def test_autofill_never_overwrites_existing_values(env):
    client, TestSession, state, ids = env
    uuid = _visit_with_intake(client)   # fills রহিম উদ্দিন / male / 45

    # The extractor now claims DIFFERENT demographics; re-running intake must
    # change nothing (fill-only-when-empty).
    state["demo"] = {"name": "Someone Else", "age_years": 20, "sex": "female"}
    assert client.post(f"/api/visits/{uuid}/intake").status_code == 200

    db = TestSession()
    p = db.query(Patient).one()
    db.close()
    assert p.display_name == "রহিম উদ্দিন"
    assert p.sex == "male"
    assert p.birth_year == datetime.now(timezone.utc).year - 45


def test_absent_or_malformed_demographics_are_ignored(env):
    client, TestSession, state, ids = env
    state["demo"] = None                 # key absent entirely (older prompt shape)
    _visit_with_intake(client)
    db = TestSession()
    p = db.query(Patient).one()
    db.close()
    assert p.display_name is None and p.sex is None and p.birth_year is None

    # Malformed values must not crash and must not write garbage.
    state["demo"] = {"name": "", "age_years": 500, "sex": "banana"}
    r = client.post("/api/patients/verify-otp", json={"phone": "01712345678", "otp": "000000"})
    uuid2 = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid2}/utterances", json={"raw_text": "জ্বর", "role": "patient"})
    assert client.post(f"/api/visits/{uuid2}/intake").status_code == 200
    db = TestSession()
    p2 = db.query(Patient).filter(Patient.external_ref == "+8801712345678").one()
    db.close()
    assert p2.display_name is None and p2.sex is None and p2.birth_year is None


def test_staff_patch_edits_identity_and_is_final(env):
    client, TestSession, state, ids = env
    state["demo"] = None
    _visit_with_intake(client)
    db = TestSession()
    patient_id = db.query(Patient).one().id
    db.close()

    # Staff sets identity via the extended vitals PATCH.
    r = client.patch(f"/api/patients/{patient_id}/vitals",
                     json={"display_name": "Karim Ahmed", "sex": "female",
                           "age_years": 30, "editor_id": ids["medic"]})
    assert r.status_code == 200
    body = r.json()
    assert body["display_name"] == "Karim Ahmed" and body["sex"] == "female"
    assert body["birth_year"] == datetime.now(timezone.utc).year - 30

    # A later AI extraction with demographics cannot overwrite the staff values.
    state["demo"] = {"name": "AI Name", "age_years": 60, "sex": "male"}
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances", json={"raw_text": "কথা", "role": "patient"})
    assert client.post(f"/api/visits/{uuid}/intake").status_code == 200
    db = TestSession()
    p = db.get(Patient, patient_id)
    db.close()
    assert p.display_name == "Karim Ahmed" and p.sex == "female"
    assert p.birth_year == datetime.now(timezone.utc).year - 30

    # Validation: bad sex value -> 422 (pydantic pattern); empty edit -> 400.
    assert client.patch(f"/api/patients/{patient_id}/vitals",
                        json={"sex": "banana", "editor_id": ids["medic"]}).status_code == 422
    assert client.patch(f"/api/patients/{patient_id}/vitals",
                        json={"editor_id": ids["medic"]}).status_code == 400
