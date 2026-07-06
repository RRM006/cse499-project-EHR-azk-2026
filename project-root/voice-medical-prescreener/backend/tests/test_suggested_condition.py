"""MEDIC-4 / C1 — the AI suggested condition (ADR-0036), fully offline.

Must: generate + store the bilingual suggestion at submit (module M10C, its own
module_events row), NEVER block submit when the LLM is down, carry the
'not a diagnosis' disclaimer in every payload that carries the suggestion,
support the staff edit path (source='human', all slots untranslated, audit row),
and reject non-staff editors. The doctor's prescription Diagnosis field is a
step-18 concern — nothing here writes anywhere near it (rule #2).
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import AuditLog, CaseProfile, Clinic, ModuleEvent, User, Visit
from backend.app.main import app
from backend.app.services.suggestion import CONDITION_DISCLAIMER, CONDITION_DISCLAIMER_BN


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

    monkeypatch.setattr(
        "backend.app.services.llm_client.provider_chain_for_module",
        lambda code, settings=None: [lp.ProviderConfig("gemini_flash", "k", "http://fake", "m")],
    )

    state = {"suggest_fail": False}

    def fake_attempt(provider, *, system, user, timeout):
        if "classify the urgency" in system:
            return json.dumps({"tier": "medium", "drivers": ["chest burning after meals"]})
        if "explain, in 1-3 plain sentences" in system:
            return "Assigned due to the listed factors."
        if "single most plausible possible condition" in system:
            if state["suggest_fail"]:
                raise RuntimeError("bucket down")
            return json.dumps({
                "condition_en": "GERD (Acid Reflux)",
                "condition_bn": "জিইআরডি (অ্যাসিড রিফ্লাক্স)",
                "reasoning_en": "Chest burning after meals and sour burps are consistent with reflux.",
                "reasoning_bn": "খাওয়ার পরে বুক জ্বালা ও টক ঢেকুর রিফ্লাক্সের সাথে সঙ্গতিপূর্ণ।",
            })
        raise AssertionError(f"Unexpected prompt: {system[:50]}")

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)
    yield TestClient(app), TestSession, state
    app.dependency_overrides.clear()


def _visit_with_profile(client, TestSession, phone="01715984632", with_profile=True):
    r = client.post("/api/patients/verify-otp", json={"phone": phone, "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances",
                json={"raw_text": "খাওয়ার পরে বুক জ্বালাপোড়া করে", "role": "patient"})
    if with_profile:
        db = TestSession()
        visit = db.query(Visit).filter(Visit.uuid == uuid).one()
        db.add(CaseProfile(visit_id=visit.id, entities={"summary_fields": {}},
                           summary="খাওয়ার পরে বুক জ্বালা"))
        db.commit()
        db.close()
    return uuid


def _seed_user(TestSession, role):
    db = TestSession()
    clinic = db.query(Clinic).first()
    if clinic is None:
        clinic = Clinic(name="Demo Clinic")
        db.add(clinic)
        db.flush()
    user = User(clinic_id=clinic.id, name=f"Test {role}", role=role)
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    return user_id


def test_submit_generates_bilingual_suggestion_with_disclaimer(env):
    client, TestSession, _ = env
    uuid = _visit_with_profile(client, TestSession)
    assert client.post(f"/api/visits/{uuid}/submit").status_code == 200

    profile = client.get(f"/api/visits/{uuid}/profile").json()
    s = profile["entities"]["suggested_condition"]
    assert s["condition"] == s["condition_en"] == "GERD (Acid Reflux)"
    assert s["condition_bn"] == "জিইআরডি (অ্যাসিড রিফ্লাক্স)"
    assert "reflux" in s["reasoning_en"]
    assert s["reasoning_bn"]
    assert s["source"] == "ai" and s["edited_by"] is None
    # The 'not a diagnosis' disclaimer travels INSIDE the payload (rule #2 / C1).
    assert s["disclaimer"] == CONDITION_DISCLAIMER
    assert s["disclaimer_bn"] == CONDITION_DISCLAIMER_BN

    # M10C is observable as its own module_events row (ADR-0026 principle 5).
    db = TestSession()
    event = db.query(ModuleEvent).filter(ModuleEvent.module_code == "M10C").one()
    assert event.status == "ok" and event.provider == "gemini_flash"
    db.close()


def test_llm_failure_never_blocks_submit(env):
    client, TestSession, state = env
    state["suggest_fail"] = True
    uuid = _visit_with_profile(client, TestSession)

    r = client.post(f"/api/visits/{uuid}/submit")
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_review"
    profile = client.get(f"/api/visits/{uuid}/profile").json()
    assert "suggested_condition" not in (profile["entities"] or {})


def test_no_profile_no_suggestion_still_submits(env):
    client, TestSession, _ = env
    uuid = _visit_with_profile(client, TestSession, phone="01712345678", with_profile=False)
    r = client.post(f"/api/visits/{uuid}/submit")
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_review"


def test_staff_edit_replaces_with_provenance_and_audit(env):
    client, TestSession, _ = env
    uuid = _visit_with_profile(client, TestSession)
    client.post(f"/api/visits/{uuid}/submit")
    medic_id = _seed_user(TestSession, "medic")

    r = client.patch(f"/api/visits/{uuid}/profile/condition",
                     json={"condition": "Gastritis", "reasoning": "History of NSAID use.",
                           "editor_id": medic_id})
    assert r.status_code == 200
    s = r.json()["entities"]["suggested_condition"]
    # Staff text fills EVERY language slot untranslated (ADR-0033 staff-edit rule).
    assert s["condition"] == s["condition_en"] == s["condition_bn"] == "Gastritis"
    assert s["reasoning_en"] == s["reasoning_bn"] == "History of NSAID use."
    assert s["source"] == "human" and s["edited_by"] == medic_id and s["edited_at"]
    # The disclaimer survives the edit — the server re-attaches it (rule #2).
    assert s["disclaimer"] == CONDITION_DISCLAIMER
    assert s["disclaimer_bn"] == CONDITION_DISCLAIMER_BN

    db = TestSession()
    log = db.query(AuditLog).filter(AuditLog.action == "profile.condition_edit").one()
    assert log.actor_id == medic_id
    assert log.detail == {"condition": "Gastritis"}
    db.close()


def test_edit_guard_rails(env):
    client, TestSession, _ = env
    uuid = _visit_with_profile(client, TestSession)
    medic_id = _seed_user(TestSession, "medic")
    desk_id = _seed_user(TestSession, "desk")

    # Non-staff editor -> 403 (desk cannot shape clinical suggestions).
    assert client.patch(f"/api/visits/{uuid}/profile/condition",
                        json={"condition": "X", "editor_id": desk_id}).status_code == 403
    assert client.patch(f"/api/visits/{uuid}/profile/condition",
                        json={"condition": "X", "editor_id": 9999}).status_code == 403
    # Unknown visit -> 404.
    assert client.patch("/api/visits/nope/profile/condition",
                        json={"condition": "X", "editor_id": medic_id}).status_code == 404
    # Empty condition -> 422 (schema-validated).
    assert client.patch(f"/api/visits/{uuid}/profile/condition",
                        json={"condition": "", "editor_id": medic_id}).status_code == 422
    # No profile yet -> 400.
    uuid2 = _visit_with_profile(client, TestSession, phone="01798765432", with_profile=False)
    assert client.patch(f"/api/visits/{uuid2}/profile/condition",
                        json={"condition": "X", "editor_id": medic_id}).status_code == 400
