"""P3-2 (2.0 build) — the doctor portal always shows the LATEST patient details,
including every kind of medic edit.

Verification item: the doctor's case view is built from fresh reads
(GET /visits/{uuid} embeds the live Patient row; /profile and /risk re-read on
every open), so medic edits — identity/vitals (PATCH vitals), a summary-field
correction, a C1 condition replacement, a risk override — must all be visible to
the doctor, including edits made AFTER the case was forwarded (the medic's
post-referral card edits identity/weight exactly then). Offline — LLM faked.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import Clinic, User
from backend.app.main import app
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS


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
    doctor = User(clinic_id=clinic.id, name="Dr. Yasmin", role="doctor")
    db.add_all([medic, doctor])
    db.commit()
    ids = {"medic": medic.id, "doctor": doctor.id}
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

    def fake_attempt(provider, *, system, user, timeout):
        if "classify the urgency" in system:
            return json.dumps({"tier": "medium", "drivers": ["fever 3 days"]})
        if "explain, in 1-3 plain sentences" in system:
            return "Medium due to fever duration."
        if '"condition_en"' in system:
            return json.dumps({"condition_en": "Viral fever (possible)",
                               "condition_bn": "ভাইরাল জ্বর (সম্ভাব্য)",
                               "reasoning_en": "Fever reported for three days.",
                               "reasoning_bn": "তিন দিনের জ্বর।"})
        if "extract structured" in system:
            data = {k: f"<{k}>" for k in SUMMARY_FIELD_KEYS}
            data["symptom_details_structured"] = {}
            return json.dumps(data)
        if "chief-complaint summary" in system:
            return "Fever for three days."
        if "completeness checker" in system:
            return json.dumps({"present": [], "missing": ["temperature"]})
        raise AssertionError(system[:50])

    monkeypatch.setattr("backend.app.services.llm_client._attempt", fake_attempt)
    yield TestClient(app), ids
    app.dependency_overrides.clear()


def test_doctor_reads_show_every_medic_edit_even_after_forward(env):
    client, ids = env

    # Patient submits (P1 flow), case lands in the medic queue.
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]
    client.post(f"/api/visits/{uuid}/utterances",
                json={"raw_text": "তিন দিন ধরে জ্বর", "role": "patient"})
    client.post(f"/api/visits/{uuid}/intake")
    assert client.post(f"/api/visits/{uuid}/submit").status_code == 200
    patient_id = client.get(f"/api/visits/{uuid}").json()["patient"]["id"]

    # Medic corrects a summary field, replaces the C1 condition, overrides risk…
    assert client.patch(
        f"/api/visits/{uuid}/profile/fields/main_problem",
        json={"value": "Fever with chills, 3 days", "editor_id": ids["medic"]},
    ).status_code == 200
    assert client.patch(
        f"/api/visits/{uuid}/profile/condition",
        json={"condition": "Dengue (suspected)", "reasoning": "Seasonal outbreak.",
              "editor_id": ids["medic"]},
    ).status_code == 200
    assert client.post(
        f"/api/visits/{uuid}/risk/override",
        json={"tier": "high", "editor_id": ids["medic"], "reason": "Local dengue wave"},
    ).status_code == 200

    # …then forwards, and edits identity/vitals AFTERWARDS (the post-referral card).
    assert client.post(f"/api/visits/{uuid}/assign",
                       json={"doctor_id": ids["doctor"]}).status_code == 200
    assert client.patch(
        f"/api/patients/{patient_id}/vitals",
        json={"display_name": "Rahim Uddin", "sex": "male", "age_years": 38,
              "weight_kg": 72.5, "bp": "130/85", "editor_id": ids["medic"]},
    ).status_code == 200

    # The doctor's queue row reflects the medic's world…
    item = client.get("/api/dashboard",
                      params={"role": "doctor", "doctor_id": ids["doctor"]}).json()[0]
    assert item["visit_uuid"] == uuid
    assert item["tier"] == "high"                       # the human override, not the AI tier
    assert item["patient_name"] == "Rahim Uddin"
    assert item["main_problem"] == "Fever with chills, 3 days"

    # …and so does everything the doctor's case view fetches on open:
    patient = client.get(f"/api/visits/{uuid}").json()["patient"]
    assert patient["display_name"] == "Rahim Uddin"
    assert patient["sex"] == "male"
    assert patient["weight_kg"] == 72.5 and patient["bp"] == "130/85"
    assert patient["birth_year"] is not None            # age edit landed

    entities = client.get(f"/api/visits/{uuid}/profile").json()["entities"]
    field = entities["summary_fields"]["main_problem"]
    assert field["value"] == "Fever with chills, 3 days" and field["source"] == "human"
    condition = entities["suggested_condition"]
    assert condition["condition_en"] == "Dengue (suspected)" and condition["source"] == "human"
    assert condition.get("disclaimer")                  # rule #2: disclaimer survives the edit

    risk = client.get(f"/api/visits/{uuid}/risk").json()
    assert risk["tier"] == "high" and risk["model_provider"] == "human"
