"""S37 (ADR-0058) — the doctor's longitudinal layer: patient history, prescription
history, and the 'recent' scope that stops a reviewed case from vanishing.

Two of these tests exist for safety rather than for the feature:
  * ``test_history_carries_no_transcript`` — a history row must never become a
    second, lossy rendering of the patient's words (rule #1);
  * ``test_recent_scope_never_leaks_another_doctors_cases`` — a completed-consultation
    list is personal, so an unowned request is a 400 and a scoped one is filtered.

The prescription half runs through the REAL POST /prescription route (with storage
redirected to tmp_path) rather than hand-written rows, so what the history reads back
is what the prescription module actually writes.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import CaseProfile, Clinic, Patient, RiskAssessment, User, Visit
from backend.app.main import app
from backend.app.services.documents.storage import FilesystemStorage
from backend.app.services.history import MAX_MEDICINE_PREVIEW, _medicine_names


@pytest.fixture()
def env(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    db = TestSession()
    clinic = Clinic(name="Demo Clinic", address="Dhanmondi, Dhaka")
    db.add(clinic)
    db.flush()
    doctor_a = User(clinic_id=clinic.id, name="Dr. Yasmin", role="doctor")
    doctor_b = User(clinic_id=clinic.id, name="Dr. Karim", role="doctor")
    medic = User(clinic_id=clinic.id, name="Medic Rahman", role="medic")
    patient = Patient(
        clinic_id=clinic.id, external_ref="+8801712345678",
        display_name="Kamal Hossain", birth_year=1985, sex="male",
    )
    db.add_all([doctor_a, doctor_b, medic, patient])
    db.commit()
    ids = {
        "clinic": clinic.id,
        "doctor_a": doctor_a.id,
        "doctor_b": doctor_b.id,
        "medic": medic.id,
        "patient": patient.id,
    }
    db.close()

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    storage = FilesystemStorage(tmp_path)
    monkeypatch.setattr("backend.app.services.documents.build_storage", lambda *a, **k: storage)
    monkeypatch.setattr(
        "backend.app.api.routes_documents.build_storage", lambda *a, **k: storage
    )
    yield TestClient(app), TestSession, ids
    app.dependency_overrides.clear()


def _visit(session, ids, *, days_ago=0, status="reviewed", doctor_id=None,
           problem=None, tier=None):
    when = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_ago)
    visit = Visit(
        clinic_id=ids["clinic"], patient_id=ids["patient"], status=status,
        assigned_doctor_id=doctor_id, started_at=when, submitted_at=when,
        completed_at=when if status in ("reviewed", "closed") else None,
    )
    session.add(visit)
    session.flush()
    if problem is not None:
        session.add(CaseProfile(visit_id=visit.id, entities={
            "summary_fields": {"main_problem": {"value_en": problem, "source": "ai"}}}))
    if tier is not None:
        session.add(RiskAssessment(visit_id=visit.id, tier=tier, red_flags=[]))
    session.commit()
    return visit.uuid


def _rx_payload(**over):
    payload = {
        "language": "en",
        "date": "2026-08-13",
        "clinic": {"name": "Demo Clinic"},
        "doctor": {"name": "Dr. Yasmin"},
        "patient": {"name": "Kamal Hossain"},
        "symptoms": "chest tightness",
        "diagnosis": "Acid reflux",
        "medicines": [
            {"name": "Omeprazole", "strength": "20mg", "dosage": "1+0+1"},
            {"name": "Antacid syrup", "strength": "", "dosage": "0+0+1"},
        ],
        "advice": "avoid spicy food",
    }
    payload.update(over)
    return payload


# --- patient timeline ---


def test_history_lists_prior_visits_newest_first(env):
    client, Session, ids = env
    db = Session()
    _visit(db, ids, days_ago=60, problem="Cough", tier="low", doctor_id=ids["doctor_a"])
    _visit(db, ids, days_ago=20, problem="Chest tightness", tier="high",
           doctor_id=ids["doctor_a"])
    current = _visit(db, ids, days_ago=0, status="awaiting_doctor",
                     problem="Chest tightness again", tier="critical",
                     doctor_id=ids["doctor_a"])
    db.close()

    body = client.get(f"/api/patients/{ids['patient']}/history").json()
    assert body["patient"]["display_name"] == "Kamal Hossain"
    assert [v["main_problem"] for v in body["visits"]] == [
        "Chest tightness again", "Chest tightness", "Cough",
    ]
    assert body["visits"][0]["visit_uuid"] == current
    assert body["visits"][0]["tier"] == "critical"
    assert body["visits"][0]["status"] == "awaiting_doctor"
    assert body["visits"][1]["assigned_doctor_name"] == "Dr. Yasmin"
    assert all(v["prescription_count"] == 0 for v in body["visits"])


def test_history_carries_no_transcript(env):
    """Rule #1: prior words are read from the one immutable copy via
    GET /api/visits/{uuid}. A summarised history row would be a second rendering."""
    client, Session, ids = env
    db = Session()
    uuid = _visit(db, ids, days_ago=5, problem="Cough", tier="low")
    db.close()
    client.post(f"/api/visits/{uuid}/utterances", json={"raw_text": "কাশি হচ্ছে"})

    body = client.get(f"/api/patients/{ids['patient']}/history").json()
    row = body["visits"][0]
    assert "utterances" not in row and "raw_text" not in row and "corrected_text" not in row
    assert "কাশি হচ্ছে" not in str(body)


def test_history_limit_and_missing_patient(env):
    client, Session, ids = env
    db = Session()
    for day in range(5):
        _visit(db, ids, days_ago=day, problem=f"Problem {day}", tier="low")
    db.close()

    assert len(client.get(f"/api/patients/{ids['patient']}/history").json()["visits"]) == 5
    limited = client.get(f"/api/patients/{ids['patient']}/history", params={"limit": 2}).json()
    assert [v["main_problem"] for v in limited["visits"]] == ["Problem 0", "Problem 1"]

    assert client.get("/api/patients/999999/history").status_code == 404
    assert client.get(f"/api/patients/{ids['patient']}/history",
                      params={"limit": 0}).status_code == 422


def test_history_of_a_patient_with_no_visits_is_empty_not_an_error(env):
    client, Session, ids = env
    db = Session()
    lonely = Patient(clinic_id=ids["clinic"], external_ref="+8801799999999",
                     display_name="New Patient")
    db.add(lonely)
    db.commit()
    lonely_id = lonely.id
    db.close()

    body = client.get(f"/api/patients/{lonely_id}/history").json()
    assert body["visits"] == [] and body["prescriptions"] == []


# --- prescription history (closing a write-only table) ---


def test_previous_prescriptions_come_back_with_a_download_link(env):
    client, Session, ids = env
    db = Session()
    old = _visit(db, ids, days_ago=30, problem="Reflux", tier="medium",
                 doctor_id=ids["doctor_a"])
    db.close()

    created = client.post(
        f"/api/visits/{old}/prescription",
        json={"doctor_id": ids["doctor_a"], "payload": _rx_payload()},
    )
    assert created.status_code == 200
    document_id = created.json()["document"]["id"]

    body = client.get(f"/api/patients/{ids['patient']}/history").json()
    assert len(body["prescriptions"]) == 1
    rx = body["prescriptions"][0]
    assert rx["visit_uuid"] == old
    assert rx["doctor_name"] == "Dr. Yasmin"
    assert rx["diagnosis"] == "Acid reflux"          # doctor-authored, echoed unchanged
    assert rx["medicines"] == ["Omeprazole", "Antacid syrup"]
    assert rx["document_id"] == document_id
    assert rx["download_url"] == f"/api/documents/{document_id}/download"
    assert client.get(rx["download_url"]).status_code == 200

    assert body["visits"][0]["prescription_count"] == 1


def test_medicine_preview_is_capped_and_survives_an_odd_payload(env):
    """prescriptions.payload is deliberately free-form JSON, so the reader must not
    500 on a shape it did not write."""
    many = {"medicines": [{"name": f"Drug {i}"} for i in range(12)]}
    assert len(_medicine_names(many)) == MAX_MEDICINE_PREVIEW

    assert _medicine_names(None) == []
    assert _medicine_names({}) == []
    assert _medicine_names({"medicines": "not a list"}) == []
    assert _medicine_names({"medicines": ["Aspirin", "", None]}) == ["Aspirin"]
    assert _medicine_names({"medicines": [{"strength": "20mg"}]}) == []


def test_prescriptions_from_every_doctor_are_visible_on_the_patient(env):
    """A repeat medication is only detectable if the OTHER doctor's prescription is
    visible too — the patient owns their medication history, not one doctor."""
    client, Session, ids = env
    db = Session()
    first = _visit(db, ids, days_ago=40, problem="Reflux", doctor_id=ids["doctor_a"])
    second = _visit(db, ids, days_ago=3, problem="Reflux again", doctor_id=ids["doctor_b"])
    db.close()

    client.post(f"/api/visits/{first}/prescription",
                json={"doctor_id": ids["doctor_a"], "payload": _rx_payload()})
    client.post(f"/api/visits/{second}/prescription",
                json={"doctor_id": ids["doctor_b"],
                      "payload": _rx_payload(diagnosis="Gastritis",
                                             medicines=[{"name": "Omeprazole"}])})

    body = client.get(f"/api/patients/{ids['patient']}/history").json()
    assert [rx["doctor_name"] for rx in body["prescriptions"]] == ["Dr. Karim", "Dr. Yasmin"]
    assert body["prescriptions"][0]["visit_uuid"] == second


# --- the 'recent' scope: a reviewed case must stay reachable ---


def test_recent_scope_returns_the_doctors_completed_cases(env):
    client, Session, ids = env
    db = Session()
    open_case = _visit(db, ids, days_ago=0, status="awaiting_doctor",
                       doctor_id=ids["doctor_a"], problem="Now", tier="high")
    done = _visit(db, ids, days_ago=1, status="reviewed", doctor_id=ids["doctor_a"],
                  problem="Yesterday", tier="low")
    closed = _visit(db, ids, days_ago=2, status="closed", doctor_id=ids["doctor_a"],
                    problem="Older", tier="low")
    db.close()

    queue = client.get("/api/dashboard", params={"role": "doctor",
                                                 "doctor_id": ids["doctor_a"]}).json()
    assert [i["visit_uuid"] for i in queue] == [open_case]

    recent = client.get("/api/dashboard", params={"role": "doctor", "scope": "recent",
                                                  "doctor_id": ids["doctor_a"]}).json()
    assert [i["visit_uuid"] for i in recent] == [done, closed]
    assert recent[0]["assigned_doctor_name"] == "Dr. Yasmin"


def test_recent_scope_never_leaks_another_doctors_cases(env):
    client, Session, ids = env
    db = Session()
    mine = _visit(db, ids, days_ago=1, status="reviewed", doctor_id=ids["doctor_a"],
                  problem="Mine")
    _visit(db, ids, days_ago=1, status="reviewed", doctor_id=ids["doctor_b"],
           problem="Theirs")
    db.close()

    recent = client.get("/api/dashboard", params={"role": "doctor", "scope": "recent",
                                                  "doctor_id": ids["doctor_a"]}).json()
    assert [i["visit_uuid"] for i in recent] == [mine]

    # A personal list with no owner is refused, never served unfiltered.
    r = client.get("/api/dashboard", params={"role": "doctor", "scope": "recent"})
    assert r.status_code == 400 and "doctor_id" in r.json()["detail"]


def test_history_never_mixes_two_patients(env):
    """The timeline is keyed on patients.id and joins nothing broader. A second
    patient's visits and prescriptions must be invisible from the first's history."""
    client, Session, ids = env
    db = Session()
    mine = _visit(db, ids, days_ago=2, problem="Mine", doctor_id=ids["doctor_a"])
    other = Patient(clinic_id=ids["clinic"], external_ref="+8801755555555",
                    display_name="Other Person", birth_year=1975)
    db.add(other)
    db.flush()
    other_visit = Visit(clinic_id=ids["clinic"], patient_id=other.id, status="reviewed",
                        assigned_doctor_id=ids["doctor_a"])
    db.add(other_visit)
    db.flush()
    db.add(CaseProfile(visit_id=other_visit.id, entities={
        "summary_fields": {"main_problem": {"value_en": "Theirs", "source": "ai"}}}))
    db.commit()
    other_id, other_uuid = other.id, other_visit.uuid
    db.close()

    client.post(f"/api/visits/{other_uuid}/prescription",
                json={"doctor_id": ids["doctor_a"],
                      "payload": _rx_payload(medicines=[{"name": "Metformin"}])})

    body = client.get(f"/api/patients/{ids['patient']}/history").json()
    assert [v["visit_uuid"] for v in body["visits"]] == [mine]
    assert body["prescriptions"] == []
    assert "Theirs" not in str(body) and "Metformin" not in str(body)
    assert "Other Person" not in str(body)

    theirs = client.get(f"/api/patients/{other_id}/history").json()
    assert [v["main_problem"] for v in theirs["visits"]] == ["Theirs"]
    assert theirs["prescriptions"][0]["medicines"] == ["Metformin"]
