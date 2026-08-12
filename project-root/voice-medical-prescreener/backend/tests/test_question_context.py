"""S35 / Finding 4 — the next question follows what has ALREADY been collected.

The gap: M7 was told what was MISSING and never told what was KNOWN. The conversation
was in the prompt, but nothing named the *structured* facts extracted from it, so
"don't ask the patient their age twice" was left to the model noticing on its own.

What this file defends is deliberately NOT a new decision system — that would be a
clinical-safety change nobody authorised. It defends that the EXISTING pieces are
wired together honestly:

  * `collected_context()` is the exact mirror of `missing_summary_fields()` — same
    keys, same `field_has_text` predicate — so the two can never disagree about
    whether a field is filled;
  * what is already known reaches the model, in the same prompt, ahead of the
    conversation it frames;
  * the system prompt forbids re-asking it, and asks for CLARIFICATION rather than
    invention when something is vague;
  * none of this changes WHICH field is chosen: the M6 gap list (main scope) and the
    server-named field (resume scope, F2/ADR-0052) still own that entirely.

⚠ Scope, stated honestly: this is Tier-1/Tier-2 validation in S33's sense — the
deterministic wiring and the prompt's content. **Whether the model OBEYS is not
claimed here**, exactly as ADR-0054 (f) requires; `test_age_appropriate_questions.py`
owns that distinction and its opt-in `M7_LIVE=1` probe.
"""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import repository_visits as repo
from backend.app.db.database import Base
from backend.app.db.models import CaseProfile
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services import followup as followup_mod
from backend.app.services.followup import (
    _QUESTION_SYSTEM,
    collected_context,
    generate_next_question,
    missing_summary_fields,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool, future=True,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, future=True)()
    try:
        yield session
    finally:
        session.close()


def make_visit(db, *, phone, fields=None, age=None, sex=None, area=None):
    clinic = repo.get_default_clinic(db)
    patient, _ = repo.get_or_create_patient_by_phone(db, clinic_id=clinic.id, phone=phone)
    if age is not None:
        patient.birth_year = datetime.now(timezone.utc).year - age
    if sex:
        patient.sex = sex
    visit = repo.create_visit(db, clinic_id=clinic.id, patient_id=patient.id)
    entities = {"summary_fields": fields or {}}
    if area:
        entities["problem_area"] = area
    profile = CaseProfile(visit_id=visit.id, entities=entities, gaps={})
    db.add(profile)
    db.commit()
    return visit, profile


def capture_prompt(db, visit, profile, *, missing):
    """Run the REAL generate_next_question with only the model call intercepted."""
    seen = {}

    def fake_call_module(_db, *, visit_id, module_code, system, user):
        seen.update(system=system, user=user, module=module_code)
        return json.dumps({"target_gap": (missing or ["x"])[0], "priority": 1,
                           "question": "আপনার কি জ্বর আছে? (Do you have a fever?)"})

    original = followup_mod.call_module
    followup_mod.call_module = fake_call_module
    try:
        question = generate_next_question(db, visit, profile, missing=missing)
    finally:
        followup_mod.call_module = original
    return seen, question


def field(text):
    return {"value_en": text, "value_bn": text, "source": "ai"}


# --- the block is the exact mirror of the missing-field checklist ---


def test_collected_and_missing_are_complementary_over_the_same_ten_keys(db_session):
    """If these two could ever disagree, the model would be told a field is both known
    and missing — and the resume loop would ask for something it had just been shown."""
    fields = {"main_problem": field("পেটে ব্যথা"), "onset_duration": field("তিন দিন")}
    _, profile = make_visit(db_session, phone="01715984701", fields=fields)

    block = collected_context(profile)
    missing = missing_summary_fields(profile)

    for key in ("main_problem", "onset_duration"):
        assert key in block
        assert key not in missing
    for key in set(SUMMARY_FIELD_KEYS) - {"main_problem", "onset_duration"}:
        assert key not in block
        assert key in missing


def test_an_empty_profile_produces_no_block_at_all(db_session):
    """Same rule patient_context() already follows: an empty labelled block invites the
    model to fill it in. Silence is the safe empty state."""
    _, profile = make_visit(db_session, phone="01715984702")
    assert collected_context(profile) == ""


def test_a_field_that_is_present_but_blank_counts_as_missing_not_collected(db_session):
    """`field_has_text` is the one predicate. A field holding "" or whitespace has been
    ASKED but not answered, and telling the model it is collected would end the topic."""
    fields = {"allergies": {"value_en": "   ", "value_bn": "", "source": "ai"}}
    _, profile = make_visit(db_session, phone="01715984703", fields=fields)
    assert collected_context(profile) == ""
    assert "allergies" in missing_summary_fields(profile)


def test_a_bangla_only_answer_still_counts_as_collected(db_session):
    """Most real answers arrive Bangla-only. Requiring value_en would have declared
    every one of them missing and re-asked the lot."""
    fields = {"current_medicines": {"value_bn": "প্যারাসিটামল", "source": "ai"}}
    _, profile = make_visit(db_session, phone="01715984704", fields=fields)
    block = collected_context(profile)
    assert "current_medicines" in block and "প্যারাসিটামল" in block


def test_a_long_answer_is_truncated_because_the_block_is_context_not_a_second_record():
    """The full conversation is already in the prompt. This block exists to say "you
    know this", not to duplicate the transcript into every request."""
    long_answer = "ব " * 400          # 800 characters of real Bangla text
    profile = CaseProfile(
        visit_id=1, entities={"summary_fields": {"symptom_details": field(long_answer)}}, gaps={})
    line = collected_context(profile).splitlines()[1]
    # The cap applies to the VALUE, not to the line: the field's own description is a
    # fixed prefix from FIELD_PROMPTS and is not the thing that can run away.
    value = line.split("): ", 1)[1]
    assert len(value) == 160 < len(long_answer)


# --- it reaches the model, in the right place ---


def test_what_is_known_reaches_the_question_prompt(db_session):
    fields = {"main_problem": field("পেটে ব্যথা"), "onset_duration": field("তিন দিন ধরে")}
    visit, profile = make_visit(db_session, phone="01715984705", fields=fields)
    seen, _ = capture_prompt(db_session, visit, profile, missing=["allergies"])
    assert "ALREADY COLLECTED (do not ask for these again):" in seen["user"]
    assert "তিন দিন ধরে" in seen["user"]
    assert seen["module"] == "M7"


def test_it_frames_the_conversation_rather_than_following_it(db_session):
    """Same placement rule as PATIENT CONTEXT, and the same reason: context that arrives
    after the transcript has already been read is context the model reasons around."""
    fields = {"main_problem": field("পেটে ব্যথা")}
    visit, profile = make_visit(db_session, phone="01715984706", fields=fields,
                                age=78, area={"en": "stomach", "bn": "পেট"})
    seen, _ = capture_prompt(db_session, visit, profile, missing=["allergies"])
    user = seen["user"]
    assert user.index("PATIENT CONTEXT:") < user.index("ALREADY COLLECTED")
    assert user.index("ALREADY COLLECTED") < user.index("CONVERSATION:")


def test_identity_already_known_is_in_the_prompt_and_is_forbidden_to_re_ask(db_session):
    """"Don't ask my age again" — age/sex/area live in PATIENT CONTEXT (F4), and the
    system prompt now names that block as off-limits for re-asking."""
    visit, profile = make_visit(db_session, phone="01715984707", age=78, sex="female",
                                area={"en": "stomach", "bn": "পেট"})
    seen, _ = capture_prompt(db_session, visit, profile, missing=["allergies"])
    assert "Age: 78 years" in seen["user"]
    assert "Sex: female" in seen["user"]
    assert "never ask again for anything in PATIENT CONTEXT" in _QUESTION_SYSTEM
    assert "age, sex or the area they came about are already known" in _QUESTION_SYSTEM


def test_the_prompt_asks_for_clarification_instead_of_invention(db_session):
    """"If information is unclear: ask for clarification instead of inventing it." The
    instruction is explicitly scoped to THAT SAME item, so "clarify" cannot become
    licence to wander onto a new topic."""
    assert "ask the patient to clarify THAT SAME item" in _QUESTION_SYSTEM
    assert "better than assuming or inventing a detail they did not give" in _QUESTION_SYSTEM


# --- and it changes nothing about WHICH field is chosen ---


def test_the_field_choice_is_still_owned_by_the_existing_logic(db_session):
    """The resume scope still records the SERVER-named field (F2/ADR-0052) and the model
    is still handed the same MISSING list. Context informs the wording of the question;
    it must not become a second selector."""
    fields = {"main_problem": field("পেটে ব্যথা")}
    visit, profile = make_visit(db_session, phone="01715984708", fields=fields)
    seen, question = capture_prompt(db_session, visit, profile, missing=["allergies"])
    assert question.target_gap == "allergies"
    assert "ASK ABOUT EXACTLY THIS ONE FIELD, nothing else: allergies" in seen["user"]
    assert '"allergies"' in seen["user"]          # the MISSING DATA POINTS list, unchanged


def test_a_collected_field_is_never_offered_as_the_next_target(db_session):
    """The end-to-end statement of "don't ask what you already know": a filled field is
    absent from the resume loop's own checklist, so it can never be named."""
    fields = {k: field("answered") for k in SUMMARY_FIELD_KEYS if k != "allergies"}
    visit, profile = make_visit(db_session, phone="01715984709", fields=fields)
    remaining = missing_summary_fields(profile)
    assert remaining == ["allergies"]
    _, question = capture_prompt(db_session, visit, profile, missing=remaining)
    assert question.target_gap == "allergies"


def test_the_block_adds_no_clinical_reasoning_of_its_own(db_session):
    """Rule #2. This is a restatement of collected values — it must not rank, score,
    triage or name a condition. If it ever starts to, that is a decision system nobody
    approved, and it would be hiding inside a "context" helper."""
    fields = {"main_problem": field("বুকে ব্যথা"), "associated_symptoms": field("শ্বাসকষ্ট")}
    _, profile = make_visit(db_session, phone="01715984710", fields=fields)
    block = collected_context(profile).lower()
    for forbidden in ("diagnos", "likely", "suspect", "risk", "urgent", "priority",
                      "severe", "probable", "recommend"):
        assert forbidden not in block, f"collected_context is editorialising: {forbidden!r}"
