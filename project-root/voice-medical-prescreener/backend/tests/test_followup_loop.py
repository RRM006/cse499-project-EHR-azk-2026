"""BE-3 checks — the M7 -> answer -> M8 -> M9 loop, fully offline.

The fake LLM starts with a sparse extraction (low completeness), then returns a
fuller one after the answer, so the loop's exit-on-threshold is exercised end to
end. Also covers: question stored + spoken (system utterance), no re-generation
while a question is open, human-edited fields surviving the M8 merge, the answered
gap moving missing -> present, max-turns exit, and guard rails.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import CaseProfile, ModuleEvent
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS

_QUESTION = {"target_gap": "fever duration", "priority": 1,
             "question": "আপনার কতদিন ধরে জ্বর হচ্ছে? (How long have you had the fever?)"}


def _extraction(filled: int) -> str:
    data = {k: (f"<{k}>" if i < filled else "") for i, k in enumerate(SUMMARY_FIELD_KEYS)}
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

    state = {"filled": 2}  # sparse at intake; fuller after the answer

    def fake_attempt(provider, *, system, user, timeout):
        if "extract structured" in system:
            return _extraction(state["filled"])
        if "chief-complaint summary" in system:
            return "Short summary."
        if "completeness checker" in system:
            return json.dumps({"present": ["chest pain"],
                               "missing": ["fever duration", "temperature measurement"]})
        if "ONE follow-up question" in system:
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


def test_full_loop_question_answer_complete(env):
    client, TestSession, state = env
    uuid = _visit_with_intake(client)

    # next -> a question (score 0.2 < 0.7), stored AND spoken as a system utterance
    r = client.post(f"/api/visits/{uuid}/followup/next")
    assert r.status_code == 200
    body = r.json()
    assert body["complete"] is False and body["completeness_score"] == pytest.approx(0.2)
    q = body["question"]
    assert q["target_gap"] == "fever duration" and "জ্বর" in q["question_text"]
    turns = client.get(f"/api/visits/{uuid}").json()["utterances"]
    assert turns[-1]["role"] == "system" and turns[-1]["raw_text"] == q["question_text"]

    # calling next again re-serves the SAME open question (no duplicate M7 spend)
    assert client.post(f"/api/visits/{uuid}/followup/next").json()["question"]["id"] == q["id"]

    # answer -> M8 re-extract (fuller now) -> M9 over threshold -> complete
    state["filled"] = 8
    r = client.post(f"/api/visits/{uuid}/followup/answer",
                    json={"question_id": q["id"], "raw_text": "তিন দিন ধরে জ্বর"})
    assert r.status_code == 200
    body = r.json()
    assert body["complete"] is True and body["completeness_score"] == pytest.approx(0.8)

    # linkage + gap bookkeeping + module_events
    db = TestSession()
    profile = db.query(CaseProfile).one()
    assert "fever duration" in profile.gaps["present"]
    assert "fever duration" not in profile.gaps["missing"]
    modules = [e.module_code for e in db.query(ModuleEvent).all()]
    assert "M7" in modules and "M8" in modules
    db.close()

    # question answered -> answering again is a 409
    r = client.post(f"/api/visits/{uuid}/followup/answer",
                    json={"question_id": q["id"], "raw_text": "again"})
    assert r.status_code == 409


def test_human_edited_field_survives_m8_merge(env):
    client, TestSession, state = env
    uuid = _visit_with_intake(client)

    # A staff member edited field 1 (simulated directly; the PATCH route is BE-5).
    db = TestSession()
    profile = db.query(CaseProfile).one()
    fields = dict(profile.entities["summary_fields"])
    fields["main_problem"] = {"value": "HUMAN TEXT", "source": "human",
                              "edited_by": 1, "edited_at": None}
    profile.entities = {"summary_fields": fields}
    db.commit()
    db.close()

    q = client.post(f"/api/visits/{uuid}/followup/next").json()["question"]
    state["filled"] = 8
    client.post(f"/api/visits/{uuid}/followup/answer",
                json={"question_id": q["id"], "raw_text": "উত্তর"})

    db = TestSession()
    fields = db.query(CaseProfile).one().entities["summary_fields"]
    db.close()
    assert fields["main_problem"]["value"] == "HUMAN TEXT"       # human wins
    assert fields["onset_duration"]["value"] == "<onset_duration>"  # AI updated


def test_max_questions_and_guard_rails(env, monkeypatch):
    client, _, _ = env
    uuid = _visit_with_intake(client)

    monkeypatch.setattr(
        "backend.app.services.followup.get_settings",
        lambda: type("S", (), {"followup_max_questions": 0, "completeness_threshold": 0.7})(),
    )
    r = client.post(f"/api/visits/{uuid}/followup/next")
    assert r.json()["complete"] is True  # turn limit -> loop exits

    assert client.post("/api/visits/nope/followup/next").status_code == 404
    r = client.post(f"/api/visits/{uuid}/followup/answer",
                    json={"question_id": 999, "raw_text": "x"})
    assert r.status_code == 404


def test_next_requires_intake_first(env):
    client, _, _ = env
    r = client.post("/api/patients/verify-otp", json={"phone": "01712345678", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    assert client.post(f"/api/visits/{uuid}/followup/next").status_code == 400
