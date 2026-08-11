"""F2 — a resume-scope question is recorded against the field it actually asks about.

THE DEFECT THIS CLOSES. `generate_next_question` used to let M7 pick the field and
then "repair" its answer with `if fields_scope and target_gap not in remaining:
target_gap = remaining[0]`. The repair is what broke it: when the model echoed back
anything that was not an exact key — a label, different case, a descriptive phrase —
the question was silently filed against `remaining[0]` instead.

Consequences, both of which the human reported as symptoms:
  * the field actually ASKED about kept its "not yet asked" status, so the resume
    loop asked about it AGAIN ("unnecessary repeated questions");
  * a field nobody had asked about was marked asked and therefore NEVER revisited,
    so it reached the review page permanently empty.

The fix inverts the flow: the SERVER names the field in the prompt, and records that
same field. The pairing is true by construction, so there is nothing left to repair.

⚠ These tests stub `call_module` — they pin the CONTRACT (which field is named, which
field is stored), never the model's wording.
"""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import repository_visits as repo
from backend.app.db.database import Base
from backend.app.db.models import CaseProfile, FollowupQuestion
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services import followup as followup_mod
from backend.app.services.followup import FIELD_PROMPTS, generate_next_question


@pytest.fixture()
def db_session():
    """A private in-memory DB — these tests call the service directly, so they need
    no TestClient and no route wiring."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, future=True)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def visit_and_profile(db_session):
    clinic = repo.get_default_clinic(db_session)   # created on the fly for test DBs
    visit = repo.create_visit(db_session, clinic_id=clinic.id)
    profile = CaseProfile(visit_id=visit.id, entities={"summary_fields": {}}, gaps={})
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return visit, profile


def _capture(monkeypatch, reply: str) -> dict:
    """Stub M7 and record the prompt it was handed."""
    seen: dict = {}

    def fake_call_module(db, *, visit_id, module_code, system, user):
        seen["user"] = user
        seen["system"] = system
        return reply

    monkeypatch.setattr(followup_mod, "call_module", fake_call_module)
    return seen


# --- the contract: every field has a description ----------------------------


def test_every_canonical_field_is_described():
    """A field with no description would be named to M7 as a bare key like
    'recent_changes_exposures', which is not enough to write a Bangla question from."""
    assert set(FIELD_PROMPTS) == set(SUMMARY_FIELD_KEYS)


# --- the fix: named field in, same field out --------------------------------


def test_the_server_names_the_field_in_the_prompt(monkeypatch, db_session, visit_and_profile):
    visit, profile = visit_and_profile
    seen = _capture(monkeypatch, json.dumps(
        {"target_gap": "allergies", "priority": 1, "question": "প্রশ্ন? (Question?)"}
    ))
    generate_next_question(db_session, visit, profile, missing=["allergies", "medical_history"])
    assert "ASK ABOUT EXACTLY THIS ONE FIELD" in seen["user"]
    assert "allergies" in seen["user"]
    assert FIELD_PROMPTS["allergies"] in seen["user"]


@pytest.mark.parametrize(
    "echoed_gap",
    [
        "Allergies",                     # different case
        "allergy",                       # near miss
        "7. Allergies / অ্যালার্জি",      # the display label
        "any drug allergies",            # a descriptive phrase
        "",                              # nothing at all
        "medical_history",               # a DIFFERENT real key — the dangerous one
    ],
)
def test_the_recorded_field_is_the_one_we_asked_about(
    monkeypatch, db_session, visit_and_profile, echoed_gap
):
    """Whatever M7 echoes back is ignored. This is the whole defect: previously any
    of these would have been filed against remaining[0]."""
    visit, profile = visit_and_profile
    _capture(monkeypatch, json.dumps(
        {"target_gap": echoed_gap, "priority": 1, "question": "প্রশ্ন? (Question?)"}
    ))
    question = generate_next_question(
        db_session, visit, profile, missing=["allergies", "medical_history"]
    )
    assert question.target_gap == "allergies"


def test_the_json_salvage_path_records_the_named_field_too(
    monkeypatch, db_session, visit_and_profile
):
    """A non-JSON reply is salvaged as raw question text; it must not also lose the
    field pairing, or the salvage would reintroduce the mismatch."""
    visit, profile = visit_and_profile
    _capture(monkeypatch, "not json at all — just a question?")
    question = generate_next_question(
        db_session, visit, profile, missing=["current_medicines", "allergies"]
    )
    assert question.target_gap == "current_medicines"
    assert question.question_text == "not json at all — just a question?"


def test_asking_one_field_never_marks_a_different_field_answered(
    monkeypatch, db_session, visit_and_profile
):
    """The end-to-end symptom: ask about A, and B must NOT become unaskable."""
    visit, profile = visit_and_profile
    missing = ["allergies", "medical_history", "current_concern"]
    _capture(monkeypatch, json.dumps(
        {"target_gap": "something the model made up", "priority": 1, "question": "ক? (Q?)"}
    ))
    first = generate_next_question(db_session, visit, profile, missing=missing)
    assert first.target_gap == "allergies"

    # Answer it, then ask again: the next field must be the next UNASKED one.
    first.answered_at = first.asked_at
    db_session.commit()
    second = generate_next_question(db_session, visit, profile, missing=missing)
    assert second.target_gap == "medical_history"
    assert second.id != first.id


# --- the main loop is deliberately NOT changed ------------------------------


def test_the_main_loop_still_lets_m7_choose_its_own_gap(
    monkeypatch, db_session, visit_and_profile
):
    """F2 is scoped to the resume loop. In the MAIN loop the gap list is M6's
    free-text phrases, there is no key contract to violate, and P1-3's deepening
    questions depend on M7 naming its own target."""
    visit, profile = visit_and_profile
    profile.gaps = {"missing": ["fever duration"]}
    db_session.commit()
    _capture(monkeypatch, json.dumps(
        {"target_gap": "how high the fever got", "priority": 1, "question": "ক? (Q?)"}
    ))
    question = generate_next_question(db_session, visit, profile)  # no `missing=` kwarg
    assert question.target_gap == "how high the fever got"


def test_the_main_loop_prompt_carries_no_field_directive(
    monkeypatch, db_session, visit_and_profile
):
    visit, profile = visit_and_profile
    profile.gaps = {"missing": ["fever duration"]}
    db_session.commit()
    seen = _capture(monkeypatch, json.dumps(
        {"target_gap": "x", "priority": 1, "question": "ক? (Q?)"}
    ))
    generate_next_question(db_session, visit, profile)
    assert "ASK ABOUT EXACTLY THIS ONE FIELD" not in seen["user"]


# --- the question is still stored verbatim as a system utterance (rule #1) --


def test_the_question_is_still_recorded_in_the_conversation(
    monkeypatch, db_session, visit_and_profile
):
    """F2 must not disturb the record: every asked question stays a system utterance
    so the doctor's chronological conversation is complete."""
    visit, profile = visit_and_profile
    _capture(monkeypatch, json.dumps(
        {"target_gap": "allergies", "priority": 1, "question": "অ্যালার্জি আছে? (Any allergies?)"}
    ))
    question = generate_next_question(db_session, visit, profile, missing=["allergies"])
    stored = (
        db_session.query(FollowupQuestion)
        .filter(FollowupQuestion.id == question.id)
        .one()
    )
    assert stored.question_text == "অ্যালার্জি আছে? (Any allergies?)"
