"""F4 — area asked first, name/age collected, and both fed into the questioning.

What this pins:
  * ``problem_area`` is extracted and stored BESIDE ``summary_fields``, so the
    10-field contract stays byte-identical (the human's explicit decision) while the
    area still has a first-class home.
  * ``entities`` is MERGED, not replaced. Intake used to overwrite the whole dict, so
    a later re-run would silently drop the area (and the C1 suggested_condition).
  * M7 receives age + area and is told to keep questions age-appropriate — this is
    what turns "the same questionnaire for everyone" into a context-aware interview.
  * The kiosk asks for area FIRST, and every scripted question is an ordinary
    recorded turn, so requirement 8 (full conversation) is unaffected.
"""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import repository_visits as repo
from backend.app.db.database import Base
from backend.app.db.models import CaseProfile
from backend.app.main import app
from backend.app.services import followup as followup_mod
from backend.app.services.followup import _QUESTION_SYSTEM, generate_next_question, patient_context
from backend.app.services.intake import problem_area


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


# --- extraction -------------------------------------------------------------


@pytest.mark.parametrize("payload, expected", [
    ({"problem_area": {"en": "abdomen", "bn": "পেট"}}, {"en": "abdomen", "bn": "পেট"}),
    ({"problem_area": {"en": "", "bn": "বুক"}}, {"en": "", "bn": "বুক"}),
])
def test_a_stated_area_is_captured(payload, expected):
    assert problem_area(payload) == expected


@pytest.mark.parametrize("payload", [
    {},                                             # key absent
    {"problem_area": None},
    {"problem_area": {"en": "", "bn": ""}},         # model found nothing
    {"problem_area": {"en": "   ", "bn": "\t"}},    # whitespace only
    {"problem_area": "chest"},                      # wrong shape
])
def test_no_area_returns_none_rather_than_an_empty_record(payload):
    """None is what stops a later, emptier extraction from erasing a found area."""
    assert problem_area(payload) is None


def test_the_extraction_prompt_asks_for_the_area_without_inviting_a_diagnosis():
    from backend.app.services.intake import _EXTRACT_SYSTEM
    assert "problem_area" in _EXTRACT_SYSTEM
    assert "this is a location, not a diagnosis" in _EXTRACT_SYSTEM   # rule #2


# --- entities are merged, never replaced ------------------------------------


def test_an_existing_area_and_suggestion_survive_a_profile_update(db_session, monkeypatch):
    """Regression: `profile.entities = {...}` used to REPLACE the dict wholesale."""
    from backend.app.db.models import FollowupQuestion, Utterance
    from backend.app.services import profile_update as pu

    clinic = repo.get_default_clinic(db_session)
    visit = repo.create_visit(db_session, clinic_id=clinic.id)
    db_session.add(CaseProfile(visit_id=visit.id, entities={
        "summary_fields": {},
        "problem_area": {"en": "abdomen", "bn": "পেট"},
        "suggested_condition": {"condition": "GERD"},
    }))
    question = FollowupQuestion(visit_id=visit.id, target_gap="allergies",
                                question_text="q?", priority=1)
    db_session.add(question)
    answer = Utterance(visit_id=visit.id, raw_text="নেই", role="patient", source="mic")
    db_session.add(answer)
    db_session.commit()

    # A fresh extraction that mentions NO area at all.
    monkeypatch.setattr(pu, "call_module", lambda *a, **k: json.dumps(
        {"symptom_details_structured": {}}))
    profile = pu.process_answer(db_session, visit=visit, question=question, answer=answer)

    assert profile.entities["problem_area"] == {"en": "abdomen", "bn": "পেট"}
    assert profile.entities["suggested_condition"] == {"condition": "GERD"}


# --- the context handed to M7 ----------------------------------------------


def _visit_with_context(db, *, age=None, area=None, sex=None):
    clinic = repo.get_default_clinic(db)
    patient, _ = repo.get_or_create_patient_by_phone(
        db, clinic_id=clinic.id, phone="01715984632")
    if age is not None:
        patient.birth_year = datetime.now(timezone.utc).year - age
    if sex:
        patient.sex = sex
    visit = repo.create_visit(db, clinic_id=clinic.id, patient_id=patient.id)
    entities = {"summary_fields": {}}
    if area:
        entities["problem_area"] = area
    profile = CaseProfile(visit_id=visit.id, entities=entities, gaps={})
    db.add(profile)
    db.commit()
    return visit, profile


def test_context_carries_age_and_area(db_session):
    visit, profile = _visit_with_context(
        db_session, age=72, area={"en": "chest", "bn": "বুক"}, sex="female")
    block = patient_context(db_session, visit, profile)
    assert "Age: 72 years" in block
    assert "chest" in block
    assert "Sex: female" in block


def test_context_is_empty_when_nothing_is_known(db_session):
    """An empty 'Age:' line would invite the model to invent one."""
    visit, profile = _visit_with_context(db_session)
    assert patient_context(db_session, visit, profile) == ""


def test_the_context_reaches_the_model(db_session):
    visit, profile = _visit_with_context(
        db_session, age=9, area={"en": "skin", "bn": "ত্বক"})
    seen = {}

    def fake_call_module(db, *, visit_id, module_code, system, user):
        seen["user"] = user
        return json.dumps({"target_gap": "allergies", "priority": 1, "question": "ক? (Q?)"})

    monkeypatch_target = followup_mod
    original = monkeypatch_target.call_module
    monkeypatch_target.call_module = fake_call_module
    try:
        generate_next_question(db_session, visit, profile, missing=["allergies"])
    finally:
        monkeypatch_target.call_module = original

    assert "PATIENT CONTEXT:" in seen["user"]
    assert "Age: 9 years" in seen["user"]
    assert "skin" in seen["user"]
    # ...and it comes BEFORE the conversation, so it frames what follows.
    assert seen["user"].index("PATIENT CONTEXT:") < seen["user"].index("CONVERSATION:")


def test_the_system_prompt_demands_age_appropriate_questions():
    assert "AGE-APPROPRIATE" in _QUESTION_SYSTEM
    assert "never ask a" in _QUESTION_SYSTEM
    # It must not leak the age back at the patient.
    assert "Never mention the patient's age back to them" in _QUESTION_SYSTEM


# --- the kiosk script -------------------------------------------------------


def test_area_is_asked_before_anything_clinical():
    js = TestClient(app).get("/kiosk.js").text
    script = js[js.index("const INTAKE_SCRIPT = ["):js.index("function scriptEntry(")]
    assert script.index("problem_area") < script.index("patient_name")
    assert script.index("patient_name") < script.index("patient_age")
    assert script.index("patient_age") < script.index("main_problem")


def test_the_scripted_opening_starts_after_otp_and_is_bilingual():
    js = TestClient(app).get("/kiosk.js").text
    assert "await askScriptedQuestion(0);" in js
    assert "আপনার নাম কী?" in js and "What is your name?" in js
    assert "আপনার বয়স কত?" in js and "How old are you?" in js


def test_scripted_answers_use_the_same_pipeline_and_are_recorded():
    """No second flow (ADR-0048): a scripted answer is an ordinary stored turn, and
    intake waits until the whole opening is in."""
    js = TestClient(app).get("/kiosk.js").text
    opening = js[js.index("} else if (inScriptedOpening()) {"):js.index("      // Free opening turn(s)")]
    assert "/utterances" in opening
    assert "askScriptedQuestion(state.scriptIndex + 1)" in opening
    assert "/intake" not in opening       # intake must NOT run per scripted turn
