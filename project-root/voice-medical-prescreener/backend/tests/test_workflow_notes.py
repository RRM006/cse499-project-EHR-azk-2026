"""S38 (C1-C4, ADR-0060) — the four workflow features S37 deferred.

  C1 medic completed-referral history   — DERIVED from audit_log; no new table
  C2 per-field verification             — inside the existing summary_fields JSON
  C3 doctor recall scheduling           — clinical_notes, kind='recall'
  C4 doctor -> medic back-channel       — clinical_notes, kind='handover_note'

The assertions that matter most are the ones about what these features must NOT become:

  * C1 must not INVENT an owner for a referral made before S37 started recording one.
    Reporting an incomplete list honestly is the requirement; a plausible-looking
    complete one would be a lie about who did the work.
  * C2 must not touch the VALUE. Before S38 the only way to signal "I checked this"
    was to edit the field, which put a false edit in a medical record — so a test
    proves the value and its ``source`` survive verification untouched.
  * C3/C4 must not become a chat. One table, no thread, no reply, addressed to a ROLE.
  * A note must never be a clinical finding — it is human-authored workflow text
    (rule #2), and nothing reads it back into the pipeline.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import (
    AuditLog, CaseProfile, Clinic, ClinicalNote, Patient, RiskAssessment, User, Visit,
)
from backend.app.main import app
from backend.app.services.clinical_dates import dhaka_today_iso

TODAY = date.fromisoformat(dhaka_today_iso())
YESTERDAY = (TODAY - timedelta(days=1)).isoformat()
NEXT_WEEK = (TODAY + timedelta(days=7)).isoformat()
NEXT_MONTH = (TODAY + timedelta(days=30)).isoformat()


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
    medic_a = User(clinic_id=clinic.id, name="Medic Rahman", role="medic")
    medic_b = User(clinic_id=clinic.id, name="Medic Nasrin", role="medic")
    doctor = User(clinic_id=clinic.id, name="Dr. Yasmin", role="doctor")
    desk = User(clinic_id=clinic.id, name="Front Desk", role="desk")
    db.add_all([medic_a, medic_b, doctor, desk])
    db.commit()
    ids = {"clinic": clinic.id, "medic_a": medic_a.id, "medic_b": medic_b.id,
           "doctor": doctor.id, "desk": desk.id}
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


def _case(session, ids, *, name, status="awaiting_review", fields=None, tier=None):
    patient = Patient(clinic_id=ids["clinic"], display_name=name,
                      external_ref=f"+88017{abs(hash(name)) % 100000000:08d}")
    session.add(patient)
    session.flush()
    visit = Visit(clinic_id=ids["clinic"], patient_id=patient.id, status=status,
                  started_at=datetime.now(timezone.utc) - timedelta(minutes=30),
                  submitted_at=datetime.now(timezone.utc) - timedelta(minutes=25))
    session.add(visit)
    session.flush()
    session.add(CaseProfile(visit_id=visit.id, summary=name,
                            entities={"summary_fields": fields or {}}))
    if tier:
        session.add(RiskAssessment(visit_id=visit.id, tier=tier, red_flags=[]))
    session.commit()
    return visit.uuid


# ===========================================================================
# C2 — per-field verification
# ===========================================================================


AI_FIELD = {"main_problem": {"value": "Chest pain", "value_en": "Chest pain",
                             "value_bn": "বুকে ব্যথা", "source": "ai"}}


def test_verifying_a_field_does_not_change_its_value_or_its_source(env):
    """THE point of C2. Before S38 the only way to record 'I read this and it is
    correct' was to EDIT the field — retyping the model's own words — which left a
    false edit in a medical record and made 'verified' and 'corrected' identical
    afterwards."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal", fields=dict(AI_FIELD))

    r = client.post(f"/api/visits/{uuid}/profile/fields/main_problem/verify",
                    json={"editor_id": ids["medic_a"]})
    assert r.status_code == 200, r.text
    field = r.json()["entities"]["summary_fields"]["main_problem"]
    assert field["value"] == "Chest pain"
    assert field["value_bn"] == "বুকে ব্যথা"
    # The model DID write this value; erasing that provenance would be a lie.
    assert field["source"] == "ai"
    assert field["verified_by"] == ids["medic_a"]
    assert field["verified_at"]


def test_a_verified_field_counts_towards_fields_verified(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal", fields=dict(AI_FIELD))
    before = client.get("/api/dashboard?role=medic").json()[0]["fields_verified"]
    client.post(f"/api/visits/{uuid}/profile/fields/main_problem/verify",
                json={"editor_id": ids["medic_a"]})
    after = client.get("/api/dashboard?role=medic").json()[0]["fields_verified"]
    assert (before, after) == (0, 1)


def test_an_edited_field_still_counts_as_verified(env):
    """Both acts mean 'a human owns this'; C2 adds a second route to it, it does not
    replace the first."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal", fields=dict(AI_FIELD))
    client.patch(f"/api/visits/{uuid}/profile/fields/main_problem",
                 json={"value": "Central chest pain", "editor_id": ids["medic_a"]})
    assert client.get("/api/dashboard?role=medic").json()[0]["fields_verified"] == 1


def test_verification_can_be_undone(env):
    """A mis-click is a mis-click. Undoing removes the claim rather than recording a
    negative one."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal", fields=dict(AI_FIELD))
    client.post(f"/api/visits/{uuid}/profile/fields/main_problem/verify",
                json={"editor_id": ids["medic_a"]})
    r = client.post(f"/api/visits/{uuid}/profile/fields/main_problem/verify",
                    json={"editor_id": ids["medic_a"], "verified": False})
    field = r.json()["entities"]["summary_fields"]["main_problem"]
    assert "verified_by" not in field and "verified_at" not in field


def test_an_empty_field_cannot_be_verified(env):
    """'I have checked this blank' is not a claim anyone can make — and allowing it
    would let a case reach 10/10 verified with nothing in it."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal", fields={})
    r = client.post(f"/api/visits/{uuid}/profile/fields/main_problem/verify",
                    json={"editor_id": ids["medic_a"]})
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower()


def test_verification_guard_rails(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal", fields=dict(AI_FIELD))
    # Unknown field key -> 400.
    assert client.post(f"/api/visits/{uuid}/profile/fields/nope/verify",
                       json={"editor_id": ids["medic_a"]}).status_code == 400
    # Non-clinical staff -> 403 (a desk clerk does not verify clinical extraction).
    assert client.post(f"/api/visits/{uuid}/profile/fields/main_problem/verify",
                       json={"editor_id": ids["desk"]}).status_code == 403
    # Unknown visit -> 404.
    assert client.post("/api/visits/nope/profile/fields/main_problem/verify",
                       json={"editor_id": ids["medic_a"]}).status_code == 404


def test_verification_is_audited(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal", fields=dict(AI_FIELD))
    client.post(f"/api/visits/{uuid}/profile/fields/main_problem/verify",
                json={"editor_id": ids["medic_a"]})
    with TestSession() as db:
        log = db.query(AuditLog).filter(AuditLog.action == "profile.field_verify").one()
        assert log.actor_id == ids["medic_a"]
        assert log.detail == {"field": "main_problem", "verified": True}


def test_verification_never_touches_the_raw_transcript(env):
    """Rule #1 twice over: it edits only the DERIVED profile, and not even a value there."""
    from backend.app.db.models import Utterance

    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal", fields=dict(AI_FIELD))
        visit = db.query(Visit).filter(Visit.uuid == uuid).one()
        db.add(Utterance(visit_id=visit.id, role="patient", seq=1,
                         raw_text="আমার বুকে ব্যথা", source="mic"))
        db.commit()
    client.post(f"/api/visits/{uuid}/profile/fields/main_problem/verify",
                json={"editor_id": ids["medic_a"]})
    with TestSession() as db:
        assert db.query(Utterance).one().raw_text == "আমার বুকে ব্যথা"


# ===========================================================================
# C1 — the medic's completed referrals
# ===========================================================================


def _forward(client, uuid, ids, medic_key="medic_a"):
    return client.post(f"/api/visits/{uuid}/assign",
                       json={"doctor_id": ids["doctor"], "editor_id": ids[medic_key]})


def test_a_medic_sees_the_referrals_they_made(env):
    client, TestSession, ids = env
    with TestSession() as db:
        first = _case(db, ids, name="Kamal", tier="high")
        second = _case(db, ids, name="Rahima", tier="low")
    assert _forward(client, first, ids).status_code == 200
    assert _forward(client, second, ids).status_code == 200

    r = client.get(f"/api/medics/{ids['medic_a']}/referrals")
    assert r.status_code == 200, r.text
    body = r.json()
    assert {ref["patient_name"] for ref in body["referrals"]} == {"Kamal", "Rahima"}
    assert body["referrals"][0]["doctor_name"] == "Dr. Yasmin"
    assert {ref["tier"] for ref in body["referrals"]} == {"high", "low"}


def test_a_medic_never_sees_another_medics_referrals(env):
    """The whole reason S37 refused this: a list that mixed two people's work would be
    worse than no list."""
    client, TestSession, ids = env
    with TestSession() as db:
        mine = _case(db, ids, name="Kamal")
        theirs = _case(db, ids, name="Rahima")
    _forward(client, mine, ids, "medic_a")
    _forward(client, theirs, ids, "medic_b")

    a = client.get(f"/api/medics/{ids['medic_a']}/referrals").json()["referrals"]
    b = client.get(f"/api/medics/{ids['medic_b']}/referrals").json()["referrals"]
    assert [ref["patient_name"] for ref in a] == ["Kamal"]
    assert [ref["patient_name"] for ref in b] == ["Rahima"]


def test_unattributed_referrals_are_counted_not_invented(env):
    """Referrals made before S37 recorded an actor belong to NOBODY. Assigning them to
    whoever asks would be a lie; hiding them entirely would look like lost work."""
    client, TestSession, ids = env
    with TestSession() as db:
        legacy = _case(db, ids, name="Legacy Patient")
    # A forward with no editor — exactly the pre-S37 shape.
    assert client.post(f"/api/visits/{legacy}/assign",
                       json={"doctor_id": ids["doctor"]}).status_code == 200

    body = client.get(f"/api/medics/{ids['medic_a']}/referrals").json()
    assert body["referrals"] == []
    assert body["unattributed_total"] == 1


def test_the_referral_history_stores_nothing_new(env):
    """C1 is a different QUESTION asked of audit_log, not a new record of its own."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    _forward(client, uuid, ids)
    with TestSession() as db:
        rows_before = db.query(AuditLog).count(), db.query(ClinicalNote).count()
    client.get(f"/api/medics/{ids['medic_a']}/referrals")
    with TestSession() as db:
        assert (db.query(AuditLog).count(), db.query(ClinicalNote).count()) == rows_before


def test_referral_history_rejects_a_non_medic(env):
    client, _, ids = env
    assert client.get(f"/api/medics/{ids['doctor']}/referrals").status_code == 404
    assert client.get("/api/medics/99999/referrals").status_code == 404


# ===========================================================================
# C3 — recall scheduling
# ===========================================================================


def _recall(client, uuid, ids, **over):
    payload = {"kind": "recall", "body": "Recheck blood pressure",
               "author_id": ids["doctor"], "due_date": NEXT_WEEK}
    payload.update(over)
    return client.post(f"/api/visits/{uuid}/notes", json=payload)


def test_a_doctor_can_schedule_a_recall(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal", status="reviewed")
    r = _recall(client, uuid, ids)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "recall"
    assert body["due_date"] == NEXT_WEEK
    assert body["status"] == "open"
    assert body["author_name"] == "Dr. Yasmin"
    assert body["patient_name"] == "Kamal"


def test_a_recall_cannot_be_scheduled_in_the_past(env):
    """ADR-0061 category C: a recall is a scheduled-forward date."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    r = _recall(client, uuid, ids, due_date=YESTERDAY)
    assert r.status_code == 400
    assert "past" in r.json()["detail"].lower()


def test_a_recall_today_or_far_ahead_is_fine(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    assert _recall(client, uuid, ids, due_date=dhaka_today_iso()).status_code == 200
    assert _recall(client, uuid, ids, due_date=NEXT_MONTH).status_code == 200


def test_the_recall_list_is_ordered_by_due_date(env):
    """A recall due today outranks one due next month; the fairness rule matches the
    triage queue's inside a tier."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    _recall(client, uuid, ids, due_date=NEXT_MONTH, body="Late one")
    _recall(client, uuid, ids, due_date=dhaka_today_iso(), body="Due today")
    _recall(client, uuid, ids, due_date=NEXT_WEEK, body="Middle")

    rows = client.get("/api/notes?kind=recall").json()
    assert [n["body"] for n in rows] == ["Due today", "Middle", "Late one"]


def test_a_resolved_recall_leaves_the_open_list(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    note_id = _recall(client, uuid, ids).json()["id"]

    r = client.patch(f"/api/notes/{note_id}",
                     json={"status": "done", "actor_id": ids["medic_a"]})
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert r.json()["resolved_by_name"] == "Medic Rahman"
    assert client.get("/api/notes?kind=recall&status=open").json() == []
    assert len(client.get("/api/notes?kind=recall&status=done").json()) == 1


def test_a_note_cannot_be_resolved_twice(env):
    """The first person to act on it is the one who acted on it."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    note_id = _recall(client, uuid, ids).json()["id"]
    client.patch(f"/api/notes/{note_id}", json={"status": "done", "actor_id": ids["medic_a"]})
    again = client.patch(f"/api/notes/{note_id}",
                         json={"status": "cancelled", "actor_id": ids["medic_b"]})
    assert again.status_code == 409


# ===========================================================================
# C4 — the doctor -> medic back-channel
# ===========================================================================


def _handover(client, uuid, ids, **over):
    payload = {"kind": "handover_note", "body": "Please repeat the BP before I see her.",
               "author_id": ids["doctor"], "recipient_role": "medic"}
    payload.update(over)
    return client.post(f"/api/visits/{uuid}/notes", json=payload)


def test_a_doctor_can_send_a_note_back_to_the_desk(env):
    """The status flow runs one way by design; this is the one narrow exception, and
    it carries no clinical decision."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Rahima", status="awaiting_doctor")
    r = _handover(client, uuid, ids)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "handover_note"
    assert body["recipient_role"] == "medic"
    assert body["author_role"] == "doctor"
    assert body["due_date"] is None


def test_the_medic_inbox_shows_it(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Rahima")
    _handover(client, uuid, ids)
    inbox = client.get("/api/notes?recipient_role=medic&status=open").json()
    assert len(inbox) == 1
    assert inbox[0]["patient_name"] == "Rahima"
    assert inbox[0]["visit_uuid"] == uuid
    # ...and it is not in the doctor's.
    assert client.get("/api/notes?recipient_role=doctor&status=open").json() == []


def test_a_handover_note_takes_no_due_date(env):
    """It is for the next person at the desk NOW. A due date would imply a queue
    nobody works."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Rahima")
    r = _handover(client, uuid, ids, due_date=NEXT_WEEK)
    assert r.status_code == 400
    assert "recall" in r.json()["detail"].lower()


def test_the_medic_closes_the_note(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Rahima")
    note_id = _handover(client, uuid, ids).json()["id"]
    r = client.patch(f"/api/notes/{note_id}",
                     json={"status": "done", "actor_id": ids["medic_a"]})
    assert r.status_code == 200
    assert client.get("/api/notes?recipient_role=medic&status=open").json() == []


def test_notes_are_visible_on_the_case_they_belong_to(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Rahima")
        other = _case(db, ids, name="Kamal")
    _handover(client, uuid, ids)
    _recall(client, uuid, ids)
    _handover(client, other, ids, body="Different case")

    rows = client.get(f"/api/visits/{uuid}/notes").json()
    assert len(rows) == 2
    assert {n["kind"] for n in rows} == {"handover_note", "recall"}
    assert "Different case" not in [n["body"] for n in rows]


# ===========================================================================
# Shared guard rails — what a note may never be
# ===========================================================================


def test_every_note_names_a_human_author(env):
    """No path lets an anonymous caller — or a model — author one."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    assert client.post(f"/api/visits/{uuid}/notes",
                       json={"kind": "recall", "body": "x", "author_id": 99999,
                             "due_date": NEXT_WEEK}).status_code == 403
    assert client.post(f"/api/visits/{uuid}/notes",
                       json={"kind": "recall", "body": "x"}).status_code == 422


def test_an_unknown_kind_or_status_is_rejected(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    assert client.post(f"/api/visits/{uuid}/notes",
                       json={"kind": "chat_message", "body": "hi",
                             "author_id": ids["doctor"]}).status_code == 400
    note_id = _handover(client, uuid, ids).json()["id"]
    assert client.patch(f"/api/notes/{note_id}",
                        json={"status": "archived", "actor_id": ids["medic_a"]}).status_code == 400


def test_an_empty_note_is_rejected(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    assert client.post(f"/api/visits/{uuid}/notes",
                       json={"kind": "handover_note", "body": "   ",
                             "author_id": ids["doctor"]}).status_code == 400


def test_a_note_never_becomes_clinical_data(env):
    """Rule #2: workflow text, stored separately from prescriptions and risk, and never
    read back into the pipeline."""
    from backend.app.db.models import Prescription, RiskAssessment as RA

    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    _handover(client, uuid, ids, body="Patient definitely has diabetes")
    with TestSession() as db:
        assert db.query(Prescription).count() == 0
        assert db.query(RA).count() == 0
        # It is not copied into the derived profile either.
        profile = db.query(CaseProfile).join(Visit).filter(Visit.uuid == uuid).one()
        assert "diabetes" not in str(profile.entities)


def test_notes_are_audited(env):
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    note_id = _recall(client, uuid, ids).json()["id"]
    client.patch(f"/api/notes/{note_id}", json={"status": "done", "actor_id": ids["medic_a"]})
    with TestSession() as db:
        actions = {a.action for a in db.query(AuditLog).all()}
        assert "note.recall.create" in actions
        assert "note.resolve" in actions


def test_a_note_needs_a_real_visit(env):
    client, _, ids = env
    assert client.post("/api/visits/no-such-visit/notes",
                       json={"kind": "handover_note", "body": "x",
                             "author_id": ids["doctor"]}).status_code == 404


def test_there_is_no_reply_or_thread_field(env):
    """The brief: 'Do not build a chat application.' Asserted on the shape, because a
    thread id is the first thing a well-meaning refactor would add."""
    client, TestSession, ids = env
    with TestSession() as db:
        uuid = _case(db, ids, name="Kamal")
    body = _handover(client, uuid, ids).json()
    for chat_shaped in ("reply_to", "thread_id", "parent_id", "read_at", "unread"):
        assert chat_shaped not in body
