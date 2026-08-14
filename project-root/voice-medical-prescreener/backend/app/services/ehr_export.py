"""S38 (B1, ADR-0062) — the encounter as an HL7 **FHIR R4 document Bundle**.

--------------------------------------------------------------------------------
WHY FHIR, AND WHAT "UNIVERSAL" HONESTLY MEANS HERE
--------------------------------------------------------------------------------

The brief asked for a "universal EHR download" and then, correctly, warned against
inventing one: *"Prefer an established healthcare interoperability representation
rather than inventing a custom 'universal EHR' format"* and *"Do NOT claim 'universal'
if the format is only a project export format."*

There is no universal EHR file. What exists is **HL7 FHIR**, the interoperability
standard essentially every modern health system speaks, and within it the *document
Bundle* — a `Bundle` with `type: "document"` whose first entry is a `Composition` that
indexes the rest. That is the standard way to say "here is one clinical encounter as a
self-contained file", and it is what this module emits. **R4** is chosen over R5
because R4 is the version with real deployment behind it.

⚠ Stated plainly, because overstating it would be the failure mode: this is a
**structurally valid, semantically conservative** FHIR R4 document. It is not certified,
not profiled against a national implementation guide, and a receiving system will still
need to map it. Where a concept had no code this module is confident in, it ships the
concept as TEXT rather than guessing a code — a wrong LOINC code is far worse than an
uncoded string, because a wrong code is silently believed.

--------------------------------------------------------------------------------
WHAT IS DELIBERATELY *NOT* IN THE BUNDLE
--------------------------------------------------------------------------------

* **The AI's suggested condition (C1) is excluded entirely.** Inside this project it is
  displayed with a disclaimer, in a card labelled "not a diagnosis", to a clinician who
  knows what it is. Exported into a FHIR bundle it would be a `Condition`-shaped thing
  travelling to a system that has no idea a model wrote it — and the disclaimer does not
  travel with the data once another EHR ingests it. Rule #2 is a property of the
  architecture, so the safe design is that the suggestion has no wire representation at
  all. The doctor's OWN diagnosis, typed by them into a prescription, is exported as a
  `Condition`; that is a human clinical judgement and belongs in the record.
* **No `Condition` is ever derived from the risk tier.** The tier is exported as a FHIR
  `RiskAssessment` — a different resource for a different thing — carrying the
  no-diagnosis disclaimer as a note.
* **Nothing is computed here that is not already stored**, except BMI, which is derived
  the same way it is everywhere else (ADR-0060).

--------------------------------------------------------------------------------
RULE #1 IN AN EXPORT
--------------------------------------------------------------------------------

The verbatim transcript IS included, reproduced exactly, in its own section labelled as
the patient's own words. It is escaped for XHTML and never edited, paraphrased or
summarised — the same contract ``visit_docx.render_visit_transcript`` already honours.
An EHR record of a voice pre-screening that omitted the voice would be missing its
primary source.

--------------------------------------------------------------------------------
BILINGUAL CONTENT
--------------------------------------------------------------------------------

Section titles carry Bangla through the standard FHIR **primitive extension** mechanism
(`_title` + the `translation` extension), not through an invented `title_bn` field — a
custom field is exactly the kind of thing that makes a "FHIR" file un-ingestible. Field
VALUES that the pipeline stores bilingually are rendered with both languages in the
narrative, because a narrative is human-readable text and a doctor in this clinic reads
both.

No new dependency: a FHIR resource is a JSON object, and this module builds JSON objects.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape

from sqlalchemy.orm import Session

from backend.app.db.models import (
    CaseProfile,
    Clinic,
    DoctorReview,
    Patient,
    Prescription,
    User,
    Visit,
    XaiExplanation,
)
from backend.app.db.repository_visits import list_visit_utterances
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services.clinical_reference import bmi
from backend.app.services.report import DISCLAIMER
from backend.app.services.risk import latest_assessment

FHIR_VERSION = "4.0.1"

#: The translation extension for a primitive element — the standard way to attach a
#: second language to a string in FHIR. NOT an invented field.
_TRANSLATION_URL = "http://hl7.org/fhir/StructureDefinition/translation"

#: LOINC codes used below. Only codes this module is confident about appear here;
#: anything else ships as ``text`` (see the module docstring).
LOINC = {
    "document": ("11488-4", "Consult note"),
    "chief_complaint": ("10154-3", "Chief complaint Narrative - Reported"),
    "hpi": ("10164-2", "History of present illness Narrative"),
    "medications": ("10160-0", "History of Medication use Narrative"),
    "allergies": ("48765-2", "Allergies and adverse reactions Document"),
    "vitals": ("8716-3", "Vital signs"),
    "body_weight": ("29463-7", "Body weight"),
    "body_height": ("8302-2", "Body height"),
    "bmi": ("39156-5", "Body mass index (BMI) [Ratio]"),
    "bp_panel": ("85354-9", "Blood pressure panel with all children optional"),
    "bp_systolic": ("8480-6", "Systolic blood pressure"),
    "bp_diastolic": ("8462-4", "Diastolic blood pressure"),
    # S39: the GENERIC blood-glucose code, chosen deliberately over the context-specific
    # ones (fasting, post-load). Following this module's own rule, a code is used only
    # where it is certainly right: 15074-8 says "glucose, in blood, in mmol/L", which is
    # exactly and only what is stored. The measurement context travels beside it as
    # text and as a coding in our own namespace, rather than being asserted through a
    # more specific LOINC that a receiver would then believe absolutely.
    "glucose": ("15074-8", "Glucose [Moles/volume] in Blood"),
}

#: How the stored context codes read in a document. The clinical MEANING of each
#: context lives in services/clinical_reference and is not repeated here — this is a
#: label, so that a receiving system is not handed a bare number.
GLUCOSE_CONTEXT_LABELS = {
    "fasting": "Fasting (no calorie intake for at least 8 hours)",
    "ogtt_2h": "2 hours after a 75 g oral glucose load (OGTT)",
    "random": "Random / casual (any time, regardless of meals)",
}
_GLUCOSE_CONTEXT_SYSTEM = "urn:niramoy:glucose-context"

#: Our four tiers -> the FHIR ``risk-probability`` value set, which has no "critical".
#: Mapping critical to "high" loses information, so the exact tier ALSO travels as
#: ``text`` and as a coding in our own namespace. A receiver that understands only the
#: standard set still gets a safe, non-understating answer.
_RISK_PROBABILITY = {"low": "low", "medium": "moderate", "high": "high", "critical": "high"}
_TIER_SYSTEM = "urn:niramoy:risk-tier"

#: Bilingual section titles: (English, Bangla).
_SECTION_TITLES = {
    "chief_complaint": ("Chief complaint", "প্রধান সমস্যা"),
    "prescreening": ("Pre-screening summary", "প্রাক-পরীক্ষার সারাংশ"),
    "medications": ("Medicines the patient reports taking", "রোগীর জানানো চলমান ওষুধ"),
    "allergies": ("Allergies", "অ্যালার্জি"),
    "vitals": ("Vital signs", "শারীরিক পরিমাপ"),
    "risk": ("Pre-screening risk assessment", "প্রাক-পরীক্ষার ঝুঁকি নিরূপণ"),
    "transcript": ("Patient's own words (verbatim, unedited)", "রোগীর নিজের কথা (হুবহু, অসম্পাদিত)"),
    "review": ("Doctor's review", "ডাক্তারের পর্যালোচনা"),
    "diagnosis": ("Diagnosis (doctor-authored)", "রোগনির্ণয় (ডাক্তার কর্তৃক)"),
    "plan": ("Treatment and plan", "চিকিৎসা ও পরিকল্পনা"),
}

#: The 10 fixed fields, bilingual, matching the labels the portals and the .docx use.
_FIELD_TITLES = {
    "main_problem": ("Main problem", "প্রধান সমস্যা"),
    "onset_duration": ("Onset and duration", "শুরুর সময় ও স্থায়িত্ব"),
    "symptom_details": ("Symptom details", "উপসর্গের বিস্তারিত"),
    "associated_symptoms": ("Associated symptoms", "আনুষঙ্গিক উপসর্গ"),
    "medical_history": ("Relevant medical history", "প্রাসঙ্গিক চিকিৎসা ইতিহাস"),
    "current_medicines": ("Current medicines", "চলমান ওষুধ"),
    "allergies": ("Allergies", "অ্যালার্জি"),
    "recent_changes_exposures": ("Recent changes / exposures", "সাম্প্রতিক পরিবর্তন"),
    "treatments_tried": ("Treatments tried", "গৃহীত ব্যবস্থা"),
    "current_concern": ("Current concern", "মূল উদ্বেগ"),
}


# --- small builders -----------------------------------------------------------


def _bilingual(text_en: str, text_bn: str) -> dict:
    """A `_title`-style primitive extension carrying the Bangla of an English string."""
    return {
        "extension": [
            {
                "url": _TRANSLATION_URL,
                "extension": [
                    {"url": "lang", "valueCode": "bn"},
                    {"url": "content", "valueString": text_bn},
                ],
            }
        ]
    }


def _narrative(html_body: str) -> dict:
    """A FHIR Narrative. ``generated`` is honest: this text is produced from the
    structured data beside it, not authored separately."""
    return {
        "status": "generated",
        "div": f'<div xmlns="http://www.w3.org/1999/xhtml">{html_body}</div>',
    }


def _instant(value: datetime | None) -> str:
    """A FHIR ``instant``. Offset-less SQLite values are UTC by construction here."""
    moment = value or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _loinc(key: str) -> dict:
    code, display = LOINC[key]
    return {"coding": [{"system": "http://loinc.org", "code": code, "display": display}]}


def _field_text(field: dict | None) -> tuple[str, str]:
    """(English, Bangla) for one summary field; either may be empty."""
    field = field or {}
    en = str(field.get("value_en") or field.get("value") or "").strip()
    bn = str(field.get("value_bn") or "").strip()
    return en, bn


def _parse_bp(bp: str | None) -> tuple[int, int] | None:
    """"120/80" -> (120, 80). Anything else -> None, and the reading then travels as
    free text only. Guessing at a malformed blood pressure is not acceptable."""
    parts = str(bp or "").split("/")
    if len(parts) != 2:
        return None
    try:
        systolic, diastolic = int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        return None
    if not (0 < systolic < 400 and 0 < diastolic < 300):
        return None
    return systolic, diastolic


# --- the bundle ---------------------------------------------------------------


def build_fhir_bundle(db: Session, visit: Visit) -> dict:
    """The whole encounter as one FHIR R4 document Bundle (a plain dict).

    Read-only: every value is already stored, and nothing here writes. Assembled fresh
    per request so a re-export always reflects the latest staff edits — the same
    property the ``summary_report`` .docx has.
    """
    patient = db.get(Patient, visit.patient_id) if visit.patient_id else None
    clinic = db.get(Clinic, visit.clinic_id)
    doctor = db.get(User, visit.assigned_doctor_id) if visit.assigned_doctor_id else None
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    assessment = latest_assessment(db, visit_id=visit.id)
    xai = (
        db.query(XaiExplanation)
        .filter(XaiExplanation.risk_assessment_id == assessment.id)
        .first()
        if assessment
        else None
    )
    review = (
        db.query(DoctorReview)
        .filter(DoctorReview.visit_id == visit.id)
        .order_by(DoctorReview.created_at.desc())
        .first()
    )
    prescriptions = (
        db.query(Prescription)
        .filter(Prescription.visit_id == visit.id)
        .order_by(Prescription.created_at.asc())
        .all()
    )
    fields = ((profile.entities if profile else None) or {}).get("summary_fields") or {}
    utterances = list_visit_utterances(db, visit_id=visit.id)

    # Stable, non-guessable URNs. urn:uuid references are what a document Bundle uses
    # for resources that have no server identity of their own.
    ref = {
        "patient": f"urn:uuid:{visit.uuid}-patient",
        "encounter": f"urn:uuid:{visit.uuid}-encounter",
        "organization": f"urn:uuid:{visit.uuid}-org",
        "practitioner": f"urn:uuid:{visit.uuid}-practitioner",
        "composition": f"urn:uuid:{visit.uuid}-composition",
    }

    entries: list[dict] = []
    sections: list[dict] = []

    def add(full_url: str, resource: dict) -> None:
        entries.append({"fullUrl": full_url, "resource": resource})

    def section(key: str, html_body: str, *, code_key: str | None = None,
                refs: list[str] | None = None) -> None:
        en, bn = _SECTION_TITLES[key]
        block: dict = {"title": en, "_title": _bilingual(en, bn), "text": _narrative(html_body)}
        if code_key:
            block["code"] = _loinc(code_key)
        if refs:
            block["entry"] = [{"reference": r} for r in refs]
        sections.append(block)

    # --- Patient / Organization / Practitioner / Encounter --------------------

    fhir_patient: dict = {"resourceType": "Patient", "id": f"{visit.uuid}-patient"}
    if patient is not None:
        if patient.display_name:
            fhir_patient["name"] = [{"text": patient.display_name}]
        if patient.external_ref:
            fhir_patient["telecom"] = [{"system": "phone", "value": patient.external_ref}]
        if patient.sex in ("male", "female", "other"):
            fhir_patient["gender"] = patient.sex
        if patient.birth_year:
            # Only a YEAR is known — FHIR `date` allows exactly that precision, so this
            # says "born in 1985" rather than inventing 1 January.
            fhir_patient["birthDate"] = str(patient.birth_year)
    add(ref["patient"], fhir_patient)

    add(ref["organization"], {
        "resourceType": "Organization",
        "id": f"{visit.uuid}-org",
        "name": (clinic.name if clinic else "Clinic"),
        **({"address": [{"text": clinic.address}]} if clinic and clinic.address else {}),
    })

    if doctor is not None:
        practitioner: dict = {
            "resourceType": "Practitioner",
            "id": f"{visit.uuid}-practitioner",
            "name": [{"text": doctor.name}],
        }
        if doctor.registration_no:
            practitioner["identifier"] = [
                {"system": "urn:niramoy:bmdc-registration", "value": doctor.registration_no}
            ]
        if doctor.qualification:
            practitioner["qualification"] = [{"code": {"text": doctor.qualification}}]
        add(ref["practitioner"], practitioner)

    encounter: dict = {
        "resourceType": "Encounter",
        "id": f"{visit.uuid}-encounter",
        # Reviewed/closed = the consultation is over; anything else is still running.
        "status": "finished" if visit.status in ("reviewed", "closed") else "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory",
        },
        "subject": {"reference": ref["patient"]},
        "serviceProvider": {"reference": ref["organization"]},
        "period": {"start": _instant(visit.started_at)},
    }
    if visit.completed_at:
        encounter["period"]["end"] = _instant(visit.completed_at)
    if doctor is not None:
        encounter["participant"] = [{"individual": {"reference": ref["practitioner"]}}]
    add(ref["encounter"], encounter)

    # --- Chief complaint + the 10 pre-screening fields ------------------------

    main_en, main_bn = _field_text(fields.get("main_problem"))
    if main_en or main_bn:
        section("chief_complaint",
                f"<p>{escape(main_en or main_bn)}</p>"
                + (f"<p lang='bn'>{escape(main_bn)}</p>" if main_bn and main_en else ""),
                code_key="chief_complaint")

    rows = []
    for key in SUMMARY_FIELD_KEYS:
        en, bn = _field_text(fields.get(key))
        if not (en or bn):
            continue
        title_en, title_bn = _FIELD_TITLES.get(key, (key, key))
        value = escape(en or bn)
        if bn and en and bn != en:
            value += f"<br/><span lang='bn'>{escape(bn)}</span>"
        rows.append(f"<tr><td>{escape(title_en)} / <span lang='bn'>{escape(title_bn)}</span></td>"
                    f"<td>{value}</td></tr>")
    if rows:
        section("prescreening", "<table>" + "".join(rows) + "</table>", code_key="hpi")

    meds_en, meds_bn = _field_text(fields.get("current_medicines"))
    if meds_en or meds_bn:
        section("medications", f"<p>{escape(meds_en or meds_bn)}</p>", code_key="medications")
    allergy_en, allergy_bn = _field_text(fields.get("allergies"))
    if allergy_en or allergy_bn:
        section("allergies", f"<p>{escape(allergy_en or allergy_bn)}</p>", code_key="allergies")

    # --- Vital signs as real Observations -------------------------------------

    vital_refs: list[str] = []
    recorded = _instant(visit.submitted_at or visit.started_at)

    def observation(suffix: str, code_key: str, value: dict, *, components=None) -> str:
        url = f"urn:uuid:{visit.uuid}-obs-{suffix}"
        resource = {
            "resourceType": "Observation",
            "id": f"{visit.uuid}-obs-{suffix}",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs",
                }]
            }],
            "code": _loinc(code_key),
            "subject": {"reference": ref["patient"]},
            "encounter": {"reference": ref["encounter"]},
            "effectiveDateTime": recorded,
        }
        resource.update(value)
        if components:
            resource["components"] = components
        add(url, resource)
        vital_refs.append(url)
        return url

    vital_rows = []
    if patient is not None and patient.weight_kg is not None:
        observation("weight", "body_weight", {"valueQuantity": {
            "value": patient.weight_kg, "unit": "kg",
            "system": "http://unitsofmeasure.org", "code": "kg"}})
        vital_rows.append(f"<tr><td>Weight</td><td>{patient.weight_kg} kg</td></tr>")
    if patient is not None and patient.height_cm is not None:
        observation("height", "body_height", {"valueQuantity": {
            "value": patient.height_cm, "unit": "cm",
            "system": "http://unitsofmeasure.org", "code": "cm"}})
        vital_rows.append(f"<tr><td>Height</td><td>{patient.height_cm} cm</td></tr>")

    # BMI is DERIVED here exactly as it is on screen (ADR-0060) — never read from a
    # stored column, because there isn't one and there must not be.
    derived_bmi = bmi(
        patient.weight_kg if patient else None, patient.height_cm if patient else None
    )
    if derived_bmi is not None:
        observation("bmi", "bmi", {"valueQuantity": {
            "value": derived_bmi, "unit": "kg/m2",
            "system": "http://unitsofmeasure.org", "code": "kg/m2"}})
        # S39: "kg/m2", not "kg/m²". It is the UCUM unit already used by the coded
        # value two lines above, so the narrative and the Observation now agree — and
        # the superscript was being SILENTLY DROPPED by the PDF renderer (the shipped
        # font has no U+00B2), which printed "kg/m": a different unit entirely.
        vital_rows.append(f"<tr><td>BMI</td><td>{derived_bmi} kg/m2</td></tr>")

    parsed_bp = _parse_bp(patient.bp if patient else None)
    if parsed_bp:
        systolic, diastolic = parsed_bp
        url = f"urn:uuid:{visit.uuid}-obs-bp"
        add(url, {
            "resourceType": "Observation",
            "id": f"{visit.uuid}-obs-bp",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs", "display": "Vital Signs",
                }]
            }],
            "code": _loinc("bp_panel"),
            "subject": {"reference": ref["patient"]},
            "encounter": {"reference": ref["encounter"]},
            "effectiveDateTime": recorded,
            "component": [
                {"code": _loinc("bp_systolic"), "valueQuantity": {
                    "value": systolic, "unit": "mm[Hg]",
                    "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}},
                {"code": _loinc("bp_diastolic"), "valueQuantity": {
                    "value": diastolic, "unit": "mm[Hg]",
                    "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}},
            ],
        })
        vital_refs.append(url)
        vital_rows.append(f"<tr><td>Blood pressure</td><td>{systolic}/{diastolic} mmHg</td></tr>")
    elif patient is not None and (patient.bp or "").strip():
        # Unparseable: carried as text so nothing is lost, but NOT as a coded reading.
        vital_rows.append(f"<tr><td>Blood pressure (as recorded)</td>"
                          f"<td>{escape(patient.bp)}</td></tr>")

    # S39 (ADR-0064): the medic's blood-sugar reading. Built out here rather than
    # through observation() for two reasons that both matter to a receiver:
    #   * its category is `laboratory`, NOT `vital-signs` — a glucose reading is a lab
    #     measurement, and mis-categorising it would file it beside pulse and weight;
    #   * the measurement CONTEXT is part of the fact. A fasting 6.5 and a random 6.5
    #     are different findings, so the context ships three ways (a coding in our own
    #     namespace, the code's own text, and a human-readable note) and the value is
    #     never exported without it. The stored pair cannot come apart — the route
    #     refuses one without the other — but nothing is asserted here either way.
    # ⚠ No interpretation, no `Observation.interpretation`, no reference range: the
    # number is reported, and what it means is the clinician's judgement against the
    # published chart (rule #2; ADR-0060's "glucose_reference() takes no value").
    if patient is not None and patient.blood_glucose_mmol_l is not None:
        context_code = patient.blood_glucose_context or ""
        context_label = GLUCOSE_CONTEXT_LABELS.get(context_code, context_code or "context not recorded")
        code = dict(_loinc("glucose"))
        if context_code:
            code["coding"] = list(code["coding"]) + [
                {"system": _GLUCOSE_CONTEXT_SYSTEM, "code": context_code,
                 "display": context_label}
            ]
        code["text"] = f"Blood glucose — {context_label}"
        url = f"urn:uuid:{visit.uuid}-obs-glucose"
        add(url, {
            "resourceType": "Observation",
            "id": f"{visit.uuid}-obs-glucose",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "laboratory", "display": "Laboratory",
                }]
            }],
            "code": code,
            "subject": {"reference": ref["patient"]},
            "encounter": {"reference": ref["encounter"]},
            "effectiveDateTime": recorded,
            "valueQuantity": {
                "value": patient.blood_glucose_mmol_l, "unit": "mmol/L",
                "system": "http://unitsofmeasure.org", "code": "mmol/L",
            },
            "note": [{"text": f"Measurement context: {context_label}."}],
        })
        vital_refs.append(url)
        vital_rows.append(
            f"<tr><td>Blood glucose</td>"
            f"<td>{patient.blood_glucose_mmol_l} mmol/L &#183; {escape(context_label)}</td></tr>"
        )

    if vital_rows:
        section("vitals", "<table>" + "".join(vital_rows) + "</table>",
                code_key="vitals", refs=vital_refs)

    # --- Risk assessment (a RiskAssessment, never a Condition) ----------------

    if assessment is not None:
        url = f"urn:uuid:{visit.uuid}-risk"
        resource: dict = {
            "resourceType": "RiskAssessment",
            "id": f"{visit.uuid}-risk",
            "status": "final",
            "subject": {"reference": ref["patient"]},
            "encounter": {"reference": ref["encounter"]},
            "occurrenceDateTime": _instant(assessment.created_at),
            "prediction": [{
                "outcome": {"text": "Pre-screening urgency tier (NOT a diagnosis)"},
                "qualitativeRisk": {
                    "coding": [
                        {"system": "http://terminology.hl7.org/CodeSystem/risk-probability",
                         "code": _RISK_PROBABILITY.get(assessment.tier, "moderate")},
                        # The exact tier, because the standard set has no "critical".
                        {"system": _TIER_SYSTEM, "code": assessment.tier},
                    ],
                    "text": assessment.tier,
                },
            }],
            # The no-diagnosis statement travels WITH the resource, so it survives being
            # ingested on its own by another system.
            "note": [{"text": DISCLAIMER}],
        }
        if xai is not None:
            resource["note"].append({"text": f"Reason: {xai.reason_text}"})
        if assessment.red_flags:
            resource["basis"] = [{"display": str(flag)} for flag in assessment.red_flags]
        if assessment.rule_overrode:
            resource["note"].append({
                "text": "A deterministic red-flag rule forced this tier, overriding the model."
            })
        add(url, resource)

        body = f"<p>Urgency tier: <b>{escape(assessment.tier)}</b></p>"
        if assessment.red_flags:
            flags = "".join(f"<li>{escape(str(f))}</li>" for f in assessment.red_flags)
            body += f"<p>Red flags:</p><ul>{flags}</ul>"
        if xai is not None:
            body += f"<p>{escape(xai.reason_text)}</p>"
        body += f"<p><i>{escape(DISCLAIMER)}</i></p>"
        section("risk", body, refs=[url])

    # --- Doctor's own diagnosis + treatment, from SAVED prescriptions ---------
    #
    # ⚠ Only the human doctor's text becomes clinical resources. The AI suggested
    # condition has no representation in this bundle at all (see the module docstring).

    med_refs: list[str] = []
    test_refs: list[str] = []
    diagnosis_refs: list[str] = []
    plan_rows: list[str] = []

    for index, rx in enumerate(prescriptions):
        payload = rx.payload if isinstance(rx.payload, dict) else {}
        authored = _instant(rx.created_at)
        prescriber = {"reference": ref["practitioner"]} if doctor is not None else None

        diagnosis = str(payload.get("diagnosis") or "").strip()
        if diagnosis:
            url = f"urn:uuid:{visit.uuid}-condition-{index}"
            condition: dict = {
                "resourceType": "Condition",
                "id": f"{visit.uuid}-condition-{index}",
                "clinicalStatus": {"coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active"}]},
                "verificationStatus": {"coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed"}]},
                # Free TEXT, not a guessed SNOMED code: the doctor typed a phrase, and
                # mapping it to a code here would be this module inventing a diagnosis.
                "code": {"text": diagnosis},
                "subject": {"reference": ref["patient"]},
                "encounter": {"reference": ref["encounter"]},
                "recordedDate": authored,
            }
            if doctor is not None:
                condition["recorder"] = {"reference": ref["practitioner"]}
            add(url, condition)
            diagnosis_refs.append(url)

        for m_index, medicine in enumerate(payload.get("medicines") or []):
            if not isinstance(medicine, dict):
                continue
            name = str(medicine.get("name") or "").strip()
            if not name:
                continue
            strength = str(medicine.get("strength") or "").strip()
            instruction = " ".join(
                str(medicine.get(part) or "").strip()
                for part in ("dosage", "timing", "duration")
            ).strip()
            url = f"urn:uuid:{visit.uuid}-medreq-{index}-{m_index}"
            request: dict = {
                "resourceType": "MedicationRequest",
                "id": f"{visit.uuid}-medreq-{index}-{m_index}",
                "status": "active",
                "intent": "order",
                "medicationCodeableConcept": {
                    "text": f"{name} {strength}".strip()
                },
                "subject": {"reference": ref["patient"]},
                "encounter": {"reference": ref["encounter"]},
                "authoredOn": authored,
            }
            if prescriber:
                request["requester"] = prescriber
            if instruction:
                request["dosageInstruction"] = [{"text": instruction}]
            add(url, request)
            med_refs.append(url)
            plan_rows.append(
                f"<tr><td>Medicine</td><td>{escape(f'{name} {strength}'.strip())}"
                + (f" — {escape(instruction)}" if instruction else "")
                + "</td></tr>"
            )

        # Required tests, as the doctor wrote them on the prescription. A ServiceRequest
        # here RECORDS an order a human made and printed; nothing in this system places
        # an order automatically (rule #2 / the brief's "never automatically order").
        raw_tests = str(payload.get("tests") or "")
        for t_index, test in enumerate(
            [part.strip() for part in raw_tests.replace(",", "\n").split("\n") if part.strip()]
        ):
            url = f"urn:uuid:{visit.uuid}-servreq-{index}-{t_index}"
            service: dict = {
                "resourceType": "ServiceRequest",
                "id": f"{visit.uuid}-servreq-{index}-{t_index}",
                "status": "active",
                "intent": "order",
                "code": {"text": test},
                "subject": {"reference": ref["patient"]},
                "encounter": {"reference": ref["encounter"]},
                "authoredOn": authored,
            }
            if prescriber:
                service["requester"] = prescriber
            add(url, service)
            test_refs.append(url)
            plan_rows.append(f"<tr><td>Test</td><td>{escape(test)}</td></tr>")

        advice = str(payload.get("advice") or "").strip()
        if advice:
            plan_rows.append(f"<tr><td>Advice</td><td>{escape(advice)}</td></tr>")
        followup = str(payload.get("followup_date") or "").strip()
        if followup:
            plan_rows.append(f"<tr><td>Follow-up</td><td>{escape(followup)}</td></tr>")

    if diagnosis_refs:
        body = "".join(
            f"<p>{escape(str((rx.payload or {}).get('diagnosis') or '').strip())}</p>"
            for rx in prescriptions
            if str((rx.payload or {}).get("diagnosis") or "").strip()
        )
        section("diagnosis", body, refs=diagnosis_refs)
    if plan_rows:
        section("plan", "<table>" + "".join(plan_rows) + "</table>",
                refs=med_refs + test_refs)

    # --- Doctor's review ------------------------------------------------------

    if review is not None:
        body = f"<p>Disposition: {escape(str(review.disposition or 'accepted'))}</p>"
        if review.override_tier:
            body += f"<p>Doctor overrode the tier to: {escape(review.override_tier)}</p>"
        if review.notes:
            body += f"<p>{escape(review.notes)}</p>"
        section("review", body)

    # --- The patient's own words (rule #1: verbatim, unedited) ---------------

    if utterances:
        turns = []
        for turn in utterances:
            speaker = "Assistant asked" if turn.role == "system" else "Patient said"
            # escape() only — the raw string is reproduced exactly, never normalised,
            # re-cased, trimmed of meaning or replaced by its correction.
            turns.append(f"<p><b>{speaker}:</b> {escape(turn.raw_text)}</p>")
        section("transcript", "".join(turns))

    # --- Composition + Bundle -------------------------------------------------

    now = _instant(None)
    composition: dict = {
        "resourceType": "Composition",
        "id": f"{visit.uuid}-composition",
        "status": "final" if visit.status in ("reviewed", "closed") else "preliminary",
        "type": _loinc("document"),
        "subject": {"reference": ref["patient"]},
        "encounter": {"reference": ref["encounter"]},
        "date": now,
        "author": [{"reference": ref["practitioner"]}] if doctor is not None
                  else [{"reference": ref["organization"]}],
        "title": "Voice pre-screening record",
        "_title": _bilingual("Voice pre-screening record", "কণ্ঠস্বর প্রাক-পরীক্ষার রেকর্ড"),
        "custodian": {"reference": ref["organization"]},
        "language": visit.language or "bn-BD",
        "section": sections,
    }

    return {
        "resourceType": "Bundle",
        "id": f"{visit.uuid}-document",
        "meta": {"lastUpdated": now, "profile": ["http://hl7.org/fhir/StructureDefinition/Bundle"]},
        "identifier": {"system": "urn:niramoy:visit", "value": visit.uuid},
        "type": "document",
        "timestamp": now,
        # The Composition MUST be the first entry of a document Bundle.
        "entry": [{"fullUrl": ref["composition"], "resource": composition}] + entries,
    }


def render_fhir_bundle(db: Session, visit: Visit) -> bytes:
    """The bundle as UTF-8 JSON bytes, ready to store and download.

    ``ensure_ascii=False`` so Bangla survives as Bangla rather than as \\uXXXX escapes —
    the file is meant to be readable as well as ingestible.
    """
    return json.dumps(
        build_fhir_bundle(db, visit), ensure_ascii=False, indent=2
    ).encode("utf-8")
