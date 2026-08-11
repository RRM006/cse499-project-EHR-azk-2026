"""F6 — the FULL chronological conversation survives summarization (requirement 8).

Inspection found this requirement already satisfied by the existing design: every
turn is an insert-only ``utterances`` row, and nothing in the pipeline deletes or
rewrites one. So this file adds no feature — it converts "true today" into "cannot
silently stop being true", which is the whole point of a regression test.

It asserts, over a real end-to-end visit:
  * assistant questions AND patient answers are both stored, in order;
  * generating the summary/report ADDS rows and removes none;
  * every ``raw_text`` is byte-identical to what was sent (rule #1);
  * the doctor's document renders the whole conversation verbatim;
  * the structured 10-field summary and the conversation coexist — the summary never
    replaces the transcript.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import Utterance
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS

_Q = {"target_gap": "fever duration", "priority": 1,
      "question": "কতদিন ধরে? (For how many days?)"}

# Deliberately awkward: punctuation, mixed script, and a trailing space that a
# "helpful" cleaner would strip.
_ANSWERS = [
    "পেটের সমস্যা",
    "রহিম উদ্দিন",
    "৪৫ বছর",
    "তিন দিন ধরে পেট ব্যথা, খাওয়ার পরে বাড়ে — gastric problem হতে পারে ",
]


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

    def fake_attempt(provider, *, system, user, timeout):
        if "extract structured" in system:
            data = {k: {"en": f"<{k}>", "bn": f"<bn:{k}>"} for k in SUMMARY_FIELD_KEYS}
            data["symptom_details_structured"] = {}
            data["problem_area"] = {"en": "abdomen", "bn": "পেট"}
            data["patient_demographics"] = {"name": "রহিম উদ্দিন", "age_years": 45,
                                            "sex": "male"}
            return json.dumps(data)
        if "chief-complaint summary" in system:
            return "Abdominal pain for three days, worse after eating."
        if "completeness checker" in system:
            return json.dumps({"present": ["duration"], "missing": []})
        if "ONE follow-up question" in system:
            return json.dumps(_Q)
        if "classify the urgency" in system:
            return json.dumps({"tier": "medium", "drivers": ["abdominal pain"]})
        if "explain, in 1-3 plain sentences" in system:
            return "Medium tier from reported duration."
        if "possible condition" in system.lower():
            return json.dumps({"condition_en": "Gastritis", "condition_bn": "গ্যাস্ট্রাইটিস",
                               "reasoning_en": "r", "reasoning_bn": "র"})
        raise AssertionError(f"Unexpected prompt: {system[:60]}")

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)
    yield TestClient(app), TestSession
    app.dependency_overrides.clear()


def _full_visit(client):
    """The kiosk journey: scripted opening (4 turns) -> intake -> one follow-up."""
    r = client.post("/api/patients/verify-otp",
                    json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    # The kiosk records each scripted question as a system turn, then the answer.
    for i, answer in enumerate(_ANSWERS):
        client.post(f"/api/visits/{uuid}/utterances",
                    json={"raw_text": f"scripted question {i}", "role": "system",
                          "source": "tts", "stt_provider": None})
        client.post(f"/api/visits/{uuid}/utterances",
                    json={"raw_text": answer, "role": "patient", "source": "mic"})
    client.post(f"/api/visits/{uuid}/intake")
    q = client.post(f"/api/visits/{uuid}/followup/next").json()["question"]
    client.post(f"/api/visits/{uuid}/followup/answer",
                json={"question_id": q["id"], "raw_text": "না, জ্বর নেই"})
    return uuid


def _turns(client, uuid):
    return client.get(f"/api/visits/{uuid}").json()["utterances"]


def test_both_speakers_are_preserved_in_order(env):
    client, _ = env
    uuid = _full_visit(client)
    turns = _turns(client, uuid)

    roles = [t["role"] for t in turns]
    assert "system" in roles and "patient" in roles
    # Chronological: ids ascend in the order the turns happened.
    assert [t["id"] for t in turns] == sorted(t["id"] for t in turns)
    # Every patient answer is present, verbatim — including the trailing space.
    said = [t["raw_text"] for t in turns if t["role"] == "patient"]
    for answer in _ANSWERS:
        assert answer in said
    assert "না, জ্বর নেই" in said


def test_the_assistants_own_questions_are_part_of_the_record(env):
    """A transcript of only the patient's half is not a conversation."""
    client, _ = env
    uuid = _full_visit(client)
    asked = [t["raw_text"] for t in _turns(client, uuid) if t["role"] == "system"]
    assert len(asked) >= len(_ANSWERS)
    assert _Q["question"] in asked        # the M7 question was recorded too


def test_generating_the_summary_and_report_deletes_nothing(env):
    """The heart of requirement 8: summarizing must ADD, never replace."""
    client, _ = env
    uuid = _full_visit(client)
    before = [(t["id"], t["raw_text"]) for t in _turns(client, uuid)]

    client.post(f"/api/visits/{uuid}/submit")
    client.post(f"/api/visits/{uuid}/assess")
    client.post(f"/api/visits/{uuid}/report")

    after = [(t["id"], t["raw_text"]) for t in _turns(client, uuid)]
    assert after[: len(before)] == before          # every original turn, unchanged
    assert len(after) >= len(before)               # only ever grows


def test_the_structured_summary_and_the_conversation_coexist(env):
    client, _ = env
    uuid = _full_visit(client)
    client.post(f"/api/visits/{uuid}/submit")
    client.post(f"/api/visits/{uuid}/assess")
    sections = client.post(f"/api/visits/{uuid}/report").json()["sections"]

    # The 10 structured points...
    assert list(sections["summary_fields"]) == list(SUMMARY_FIELD_KEYS)
    # ...and the follow-up answer still verbatim beside them.
    assert sections["followup_qa"][0]["answer_raw"] == "না, জ্বর নেই"
    # ...and the conversation itself untouched.
    assert len(_turns(client, uuid)) >= 2 * len(_ANSWERS)


def test_raw_text_is_never_rewritten_in_the_database(env):
    """Read the rows directly — not through a serializer that might normalize."""
    client, TestSession = env
    uuid = _full_visit(client)
    client.post(f"/api/visits/{uuid}/submit")

    db = TestSession()
    stored = [u.raw_text for u in db.query(Utterance).order_by(Utterance.id).all()]
    db.close()
    for answer in _ANSWERS:
        assert answer in stored, "an answer was altered or dropped (rule #1)"


def test_the_doctor_document_renders_the_whole_conversation_verbatim(env):
    client, _ = env
    uuid = _full_visit(client)
    r = client.post(f"/api/visits/{uuid}/documents/transcript")
    assert r.status_code == 200

    from io import BytesIO

    from docx import Document

    # Download it the way the kiosk does, rather than guessing the storage layout.
    content = client.get(r.json()["download_url"]).content
    text = "\n".join(p.text for p in Document(BytesIO(content)).paragraphs)
    for answer in _ANSWERS:
        assert answer.strip() in text
    assert _Q["question"] in text          # the assistant's side is in the doc too
