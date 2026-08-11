"""KIOSK-7 — the summary-screen resume loop (?scope=fields), fully offline.

The resume scope must: ignore the 0.7 completeness threshold; target the EMPTY
summary-field keys (not the M6 free-text gaps); never re-ask a field once asked,
so a "নেই / জানি না" answer counts as answered even when the extractor leaves the
field blank; respect the SHARED per-visit question cap; and report complete with
no LLM spend when all 10 fields already carry text.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import FollowupQuestion
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS

_QUESTION = {"target_gap": "fever duration", "priority": 1,
             "question": "আপনার কি আগে থেকে কোনো রোগ আছে? (Any existing conditions?)"}


def _extraction(filled: int) -> str:
    data = {
        k: ({"en": f"<{k}>", "bn": f"<bn:{k}>"} if i < filled else {"en": "", "bn": ""})
        for i, k in enumerate(SUMMARY_FIELD_KEYS)
    }
    data["symptom_details_structured"] = {}
    return json.dumps(data)


@pytest.fixture()
def env(monkeypatch):
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

    from backend.app.core import llm_providers as lp

    def fake_chain(module_code, settings=None):
        key = lp.MODULE_PROVIDERS.get(module_code, lp.GEMINI_FLASH)
        return [lp.ProviderConfig(key, "k", "http://fake", "m")]

    monkeypatch.setattr("backend.app.services.llm_client.provider_chain_for_module", fake_chain)

    # 8/10 fields filled -> score 0.8, ABOVE the 0.7 threshold. The empty two are
    # SUMMARY_FIELD_KEYS[8] and [9] (treatments_tried, current_concern).
    state = {"filled": 8, "m7_calls": 0}

    def fake_attempt(provider, *, system, user, timeout):
        if "extract structured" in system:
            return _extraction(state["filled"])
        if "chief-complaint summary" in system:
            return "Short summary."
        if "completeness checker" in system:
            return json.dumps({"present": ["chest pain"],
                               "missing": ["fever duration"]})
        if "ONE follow-up question" in system:
            state["m7_calls"] += 1
            return json.dumps(_QUESTION)
        raise AssertionError(f"Unexpected prompt: {system[:60]}")

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)

    yield TestClient(app), TestSession, state
    app.dependency_overrides.clear()


def _visit_with_intake(client):
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances",
                json={"raw_text": "বুকে ব্যথা", "role": "patient"})
    assert client.post(f"/api/visits/{uuid}/intake").status_code == 200
    return uuid


def test_fields_scope_ignores_threshold_and_targets_field_keys(env):
    client, TestSession, state = env
    uuid = _visit_with_intake(client)

    # Resume scope: 2 fields still empty -> a question, targeting a FIELD KEY
    # (the fake LLM echoed a non-key target_gap; the service must correct it).
    r = client.post(f"/api/visits/{uuid}/followup/next?scope=fields")
    assert r.status_code == 200
    body = r.json()
    assert body["complete"] is False
    assert body["question"]["target_gap"] == SUMMARY_FIELD_KEYS[8]  # treatments_tried

    # The question is also stored + spoken (system utterance), same as the main loop.
    turns = client.get(f"/api/visits/{uuid}").json()["utterances"]
    assert turns[-1]["role"] == "system"
    assert turns[-1]["raw_text"] == body["question"]["question_text"]

    # Default scope at score 0.8: before P1-3 this said complete at 0 questions
    # asked; the floor now keeps the MAIN loop open (here it re-serves the same
    # open question instead of minting a duplicate).
    r0 = client.post(f"/api/visits/{uuid}/followup/next").json()
    assert r0["complete"] is False
    assert r0["question"]["id"] == body["question"]["id"]


def test_negative_answer_counts_as_answered_never_reasked(env):
    client, TestSession, state = env
    uuid = _visit_with_intake(client)

    q1 = client.post(f"/api/visits/{uuid}/followup/next?scope=fields").json()["question"]
    assert q1["target_gap"] == SUMMARY_FIELD_KEYS[8]

    # Patient answers "নেই" and the extractor STILL leaves the field empty
    # (state["filled"] stays 8) -> the field must not be asked again; the loop
    # moves to the other empty field.
    r = client.post(f"/api/visits/{uuid}/followup/answer?scope=fields",
                    json={"question_id": q1["id"], "raw_text": "নেই"})
    assert r.status_code == 200
    body = r.json()
    assert body["complete"] is False
    q2 = body["next_question"]
    assert q2["target_gap"] == SUMMARY_FIELD_KEYS[9]  # current_concern, NOT a repeat

    # "জানি না" for the last empty field -> nothing left to ask -> complete,
    # even though only 8/10 fields carry text.
    r = client.post(f"/api/visits/{uuid}/followup/answer?scope=fields",
                    json={"question_id": q2["id"], "raw_text": "জানি না"})
    body = r.json()
    assert body["complete"] is True and body["next_question"] is None
    assert body["completeness_score"] == pytest.approx(0.8)

    # Raw answers stored verbatim (rule #1).
    turns = client.get(f"/api/visits/{uuid}").json()["utterances"]
    patient_turns = [t["raw_text"] for t in turns if t["role"] == "patient"]
    assert "নেই" in patient_turns and "জানি না" in patient_turns


def test_resume_respects_its_question_cap(env, monkeypatch):
    """F3 note: the resume loop no longer shares the main cap — it has its OWN budget
    on top of it (`followup_resume_max_questions`). Exhausting the budget therefore
    means zeroing BOTH; the behaviour being pinned here is unchanged, and is the
    fail-safe that matters: a spent budget must report complete, never trap the
    patient behind a question the server has decided not to ask."""
    client, _, _ = env
    uuid = _visit_with_intake(client)

    monkeypatch.setattr(
        "backend.app.services.followup.get_settings",
        lambda: type("S", (), {"followup_max_questions": 0,
                               "followup_resume_max_questions": 0,
                               "completeness_threshold": 0.7})(),
    )
    r = client.post(f"/api/visits/{uuid}/followup/next?scope=fields")
    body = r.json()
    # Cap reached -> complete (the kiosk shows Confirm & Submit; never trap the patient).
    assert body["complete"] is True and body["question"] is None


def test_all_fields_filled_is_complete_without_llm_spend(env):
    client, _, state = env
    state["filled"] = 10
    uuid = _visit_with_intake(client)

    m7_before = state["m7_calls"]
    r = client.post(f"/api/visits/{uuid}/followup/next?scope=fields")
    body = r.json()
    assert body["complete"] is True and body["question"] is None
    assert body["completeness_score"] == pytest.approx(1.0)
    assert state["m7_calls"] == m7_before  # no M7 call was made


def test_scope_param_validated(env):
    client, _, _ = env
    uuid = _visit_with_intake(client)
    assert client.post(f"/api/visits/{uuid}/followup/next?scope=bogus").status_code == 422
