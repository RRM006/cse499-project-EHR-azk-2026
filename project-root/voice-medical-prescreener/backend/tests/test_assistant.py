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
    }

    def fake_attempt(provider, *, system, user, timeout):
        assert "drug-information assistant" in system
        state["last_user"] = user
        if state["llm_fails"]:
            raise RuntimeError("model down")
        return state["llm_reply"]

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)
    monkeypatch.setattr(
        "backend.app.services.assistant._search",
        lambda q: [{"title": "Paracetamol — NHS", "url": "https://example.org/para",
                    "snippet": "Adult dose 500mg to 1g every 4 to 6 hours."}],
    )
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
