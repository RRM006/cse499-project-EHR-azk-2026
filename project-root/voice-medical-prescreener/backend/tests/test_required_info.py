"""F3 — required pre-screening information cannot be skipped.

THREE THINGS THIS PINS.

1. **The definition of "required" is one thing, in one place**
   (`services/requirements.py`), and it distinguishes *must carry a value* from
   *must have been asked*. "I take no medicines" is a real answer; forcing text into
   that field would make the patient invent one, and an invented answer in a medical
   record is worse than an empty one.

2. **The resume loop has its own budget.** It used to share the main loop's cap of 5,
   which the main conversation spent entirely — so the loop that exists specifically
   to fill gaps routinely had zero questions left, and the patient reached the review
   page with required fields empty and no way to fill them.

3. **The gate is server-side.** `?require_complete=true` is what makes "cannot skip"
   a rule rather than a hidden button. It is opt-in because the same endpoint serves
   staff/walk-in paths that legitimately submit partial cases — so the default is
   verified to be unchanged, too.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings
from backend.app.db import repository_visits as repo
from backend.app.db.database import Base, get_db
from backend.app.db.models import CaseProfile, FollowupQuestion, Patient
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services.requirements import (
    IDENTITY_REQUIREMENTS,
    MUST_HAVE_BEEN_ASKED,
    MUST_HAVE_VALUE,
    missing_requirements,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, future=True)()
    try:
        yield session
    finally:
        session.close()


def _visit_with_fields(db, filled_keys=(), asked_keys=(), identity=True):
    """`identity=True` gives the visit a name, age and problem area, so a test can
    isolate the 10-field requirements from the F4 identity ones."""
    clinic = repo.get_default_clinic(db)
    patient, _ = repo.get_or_create_patient_by_phone(
        db, clinic_id=clinic.id, phone="01715984632"
    )
    visit = repo.create_visit(db, clinic_id=clinic.id, patient_id=patient.id)
    entities = {
        "summary_fields": {
            k: {"value": f"<{k}>", "value_en": f"<{k}>", "value_bn": "", "source": "ai"}
            for k in filled_keys
        }
    }
    if identity:
        patient.display_name = "রহিম উদ্দিন"
        patient.birth_year = datetime.now(timezone.utc).year - 40
        entities["problem_area"] = {"en": "abdomen", "bn": "পেট"}
    db.add(CaseProfile(visit_id=visit.id, entities=entities))
    for key in asked_keys:
        db.add(FollowupQuestion(visit_id=visit.id, target_gap=key,
                                question_text=f"about {key}?", priority=1))
    db.commit()
    return visit


# --- the definition ---------------------------------------------------------


def test_required_keys_are_real_summary_fields():
    """A requirement naming a field that does not exist could never be satisfied."""
    for key in MUST_HAVE_VALUE + MUST_HAVE_BEEN_ASKED:
        assert key in SUMMARY_FIELD_KEYS


def test_a_bare_visit_owes_everything(db_session):
    visit = _visit_with_fields(db_session, identity=False)
    assert missing_requirements(db_session, visit) == list(
        IDENTITY_REQUIREMENTS + MUST_HAVE_VALUE + MUST_HAVE_BEEN_ASKED
    )


def test_main_problem_must_carry_an_actual_value(db_session):
    """Asking about the main problem is not enough — a pre-screening with no chief
    complaint gives the doctor nothing to read."""
    visit = _visit_with_fields(db_session, asked_keys=("main_problem",))
    assert "main_problem" in missing_requirements(db_session, visit)


def test_asking_is_enough_for_a_field_that_may_legitimately_be_empty(db_session):
    """The human's rule: do not force a value into a field that does not apply.
    'No allergies' must be able to end the requirement."""
    visit = _visit_with_fields(
        db_session,
        filled_keys=("main_problem",),
        asked_keys=MUST_HAVE_BEEN_ASKED,
    )
    assert missing_requirements(db_session, visit) == []


def test_a_filled_field_needs_no_question(db_session):
    """Volunteered information counts — the patient is not re-interrogated about
    something they already said."""
    visit = _visit_with_fields(
        db_session, filled_keys=("main_problem",) + MUST_HAVE_BEEN_ASKED
    )
    assert missing_requirements(db_session, visit) == []


def test_partially_satisfied_reports_only_what_is_owed(db_session):
    visit = _visit_with_fields(
        db_session, filled_keys=("main_problem", "onset_duration"),
        asked_keys=("symptom_details",),
    )
    assert missing_requirements(db_session, visit) == ["current_medicines", "allergies"]


# --- the resume budget ------------------------------------------------------


def test_the_resume_loop_has_its_own_budget_on_top_of_the_main_cap():
    """The bug this closes: main cap 5, main loop asks 5, resume loop gets 0."""
    settings = Settings()
    assert settings.followup_resume_max_questions > 0
    resume_cap = settings.followup_max_questions + settings.followup_resume_max_questions
    assert resume_cap > settings.followup_max_questions
    # The budget must be able to cover every field the loop might have to ask about.
    assert settings.followup_resume_max_questions >= len(MUST_HAVE_BEEN_ASKED)


# --- the server-side gate ---------------------------------------------------


@pytest.fixture()
def client_env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), TestSession
    app.dependency_overrides.clear()


def _kiosk_visit(client, TestSession, *, filled_keys=(), asked_keys=(), identity=True):
    r = client.post("/api/patients/verify-otp",
                    json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances",
                json={"raw_text": "বুকে ব্যথা", "role": "patient"})
    db = TestSession()
    visit = repo.get_visit_by_uuid(db, uuid)
    entities = {
        "summary_fields": {
            k: {"value": f"<{k}>", "value_en": f"<{k}>", "value_bn": "", "source": "ai"}
            for k in filled_keys
        }
    }
    if identity:
        patient = db.get(Patient, visit.patient_id)
        patient.display_name = "রহিম উদ্দিন"
        patient.birth_year = datetime.now(timezone.utc).year - 40
        entities["problem_area"] = {"en": "chest", "bn": "বুক"}
    db.add(CaseProfile(visit_id=visit.id, entities=entities))
    for key in asked_keys:
        db.add(FollowupQuestion(visit_id=visit.id, target_gap=key,
                                question_text=f"about {key}?", priority=1))
    db.commit()
    db.close()
    return uuid


def test_identity_is_required_and_reported(client_env):
    """F4 — name, age and area are required even when all 10 fields are perfect."""
    client, TestSession = client_env
    uuid = _kiosk_visit(client, TestSession, identity=False,
                        filled_keys=("main_problem",) + MUST_HAVE_BEEN_ASKED)
    body = client.get(f"/api/visits/{uuid}/readiness").json()
    assert body["complete"] is False
    assert body["missing"] == list(IDENTITY_REQUIREMENTS)


def test_identity_gaps_block_the_kiosk_submit(client_env):
    client, TestSession = client_env
    uuid = _kiosk_visit(client, TestSession, identity=False,
                        filled_keys=("main_problem",) + MUST_HAVE_BEEN_ASKED)
    r = client.post(f"/api/visits/{uuid}/submit?require_complete=true")
    assert r.status_code == 409
    assert "patient_name" in r.json()["detail"]


def test_every_identity_requirement_has_a_question_the_kiosk_can_ask():
    """The anti-trap invariant: requiring something nothing can ask about would
    strand the patient at the review screen forever."""
    js = TestClient(app).get("/kiosk.js").text
    for key in IDENTITY_REQUIREMENTS:
        assert f"key: '{key}'" in js, f"INTAKE_SCRIPT cannot ask for {key}"
    assert "function pendingScriptedRequirement()" in js


def test_readiness_reports_what_is_owed(client_env):
    client, TestSession = client_env
    uuid = _kiosk_visit(client, TestSession, filled_keys=("main_problem",))
    body = client.get(f"/api/visits/{uuid}/readiness").json()
    assert body["complete"] is False
    assert body["missing"] == list(MUST_HAVE_BEEN_ASKED)


def test_readiness_is_complete_once_everything_is_covered(client_env):
    client, TestSession = client_env
    uuid = _kiosk_visit(client, TestSession, filled_keys=("main_problem",),
                        asked_keys=MUST_HAVE_BEEN_ASKED)
    body = client.get(f"/api/visits/{uuid}/readiness").json()
    assert body == {"complete": True, "missing": []}


def test_readiness_404s_for_an_unknown_visit(client_env):
    client, _ = client_env
    assert client.get("/api/visits/nope/readiness").status_code == 404


def test_an_incomplete_case_cannot_be_submitted_by_the_kiosk(client_env):
    """The heart of 3C: pressing Confirm & Submit is not enough."""
    client, TestSession = client_env
    uuid = _kiosk_visit(client, TestSession, filled_keys=("main_problem",))
    r = client.post(f"/api/visits/{uuid}/submit?require_complete=true")
    assert r.status_code == 409
    assert "allergies" in r.json()["detail"]
    # ...and the visit really did not move on.
    assert client.get(f"/api/visits/{uuid}").json()["status"] == "in_progress"


def test_a_complete_case_submits_normally(client_env):
    client, TestSession = client_env
    uuid = _kiosk_visit(client, TestSession, filled_keys=("main_problem",),
                        asked_keys=MUST_HAVE_BEEN_ASKED)
    r = client.post(f"/api/visits/{uuid}/submit?require_complete=true")
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_review"


def test_the_default_submit_contract_is_unchanged(client_env):
    """Staff and walk-in paths never went through the kiosk interview and legitimately
    submit partial cases — the guard must stay opt-in so they are not blocked."""
    client, TestSession = client_env
    uuid = _kiosk_visit(client, TestSession, filled_keys=("main_problem",))
    assert client.post(f"/api/visits/{uuid}/submit").status_code == 200


def test_the_empty_visit_guard_still_wins(client_env):
    """A visit with no patient speech is still a 400, not a requirements 409 — the
    older, more specific message must not be shadowed."""
    client, _ = client_env
    r = client.post("/api/patients/verify-otp",
                    json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    assert client.post(f"/api/visits/{uuid}/submit?require_complete=true").status_code == 400


# --- the kiosk honours the gate --------------------------------------------


def test_the_kiosk_asks_the_server_and_sends_the_flag():
    client = TestClient(app)
    js = client.get("/kiosk.js").text
    assert "/readiness" in js
    assert "submit?require_complete=true" in js


def test_the_submit_button_is_hidden_while_something_is_required():
    js = TestClient(app).get("/kiosk.js").text
    assert "function updateSubmitVisibility()" in js
    assert "state.resumeActive || (state.readiness && !state.readiness.complete)" in js


def test_an_unreachable_readiness_check_does_not_trap_the_patient():
    """`state.readiness` stays null on failure, and null must NOT block — one flaky
    request must never strand a patient on the review screen. The server still
    refuses an incomplete submit, so nothing is actually bypassed."""
    js = TestClient(app).get("/kiosk.js").text
    assert "state.readiness = null;" in js


def test_the_required_notice_exists_and_is_rendered_from_the_server_verdict():
    html = TestClient(app).get("/kiosk.html").text
    js = TestClient(app).get("/kiosk.js").text
    assert 'id="required-notice"' in html
    assert "function renderRequiredNotice()" in js
    assert "state.readiness.missing" in js
