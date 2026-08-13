"""S36 / Finding 3 (ADR-0057) — the session-scoped context tools behind an M7 question.

⚠ The headline of this finding is a REJECTION, and it is deliberate: **MCP was evaluated
and not adopted.** ADR-0057 records it in full. Four facts about this codebase decided it:

  1. There is no tool-calling loop to attach a protocol to — ``call_module()`` is a
     one-shot system+user request that returns text. MCP presumes an agent that can call
     a tool, read the result and call again.
  2. Those round-trips are the scarce resource. ADR-0026 exists to spread ~1,000-1,500
     free requests/day across three buckets, and M7 is in the LIVE loop — the worst place
     to spend three or four calls where one will do.
  3. A second context path is the defect class this project keeps fixing. S35 built
     ``collected_context()`` as the exact mirror of ``missing_summary_fields()`` so they
     could never disagree; a server assembling context its own way rebuilds that
     disagreement one layer further from the tests.
  4. Session scoping here is STRUCTURAL, and a protocol would weaken it. Every function
     takes ``visit`` and reads only rows joined to it — a function that is not given
     visit B cannot return visit B. Over a transport that becomes a runtime property
     enforced by passing the right argument, which is strictly weaker.

So the three responsibilities are implemented as three small explicit functions with the
narrow contracts an MCP tool would have declared, and none of the transport. What is
genuinely NEW in this session is the second and third of them: the conversation handed to
M7 is now BOUNDED (it was the entire unbounded history), and the model's question is now
CHECKED on the way out rather than merely asked not to misbehave.
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
from backend.app.services import followup as followup_mod
from backend.app.services.followup import FIELD_PROMPTS, generate_next_question
from backend.app.services.question_tools import (
    MAX_CONTEXT_TURNS,
    conversation_text,
    get_patient_context,
    get_question_context,
    safe_fallback_question,
    unsafe_question_reason,
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


def make_visit(db, *, phone, fields=None, age=None, sex=None, area=None,
               name=None, turns=(), weight=None, bp=None):
    clinic = repo.get_default_clinic(db)
    patient, _ = repo.get_or_create_patient_by_phone(db, clinic_id=clinic.id, phone=phone)
    if age is not None:
        patient.birth_year = datetime.now(timezone.utc).year - age
    if sex:
        patient.sex = sex
    if name:
        patient.display_name = name
    if weight:
        patient.weight_kg = weight
    if bp:
        patient.bp = bp
    visit = repo.create_visit(db, clinic_id=clinic.id, patient_id=patient.id)
    entities = {"summary_fields": fields or {}}
    if area:
        entities["problem_area"] = area
    db.add(CaseProfile(visit_id=visit.id, entities=entities, gaps={}))
    db.commit()
    for role, text in turns:
        repo.add_utterance(db, visit_id=visit.id, raw_text=text, role=role,
                           source="mic" if role == "patient" else "tts", stt_provider=None)
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).one()
    return visit, profile


def field(text):
    return {"value_en": text, "value_bn": text, "source": "ai"}


# =====================================================================================
# Tool 1 — get_patient_context: the MINIMUM permitted identity context
# =====================================================================================


def test_it_returns_only_the_three_facts_a_question_needs(db_session):
    """Age changes what is age-appropriate, sex gates pregnancy-adjacent questions, area
    keeps the question on the body region the patient came about. Nothing else does any
    work in a follow-up question, so nothing else is returned."""
    visit, profile = make_visit(
        db_session, phone="01715980001", age=62, sex="female",
        area={"en": "stomach", "bn": "পেট"},
        name="Kamal Hossain", weight=70.5, bp="120/80")
    context = get_patient_context(db_session, visit, profile)
    assert set(context) == {"age_years", "sex", "area"}
    assert context == {"age_years": 62, "sex": "female", "area": "stomach"}


def test_it_never_carries_the_identifying_fields(db_session):
    """Name, phone, weight and BP all sit on the same patients row and none of them can
    improve a question — so the smallest context that does the job is the one that
    cannot leak them."""
    visit, profile = make_visit(db_session, phone="01715980002", age=40,
                                name="Kamal Hossain", weight=70.5, bp="120/80")
    blob = json.dumps(get_patient_context(db_session, visit, profile), ensure_ascii=False)
    for secret in ("Kamal", "Hossain", "1715980002", "70.5", "120/80"):
        assert secret not in blob


def test_nothing_known_returns_nothing_rather_than_empty_labels(db_session):
    """An empty "Age:" line invites a model to fill it in — the renderer must have
    nothing to render, not a blank to complete."""
    visit, profile = make_visit(db_session, phone="01715980003")
    assert get_patient_context(db_session, visit, profile) == {
        "age_years": None, "sex": None, "area": None}
    assert followup_mod.patient_context(db_session, visit, profile) == ""


def test_an_implausible_age_is_dropped_not_passed_on(db_session):
    visit, profile = make_visit(db_session, phone="01715980004", age=200, sex="male")
    context = get_patient_context(db_session, visit, profile)
    assert context["age_years"] is None
    assert context["sex"] is None, "sex travels only with a usable age"


# =====================================================================================
# ISOLATION — the property the whole finding turns on
# =====================================================================================


def test_one_patients_context_can_never_reach_anothers_question(db_session):
    """Patient A -> tool -> patient B's question is the failure this must make
    impossible. It is impossible by construction: the visit is an ARGUMENT, and there is
    no cache, registry or shared buffer between the call and the rows."""
    a_visit, a_profile = make_visit(
        db_session, phone="01715980010", age=71, sex="male",
        area={"en": "chest", "bn": "বুক"}, name="Patient A",
        fields={"main_problem": field("বুকে ব্যথা তিন দিন")},
        turns=[("patient", "আমার বুকে ব্যথা")])
    b_visit, b_profile = make_visit(
        db_session, phone="01715980011", age=24, sex="female",
        area={"en": "skin", "bn": "ত্বক"}, name="Patient B",
        fields={"main_problem": field("ত্বকে র‍্যাশ")},
        turns=[("patient", "আমার ত্বকে র‍্যাশ")])

    b_identity = get_patient_context(db_session, b_visit, b_profile)
    b_question = get_question_context(db_session, b_visit, b_profile)
    blob = json.dumps([b_identity, b_question], ensure_ascii=False)

    assert b_identity == {"age_years": 24, "sex": "female", "area": "skin"}
    for a_only in ("71", "chest", "বুক", "বুকে ব্যথা", "Patient A"):
        assert a_only not in blob, f"patient A's {a_only!r} reached patient B's context"
    assert b_question["collected"] == {"main_problem": "ত্বকে র‍্যাশ"}


def test_the_asked_questions_memory_is_per_visit(db_session):
    """`already_asked` is what stops a repeat. Shared across visits it would suppress a
    question patient B has never been asked."""
    a_visit, a_profile = make_visit(db_session, phone="01715980012")
    b_visit, b_profile = make_visit(db_session, phone="01715980013")

    def ask(visit, profile, text):
        def fake(_db, *, visit_id, module_code, system, user):
            return json.dumps({"target_gap": "allergies", "priority": 1, "question": text})
        original = followup_mod.call_module
        followup_mod.call_module = fake
        try:
            generate_next_question(db_session, visit, profile, missing=["allergies"])
        finally:
            followup_mod.call_module = original

    ask(a_visit, a_profile, "রোগী A এর প্রশ্ন (Patient A question)")
    assert get_question_context(db_session, a_visit, a_profile)["already_asked"] == [
        "রোগী A এর প্রশ্ন (Patient A question)"]
    assert get_question_context(db_session, b_visit, b_profile)["already_asked"] == []


def test_the_conversation_is_per_visit(db_session):
    a_visit, a_profile = make_visit(db_session, phone="01715980014",
                                    turns=[("patient", "রোগী A এর গোপন কথা")])
    b_visit, b_profile = make_visit(db_session, phone="01715980015",
                                    turns=[("patient", "রোগী B এর কথা")])
    b_text = conversation_text(get_question_context(db_session, b_visit, b_profile))
    assert "রোগী B এর কথা" in b_text
    assert "রোগী A" not in b_text


# =====================================================================================
# Tool 2 — get_question_context: bounded, deterministic inputs
# =====================================================================================


def test_the_conversation_handed_to_the_model_is_bounded(db_session):
    """"Prefer deterministic/context-controlled inputs over blindly sending large
    conversation history." Before this the ENTIRE history went into every M7 prompt, so
    the prompt grew without limit as the loop ran."""
    turns = [("patient" if i % 2 else "system", f"turn-{i}") for i in range(MAX_CONTEXT_TURNS * 2)]
    visit, profile = make_visit(db_session, phone="01715980020", turns=turns)
    context = get_question_context(db_session, visit, profile)
    assert len(context["turns"]) == MAX_CONTEXT_TURNS
    assert context["truncated"] is True
    # the MOST RECENT turns are the ones kept — the oldest are the ones already extracted
    assert context["turns"][-1]["text"] == f"turn-{MAX_CONTEXT_TURNS * 2 - 1}"
    assert "turn-0" not in conversation_text(context)


def test_a_normal_length_visit_is_never_truncated(db_session):
    """A full screening is ~18 turns (4 scripted questions + answers, then the M7 loop),
    so the bound must not change how any real visit is handled."""
    turns = [("patient" if i % 2 else "system", f"turn-{i}") for i in range(18)]
    visit, profile = make_visit(db_session, phone="01715980021", turns=turns)
    context = get_question_context(db_session, visit, profile)
    assert context["truncated"] is False
    assert len(context["turns"]) == 18


def test_the_rendered_conversation_keeps_the_shape_m7_has_always_seen(db_session):
    visit, profile = make_visit(db_session, phone="01715980022", turns=[
        ("system", "আপনার সমস্যা কী?"), ("patient", "পেটে ব্যথা")])
    assert conversation_text(get_question_context(db_session, visit, profile)) == (
        "ASSISTANT: আপনার সমস্যা কী?\nPATIENT: পেটে ব্যথা")


def test_collected_and_missing_stay_complementary(db_session):
    """Same predicate, same key list — the tool must not become a third opinion about
    whether a field is filled."""
    from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
    visit, profile = make_visit(db_session, phone="01715980023",
                                fields={"main_problem": field("পেটে ব্যথা")})
    context = get_question_context(db_session, visit, profile)
    assert set(context["collected"]) == {"main_problem"}
    assert "main_problem" not in context["missing"]
    assert set(context["collected"]) | set(context["missing"]) == set(SUMMARY_FIELD_KEYS)


# =====================================================================================
# Tool 3 — the output guard
# =====================================================================================


@pytest.mark.parametrize("question", [
    "আপনার কি জ্বর আছে? (Do you have a fever?)",
    "আপনি কি বর্তমানে কোনো ওষুধ খাচ্ছেন? (Are you taking any medicine at the moment?)",
    "আগে কি কখনো এমন হয়েছিল? (Has this ever happened before?)",
    "ব্যথাটি ১ থেকে ১০ এর মধ্যে কতটুকু? (On a scale of 1 to 10, how bad is the pain?)",
    "আপনার কি কোনো রোগ নির্ণয় হয়েছিল আগে? (Have you had a diagnosis before?)",
])
def test_a_legitimate_question_passes(question):
    """The guard must not delete the useful half of M7. Asking ABOUT medicines, ABOUT a
    previous diagnosis, or for a 1-10 severity are exactly the questions it should ask —
    which is why the words "ওষুধ", "medicine" and "diagnosis" are not banned."""
    assert unsafe_question_reason(question) is None


@pytest.mark.parametrize("question,expected", [
    ("Take Napa 500 mg twice daily.", "dosage"),
    ("প্যারাসিটামল ৫০০ মিলিগ্রাম খান।", "dosage"),
    ("You should take an antacid before meals.", "assertion:you should take"),
    ("I think you have gastritis — does that sound right?", "assertion:i think you have"),
    ("You are suffering from a chest infection.", "assertion:you are suffering from"),
    ("এই ওষুধটি খান এবং বিশ্রাম নিন।", "assertion:ওষুধটি খান"),
    ("", "empty"),
])
def test_a_prescribing_or_diagnosing_question_is_rejected(question, expected):
    assert unsafe_question_reason(question) == expected


def test_a_rejected_question_is_replaced_and_the_turn_continues(db_session):
    """The patient must never lose their turn because the guard fired — a dead kiosk is
    worse than a plain question. The replacement is LOCAL and server-authored."""
    visit, profile = make_visit(db_session, phone="01715980030")

    def fake(_db, *, visit_id, module_code, system, user):
        return json.dumps({"target_gap": "allergies", "priority": 1,
                           "question": "Take Napa 500 mg twice a day."})

    original = followup_mod.call_module
    followup_mod.call_module = fake
    try:
        question = generate_next_question(db_session, visit, profile, missing=["allergies"])
    finally:
        followup_mod.call_module = original

    assert question is not None, "the patient must still get a question"
    assert "500" not in question.question_text
    assert "mg" not in question.question_text.lower()
    assert question.target_gap == "allergies", "the field asked about is still recorded"
    # …and what the patient hears is the deterministic fallback for that field
    assert FIELD_PROMPTS["allergies"] in question.question_text


def test_the_stored_system_utterance_is_the_safe_question_not_the_rejected_one(db_session):
    """The rejected text must not survive anywhere the patient or the doctor can read
    it — the verbatim conversation record included."""
    visit, profile = make_visit(db_session, phone="01715980031")

    def fake(_db, *, visit_id, module_code, system, user):
        return json.dumps({"target_gap": "allergies", "priority": 1,
                           "question": "I think you have gastritis."})

    original = followup_mod.call_module
    followup_mod.call_module = fake
    try:
        generate_next_question(db_session, visit, profile, missing=["allergies"])
    finally:
        followup_mod.call_module = original

    stored = [u.raw_text for u in repo.list_visit_utterances(db_session, visit_id=visit.id)]
    assert not any("gastritis" in text for text in stored)


def test_the_fallback_is_bilingual_like_every_other_question():
    """M7's contract is "Bangla question (English question)". A fallback that broke it
    would be visibly a different kind of question to the patient."""
    text = safe_fallback_question("allergies", FIELD_PROMPTS)
    assert "(" in text and ")" in text
    assert any("ঀ" <= ch <= "৿" for ch in text), "no Bangla in the fallback"
    generic = safe_fallback_question(None, FIELD_PROMPTS)
    assert any("ঀ" <= ch <= "৿" for ch in generic)


def test_the_guard_names_a_condition_nowhere():
    """Rule #2. The guard rejects text; it must not carry a vocabulary of diseases, which
    would be a diagnosis list living in the repository by another name."""
    import backend.app.services.question_tools as tools
    source = tools.__doc__ or ""
    for disease in ("diabetes", "asthma", "gastritis", "pneumonia", "cancer"):
        assert disease not in source.lower()
    assert not any(
        disease in phrase.lower()
        for phrase in tools._ASSERTIONS
        for disease in ("diabetes", "asthma", "gastritis", "pneumonia", "cancer")
    )
