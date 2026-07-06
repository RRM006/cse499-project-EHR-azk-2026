"""DOCTOR-4/5 — prescription form prefill (letterhead) + idempotent letterhead seed.

The context endpoint feeds the letterhead into the form; the patient + symptoms are
assembled client-side, so they are intentionally NOT part of this payload. There is no
Diagnosis field on the contract — the doctor authors it, never the AI (rule #2 / ADR-0036).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import Clinic, Patient, User, Visit
from backend.app.db.seed import seed_demo_letterhead
from backend.app.main import app


@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    db = TestSession()
    clinic = Clinic(name="Demo Clinic")
    db.add(clinic)
    db.flush()
    patient = Patient(clinic_id=clinic.id, external_ref="+8801712345678",
                      display_name="Kamal Hossain", birth_year=1985, sex="male")
    doctor = User(clinic_id=clinic.id, name="Dr. M. Rahman", role="doctor")
    medic = User(clinic_id=clinic.id, name="Medic Rahman", role="medic")
    db.add_all([patient, doctor, medic])
    db.flush()
    visit = Visit(clinic_id=clinic.id, patient_id=patient.id, status="awaiting_doctor")
    db.add(visit)
    db.commit()
    ids = {"visit_uuid": visit.uuid, "clinic_id": clinic.id,
           "doctor_id": doctor.id, "medic_id": medic.id}
    db.close()

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), TestSession, ids
    app.dependency_overrides.clear()


def test_context_returns_seeded_letterhead(env):
    client, TestSession, ids = env
    with TestSession() as db:
        seed_demo_letterhead(db)  # fills the NULL letterhead fields

    body = client.get(
        f"/api/visits/{ids['visit_uuid']}/prescription/context",
        params={"doctor_id": ids["doctor_id"]},
    )
    assert body.status_code == 200, body.text
    data = body.json()
    assert data["clinic"]["name"] == "Demo Clinic"
    assert "Dhaka" in data["clinic"]["address"]
    assert data["doctor"]["id"] == ids["doctor_id"]
    assert data["doctor"]["name"] == "Dr. M. Rahman"
    assert data["doctor"]["qualification"] == "MBBS, FCPS (Medicine)"
    assert data["doctor"]["registration_no"].startswith("BMDC-A-")
    assert data["doctor"]["specialization"] == "Internal Medicine"
    # No Diagnosis is ever part of the prefill (rule #2).
    assert "diagnosis" not in data and "suggested_condition" not in data


def test_context_letterhead_null_before_seed(env):
    """Contract holds even with NULL letterhead — the fields are simply null."""
    client, _, ids = env
    data = client.get(
        f"/api/visits/{ids['visit_uuid']}/prescription/context",
        params={"doctor_id": ids["doctor_id"]},
    ).json()
    assert data["clinic"]["address"] is None
    assert data["doctor"]["qualification"] is None


def test_context_unknown_visit_404(env):
    client, _, ids = env
    r = client.get(
        "/api/visits/nope-not-a-visit/prescription/context",
        params={"doctor_id": ids["doctor_id"]},
    )
    assert r.status_code == 404


def test_context_unknown_doctor_404(env):
    client, _, ids = env
    r = client.get(
        f"/api/visits/{ids['visit_uuid']}/prescription/context",
        params={"doctor_id": 9999},
    )
    assert r.status_code == 404


def test_context_non_doctor_role_400(env):
    """A real user who is not a doctor cannot author a prescription letterhead."""
    client, _, ids = env
    r = client.get(
        f"/api/visits/{ids['visit_uuid']}/prescription/context",
        params={"doctor_id": ids["medic_id"]},
    )
    assert r.status_code == 400


def test_seed_is_idempotent_and_nonclobbering(env):
    """Seeding twice changes nothing the second time, and never overwrites a real value."""
    _, TestSession, ids = env
    with TestSession() as db:
        # a doctor who already has a custom qualification must keep it
        doc = db.get(User, ids["doctor_id"])
        doc.qualification = "MBBS, MD (Cardiology)"
        db.commit()
        seed_demo_letterhead(db)
        seed_demo_letterhead(db)
        doc = db.get(User, ids["doctor_id"])
        assert doc.qualification == "MBBS, MD (Cardiology)"   # untouched
        assert doc.specialization == "Internal Medicine"      # NULL slot filled once
