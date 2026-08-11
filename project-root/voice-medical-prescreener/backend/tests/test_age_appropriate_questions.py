"""P3 — age-appropriate questioning, validated as far as the architecture actually allows.

⚠ READ THIS BEFORE TRUSTING ANY RESULT IN THIS FILE. There are three separable claims,
and only the first two are proven by the automated suite:

  **Tier 1 — deterministic code validation (PROVEN HERE).** The age is computed
  correctly from `patients.birth_year`, survives into the M7 prompt as an exact string,
  is confined to the PATIENT CONTEXT block, is rejected when implausible, and does not
  change any other part of the pipeline — same 10 fields, same requirements, same
  recording path, same conversation preservation.

  **Tier 2 — prompt validation (PROVEN HERE).** `_QUESTION_SYSTEM` carries specific,
  directional age instructions rather than the word "age-appropriate" on its own, and it
  forbids both diagnosis and reflecting the age back at the patient.

  **Tier 3 — model behaviour (NOT PROVEN, and cannot be by these tests).** Whether the
  LLM actually asks a 78-year-old different questions than a 19-year-old is a property of
  the model, not of this code. Asserting it offline would mean asserting against a stub
  we wrote ourselves, which proves nothing. An OPT-IN live probe is provided at the
  bottom (`M7_LIVE=1`, following the `TTS_LIVE=1` precedent) so a human can exercise it
  deliberately without spending free-tier quota on every run.

So: this file proves the model is ASKED correctly and that nothing downstream breaks. It
does not prove the model OBEYS. Do not report it as though it did.
"""

import json
import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.services.followup as followup_mod
from backend.app.db import repository_visits as repo
from backend.app.db.database import Base
from backend.app.db.models import CaseProfile, FollowupQuestion, Utterance
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services.followup import (
    _QUESTION_SYSTEM,
    generate_next_question,
    patient_context,
)

YOUNG_ADULT = 19
OLDER_ADULT = 78


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


def make_visit(db, *, age, phone, area=None, sex=None):
    clinic = repo.get_default_clinic(db)
    patient, _ = repo.get_or_create_patient_by_phone(db, clinic_id=clinic.id, phone=phone)
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


def capture_prompt(db, visit, profile, *, missing):
    """Run the REAL generate_next_question with the model call intercepted, and return
    the exact prompt the model would have received."""
    seen = {}

    def fake_call_module(_db, *, visit_id, module_code, system, user):
        seen["system"] = system
        seen["user"] = user
        seen["module"] = module_code
        return json.dumps({"target_gap": missing[0], "priority": 1,
                           "question": "আপনার কি জ্বর আছে? (Do you have a fever?)"})

    original = followup_mod.call_module
    followup_mod.call_module = fake_call_module
    try:
        question = generate_next_question(db, visit, profile, missing=missing)
    finally:
        followup_mod.call_module = original
    return seen, question


# === Tier 1 — the age genuinely reaches the model, correctly, for both ages ===


@pytest.mark.parametrize("age", [YOUNG_ADULT, OLDER_ADULT])
def test_the_exact_age_reaches_the_question_prompt(db_session, age):
    visit, profile = make_visit(db_session, age=age, phone=f"017159846{age}")
    seen, _ = capture_prompt(db_session, visit, profile, missing=["allergies"])
    assert f"Age: {age} years" in seen["user"]
    assert seen["module"] == "M7"


def test_a_young_and_an_older_patient_differ_ONLY_in_the_age_line(db_session):
    """The strongest deterministic statement available: age is confined to PATIENT
    CONTEXT and nothing else in the pipeline branches on it. If some other part of the
    prompt ever became age-coupled, this catches it — and an age-coupled requirement
    list or field set would be a clinical-safety problem, not a prompt-tuning one."""
    young_visit, young_profile = make_visit(
        db_session, age=YOUNG_ADULT, phone="01715984611", area={"en": "chest", "bn": "বুক"})
    old_visit, old_profile = make_visit(
        db_session, age=OLDER_ADULT, phone="01715984622", area={"en": "chest", "bn": "বুক"})

    young, _ = capture_prompt(db_session, young_visit, young_profile, missing=["allergies"])
    old, _ = capture_prompt(db_session, old_visit, old_profile, missing=["allergies"])

    assert f"Age: {YOUNG_ADULT} years" in young["user"]
    assert f"Age: {OLDER_ADULT} years" in old["user"]
    assert f"Age: {OLDER_ADULT}" not in young["user"]
    assert f"Age: {YOUNG_ADULT}" not in old["user"]

    # Same system prompt — the clinical rules are not age-tiered.
    assert young["system"] == old["system"]
    # Same everything after the context block.
    tail = lambda p: p["user"].split("CONVERSATION:", 1)[1]
    assert tail(young) == tail(old)


def test_the_age_line_sits_before_the_conversation_so_it_frames_it(db_session):
    visit, profile = make_visit(db_session, age=OLDER_ADULT, phone="01715984633")
    seen, _ = capture_prompt(db_session, visit, profile, missing=["allergies"])
    assert seen["user"].index("PATIENT CONTEXT:") < seen["user"].index("CONVERSATION:")


@pytest.mark.parametrize("bad_age", [0, 130, 200])
def test_an_implausible_age_is_omitted_rather_than_asserted(db_session, bad_age):
    """A corrupt birth_year must not produce "Age: 1932 years" in a clinical prompt.
    Silence is the safe failure — the model then asks generically instead of reasoning
    from a wrong number."""
    visit, profile = make_visit(db_session, age=bad_age, phone=f"0171598{bad_age:04d}")
    block = patient_context(db_session, visit, profile)
    assert "Age:" not in block


def test_no_age_at_all_still_produces_a_usable_question(db_session):
    """Age is optional. A patient who declines it must still be screened, not blocked."""
    visit, profile = make_visit(db_session, age=None, phone="01715984644")
    seen, question = capture_prompt(db_session, visit, profile, missing=["allergies"])
    assert "PATIENT CONTEXT:" not in seen["user"]
    assert question is not None and question.question_text.strip()


# === Tier 1 — age must not disturb anything else ===


@pytest.mark.parametrize("age", [YOUNG_ADULT, OLDER_ADULT])
def test_the_ten_field_structure_is_identical_for_every_age(db_session, age):
    """The summary the doctor reads has a fixed shape. If age ever pruned a field, a
    doctor would silently receive a different report for an older patient."""
    from backend.app.services import requirements as reqs
    assert len(SUMMARY_FIELD_KEYS) == 10
    assert set(reqs.MUST_HAVE_VALUE) | set(reqs.MUST_HAVE_BEEN_ASKED) <= set(SUMMARY_FIELD_KEYS)


@pytest.mark.parametrize("age", [YOUNG_ADULT, OLDER_ADULT])
def test_the_question_is_recorded_and_preserved_verbatim_for_every_age(db_session, age):
    """rule #1 through the age path: the spoken question is stored as a system utterance,
    byte-exact, and the FollowupQuestion row records the field the server named."""
    visit, profile = make_visit(db_session, age=age, phone=f"017159847{age}")
    seen, question = capture_prompt(db_session, visit, profile, missing=["allergies"])

    row = db_session.query(FollowupQuestion).filter_by(visit_id=visit.id).one()
    assert row.target_gap == "allergies"        # F2: the SERVER names the field
    assert row.question_text == question.question_text

    utt = db_session.query(Utterance).filter_by(visit_id=visit.id, role="system").all()
    assert len(utt) == 1
    assert utt[0].raw_text == question.question_text   # verbatim, no rewrite
    assert utt[0].source == "tts"


def test_required_medical_questioning_is_never_relaxed_by_age(db_session):
    """An elderly patient must not be asked FEWER safety questions because the wording is
    simplified.

    Asserted BEHAVIOURALLY, by running the real gate for a 19-year-old and a 78-year-old
    with identical (empty) case profiles and comparing what it demands. An earlier
    attempt to assert this by inspecting requirements.py for the token "age" was simply
    wrong: the module legitimately reads an age — to check the age itself was COLLECTED
    and is plausible (`patient_age`), which is the opposite of relaxing a clinical
    requirement. Running the gate distinguishes the two; reading the source cannot."""
    from backend.app.services import requirements as reqs

    demanded = {}
    for age in (YOUNG_ADULT, OLDER_ADULT):
        visit, _ = make_visit(db_session, age=age, phone=f"017159850{age}")
        demanded[age] = reqs.missing_requirements(db_session, visit)

    clinical = lambda keys: [k for k in keys if k not in reqs.IDENTITY_REQUIREMENTS]
    assert clinical(demanded[YOUNG_ADULT]) == clinical(demanded[OLDER_ADULT])
    assert clinical(demanded[YOUNG_ADULT]), "the gate must demand something clinical"

    # Both ages satisfied `patient_age` itself, so the only difference is nothing.
    assert "patient_age" not in demanded[YOUNG_ADULT]
    assert "patient_age" not in demanded[OLDER_ADULT]

    # The requirement sets are constants, not callables — they cannot vary per patient.
    assert isinstance(reqs.MUST_HAVE_VALUE, (tuple, list, set, frozenset))
    assert isinstance(reqs.MUST_HAVE_BEEN_ASKED, (tuple, list, set, frozenset))
    assert "main_problem" in reqs.MUST_HAVE_VALUE


# === Tier 2 — the instruction itself is specific and safe ===


def test_the_age_instruction_is_directional_not_just_the_word():
    """"Make it age-appropriate" alone is not an instruction a model can act on. These
    are the concrete directions that make it actionable in both directions."""
    s = _QUESTION_SYSTEM
    assert "AGE-APPROPRIATE" in s
    assert "never ask an elderly patient about school or adolescent concerns" in s
    assert "never ask a child or teenager about age-related conditions" in s
    assert "pregnancy questions only where they could plausibly apply" in s
    assert "use simpler wording for an elderly patient" in s


def test_the_prompt_forbids_reflecting_the_age_back_at_the_patient():
    """"Because you are 78..." is both alarming and useless to the doctor."""
    assert "Never mention the patient's age back to them as a reason" in _QUESTION_SYSTEM


def test_no_age_tier_may_produce_a_diagnosis(db_session):
    """Rule #2 holds across the age path — the constraint is unconditional in the prompt."""
    assert "NEVER diagnose" in _QUESTION_SYSTEM
    assert "NEVER alarm or falsely reassure" in _QUESTION_SYSTEM
    for age in (YOUNG_ADULT, OLDER_ADULT):
        visit, profile = make_visit(db_session, age=age, phone=f"017159848{age}")
        seen, _ = capture_prompt(db_session, visit, profile, missing=["allergies"])
        assert "NEVER diagnose" in seen["system"]


def test_the_opening_sequence_still_collects_age_before_the_complaint():
    """The age can only shape questions if it is gathered first — F4's ordering is part
    of the age story, so it is re-asserted from this angle."""
    from fastapi.testclient import TestClient

    from backend.app.main import app
    js = TestClient(app).get("/kiosk.js").text
    script = js[js.index("const INTAKE_SCRIPT = ["):js.index("function scriptEntry(")]
    assert script.index("problem_area") < script.index("patient_name") < script.index("patient_age")
    # …and the complaint itself comes LAST, so age is on file before any clinical turn.
    assert script.index("patient_age") < script.index("main_problem")


# === Tier 3 — OPT-IN live probe. Skipped by default. ===


@pytest.mark.skipif(
    os.getenv("M7_LIVE") != "1",
    reason="live M7 probe: spends free-tier quota. Run deliberately with M7_LIVE=1.",
)
def test_live_m7_returns_a_usable_question_for_both_ages(db_session):
    """The ONLY test here that touches a real model, and even it does not assert that the
    question is age-appropriate — no automated check can judge that. It asserts the
    contract holds live: a real reply parses, carries a non-empty bilingual question, and
    does not recite the patient's age back at them.

    Judging appropriateness is a HUMAN reading of the two questions, which is why this
    prints them.
    """
    for age in (YOUNG_ADULT, OLDER_ADULT):
        visit, profile = make_visit(db_session, age=age, phone=f"017159849{age}")
        question = generate_next_question(
            db_session, visit, profile, missing=["current_concern"])
        assert question is not None
        assert question.question_text.strip()
        assert str(age) not in question.question_text, \
            "the model recited the age back at the patient"
        print(f"\n[M7_LIVE] age {age}: {question.question_text}")
