"""S39 (ADR-0064) — the medic records BLOOD SUGAR, before the referral.

WHAT WAS ACTUALLY MISSING
-------------------------
S38 shipped the glucose reference CHART but no place to write a reading, so "the
medic cannot edit sugar" was literally true: there was nothing to edit. This adds the
value (rev 0014) and pins the properties that make it safe:

  * a reading and its measurement context are ONE fact and are refused apart — a
    fasting 6.5 and a random 6.5 are different findings, and a stored number with no
    context cannot be read safely by anyone later;
  * the medic can record and CORRECT it while the visit is still ``awaiting_review``,
    i.e. before any referral — a referral is not a prerequisite for intake;
  * the referral itself still works afterwards, and the doctor receives the value;
  * a non-staff actor still cannot write it;
  * **no band, class or interpretation is computed or stored anywhere** (rule #2).

Synthetic data only (rule #4).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import AuditLog, Clinic, Patient, User, Visit
from backend.app.main import app
from backend.app.services.clinical_reference import (
    RECORDABLE_GLUCOSE_CONTEXTS,
    glucose_reference,
)


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
    medic = User(clinic_id=clinic.id, name="Medic Rahman", role="medic")
    doctor = User(clinic_id=clinic.id, name="Dr Aziz", role="doctor")
    desk = User(clinic_id=clinic.id, name="Front Desk", role="desk")
    patient = Patient(clinic_id=clinic.id, external_ref="+8801700000000")
    db.add_all([medic, doctor, desk, patient])
    db.flush()
    # A submitted visit, in the medic queue — i.e. BEFORE any referral.
    visit = Visit(clinic_id=clinic.id, patient_id=patient.id, status="awaiting_review")
    db.add(visit)
    db.commit()
    ids = {"medic": medic.id, "doctor": doctor.id, "desk": desk.id,
           "patient": patient.id, "visit": visit.uuid}
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


# --- 1. the medic edits sugar BEFORE referring --------------------------------------


def test_medic_records_glucose_while_the_visit_is_still_pre_referral(env):
    client, TestSession, ids = env
    db = TestSession()
    assert db.query(Visit).filter(Visit.uuid == ids["visit"]).first().status == "awaiting_review"
    assert db.get(Visit, 1).assigned_doctor_id is None, "no referral has happened yet"
    db.close()

    res = client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_mmol_l": 6.4, "blood_glucose_context": "fasting",
        "editor_id": ids["medic"],
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["blood_glucose_mmol_l"] == 6.4
    assert body["blood_glucose_context"] == "fasting"


def test_the_reading_persists_and_can_be_corrected(env):
    """"Reload" is a fresh GET, and a correction is another PATCH — the medic must be
    able to fix a mistyped reading without referring the patient first."""
    client, TestSession, ids = env
    client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_mmol_l": 16.4, "blood_glucose_context": "random",
        "editor_id": ids["medic"]})

    reloaded = client.get(f"/api/visits/{ids['visit']}").json()["patient"]
    assert reloaded["blood_glucose_mmol_l"] == 16.4
    assert reloaded["blood_glucose_context"] == "random"

    res = client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_mmol_l": 6.4, "blood_glucose_context": "fasting",
        "editor_id": ids["medic"]})
    assert res.status_code == 200
    corrected = client.get(f"/api/visits/{ids['visit']}").json()["patient"]
    assert corrected["blood_glucose_mmol_l"] == 6.4
    assert corrected["blood_glucose_context"] == "fasting", "the context must be corrected too"


def test_the_other_intake_fields_still_save_in_the_same_call(env):
    """One form, one PATCH, one audit row — glucose joins the existing fields rather
    than needing a second endpoint."""
    client, TestSession, ids = env
    res = client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "display_name": "রহিমা বেগম", "age_years": 52, "sex": "female",
        "height_cm": 158.0, "weight_kg": 61.5, "bp": "130/85",
        "blood_glucose_mmol_l": 5.2, "blood_glucose_context": "ogtt_2h",
        "editor_id": ids["medic"],
    })
    assert res.status_code == 200, res.text
    p = res.json()
    assert (p["display_name"], p["sex"], p["height_cm"], p["weight_kg"], p["bp"]) == (
        "রহিমা বেগম", "female", 158.0, 61.5, "130/85")
    assert p["blood_glucose_mmol_l"] == 5.2

    db = TestSession()
    entry = (db.query(AuditLog).filter(AuditLog.action == "patient.vitals_edit")
             .order_by(AuditLog.id.desc()).first())
    assert entry is not None and entry.actor_id == ids["medic"]
    assert entry.detail["blood_glucose_mmol_l"] == 5.2
    assert entry.detail["blood_glucose_context"] == "ogtt_2h"
    db.close()


# --- 2. a value and its context cannot come apart -----------------------------------


def test_a_reading_without_a_context_is_refused(env):
    client, _TestSession, ids = env
    res = client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_mmol_l": 7.1, "editor_id": ids["medic"]})
    assert res.status_code == 400
    assert "context" in res.json()["detail"].lower()
    assert client.get(f"/api/visits/{ids['visit']}").json()[
        "patient"]["blood_glucose_mmol_l"] is None


def test_a_context_without_a_reading_is_refused(env):
    client, _TestSession, ids = env
    res = client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_context": "fasting", "editor_id": ids["medic"]})
    assert res.status_code == 400
    assert client.get(f"/api/visits/{ids['visit']}").json()[
        "patient"]["blood_glucose_context"] is None


def test_an_unknown_context_is_refused_by_the_schema(env):
    client, _TestSession, ids = env
    res = client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_mmol_l": 7.1, "blood_glucose_context": "after lunch",
        "editor_id": ids["medic"]})
    assert res.status_code == 422


def test_an_implausible_reading_is_refused(env):
    """A transposed digit must not enter the record. 650 mmol/L is not a glucometer
    reading, it is a typo for 6.5 with the decimal point lost."""
    client, _TestSession, ids = env
    for bad in (0, -3, 650):
        res = client.patch(f"/api/patients/{ids['patient']}/vitals", json={
            "blood_glucose_mmol_l": bad, "blood_glucose_context": "random",
            "editor_id": ids["medic"]})
        assert res.status_code == 422, f"{bad} was accepted"


def test_hba1c_is_not_a_recordable_context(env):
    """It is a percentage and a lab result, not the bedside mmol/L reading this column
    holds — so it stays on the reference chart with no input beside it."""
    client, _TestSession, ids = env
    assert "hba1c" not in RECORDABLE_GLUCOSE_CONTEXTS
    assert "hba1c" in {c["code"] for c in glucose_reference()["contexts"]}
    res = client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_mmol_l": 6.5, "blood_glucose_context": "hba1c",
        "editor_id": ids["medic"]})
    assert res.status_code == 422


def test_recordable_contexts_are_a_subset_of_the_published_chart(env):
    published = {c["code"] for c in glucose_reference()["contexts"]}
    assert set(RECORDABLE_GLUCOSE_CONTEXTS) <= published
    assert glucose_reference()["recordable"] == list(RECORDABLE_GLUCOSE_CONTEXTS)


# --- 3. permissions -----------------------------------------------------------------


def test_a_non_clinical_actor_cannot_record_a_reading(env):
    client, _TestSession, ids = env
    for actor in (ids["desk"], 9999):
        res = client.patch(f"/api/patients/{ids['patient']}/vitals", json={
            "blood_glucose_mmol_l": 6.4, "blood_glucose_context": "fasting",
            "editor_id": actor})
        assert res.status_code == 403, f"editor {actor} was allowed to write vitals"
    assert client.get(f"/api/visits/{ids['visit']}").json()[
        "patient"]["blood_glucose_mmol_l"] is None


def test_a_doctor_may_still_write_vitals(env):
    """Unchanged from before S39 (portal_roles §5) — this pins that the new field did
    not narrow an existing permission."""
    client, _TestSession, ids = env
    res = client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_mmol_l": 6.4, "blood_glucose_context": "fasting",
        "editor_id": ids["doctor"]})
    assert res.status_code == 200


# --- 4. the referral still works, and the doctor gets the value ---------------------


def test_referral_still_works_and_carries_the_reading_to_the_doctor(env):
    client, _TestSession, ids = env
    client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_mmol_l": 6.4, "blood_glucose_context": "fasting",
        "weight_kg": 61.5, "editor_id": ids["medic"]})

    res = client.post(f"/api/visits/{ids['visit']}/assign",
                      json={"doctor_id": ids["doctor"], "editor_id": ids["medic"]})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "awaiting_doctor"

    # What the doctor's portal loads.
    detail = client.get(f"/api/visits/{ids['visit']}").json()
    assert detail["patient"]["blood_glucose_mmol_l"] == 6.4
    assert detail["patient"]["blood_glucose_context"] == "fasting"

    queue = client.get("/api/dashboard?role=doctor").json()
    assert any(row["visit_uuid"] == ids["visit"] for row in queue)


def test_an_edit_after_the_referral_is_still_possible_for_a_doctor(env):
    """The requirement was that a referral must not be a PREREQUISITE for editing —
    not that a referral freezes the record. This pins that nothing was locked."""
    client, _TestSession, ids = env
    client.post(f"/api/visits/{ids['visit']}/assign",
                json={"doctor_id": ids["doctor"], "editor_id": ids["medic"]})
    res = client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_mmol_l": 8.9, "blood_glucose_context": "random",
        "editor_id": ids["doctor"]})
    assert res.status_code == 200


# --- 5. rule #2 — a measurement is never turned into a finding ----------------------


def test_nothing_anywhere_classifies_the_stored_reading(env):
    """The value is reported; the published chart is displayed; a person reads one
    against the other. No band, no flag, no interpretation is produced from it."""
    client, _TestSession, ids = env
    client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_mmol_l": 14.2,          # unambiguously above every threshold
        "blood_glucose_context": "fasting", "editor_id": ids["medic"]})

    payload = client.get(f"/api/visits/{ids['visit']}").json()
    text = repr(payload).lower()
    for verdict in ("diabet", "impaired", "abnormal", "high risk", "elevated"):
        assert verdict not in text, f"the payload interpreted the reading as '{verdict}'"

    handoff = client.get(f"/api/visits/{ids['visit']}/handoff").json()
    assert not any("glucose" in c["code"] or "sugar" in c["code"] for c in handoff["checks"]), (
        "a missing or high sugar must not become a handover finding"
    )


def test_the_reference_chart_still_takes_no_patient_value(env):
    """ADR-0060, re-pinned now that a value exists to be tempted with."""
    import inspect as _inspect

    from backend.app.services import clinical_reference

    assert _inspect.signature(clinical_reference.glucose_reference).parameters == {}
    client, _TestSession, ids = env
    assert client.get("/api/reference/glucose?value=14.2").status_code == 200
    assert client.get("/api/reference/glucose").json()["contexts"]


def test_the_fhir_bundle_exports_value_and_context_but_no_interpretation(env):
    client, TestSession, ids = env
    client.patch(f"/api/patients/{ids['patient']}/vitals", json={
        "blood_glucose_mmol_l": 6.4, "blood_glucose_context": "fasting",
        "editor_id": ids["medic"]})

    from backend.app.db.models import Visit as V
    from backend.app.services.ehr_export import build_fhir_bundle

    db = TestSession()
    visit = db.query(V).filter(V.uuid == ids["visit"]).first()
    bundle = build_fhir_bundle(db, visit)
    db.close()

    obs = [e["resource"] for e in bundle["entry"]
           if e["resource"]["resourceType"] == "Observation"
           and "glucose" in e["resource"]["id"]]
    assert len(obs) == 1
    glucose = obs[0]
    assert glucose["valueQuantity"] == {
        "value": 6.4, "unit": "mmol/L",
        "system": "http://unitsofmeasure.org", "code": "mmol/L"}
    # A lab measurement, not a vital sign — mis-categorising it would file it beside
    # pulse and weight in the receiving system.
    assert glucose["category"][0]["coding"][0]["code"] == "laboratory"
    codes = {c["code"] for c in glucose["code"]["coding"]}
    assert "15074-8" in codes and "fasting" in codes
    assert "fasting" in glucose["code"]["text"].lower()
    # Rule #2: reported, never judged.
    assert "interpretation" not in glucose
    assert "referenceRange" not in glucose
