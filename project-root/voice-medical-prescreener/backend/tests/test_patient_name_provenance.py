"""S39 (ADR-0064) — the patient NAME must never be shown without its origin.

THE BUG THIS PINS
-----------------
A patient ran a kiosk session and said nothing about a name, yet the medic portal
showed one. It was not fabricated: ``patients`` is keyed by phone number, so a name
recorded during an EARLIER visit (by staff, or by the M3 auto-fill) is attached to
the person and inherited by every later visit.

Keeping the name is right. Presenting it as if it had been established in the case on
screen is not. These tests hold three properties:

  1. the AI's identity auto-fill leaves an audit row — it previously left NOTHING, so
     a model could put a name into a permanent medical record untraceably;
  2. a name inherited from an earlier visit is reported as such (``from_this_visit``
     is False), which is the exact fact the reported bug hid;
  3. nothing is ever invented — no name in, no name out, and an origin that cannot be
     established is reported as ``unknown`` rather than guessed.

All offline (faked LLM, synthetic data — rule #4).
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import AuditLog, Clinic, Patient, User, Visit
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services.identity import (
    IDENTITY_AI_FILL_ACTION,
    STAFF_EDIT_ACTION,
    name_provenance,
)


def _extraction(demo: dict | None) -> str:
    data = {k: {"en": f"<{k}>", "bn": f"<bn:{k}>"} for k in SUMMARY_FIELD_KEYS}
    data["symptom_details_structured"] = {}
    if demo is not None:
        data["patient_demographics"] = demo
    return json.dumps(data)


@pytest.fixture()
def env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    db = TestSession()
    clinic = Clinic(name="Demo Clinic")
    db.add(clinic)
    db.flush()
    medic = User(clinic_id=clinic.id, name="Medic Rahman", role="medic")
    db.add(medic)
    db.commit()
    ids = {"clinic": clinic.id, "medic": medic.id}
    db.close()

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
    state = {"demo": {"name": "রহিম উদ্দিন", "age_years": 45, "sex": "male"}}

    def fake_attempt(provider, *, system, user, timeout):
        if "extract structured" in system:
            return _extraction(state["demo"])
        if "chief-complaint summary" in system:
            return "Short summary."
        if "completeness checker" in system:
            return json.dumps({"present": [], "missing": ["temperature"]})
        raise AssertionError(system[:60])

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)
    yield TestClient(app), TestSession, state, ids
    app.dependency_overrides.clear()


def _visit_with_speech(client: TestClient, phone: str) -> str:
    """One kiosk visit that has said something, ready for /intake."""
    client.post("/api/patients/lookup", json={"phone": phone})
    res = client.post("/api/patients/verify-otp", json={"phone": phone, "otp": "000000"})
    assert res.status_code == 200, res.text
    uuid = res.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances",
                json={"raw_text": "আমার জ্বর হয়েছে", "role": "patient"})
    return uuid


# --- 1. the AI auto-fill is now traceable ------------------------------------------


def test_ai_identity_fill_writes_an_audit_row(env):
    client, TestSession, _state, _ids = env
    uuid = _visit_with_speech(client, "+8801711111111")
    assert client.post(f"/api/visits/{uuid}/intake").status_code == 200

    db = TestSession()
    rows = db.query(AuditLog).filter(AuditLog.action == IDENTITY_AI_FILL_ACTION).all()
    assert len(rows) == 1, "the AI wrote a name into a medical record with no audit row"
    row = rows[0]
    # No human wrote it, and that NULL is the fact worth recording.
    assert row.actor_id is None
    assert row.entity_type == "patient"
    assert row.detail["fields"]["display_name"] == "রহিম উদ্দিন"
    assert row.detail["visit_uuid"] == uuid
    db.close()


def test_no_demographics_means_no_audit_row_and_no_name(env):
    """Nothing extracted -> nothing written. The absence of a name is preserved."""
    client, TestSession, state, _ids = env
    state["demo"] = {"name": "", "age_years": None, "sex": ""}
    uuid = _visit_with_speech(client, "+8801722222222")
    assert client.post(f"/api/visits/{uuid}/intake").status_code == 200

    db = TestSession()
    assert db.query(AuditLog).filter(AuditLog.action == IDENTITY_AI_FILL_ACTION).count() == 0
    visit = db.query(Visit).filter(Visit.uuid == uuid).first()
    patient = db.get(Patient, visit.patient_id)
    assert patient.display_name is None
    db.close()

    body = client.get(f"/api/visits/{uuid}").json()
    assert body["patient"]["display_name"] is None
    assert body["name_provenance"]["has_name"] is False
    assert body["name_provenance"]["source"] is None


# --- 2. THE REPORTED BUG: a name inherited from an earlier visit -------------------


def test_name_from_an_earlier_visit_is_reported_as_not_from_this_visit(env):
    """The exact reproduction: visit 1 records a name, visit 2 (same phone) says
    nothing about one, and visit 2 must not present the name as its own."""
    client, TestSession, state, _ids = env
    phone = "+8801733333333"

    first = _visit_with_speech(client, phone)
    assert client.post(f"/api/visits/{first}/intake").status_code == 200
    client.post(f"/api/visits/{first}/submit")

    # A second, later visit by the same phone number, where the patient says no name.
    state["demo"] = {"name": "", "age_years": None, "sex": ""}
    second = _visit_with_speech(client, phone)
    assert client.post(f"/api/visits/{second}/intake").status_code == 200

    body = client.get(f"/api/visits/{second}").json()
    # The name is still there — a returning patient is the same person.
    assert body["patient"]["display_name"] == "রহিম উদ্দিন"
    prov = body["name_provenance"]
    assert prov["has_name"] is True
    assert prov["source"] == "ai"
    assert prov["visit_uuid"] == first
    assert prov["from_this_visit"] is False, (
        "a name carried over from an earlier visit must say so — this is the bug"
    )

    # …and on the visit it actually came from, it is reported as belonging there.
    assert client.get(f"/api/visits/{first}").json()["name_provenance"]["from_this_visit"] is True


def test_staff_typed_name_is_attributed_to_the_staff_member(env):
    client, TestSession, state, ids = env
    state["demo"] = {"name": "", "age_years": None, "sex": ""}
    uuid = _visit_with_speech(client, "+8801744444444")
    client.post(f"/api/visits/{uuid}/intake")

    patient_id = client.get(f"/api/visits/{uuid}").json()["patient"]["id"]
    res = client.patch(f"/api/patients/{patient_id}/vitals",
                       json={"display_name": "করিম মিয়া", "editor_id": ids["medic"]})
    assert res.status_code == 200, res.text

    prov = client.get(f"/api/visits/{uuid}").json()["name_provenance"]
    assert prov["source"] == "staff"
    assert prov["actor_name"] == "Medic Rahman"
    assert prov["recorded_at"] is not None
    # The edit happened DURING this visit, and a staff edit records no visit of its
    # own — so it could have come from the patient in the room or from a paper form.
    # "We cannot tell" is the honest answer; a confident False would be a guess.
    assert prov["from_this_visit"] is None


def test_a_staff_name_typed_before_this_visit_began_is_not_from_it(env):
    """The reported bug's real shape: a colleague typed the name during an EARLIER
    visit, and today's case inherited it. A staff edit records no visit — but it does
    record WHEN, and a name written before this visit started provably did not come
    from it. Deducing that is not a guess, and staying silent about it would leave the
    one situation this module exists for unreported."""
    from datetime import datetime, timedelta, timezone

    from backend.app.db.models import AuditLog, Visit

    client, TestSession, state, ids = env
    state["demo"] = {"name": "", "age_years": None, "sex": ""}
    uuid = _visit_with_speech(client, "+8801799999999")
    client.post(f"/api/visits/{uuid}/intake")
    patient_id = client.get(f"/api/visits/{uuid}").json()["patient"]["id"]
    client.patch(f"/api/patients/{patient_id}/vitals",
                 json={"display_name": "পুরনো রোগী", "editor_id": ids["medic"]})

    # Backdate the edit to before the visit started — i.e. a previous attendance.
    db = TestSession()
    visit = db.query(Visit).filter(Visit.uuid == uuid).first()
    started = visit.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    entry = (db.query(AuditLog).filter(AuditLog.action == "patient.vitals_edit")
             .order_by(AuditLog.id.desc()).first())
    entry.created_at = started - timedelta(days=2)
    db.commit()
    db.close()

    prov = client.get(f"/api/visits/{uuid}").json()["name_provenance"]
    assert prov["source"] == "staff"
    assert prov["from_this_visit"] is False, (
        "a name recorded before the visit began was presented as belonging to it"
    )
    assert datetime.fromisoformat(prov["recorded_at"]) is not None


def test_a_weight_only_edit_does_not_look_like_a_rename(env):
    """`patient.vitals_edit` is written for every weight change too. Only rows that
    actually carried a display_name may count as the name's origin."""
    client, TestSession, state, ids = env
    uuid = _visit_with_speech(client, "+8801755555555")
    client.post(f"/api/visits/{uuid}/intake")           # AI writes the name
    patient_id = client.get(f"/api/visits/{uuid}").json()["patient"]["id"]
    client.patch(f"/api/patients/{patient_id}/vitals",
                 json={"weight_kg": 62.5, "editor_id": ids["medic"]})

    prov = client.get(f"/api/visits/{uuid}").json()["name_provenance"]
    assert prov["source"] == "ai", "a weight edit was mistaken for a rename"
    assert prov["actor_name"] is None


# --- 3. nothing is ever invented ----------------------------------------------------


def test_unaudited_legacy_name_is_reported_as_unknown_not_guessed(env):
    """A name written before S39 has no audit row. 'unknown' is the honest answer;
    reporting it as staff-entered would be exactly the invention this prevents."""
    client, TestSession, _state, ids = env
    db = TestSession()
    patient = Patient(clinic_id=ids["clinic"], external_ref="+8801766666666",
                      display_name="পুরনো নাম")
    db.add(patient)
    db.commit()
    prov = name_provenance(db, patient)
    assert prov["has_name"] is True
    assert prov["source"] == "unknown"
    assert prov["recorded_at"] is None
    assert prov["from_this_visit"] is None
    db.close()


def test_provenance_of_a_nameless_patient_claims_nothing(env):
    client, TestSession, _state, ids = env
    db = TestSession()
    patient = Patient(clinic_id=ids["clinic"], external_ref="+8801777777777")
    db.add(patient)
    db.commit()
    prov = name_provenance(db, patient)
    assert prov == {"has_name": False, "source": None, "recorded_at": None,
                    "visit_uuid": None, "actor_name": None, "from_this_visit": None}
    assert name_provenance(db, None)["has_name"] is False
    db.close()


def test_ai_never_overwrites_a_staff_name(env):
    """The pre-existing fill-only-when-empty rule, re-pinned: the staff value is
    final, so a later extraction cannot silently rename the patient."""
    client, TestSession, state, ids = env
    state["demo"] = {"name": "", "age_years": None, "sex": ""}
    uuid = _visit_with_speech(client, "+8801788888888")
    client.post(f"/api/visits/{uuid}/intake")
    patient_id = client.get(f"/api/visits/{uuid}").json()["patient"]["id"]
    client.patch(f"/api/patients/{patient_id}/vitals",
                 json={"display_name": "স্টাফ নাম", "editor_id": ids["medic"]})

    state["demo"] = {"name": "এআই নাম", "age_years": 30, "sex": "male"}
    client.post(f"/api/visits/{uuid}/intake")

    body = client.get(f"/api/visits/{uuid}").json()
    assert body["patient"]["display_name"] == "স্টাফ নাম"
    assert body["name_provenance"]["source"] == "staff"


def test_audit_actions_are_the_two_the_service_reads(env):
    """A guard on the string constants: renaming either action silently breaks
    provenance, and the portal would quietly fall back to 'unknown' for everything."""
    assert IDENTITY_AI_FILL_ACTION == "patient.identity_ai_fill"
    assert STAFF_EDIT_ACTION == "patient.vitals_edit"
