"""P3-3 (2.0 build) — M16 doctor drug-info assistant.

Offline: both boundaries are faked (ddgs web search + the LLM _attempt). Proves:
(1) happy path returns the answer + sources and ALWAYS the server-attached
"verify before prescribing" disclaimer (rule #2), and logs an M16 module_events
row against the visit; (2) a dead search degrades to a sourceless answer instead
of an error; (3) a non-JSON model reply is salvaged, disclaimer still attached;
(4) a dead provider chain is a clean 502; (5) unknown visit 404 / short question 422.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import ModuleEvent
from backend.app.main import app
from backend.app.services.assistant import (
    ASSISTANT_DISCLAIMER,
    ASSISTANT_DISCLAIMER_BN,
    _search,
)


@pytest.fixture()
def env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db

    from backend.app.core import llm_providers as lp

    monkeypatch.setattr(
        "backend.app.services.llm_client.provider_chain_for_module",
        lambda code, settings=None: [lp.ProviderConfig("gemini_flash", "k", "http://fake", "m")],
    )

    state = {
        "llm_reply": json.dumps({
            "answer_en": "Paracetamol: typical adult dose 500mg-1g every 4-6h, max 4g/day.",
            "answer_bn": "প্যারাসিটামল: প্রাপ্তবয়স্ক মাত্রা ৫০০মিগ্রা-১গ্রা, দিনে সর্বোচ্চ ৪গ্রা।",
        }),
        "llm_fails": False,
        "last_user": None,
        "system": None,
        "searched": [],
    }

    def fake_attempt(provider, *, system, user, timeout):
        # S38 (B6): the assistant widened from drugs alone to medicines + diagnostic
        # tests + patient-specific test suggestions, so the old assertion on the exact
        # phrase "drug-information assistant" no longer describes the prompt. What it
        # was really checking — that M16's own system prompt was used, and that it is
        # an INFORMATION-ONLY one — is asserted directly instead.
        assert "clinical information assistant" in system
        assert "INFORMATION ONLY" in system
        state["system"] = system
        state["last_user"] = user
        if state["llm_fails"]:
            raise RuntimeError("model down")
        return state["llm_reply"]

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)

    def fake_search(q):
        # Recorded so a test can prove WHAT was sent to the third-party search.
        state["searched"].append(q)
        return [{"title": "Paracetamol — NHS", "url": "https://example.org/para",
                 "snippet": "Adult dose 500mg to 1g every 4 to 6 hours."}]

    monkeypatch.setattr("backend.app.services.assistant._search", fake_search)
    yield TestClient(app), TestSession, state
    app.dependency_overrides.clear()


def _visit(client):
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    return r.json()["visit"]["uuid"]


def test_answer_carries_sources_disclaimer_and_module_event(env):
    client, TestSession, state = env
    uuid = _visit(client)

    r = client.post(f"/api/visits/{uuid}/assistant/drug-info",
                    json={"question": "Paracetamol adult dosage?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer_en"].startswith("Paracetamol")
    assert body["answer_bn"]
    assert body["sources"][0]["url"] == "https://example.org/para"
    # Rule #2: the disclaimer comes from the SERVER, on every answer.
    assert body["disclaimer"] == ASSISTANT_DISCLAIMER
    assert body["disclaimer_bn"] == ASSISTANT_DISCLAIMER_BN
    # The snippets actually reached the model, and the call was logged as M16.
    assert "NHS" in state["last_user"]
    db = TestSession()
    event = db.query(ModuleEvent).filter(ModuleEvent.module_code == "M16").one()
    assert event.status == "ok"
    db.close()


def test_dead_search_degrades_to_sourceless_answer(env, monkeypatch):
    client, _, state = env
    monkeypatch.setattr("backend.app.services.assistant._search", lambda q: [])
    uuid = _visit(client)

    r = client.post(f"/api/visits/{uuid}/assistant/drug-info",
                    json={"question": "Metformin contraindications?"})
    assert r.status_code == 200
    body = r.json()
    assert body["sources"] == [] and body["answer_en"]
    assert body["disclaimer"] == ASSISTANT_DISCLAIMER
    assert "search unavailable" in state["last_user"]


def test_search_helper_swallows_provider_exceptions(monkeypatch):
    import ddgs

    class Boom:
        def text(self, *a, **k):
            raise RuntimeError("duckduckgo unreachable")

    monkeypatch.setattr(ddgs, "DDGS", lambda: Boom())
    assert _search("anything") == []


def test_non_json_reply_is_salvaged_with_disclaimer(env):
    client, _, state = env
    state["llm_reply"] = "Paracetamol is generally dosed at 500mg-1g for adults."
    uuid = _visit(client)

    r = client.post(f"/api/visits/{uuid}/assistant/drug-info",
                    json={"question": "Paracetamol adult dosage?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer_en"].startswith("Paracetamol is generally")
    assert body["answer_bn"] == ""
    assert body["disclaimer"] == ASSISTANT_DISCLAIMER


def test_dead_provider_chain_is_502_and_bad_input_rejected(env):
    client, _, state = env
    uuid = _visit(client)

    state["llm_fails"] = True
    r = client.post(f"/api/visits/{uuid}/assistant/drug-info",
                    json={"question": "Paracetamol adult dosage?"})
    assert r.status_code == 502

    assert client.post("/api/visits/no-such-visit/assistant/drug-info",
                       json={"question": "Paracetamol?"}).status_code == 404
    assert client.post(f"/api/visits/{uuid}/assistant/drug-info",
                       json={"question": "ab"}).status_code == 422


# ===========================================================================
# S38 (B6, ADR-0063) — the assistant widened to tests and case-context
# ===========================================================================
#
# The two properties that matter most here are PRIVACY and NON-ACTION:
#   * whatever else changes, the third-party web search must only ever receive the
#     doctor's typed question (rule #4);
#   * a suggested test must remain a suggestion — nothing in this path may order one.


def _seed_case(TestSession, uuid):
    """Give the visit a clinical picture, so case-context has something to carry."""
    from backend.app.db.models import CaseProfile, Patient, Visit

    with TestSession() as db:
        visit = db.query(Visit).filter(Visit.uuid == uuid).one()
        patient = db.get(Patient, visit.patient_id)
        patient.display_name = "Kamal Hossain"
        patient.birth_year = 1975
        patient.sex = "male"
        patient.weight_kg = 88.0
        patient.height_cm = 170.0
        patient.bp = "150/95"
        db.add(CaseProfile(visit_id=visit.id, summary="Thirst and fatigue", entities={
            "problem_area": {"en": "general", "bn": "সাধারণ"},
            "summary_fields": {
                "main_problem": {"value_en": "Excessive thirst and fatigue for a month",
                                 "source": "ai"},
                "medical_history": {"value_en": "Father has diabetes", "source": "ai"},
            },
        }))
        db.commit()


def test_the_web_search_only_ever_receives_the_typed_question(env):
    """Rule #4, as a STRUCTURAL guarantee: DuckDuckGo is a third party, so no patient
    data may reach it — even when the doctor opted case context into the LLM prompt."""
    client, TestSession, state = env
    uuid = _visit(client)
    _seed_case(TestSession, uuid)

    question = "Which tests might be useful for this patient?"
    r = client.post(f"/api/visits/{uuid}/assistant/drug-info",
                    json={"question": question, "use_case_context": True})
    assert r.status_code == 200, r.text
    assert state["searched"] == [question]
    searched = " ".join(state["searched"])
    for leak in ("Kamal", "88.0", "150/95", "Excessive thirst"):
        assert leak not in searched, f"{leak} reached the web search"


def test_case_context_is_off_by_default(env):
    """A general question ships no patient data anywhere at all."""
    client, TestSession, state = env
    uuid = _visit(client)
    _seed_case(TestSession, uuid)

    r = client.post(f"/api/visits/{uuid}/assistant/drug-info",
                    json={"question": "What is metformin used for?"})
    assert r.status_code == 200
    assert r.json()["used_case_context"] is False
    assert "PATIENT CONTEXT" not in state["last_user"]
    assert "Excessive thirst" not in state["last_user"]


def test_opting_in_sends_a_de_identified_picture_and_says_so(env):
    client, TestSession, state = env
    uuid = _visit(client)
    _seed_case(TestSession, uuid)

    r = client.post(f"/api/visits/{uuid}/assistant/drug-info",
                    json={"question": "Which tests might be useful for this patient?",
                          "use_case_context": True})
    assert r.status_code == 200
    assert r.json()["used_case_context"] is True
    prompt = state["last_user"]
    assert "PATIENT CONTEXT" in prompt
    # The clinical picture is there...
    assert "Excessive thirst" in prompt
    assert "Age: 51 years" in prompt
    assert "150/95" in prompt
    # ...and the identifiers are NOT.
    for identifier in ("Kamal", "Hossain", "01715984632", "+8801715984632", uuid):
        assert identifier not in prompt, f"{identifier} leaked into the prompt"


def test_the_raw_transcript_is_never_sent_as_case_context(env):
    """Rule #1/#4: a doctor's convenience question is not a reason to ship the
    patient's own words to a model. The DERIVED summary carries the clinical picture."""
    client, TestSession, state = env
    uuid = _visit(client)
    _seed_case(TestSession, uuid)

    from backend.app.db.models import Utterance, Visit
    with TestSession() as db:
        visit = db.query(Visit).filter(Visit.uuid == uuid).one()
        db.add(Utterance(visit_id=visit.id, role="patient", seq=1,
                         raw_text="আমার খুব পিপাসা লাগে আর শরীর দুর্বল লাগে",
                         source="mic"))
        db.commit()

    client.post(f"/api/visits/{uuid}/assistant/drug-info",
                json={"question": "Which tests?", "use_case_context": True})
    assert "পিপাসা" not in state["last_user"]


def test_suggested_tests_come_back_as_a_clickable_list(env):
    client, TestSession, state = env
    uuid = _visit(client)
    _seed_case(TestSession, uuid)
    state["llm_reply"] = json.dumps({
        "answer_en": "Given thirst and fatigue, glycaemic and renal screening is commonly considered.",
        "answer_bn": "পিপাসা ও দুর্বলতার প্রেক্ষিতে সাধারণত সুগার ও কিডনির পরীক্ষা বিবেচনা করা হয়।",
        "suggested_tests": ["Fasting blood sugar (FBS)", "HbA1c", "Serum creatinine",
                            "Urine R/M/E"],
    })

    r = client.post(f"/api/visits/{uuid}/assistant/drug-info",
                    json={"question": "Which tests might be useful?", "use_case_context": True})
    body = r.json()
    assert body["suggested_tests"] == ["Fasting blood sugar (FBS)", "HbA1c",
                                       "Serum creatinine", "Urine R/M/E"]
    # Suggestions, never orders: nothing was written for this visit.
    from backend.app.db.models import Prescription
    with TestSession() as db:
        assert db.query(Prescription).count() == 0


def test_a_drug_question_returns_no_suggested_tests(env):
    client, _, state = env
    uuid = _visit(client)
    r = client.post(f"/api/visits/{uuid}/assistant/drug-info",
                    json={"question": "Paracetamol adult dosage?"})
    assert r.json()["suggested_tests"] == []


def test_malformed_suggested_tests_degrade_instead_of_raising(env):
    """`suggested_tests` is free-form model output. A string, a list of dicts, junk and
    duplicates must all become a usable list rather than a 500 in a doctor's face."""
    client, _, state = env
    uuid = _visit(client)
    state["llm_reply"] = json.dumps({
        "answer_en": "ok", "answer_bn": "ঠিক আছে",
        "suggested_tests": [{"name": "CBC"}, "1. HbA1c", "cbc", "", "   ", "x" * 300,
                            "ECG", "ECG"],
    })
    r = client.post(f"/api/visits/{uuid}/assistant/drug-info",
                    json={"question": "Which tests?"})
    assert r.json()["suggested_tests"] == ["CBC", "HbA1c", "ECG"]


def test_a_suggested_tests_string_is_accepted_as_one_test(env):
    client, _, state = env
    uuid = _visit(client)
    state["llm_reply"] = json.dumps({
        "answer_en": "ok", "answer_bn": "ok", "suggested_tests": "Chest X-ray P/A view"})
    r = client.post(f"/api/visits/{uuid}/assistant/drug-info", json={"question": "Which tests?"})
    assert r.json()["suggested_tests"] == ["Chest X-ray P/A view"]


def test_the_suggested_test_list_is_bounded(env):
    """A list long enough to be a shotgun panel is not a suggestion."""
    from backend.app.services.assistant import MAX_SUGGESTED_TESTS

    client, _, state = env
    uuid = _visit(client)
    state["llm_reply"] = json.dumps({
        "answer_en": "ok", "answer_bn": "ok",
        "suggested_tests": [f"Test {i}" for i in range(40)]})
    r = client.post(f"/api/visits/{uuid}/assistant/drug-info", json={"question": "Which tests?"})
    assert len(r.json()["suggested_tests"]) == MAX_SUGGESTED_TESTS


def test_dosage_information_is_never_flagged():
    """The guard must NOT reuse M7's dosage rule: '500 mg every 6 hours' is exactly what
    a drug-information tool exists to say, and blocking it would delete the module."""
    from backend.app.services.assistant import unsafe_answer_reason

    assert unsafe_answer_reason(
        "Typical adult dose is 500 mg to 1 g every 4-6 hours, maximum 4 g in 24 hours."
    ) is None
    assert unsafe_answer_reason(
        "Metformin is contraindicated in severe renal impairment; monitor creatinine."
    ) is None
    assert unsafe_answer_reason("HbA1c measures average glycaemia over 2-3 months.") is None


def test_a_patient_directed_instruction_is_flagged():
    from backend.app.services.assistant import unsafe_answer_reason

    for bad in ("You should prescribe amoxicillin for this patient.",
                "This patient has type 2 diabetes.",
                "Start this patient on metformin 500mg."):
        assert unsafe_answer_reason(bad) is not None, bad


def test_a_flagged_answer_is_delivered_with_a_stronger_disclaimer(env):
    """The answer is NOT deleted — hiding what the model said would be worse — but the
    server replaces the framing, which the model cannot talk its way out of."""
    from backend.app.services.assistant import (
        ASSISTANT_DISCLAIMER, ASSISTANT_FLAGGED_DISCLAIMER,
    )

    client, _, state = env
    uuid = _visit(client)
    state["llm_reply"] = json.dumps({
        "answer_en": "This patient has type 2 diabetes and should take metformin.",
        "answer_bn": "…", "suggested_tests": []})
    r = client.post(f"/api/visits/{uuid}/assistant/drug-info", json={"question": "Assess?"})
    body = r.json()
    assert body["answer_en"].startswith("This patient has")     # still delivered
    assert body["flagged_reason"] is not None
    assert body["disclaimer"] == ASSISTANT_FLAGGED_DISCLAIMER
    assert body["disclaimer"] != ASSISTANT_DISCLAIMER
    assert body["disclaimer_bn"]


def test_an_ordinary_answer_is_not_flagged(env):
    client, _, state = env
    uuid = _visit(client)
    r = client.post(f"/api/visits/{uuid}/assistant/drug-info",
                    json={"question": "Paracetamol adult dosage?"})
    assert r.json()["flagged_reason"] is None


def test_case_context_is_empty_when_there_is_no_profile(env):
    """A visit with nothing collected yet must not produce an empty labelled block —
    that invites the model to fill it in."""
    client, TestSession, state = env
    uuid = _visit(client)   # no CaseProfile seeded
    client.post(f"/api/visits/{uuid}/assistant/drug-info",
                json={"question": "Which tests?", "use_case_context": True})
    assert "PATIENT CONTEXT" not in state["last_user"]


def test_the_system_prompt_still_forbids_diagnosing_and_prescribing(env):
    client, _, state = env
    uuid = _visit(client)
    client.post(f"/api/visits/{uuid}/assistant/drug-info", json={"question": "Metformin?"})
    system = state["system"].lower()
    assert "never state or imply a diagnosis" in system
    assert "never tell the doctor what to prescribe" in system
    assert "never say a test has been ordered" in system
