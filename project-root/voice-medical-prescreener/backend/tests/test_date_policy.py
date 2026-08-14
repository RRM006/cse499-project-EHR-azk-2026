"""S38 (B5, ADR-0061) — the date policy, enforced at the API and not only in the form.

The human's requirement was "cannot use previous date anywhere". Applied literally that
would rewrite history, so it is applied BY CATEGORY (services/clinical_dates), and this
file is where each category's rule is pinned:

  A. **System / historical timestamps** — never validated, never rewritten.
     ``test_a_historical_visit_timestamp_is_never_touched`` is the important one here:
     it is easy to "fix dates everywhere" and quietly corrupt the record of when a
     patient actually arrived.
  B. **Authored now** (the prescription date) — must be today in Dhaka.
  C. **Scheduled forward** (the follow-up date) — must not be in the past.

Everything runs through the REAL ``POST /prescription`` route, because the form's
``min``/``max`` attributes are a courtesy to the doctor and prove nothing about what the
server will accept from a script or a replayed request.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import Clinic, Patient, Prescription, User, Visit
from backend.app.main import app
from backend.app.services.clinical_dates import dhaka_today_iso
from backend.app.services.documents.storage import FilesystemStorage

TODAY = date.fromisoformat(dhaka_today_iso())
YESTERDAY = (TODAY - timedelta(days=1)).isoformat()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()
NEXT_MONTH = (TODAY + timedelta(days=30)).isoformat()

#: A timestamp deliberately in the past, used to prove category A is left alone.
HISTORIC_START = datetime(2026, 3, 2, 8, 15, tzinfo=timezone.utc)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    db = TestSession()
    clinic = Clinic(name="Demo Clinic")
    db.add(clinic)
    db.flush()
    doctor = User(clinic_id=clinic.id, name="Dr. Yasmin", role="doctor")
    patient = Patient(clinic_id=clinic.id, display_name="Kamal Hossain")
    db.add_all([doctor, patient])
    db.flush()
    # An OLD visit — its timestamps must survive everything this file does.
    visit = Visit(
        clinic_id=clinic.id, patient_id=patient.id, status="awaiting_doctor",
        started_at=HISTORIC_START, submitted_at=HISTORIC_START + timedelta(minutes=12),
    )
    db.add(visit)
    db.commit()
    ids = {"visit_uuid": visit.uuid, "doctor_id": doctor.id, "visit_id": visit.id}
    db.close()

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    storage = FilesystemStorage(tmp_path)
    monkeypatch.setattr(
        "backend.app.services.documents.build_storage", lambda *a, **k: storage
    )
    yield TestClient(app), TestSession, ids
    app.dependency_overrides.clear()


def _payload(**over):
    payload = {
        "language": "en",
        "date": dhaka_today_iso(),
        "clinic": {"name": "Demo Clinic"},
        "doctor": {"name": "Dr. Yasmin"},
        "patient": {"name": "Kamal Hossain"},
        "symptoms": "cough",
        "diagnosis": "Viral URTI",
        "medicines": [{"name": "Napa", "strength": "500mg", "dosage": "1+0+1",
                       "timing": "after meals", "duration": "5 days"}],
        "advice": "Rest", "tests": "CBC", "followup_date": "",
    }
    payload.update(over)
    return payload


def _post(client, ids, **over):
    return client.post(
        f"/api/visits/{ids['visit_uuid']}/prescription",
        json={"doctor_id": ids["doctor_id"], "payload": _payload(**over)},
    )


# --- Category B: the prescription date is authored NOW -----------------------


def test_todays_prescription_is_accepted(env):
    client, _, ids = env
    assert _post(client, ids).status_code == 200


def test_a_backdated_prescription_is_refused(env):
    """A prescription is dated by the act of writing it. Backdating one misdates a
    document the patient carries to a pharmacy."""
    client, _, ids = env
    r = _post(client, ids, date=YESTERDAY)
    assert r.status_code == 400
    assert "past" in r.json()["detail"].lower()
    assert dhaka_today_iso() in r.json()["detail"], "the error must say what IS allowed"


def test_a_post_dated_prescription_is_refused(env):
    """Post-dating is the same defect pointing the other way: it makes one consultation
    look like it happened on a day it did not."""
    client, _, ids = env
    r = _post(client, ids, date=TOMORROW)
    assert r.status_code == 400
    assert "future" in r.json()["detail"].lower()


def test_a_missing_prescription_date_is_stamped_not_rejected(env):
    """An older client that never sent a date should get the RIGHT date, not a 400."""
    client, TestSession, ids = env
    r = _post(client, ids, date="")
    assert r.status_code == 200, r.text
    with TestSession() as db:
        stored = db.get(Prescription, r.json()["prescription_id"])
        assert stored.payload["date"] == dhaka_today_iso()


def test_an_unparseable_date_is_a_400_not_a_500(env):
    client, _, ids = env
    r = _post(client, ids, date="14/08/2026")
    assert r.status_code == 400
    assert "valid" in r.json()["detail"].lower()


# --- Category C: the follow-up is scheduled FORWARD ---------------------------


def test_a_follow_up_in_the_past_is_refused(env):
    client, _, ids = env
    r = _post(client, ids, followup_date=YESTERDAY)
    assert r.status_code == 400
    assert "follow-up" in r.json()["detail"].lower()


def test_a_follow_up_today_or_far_ahead_is_accepted(env):
    """A same-day recheck is real, and so is a twelve-month recall — category C has a
    floor, not a ceiling."""
    client, _, ids = env
    assert _post(client, ids, followup_date=dhaka_today_iso()).status_code == 200
    assert _post(client, ids, followup_date=NEXT_MONTH).status_code == 200


def test_an_empty_follow_up_stays_empty(env):
    """Most prescriptions have no follow-up date. Validating a blank into a 400 would
    make an optional field effectively mandatory."""
    client, _, ids = env
    assert _post(client, ids, followup_date="").status_code == 200


# --- Category A: history is not "fixed" ---------------------------------------


def test_a_historical_visit_timestamp_is_never_touched(env):
    """The dangerous reading of "cannot use previous date anywhere" is to stamp today
    onto everything. A visit records when the patient actually came."""
    client, TestSession, ids = env
    assert _post(client, ids).status_code == 200
    with TestSession() as db:
        visit = db.get(Visit, ids["visit_id"])
        assert visit.started_at.replace(tzinfo=timezone.utc) == HISTORIC_START
        assert visit.submitted_at.replace(tzinfo=timezone.utc) == HISTORIC_START + timedelta(minutes=12)


def test_a_prescription_can_be_written_today_for_an_old_visit(env):
    """The corollary, and the reason category A and category B are separate: the visit
    is from March; the prescription is written now. Both dates are correct."""
    client, TestSession, ids = env
    r = _post(client, ids)
    assert r.status_code == 200
    with TestSession() as db:
        stored = db.get(Prescription, r.json()["prescription_id"])
        assert stored.payload["date"] == dhaka_today_iso()
        assert db.get(Visit, ids["visit_id"]).started_at.year == 2026
        assert db.get(Visit, ids["visit_id"]).started_at.month == 3


def test_the_rejected_date_never_reaches_storage_or_a_document(env):
    """The check runs BEFORE the write. If it ran after, the stored payload and the
    generated .docx could disagree — and the .docx is the copy that leaves the clinic."""
    client, TestSession, ids = env
    assert _post(client, ids, date=YESTERDAY).status_code == 400
    with TestSession() as db:
        assert db.query(Prescription).count() == 0
