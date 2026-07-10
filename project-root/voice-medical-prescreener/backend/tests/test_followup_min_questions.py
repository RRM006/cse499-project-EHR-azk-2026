"""P1-3 (2.0 build) — the follow-up question FLOOR + deepening mode, fully offline.

The main loop must ask at least `followup_min_questions` (4) history-grounded
questions even when the 0.7 completeness threshold is already met, switching M7
to DEEPENING questions once the M6 gap list is exhausted; the shared cap (5)
still always terminates the loop; and the KIOSK-7 `scope=fields` resume loop is
NOT affected by the floor (it still stops when every empty field was asked).
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

    # ONE real M6 gap, and extraction jumps to 8/10 (score 0.8) after the first
    # answer — so from question 2 on, the loop can only continue via DEEPENING.
    state = {"filled": 2, "m7_calls": 0, "m7_user_msgs": []}

    def fake_attempt(provider, *, system, user, timeout):
        if "extract structured" in system:
            return _extraction(state["filled"])
        if "chief-complaint summary" in system:
            return "Short summary."
        if "completeness checker" in system:
            return json.dumps({"present": ["chest pain"], "missing": ["fever duration"]})
        if "ONE follow-up question" in system:
            state["m7_calls"] += 1
            state["m7_user_msgs"].append(user)
            if state["m7_calls"] == 1:
                return json.dumps({"target_gap": "fever duration", "priority": 1,
                                   "question": "কতদিন ধরে জ্বর? (How long the fever?)"})
            if state["m7_calls"] == 3:
                # Non-JSON deepening reply -> the salvage path must not crash on an
                # EMPTY remaining list (P1-3 fallback_gap).
                return "ব্যথা কি ১-১০ এ কত? (How severe, 1-10?)"
            return json.dumps({"target_gap": f"deepening {state['m7_calls']}", "priority": 1,
                               "question": f"গভীর প্রশ্ন {state['m7_calls']}? (Deepening {state['m7_calls']}?)"})
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


def _run_loop(client, uuid, state, max_iters=10):
    """Drive the main loop to completion; return the number of questions answered."""
    body = client.post(f"/api/visits/{uuid}/followup/next").json()
    assert body["complete"] is False
    q = body["question"]
    state["filled"] = 8  # threshold met from the very first answer onward
    answered = 0
    while True:
        assert answered < max_iters, "loop failed to terminate"
        body = client.post(f"/api/visits/{uuid}/followup/answer",
                           json={"question_id": q["id"], "raw_text": "উত্তর"}).json()
        answered += 1
        if body["complete"]:
            return answered
        q = body["next_question"]


def test_floor_reached_via_deepening_questions(env):
    client, TestSession, state = env
    uuid = _visit_with_intake(client)

    answered = _run_loop(client, uuid, state)
    assert answered == 4  # threshold met after answer 1, but the floor forced 4

    db = TestSession()
    questions = db.query(FollowupQuestion).order_by(FollowupQuestion.asked_at).all()
    db.close()
    assert len(questions) == 4
    # Q1 targeted the real M6 gap; Q2-Q4 were deepening (gap list exhausted).
    assert questions[0].target_gap == "fever duration"
    assert questions[1].target_gap == "deepening 2"
    # Q3 = the non-JSON salvage in deepening mode: raw text kept, fallback label.
    assert questions[2].target_gap == "deepening detail"
    assert "১-১০" in questions[2].question_text
    # Deepening calls tell M7 the gap list is empty (it must ground in the convo).
    assert '"fever duration"' not in state["m7_user_msgs"][2]


def test_cap_still_terminates_when_floor_is_higher(env, monkeypatch):
    client, TestSession, state = env
    uuid = _visit_with_intake(client)

    fake_settings = type("S", (), {"followup_min_questions": 10,
                                   "followup_max_questions": 5,
                                   "completeness_threshold": 0.7})()
    monkeypatch.setattr("backend.app.api.routes_followup.get_settings", lambda: fake_settings)
    monkeypatch.setattr("backend.app.services.followup.get_settings", lambda: fake_settings)

    answered = _run_loop(client, uuid, state)
    assert answered == 5  # the cap always wins — no infinite loop

    db = TestSession()
    assert db.query(FollowupQuestion).count() == 5
    db.close()


def test_fields_scope_unaffected_by_floor(env):
    client, TestSession, state = env
    state["filled"] = 8  # intake extracts 8/10 -> exactly keys[8]/[9] are empty
    uuid = _visit_with_intake(client)

    # Enter the resume loop directly (as the kiosk summary screen does): the floor
    # must NOT apply — with 2 empty fields it asks about them, and once each has
    # been asked ("নেই" answers), it reports complete at only 2 questions asked.
    q = client.post(f"/api/visits/{uuid}/followup/next?scope=fields").json()["question"]
    assert q["target_gap"] == SUMMARY_FIELD_KEYS[8]
    body = client.post(f"/api/visits/{uuid}/followup/answer?scope=fields",
                       json={"question_id": q["id"], "raw_text": "নেই"}).json()
    assert body["complete"] is False
    q2 = body["next_question"]
    assert q2["target_gap"] == SUMMARY_FIELD_KEYS[9]
    body = client.post(f"/api/visits/{uuid}/followup/answer?scope=fields",
                       json={"question_id": q2["id"], "raw_text": "জানি না"}).json()
    assert body["complete"] is True and body["next_question"] is None

    db = TestSession()
    assert db.query(FollowupQuestion).count() == 2  # floor never forced more
    db.close()
