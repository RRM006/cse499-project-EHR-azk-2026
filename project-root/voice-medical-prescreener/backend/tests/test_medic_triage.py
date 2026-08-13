"""S37 (ADR-0058) — the medic's operational layer: triage order, wait time, intake
completeness, queue load, and the ADVISORY handoff check.

Offline: no LLM, no network. Visits, profiles and risk rows are written straight to
the test session so the ordering can be driven by exact tiers and exact wait times
instead of hoping a fake model returns the right tier.

What these tests are really pinning:
  * a Critical patient who has waited must outrank a Low one who just arrived;
  * an UNASSESSED case must not sink to the bottom of the queue;
  * SQLite's offset-less UTC timestamps must not blow up the wait arithmetic;
  * the handoff check must never be able to stop a referral.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import (
    AuditLog,
    CaseProfile,
    Clinic,
    Patient,
    RiskAssessment,
    User,
    Visit,
)
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services.triage import (
    TIER_ORDER,
    empty_field_keys,
    human_verified_count,
    triage_sort_key,
    waiting_minutes,
)


@pytest.fixture()
def env():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
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
    ids = {"clinic": clinic.id, "medic": medic.id, "doctor": doctor.id}
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


def _case(
    session,
    ids,
    *,
    name,
    tier=None,
    minutes_waiting=0,
    filled=(),
    verified=(),
    red_flags=None,
    status="awaiting_review",
    doctor_id=None,
    birth_year=1990,
):
    """One submitted case with an exact tier, an exact wait, and exact filled fields.

    ``submitted_at`` is written NAIVE on purpose — that is what SQLite hands back for
    a UTC value, and it is the shape the wait arithmetic has to survive.
    """
    patient = Patient(
        clinic_id=ids["clinic"],
        external_ref=f"+8801{session.query(Patient).count():09d}",
        display_name=name,
        birth_year=birth_year,
    )
    session.add(patient)
    session.flush()
    submitted = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=minutes_waiting)
    visit = Visit(
        clinic_id=ids["clinic"],
        patient_id=patient.id,
        status=status,
        assigned_doctor_id=doctor_id,
        started_at=submitted,
        submitted_at=submitted,
    )
    session.add(visit)
    session.flush()
    fields = {}
    for key in filled:
        fields[key] = {
            "value": f"<{key}>",
            "value_en": f"<{key}>",
            "value_bn": f"<{key}>",
            "source": "human" if key in verified else "ai",
        }
    session.add(
        CaseProfile(
            visit_id=visit.id,
            entities={"summary_fields": fields, "problem_area": {"en": "chest", "bn": "বুক"}},
            summary=f"{name} summary",
        )
    )
    if tier is not None:
        session.add(
            RiskAssessment(visit_id=visit.id, tier=tier, red_flags=red_flags or [])
        )
    session.commit()
    return visit.uuid, patient.id


# --- pure functions (no DB, no HTTP) ---


def test_waiting_minutes_survives_offset_less_timestamps():
    """SQLite returns naive UTC; subtracting that from an aware now() is a TypeError.
    This is the exact defect class the frontend fixed in P2-1, one layer down."""
    naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=42)
    visit = Visit(clinic_id=1, status="awaiting_review", started_at=naive, submitted_at=naive)
    assert waiting_minutes(visit) == 42


def test_waiting_minutes_falls_back_to_started_at_and_never_goes_negative():
    started = datetime.now(timezone.utc) - timedelta(minutes=7)
    visit = Visit(clinic_id=1, status="in_progress", started_at=started, submitted_at=None)
    assert waiting_minutes(visit) == 7  # pre-0011 rows carry no submitted_at

    future = datetime.now(timezone.utc) + timedelta(minutes=5)  # clock skew
    skewed = Visit(clinic_id=1, status="awaiting_review", started_at=future, submitted_at=future)
    assert waiting_minutes(skewed) == 0

    assert waiting_minutes(Visit(clinic_id=1, status="in_progress")) is None


def test_triage_key_puts_worst_tier_first_then_longest_wait():
    rows = [
        ("low_new", "low", 1),
        ("critical_new", "critical", 1),
        ("high_old", "high", 90),
        ("high_new", "high", 2),
        ("critical_old", "critical", 30),
    ]
    ordered = [
        name for name, _, _ in sorted(rows, key=lambda r: triage_sort_key(tier=r[1], waiting=r[2]))
    ]
    assert ordered == ["critical_old", "critical_new", "high_old", "high_new", "low_new"]


def test_unassessed_sorts_between_high_and_medium():
    """"We do not know yet" is not "we know it is fine" — an unassessed case buried
    under every Low-risk row is how an unassessed Critical gets found late."""
    assert TIER_ORDER["high"] < TIER_ORDER[None] < TIER_ORDER["medium"] < TIER_ORDER["low"]
    assert TIER_ORDER["critical"] < TIER_ORDER["high"]


def test_completeness_helpers_use_the_shared_predicate():
    profile = CaseProfile(
        visit_id=1,
        entities={
            "summary_fields": {
                "main_problem": {"value_en": "fever", "source": "human"},
                "allergies": {"value": "   ", "source": "ai"},        # whitespace is empty
                "current_medicines": {"value_bn": "নাই", "source": "ai"},
            }
        },
    )
    empty = empty_field_keys(profile)
    assert "main_problem" not in empty and "current_medicines" not in empty
    assert "allergies" in empty
    assert len(empty) == len(SUMMARY_FIELD_KEYS) - 2
    assert human_verified_count(profile) == 1
    assert empty_field_keys(None) == list(SUMMARY_FIELD_KEYS)
    assert human_verified_count(None) == 0


# --- queue ordering + derived columns over HTTP ---


def test_medic_queue_is_triage_ordered_not_newest_first(env):
    client, Session, ids = env
    db = Session()
    _case(db, ids, name="Low Just Arrived", tier="low", minutes_waiting=0)
    _case(db, ids, name="Critical Waiting", tier="critical", minutes_waiting=40)
    _case(db, ids, name="High Waiting", tier="high", minutes_waiting=25)
    db.close()

    queue = client.get("/api/dashboard", params={"role": "medic"}).json()
    assert [i["patient_name"] for i in queue] == [
        "Critical Waiting",
        "High Waiting",
        "Low Just Arrived",
    ]
    assert queue[0]["waiting_minutes"] >= 40

    # The pre-S37 ordering is still selectable and still newest-submitted-first.
    recent = client.get("/api/dashboard", params={"role": "medic", "sort": "recent"}).json()
    assert recent[0]["patient_name"] == "Low Just Arrived"

    assert client.get("/api/dashboard", params={"role": "medic", "sort": "bogus"}).status_code == 400


def test_queue_rows_carry_intake_completeness(env):
    client, Session, ids = env
    db = Session()
    _case(
        db,
        ids,
        name="Partly Done",
        tier="medium",
        filled=("main_problem", "onset_duration", "allergies"),
        verified=("main_problem",),
    )
    db.close()

    row = client.get("/api/dashboard", params={"role": "medic"}).json()[0]
    assert row["fields_filled"] == 3
    assert row["fields_total"] == len(SUMMARY_FIELD_KEYS) == 10
    assert row["fields_verified"] == 1


def test_phone_search_stays_chronological(env):
    """A phone search is a patient's history, not a work list — triage order would
    scramble the chronology, so `sort` must not reach it."""
    client, Session, ids = env
    db = Session()
    _case(db, ids, name="Repeat Patient", tier="low", minutes_waiting=1)
    patient = db.query(Patient).first()
    old = Visit(
        clinic_id=ids["clinic"],
        patient_id=patient.id,
        status="reviewed",
        started_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30),
    )
    db.add(old)
    db.commit()
    db.add(RiskAssessment(visit_id=old.id, tier="critical"))
    db.commit()
    phone = patient.external_ref
    db.close()

    found = client.get("/api/dashboard", params={"phone": phone}).json()
    assert len(found) == 2
    # Newest first despite the older visit being the Critical one.
    assert found[0]["tier"] == "low" and found[1]["tier"] == "critical"


# --- queue stats ---


def test_queue_stats_describe_the_same_rows_as_the_queue(env):
    client, Session, ids = env
    db = Session()
    _case(db, ids, name="A", tier="critical", minutes_waiting=60, red_flags=["chest pain"])
    _case(db, ids, name="B", tier="high", minutes_waiting=20)
    _case(db, ids, name="C", tier=None, minutes_waiting=10)  # not assessed yet
    _case(db, ids, name="Forwarded", tier="low", status="awaiting_doctor",
          doctor_id=ids["doctor"])
    db.close()

    stats = client.get("/api/dashboard/stats", params={"role": "medic"}).json()
    assert stats["role"] == "medic"
    assert stats["waiting"] == 3            # the forwarded case is not in this queue
    assert stats["critical"] == 1 and stats["high"] == 1 and stats["low"] == 0
    assert stats["unassessed"] == 1
    assert stats["red_flagged"] == 1
    assert stats["longest_wait_minutes"] >= 60
    assert stats["average_wait_minutes"] >= 25

    assert len(client.get("/api/dashboard", params={"role": "medic"}).json()) == stats["waiting"]

    empty = client.get("/api/dashboard/stats", params={"role": "doctor",
                                                      "doctor_id": ids["medic"]}).json()
    assert empty["waiting"] == 0 and empty["longest_wait_minutes"] is None


# --- handoff readiness (ADVISORY) ---


def test_handoff_reports_what_the_doctor_will_be_missing(env):
    client, Session, ids = env
    db = Session()
    uuid, patient_id = _case(db, ids, name="", tier=None, birth_year=None)
    db.close()

    body = client.get(f"/api/visits/{uuid}/handoff").json()
    codes = {c["code"]: c for c in body["checks"]}
    assert body["visit_uuid"] == uuid
    assert body["ready"] is False
    assert codes["main_problem_missing"]["severity"] == "warn"
    assert codes["identity_incomplete"]["severity"] == "warn"
    assert "patient_name" in codes["identity_incomplete"]["detail"]
    assert codes["risk_not_assessed"]["severity"] == "warn"
    assert codes["vitals_missing"]["severity"] == "info"
    assert codes["no_field_verified"]["severity"] == "info"
    assert "main_problem" in codes["fields_empty"]["detail"]

    assert client.get("/api/visits/does-not-exist/handoff").status_code == 404


def test_handoff_turns_ready_once_the_medic_fixes_the_warnings(env):
    client, Session, ids = env
    db = Session()
    uuid, patient_id = _case(
        db, ids, name="Rahima Begum", tier="medium", filled=("main_problem",), birth_year=1980
    )
    db.close()

    body = client.get(f"/api/visits/{uuid}/handoff").json()
    assert body["ready"] is True
    severities = {c["severity"] for c in body["checks"]}
    assert "warn" not in severities
    # Still INFORMATIVE: nothing verified, no vitals, 9 empty fields.
    assert {c["code"] for c in body["checks"]} >= {"vitals_missing", "fields_empty"}

    client.patch(
        f"/api/patients/{patient_id}/vitals",
        json={"weight_kg": 62.5, "editor_id": ids["medic"]},
    )
    codes = {c["code"] for c in client.get(f"/api/visits/{uuid}/handoff").json()["checks"]}
    assert "vitals_missing" not in codes


def test_red_flags_are_surfaced_as_info_not_as_a_gap(env):
    """A red flag is the model's finding about the patient, not paperwork a medic
    can complete — so it must never make a case look 'not ready'."""
    client, Session, ids = env
    db = Session()
    uuid, _ = _case(
        db, ids, name="Karim", tier="critical", red_flags=["chest pain"],
        filled=("main_problem",), birth_year=1970,
    )
    db.close()

    body = client.get(f"/api/visits/{uuid}/handoff").json()
    flag = next(c for c in body["checks"] if c["code"] == "red_flags_present")
    assert flag["severity"] == "info" and "chest pain" in flag["detail"]
    assert body["ready"] is True


def test_handoff_is_advisory_and_cannot_block_a_referral(env):
    """The safety argument for S37: a Critical patient must reach a doctor even with
    incomplete paperwork. Nothing in the assign path may consult the readiness."""
    client, Session, ids = env
    db = Session()
    uuid, _ = _case(db, ids, name="", tier=None, birth_year=None)
    db.close()

    assert client.get(f"/api/visits/{uuid}/handoff").json()["ready"] is False
    r = client.post(f"/api/visits/{uuid}/assign", json={"doctor_id": ids["doctor"]})
    assert r.status_code == 200 and r.json()["status"] == "awaiting_doctor"


# --- referral attribution ---


def test_assign_records_the_forwarding_medic_when_supplied(env):
    client, Session, ids = env
    db = Session()
    uuid, _ = _case(db, ids, name="Nadia", tier="low", filled=("main_problem",))
    db.close()

    r = client.post(
        f"/api/visits/{uuid}/assign",
        json={"doctor_id": ids["doctor"], "editor_id": ids["medic"]},
    )
    assert r.status_code == 200
    db = Session()
    row = db.query(AuditLog).filter(AuditLog.action == "visit.assign").one()
    assert row.actor_id == ids["medic"]
    assert row.detail["doctor_id"] == ids["doctor"]
    db.close()


def test_assign_without_editor_still_works_and_rejects_a_bad_one(env):
    client, Session, ids = env
    db = Session()
    uuid_a, _ = _case(db, ids, name="A", tier="low")
    uuid_b, _ = _case(db, ids, name="B", tier="low")
    db.close()

    # Backward compatible: the walk-in / dev caller never sent an editor.
    assert client.post(f"/api/visits/{uuid_a}/assign",
                       json={"doctor_id": ids["doctor"]}).status_code == 200
    db = Session()
    assert db.query(AuditLog).filter(AuditLog.action == "visit.assign").one().actor_id is None
    db.close()

    # A wrong actor in an audit trail is worse than no actor.
    assert client.post(f"/api/visits/{uuid_b}/assign",
                       json={"doctor_id": ids["doctor"], "editor_id": 9999}).status_code == 403


def test_medic_recent_scope_is_refused_rather_than_guessed(env):
    """Nothing records WHICH medic forwarded a case, so a medic 'recent' list would
    show every medic's work as one person's. Refused, not invented (ADR-0058)."""
    client, Session, ids = env
    r = client.get("/api/dashboard", params={"role": "medic", "scope": "recent"})
    assert r.status_code == 400
    assert "doctor-only" in r.json()["detail"]


# --- data ownership (Phase 10 of the S37 brief) ---


def test_the_new_medic_views_store_nothing(env):
    """ADR-0058's ownership rule, enforced behaviourally rather than by inspection:
    the medic's operational layer is a different QUESTION asked of existing rows, so
    reading it must not create a single row anywhere. If a later change starts
    caching a wait time or a completeness score, this fails."""
    client, Session, ids = env
    db = Session()
    uuid, patient_id = _case(db, ids, name="Ownership", tier="high", filled=("main_problem",))
    tables = (Visit, Patient, CaseProfile, RiskAssessment, AuditLog, User)
    before = {t.__name__: db.query(t).count() for t in tables}
    db.close()

    client.get("/api/dashboard", params={"role": "medic"})
    client.get("/api/dashboard/stats", params={"role": "medic"})
    client.get(f"/api/visits/{uuid}/handoff")
    client.get("/api/dashboard", params={"role": "doctor", "doctor_id": ids["doctor"]})

    db = Session()
    after = {t.__name__: db.query(t).count() for t in tables}
    db.close()
    assert after == before, f"a read-only view wrote rows: {before} -> {after}"


def test_no_medic_owned_copy_of_patient_or_doctor_identity(env):
    """The queue row carries the patient's NAME and the doctor's NAME, but both are
    resolved per request from `patients` / `users`. Renaming either must change the
    queue immediately — if it does not, something cached an identity it does not own."""
    client, Session, ids = env
    db = Session()
    uuid, patient_id = _case(db, ids, name="Old Name", tier="low", doctor_id=ids["doctor"],
                             status="awaiting_doctor")
    db.close()

    row = client.get("/api/dashboard", params={"role": "doctor",
                                               "doctor_id": ids["doctor"]}).json()[0]
    assert row["patient_name"] == "Old Name" and row["assigned_doctor_name"] == "Dr. Yasmin"

    db = Session()
    db.get(Patient, patient_id).display_name = "New Name"
    db.get(User, ids["doctor"]).name = "Dr. Renamed"
    db.commit()
    db.close()

    row = client.get("/api/dashboard", params={"role": "doctor",
                                               "doctor_id": ids["doctor"]}).json()[0]
    assert row["patient_name"] == "New Name"
    assert row["assigned_doctor_name"] == "Dr. Renamed"
