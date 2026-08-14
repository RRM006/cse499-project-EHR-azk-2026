"""S38 (B1, ADR-0062) — the FHIR R4 document Bundle export.

Two kinds of assertion live here, and the second kind is the reason the file is long:

  1. **Structural FHIR correctness.** A document Bundle has rules that a hand-built dict
     will violate the moment someone edits it carelessly: ``type: "document"``, the
     Composition FIRST, every ``reference`` resolving to a ``fullUrl`` in the same
     bundle. Those are checked mechanically, because a bundle that is 95% right is
     un-ingestible in exactly the same way as one that is 5% right.

  2. **The safety boundaries of the export** — which are the whole reason this is a
     conservative module rather than a dump of the database:
       * the AI's suggested condition must have **no representation at all** (rule #2:
         the disclaimer does not survive ingestion into another system, so the data
         must not travel);
       * the risk tier must be a ``RiskAssessment``, never a ``Condition``;
       * ``critical`` must not be silently downgraded when mapped onto the standard
         ``risk-probability`` value set, which has no "critical";
       * the verbatim transcript must be reproduced EXACTLY (rule #1).

The bundle is exercised through the real ``POST /documents/ehr_bundle`` route and read
back through the real download route, so what is asserted is what a receiving system
would actually be handed.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import (
    CaseProfile, Clinic, Patient, RiskAssessment, User, Utterance, Visit, XaiExplanation,
)
from backend.app.main import app
from backend.app.services.clinical_dates import dhaka_today_iso
from backend.app.services.documents.storage import FilesystemStorage

#: The patient's exact words, including the punctuation and spacing that a
#: "helpful" normaliser would quietly clean up (rule #1).
RAW_WORDS = "আমার বুকে ব্যথা ২ দিন ধরে... খুব বেশি, আর শ্বাস নিতে কষ্ট হয়!"

#: A stored AI suggestion. It must not appear ANYWHERE in the exported bundle.
AI_SUGGESTION = "GERD (Acid Reflux)"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    db = TestSession()
    clinic = Clinic(name="Demo Clinic", address="12 Dhanmondi, Dhaka")
    db.add(clinic)
    db.flush()
    doctor = User(clinic_id=clinic.id, name="Dr. Yasmin Ara", role="doctor",
                  qualification="MBBS, FCPS", registration_no="BMDC-A-40002")
    patient = Patient(clinic_id=clinic.id, external_ref="+8801712345678",
                      display_name="Kamal Hossain", birth_year=1985, sex="male",
                      weight_kg=72.0, height_cm=165.0, bp="128/84")
    db.add_all([doctor, patient])
    db.flush()
    started = datetime.now(timezone.utc) - timedelta(hours=2)
    visit = Visit(clinic_id=clinic.id, patient_id=patient.id, status="awaiting_doctor",
                  assigned_doctor_id=doctor.id, language="bn-BD",
                  started_at=started, submitted_at=started + timedelta(minutes=11))
    db.add(visit)
    db.flush()
    db.add_all([
        Utterance(visit_id=visit.id, role="system", seq=1,
                  raw_text="আপনার প্রধান সমস্যা কী?", source="tts"),
        Utterance(visit_id=visit.id, role="patient", seq=2, raw_text=RAW_WORDS,
                  source="mic", stt_provider="browser_webspeech",
                  corrected_text="আমার বুকে ব্যথা দুই দিন ধরে।"),
    ])
    db.add(CaseProfile(visit_id=visit.id, summary="Chest pain", entities={
        "summary_fields": {
            "main_problem": {"value_en": "Chest pain for 2 days",
                             "value_bn": "দুই দিন ধরে বুকে ব্যথা", "source": "human"},
            "allergies": {"value_en": "Penicillin", "value_bn": "পেনিসিলিন", "source": "ai"},
            "current_medicines": {"value_en": "Omeprazole 20mg", "source": "ai"},
        },
        # Present in the DB, and it must NOT reach the bundle.
        "suggested_condition": {"condition_en": AI_SUGGESTION, "source": "ai",
                                "disclaimer": "AI suggestion only — NOT a diagnosis."},
    }))
    ra = RiskAssessment(visit_id=visit.id, tier="critical",
                        red_flags=["chest pain radiating to the arm"],
                        rule_overrode=True, model_provider="local_rule")
    db.add(ra)
    db.flush()
    db.add(XaiExplanation(risk_assessment_id=ra.id,
                          reason_text="Chest pain with breathing difficulty was reported."))
    db.commit()
    ids = {"visit_uuid": visit.uuid, "doctor_id": doctor.id, "patient_id": patient.id}
    db.close()

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    storage = FilesystemStorage(tmp_path)
    for target in ("backend.app.services.documents.build_storage",
                   "backend.app.api.routes_documents.build_storage"):
        monkeypatch.setattr(target, lambda *a, **k: storage)
    yield TestClient(app), TestSession, ids
    app.dependency_overrides.clear()


def _bundle(client, ids) -> tuple[dict, dict]:
    """Generate the export and read the stored FILE back. Returns (doc_meta, bundle)."""
    r = client.post(f"/api/visits/{ids['visit_uuid']}/documents/ehr_bundle")
    assert r.status_code == 200, r.text
    doc = r.json()
    download = client.get(doc["download_url"])
    assert download.status_code == 200
    return doc, json.loads(download.content.decode("utf-8"))


def _resources(bundle, resource_type):
    return [e["resource"] for e in bundle["entry"]
            if e["resource"]["resourceType"] == resource_type]


# ---------------------------------------------------------------------------
# The document is served, stored and typed correctly
# ---------------------------------------------------------------------------


def test_the_export_is_recorded_as_a_document_and_downloads_as_fhir_json(env):
    client, _, ids = env
    doc, bundle = _bundle(client, ids)
    assert doc["kind"] == "ehr_bundle"
    assert doc["format"] == "json"
    assert doc["filename"].endswith(".json")
    # Named for the standard it implements, not for an internal kind code.
    assert "fhir" in doc["filename"].lower()
    resp = client.get(doc["download_url"])
    assert resp.headers["content-type"].startswith("application/fhir+json")
    assert bundle["resourceType"] == "Bundle"


def test_the_export_reuses_the_existing_document_pipeline(env):
    """No parallel storage: it lands in the same table, behind the same download
    route, as the .docx exports (the brief's 'no huge new subsystem')."""
    client, TestSession, ids = env
    doc, _ = _bundle(client, ids)
    from backend.app.db.models import Document
    with TestSession() as db:
        row = db.get(Document, doc["id"])
        assert row is not None
        assert row.visit_id is not None and row.utterance_id is None   # visit-grain
        assert row.format == "json"


def test_an_unknown_kind_is_still_rejected(env):
    client, _, ids = env
    r = client.post(f"/api/visits/{ids['visit_uuid']}/documents/not_a_kind")
    assert r.status_code == 400


def test_the_docx_kinds_are_unaffected(env):
    """Adding a JSON kind must not change what the two existing kinds produce."""
    client, _, ids = env
    for kind in ("transcript", "summary_report"):
        r = client.post(f"/api/visits/{ids['visit_uuid']}/documents/{kind}")
        assert r.status_code == 200, r.text
        assert r.json()["format"] == "docx"
        assert r.json()["filename"].endswith(".docx")


# ---------------------------------------------------------------------------
# Structural FHIR correctness
# ---------------------------------------------------------------------------


def test_it_is_a_document_bundle_with_the_composition_first(env):
    """A FHIR document Bundle is defined by this: type=document, Composition first."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    assert bundle["type"] == "document"
    assert bundle["entry"][0]["resource"]["resourceType"] == "Composition"
    assert bundle["timestamp"]
    assert bundle["identifier"]["value"] == ids["visit_uuid"]


def test_every_internal_reference_resolves_inside_the_bundle(env):
    """A document Bundle must be self-contained. A dangling urn:uuid is the single
    most common way a hand-built bundle becomes un-ingestible."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    known = {e["fullUrl"] for e in bundle["entry"]}

    dangling = []

    def walk(node):
        if isinstance(node, dict):
            target = node.get("reference")
            if isinstance(target, str) and target.startswith("urn:uuid:") and target not in known:
                dangling.append(target)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(bundle)
    assert not dangling, f"references with no resource in the bundle: {sorted(set(dangling))}"


def test_the_core_resources_are_present(env):
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    types = {e["resource"]["resourceType"] for e in bundle["entry"]}
    assert {"Composition", "Patient", "Encounter", "Organization",
            "Practitioner", "Observation", "RiskAssessment"} <= types


def test_every_resource_has_an_id_and_a_full_url(env):
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    for entry in bundle["entry"]:
        assert entry.get("fullUrl"), entry["resource"]["resourceType"]
        assert entry["resource"].get("id"), entry["resource"]["resourceType"]


def test_every_section_carries_a_generated_narrative(env):
    """Composition.section.text is what a human-readable EHR viewer renders. A section
    with structure and no narrative shows up blank in most systems."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    for section in bundle["entry"][0]["resource"]["section"]:
        assert section["text"]["status"] == "generated"
        assert section["text"]["div"].startswith('<div xmlns="http://www.w3.org/1999/xhtml">')


def test_vitals_are_coded_observations_with_ucum_units(env):
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    codes = {}
    for obs in _resources(bundle, "Observation"):
        code = obs["code"]["coding"][0]["code"]
        codes[code] = obs
    assert "29463-7" in codes, "no body-weight Observation"
    assert "8302-2" in codes, "no body-height Observation"
    assert "39156-5" in codes, "no BMI Observation"
    assert "85354-9" in codes, "no blood-pressure panel"
    assert codes["29463-7"]["valueQuantity"]["system"] == "http://unitsofmeasure.org"
    assert codes["29463-7"]["valueQuantity"]["code"] == "kg"
    # The BP panel splits into the two standard components rather than a text blob.
    component_codes = {c["code"]["coding"][0]["code"] for c in codes["85354-9"]["component"]}
    assert component_codes == {"8480-6", "8462-4"}


def test_bmi_is_derived_in_the_export_never_read_from_a_column(env):
    """ADR-0060 again, at the export boundary: 72 kg at 165 cm is 26.4."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    bmi_obs = [o for o in _resources(bundle, "Observation")
               if o["code"]["coding"][0]["code"] == "39156-5"]
    assert bmi_obs[0]["valueQuantity"]["value"] == 26.4


def test_a_malformed_blood_pressure_is_not_guessed_into_components(env):
    """"high" is not a blood pressure. It travels as text in the narrative and produces
    no coded reading — inventing 140/90 from it would be fabricating a measurement."""
    client, TestSession, ids = env
    with TestSession() as db:
        db.get(Patient, ids["patient_id"]).bp = "high-ish"
        db.commit()
    _, bundle = _bundle(client, ids)
    panels = [o for o in _resources(bundle, "Observation")
              if o["code"]["coding"][0]["code"] == "85354-9"]
    assert panels == []
    assert "high-ish" in json.dumps(bundle, ensure_ascii=False)   # not lost, just uncoded


def test_only_the_year_of_birth_is_asserted(env):
    """The record holds a birth YEAR. Emitting 1985-01-01 would invent a birthday."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    assert _resources(bundle, "Patient")[0]["birthDate"] == "1985"


# ---------------------------------------------------------------------------
# Safety boundaries — the reason this module is conservative
# ---------------------------------------------------------------------------


def test_the_ai_suggested_condition_never_reaches_the_bundle(env):
    """Rule #2. Inside the portal it is labelled and disclaimered to a clinician who
    knows what it is; in an exported file the disclaimer does not survive ingestion by
    another system, so the data must not travel at all."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    text = json.dumps(bundle, ensure_ascii=False)
    assert AI_SUGGESTION not in text
    assert "GERD" not in text
    assert "suggested_condition" not in text


def test_the_risk_tier_is_a_riskassessment_and_never_a_condition(env):
    """A Condition is a diagnosis. The tier is not one, and the resource choice is
    what encodes that distinction for a receiving system."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    assert _resources(bundle, "RiskAssessment"), "the tier is not exported at all"
    # No prescription exists in this fixture, so there must be no Condition whatsoever.
    assert _resources(bundle, "Condition") == []


def test_critical_is_not_silently_downgraded(env):
    """The standard `risk-probability` value set has no "critical". Mapping it to
    "high" is unavoidable there, so the EXACT tier also travels in its own system —
    otherwise the most urgent tier the system can produce becomes unrecoverable."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    risk = _resources(bundle, "RiskAssessment")[0]
    qualitative = risk["prediction"][0]["qualitativeRisk"]
    codes = {c["system"]: c["code"] for c in qualitative["coding"]}
    assert codes["http://terminology.hl7.org/CodeSystem/risk-probability"] == "high"
    assert codes["urn:niramoy:risk-tier"] == "critical"
    assert qualitative["text"] == "critical"


def test_the_no_diagnosis_disclaimer_rides_on_the_risk_resource(env):
    """It must survive the resource being ingested on its own, away from our UI."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    notes = " ".join(n["text"] for n in _resources(bundle, "RiskAssessment")[0]["note"])
    assert "NOT a diagnosis" in notes
    assert "rule" in notes.lower(), "the rule-override fact is not recorded"


def test_red_flags_and_the_xai_reason_are_carried(env):
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    risk = _resources(bundle, "RiskAssessment")[0]
    assert any("radiating" in b["display"] for b in risk["basis"])
    assert any("breathing difficulty" in n["text"] for n in risk["note"])


def test_the_transcript_is_reproduced_exactly(env):
    """Rule #1: verbatim, unedited — and NOT replaced by the correction, which lives in
    a separate column precisely so the raw words stay untouched."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    sections = bundle["entry"][0]["resource"]["section"]
    transcript = [s for s in sections if "own words" in s["title"]]
    assert transcript, "the patient's words are not in the export"
    div = transcript[0]["text"]["div"]
    # Reconstruct the escaped text and compare against the stored raw string.
    from html import unescape
    import re
    plain = unescape(re.sub(r"<[^>]+>", "", div))
    assert RAW_WORDS in plain
    assert "দুই দিন ধরে।" not in plain, "the correction replaced the raw words"


# ---------------------------------------------------------------------------
# Bilingual content
# ---------------------------------------------------------------------------


def test_section_titles_carry_bangla_through_the_standard_translation_extension(env):
    """Via `_title` + the FHIR translation extension, NOT an invented `title_bn` — a
    custom field is what makes a 'FHIR' file un-ingestible."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    composition = bundle["entry"][0]["resource"]
    assert "title_bn" not in json.dumps(composition), "an invented bilingual field"
    for section in composition["section"]:
        extension = section["_title"]["extension"][0]
        assert extension["url"] == "http://hl7.org/fhir/StructureDefinition/translation"
        inner = {e["url"]: e for e in extension["extension"]}
        assert inner["lang"]["valueCode"] == "bn"
        assert inner["content"]["valueString"].strip()


def test_bilingual_field_values_appear_in_both_languages(env):
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    text = json.dumps(bundle, ensure_ascii=False)
    assert "Chest pain for 2 days" in text
    assert "দুই দিন ধরে বুকে ব্যথা" in text


def test_bangla_survives_as_bangla_in_the_stored_file(env):
    """ensure_ascii=False: the file is meant to be readable, not a wall of \\uXXXX."""
    client, _, ids = env
    doc, _ = _bundle(client, ids)
    raw = client.get(doc["download_url"]).content.decode("utf-8")
    assert "বুকে" in raw
    assert "\\u09ac" not in raw


# ---------------------------------------------------------------------------
# The doctor's own clinical content, once a prescription exists
# ---------------------------------------------------------------------------


def _write_prescription(client, ids):
    return client.post(
        f"/api/visits/{ids['visit_uuid']}/prescription",
        json={"doctor_id": ids["doctor_id"], "payload": {
            "language": "en", "date": dhaka_today_iso(),
            "clinic": {"name": "Demo Clinic"}, "doctor": {"name": "Dr. Yasmin Ara"},
            "patient": {"name": "Kamal Hossain"},
            "symptoms": "chest pain", "diagnosis": "Musculoskeletal chest pain",
            "medicines": [{"name": "Napa", "strength": "500mg", "dosage": "1+0+1",
                           "timing": "after meals", "duration": "5 days"}],
            "advice": "Rest, return if worse", "tests": "ECG\nCBC with ESR",
            "followup_date": dhaka_today_iso(),
        }},
    )


def test_the_doctors_own_diagnosis_becomes_a_condition(env):
    """The human's clinical judgement DOES belong in the record — the distinction the
    export draws is human vs model, not 'no diagnoses ever'."""
    client, _, ids = env
    assert _write_prescription(client, ids).status_code == 200
    _, bundle = _bundle(client, ids)
    conditions = _resources(bundle, "Condition")
    assert len(conditions) == 1
    assert conditions[0]["code"]["text"] == "Musculoskeletal chest pain"
    assert conditions[0]["verificationStatus"]["coding"][0]["code"] == "confirmed"
    # Free text, never a guessed clinical code.
    assert "coding" not in conditions[0]["code"]
    # ...and the AI's suggestion still is not there.
    assert AI_SUGGESTION not in json.dumps(bundle, ensure_ascii=False)


def test_medicines_become_medicationrequests_with_their_instructions(env):
    client, _, ids = env
    _write_prescription(client, ids)
    _, bundle = _bundle(client, ids)
    requests = _resources(bundle, "MedicationRequest")
    assert len(requests) == 1
    assert requests[0]["medicationCodeableConcept"]["text"] == "Napa 500mg"
    assert requests[0]["intent"] == "order"
    assert "1+0+1" in requests[0]["dosageInstruction"][0]["text"]


def test_each_required_test_becomes_its_own_servicerequest(env):
    """The tests field is newline-joined; two tests must not become one order."""
    client, _, ids = env
    _write_prescription(client, ids)
    _, bundle = _bundle(client, ids)
    services = _resources(bundle, "ServiceRequest")
    assert {s["code"]["text"] for s in services} == {"ECG", "CBC with ESR"}


def test_a_case_with_no_prescription_produces_no_orders(env):
    """Nothing is ordered automatically. Orders exist only because a human wrote and
    generated a prescription."""
    client, _, ids = env
    _, bundle = _bundle(client, ids)
    assert _resources(bundle, "MedicationRequest") == []
    assert _resources(bundle, "ServiceRequest") == []


def test_the_export_reflects_edits_made_after_an_earlier_export(env):
    """Assembled fresh per request, like the summary_report .docx — a stale EHR file
    would be worse than none."""
    client, TestSession, ids = env
    _, first = _bundle(client, ids)
    assert _resources(first, "Condition") == []
    _write_prescription(client, ids)
    _, second = _bundle(client, ids)
    assert len(_resources(second, "Condition")) == 1


def test_the_export_writes_nothing_clinical(env):
    """It is a VIEW of the encounter. The only row it may create is the documents row
    recording that an export happened."""
    client, TestSession, ids = env
    from backend.app.db.models import Document, Prescription, RiskAssessment as RA
    with TestSession() as db:
        before = (db.query(Prescription).count(), db.query(RA).count(),
                  db.query(CaseProfile).count(), db.query(Utterance).count())
        docs_before = db.query(Document).count()
    _bundle(client, ids)
    with TestSession() as db:
        after = (db.query(Prescription).count(), db.query(RA).count(),
                 db.query(CaseProfile).count(), db.query(Utterance).count())
        assert after == before
        assert db.query(Document).count() == docs_before + 1
