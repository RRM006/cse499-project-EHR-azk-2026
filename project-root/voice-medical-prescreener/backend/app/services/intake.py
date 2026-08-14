"""Intake pipeline (BE-2): M3 extraction -> M4 summary -> M6 gaps over a visit's
collected utterances, written into the visit's case_profile.

Reads the conversation (corrected text when available, else raw — raw itself is
never modified, rule #1). Never diagnoses (rule #2): prompts extract and summarize
only what the patient actually said. M2 correction stays its own endpoint/step.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.db.models import CaseProfile, Patient, Visit
from backend.app.db.repository_visits import list_visit_utterances
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS, SummaryFields
from backend.app.services.audit import audit
from backend.app.services.identity import IDENTITY_AI_FILL_ACTION
from backend.app.services.llm_client import call_module

logger = logging.getLogger(__name__)

_EXTRACT_SYSTEM = (
    "You extract structured pre-screening data for a doctor in Bangladesh from a "
    "patient conversation (Bangla / Banglish / English). You NEVER diagnose, NEVER "
    "invent details, and NEVER translate the patient's meaning into a disease name.\n"
    "Return ONLY a JSON object (no markdown, no commentary) with EXACTLY these keys:\n"
    + ", ".join(SUMMARY_FIELD_KEYS)
    + ", symptom_details_structured.\n"
    "Each of the 10 named keys maps to an object {\"en\": \"...\", \"bn\": \"...\"} — "
    "the SAME short summary of what the patient said for that field, written once in "
    "plain English (en) and once in Bangla using Bangla script (bn). If the field was "
    "not mentioned, use {\"en\": \"\", \"bn\": \"\"}.\n"
    "symptom_details_structured is an object {location, character, worse, better, "
    "pain_severity_0_10} (strings, severity an integer 0-10 or null).\n"
    "Also include a key \"patient_demographics\": an object {\"name\": \"...\", "
    "\"age_years\": <integer or null>, \"sex\": \"male|female|other or empty\"} — the "
    "patient's own name EXACTLY as they stated it (in the script they used), their "
    "age in years, and their sex/gender, each ONLY if the patient explicitly stated "
    "it about themselves in the conversation; otherwise use empty/null. Never guess "
    "these from symptoms, voice, or context.\n"
    "Also include a key \"problem_area\": an object {\"en\": \"...\", \"bn\": \"...\"} "
    "naming the BODY AREA or health area the patient came to talk about (for example "
    "\"abdomen / stomach\", \"chest\", \"head\", \"skin\", \"mental health\"), in "
    "English (en) and Bangla script (bn). Use ONLY what the patient indicated; if they "
    "have not indicated an area, use {\"en\": \"\", \"bn\": \"\"}. Do NOT infer a "
    "disease — this is a location, not a diagnosis.\n"
    "Base every value ONLY on the conversation text."
)

_SUMMARY_SYSTEM = (
    "You write a 2-4 sentence chief-complaint summary for a doctor, from a patient "
    "pre-screening conversation (Bangla / Banglish / English). Plain English. State "
    "symptoms, onset/duration, and relevant context the patient mentioned. Do NOT "
    "diagnose, do NOT name diseases, do NOT add reassurance or advice. "
    "Return ONLY the summary text."
)

_GAPS_SYSTEM = (
    "You are a clinical-intake completeness checker. Given a patient pre-screening "
    "conversation and the extracted fields, list what is present and what is still "
    "missing for a complete pre-screening picture. Do NOT diagnose.\n"
    "Return ONLY a JSON object: {\"present\": [..], \"missing\": [..]} where each "
    "item is a short English phrase naming a data point (e.g. \"fever duration\", "
    "\"temperature measurement\", \"medication dose\")."
)


def _conversation_text(db: Session, visit: Visit) -> str:
    """The dialogue as text, newest-last. Corrected text is preferred; raw is the
    fallback and is only READ here."""
    lines = []
    for u in list_visit_utterances(db, visit_id=visit.id):
        speaker = "ASSISTANT" if u.role == "system" else "PATIENT"
        lines.append(f"{speaker}: {u.corrected_text or u.raw_text}")
    return "\n".join(lines)


def _parse_json(text: str) -> dict:
    """Parse a model reply as JSON, tolerating markdown code fences."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)


def _to_summary_fields(extracted: dict) -> SummaryFields:
    """Coerce the model's extraction JSON into the enforced 10-field shape.

    Accepts BOTH reply shapes per key: the bilingual object {"en", "bn"} (current
    prompt) and a plain string (older prompt / model salvage — treated as English).
    ``value`` mirrors ``value_en`` so pre-Session-9 consumers keep working.
    """
    payload: dict = {}
    for key in SUMMARY_FIELD_KEYS:
        value = extracted.get(key, "")
        if isinstance(value, dict):
            en = str(value.get("en") or "").strip()
            bn = str(value.get("bn") or "").strip()
        else:
            en = str(value).strip() if value is not None else ""
            bn = ""
        payload[key] = {"value": en, "value_en": en, "value_bn": bn, "source": "ai"}
    structured = extracted.get("symptom_details_structured") or {}
    if isinstance(structured, dict):
        payload["symptom_details_structured"] = {
            "location": str(structured.get("location") or ""),
            "character": str(structured.get("character") or ""),
            "worse": str(structured.get("worse") or ""),
            "better": str(structured.get("better") or ""),
            "pain_severity_0_10": structured.get("pain_severity_0_10"),
        }
    return SummaryFields.model_validate(payload)


def problem_area(extracted: dict) -> dict | None:
    """F4 — the body/health area the patient came about, as ``{"en", "bn"}``.

    Stored BESIDE ``summary_fields`` in ``case_profiles.entities`` (the same place
    ``suggested_condition`` lives, ADR-0036) rather than inside it: the human's
    decision is that the 10-field contract stays byte-identical, so the area gets its
    own key instead of becoming an 11th field.

    Returns None when the model said nothing usable, so a later extraction that DOES
    find an area cannot be overwritten by an emptier one.
    """
    area = extracted.get("problem_area")
    if not isinstance(area, dict):
        return None
    en = str(area.get("en") or "").strip()
    bn = str(area.get("bn") or "").strip()
    if not (en or bn):
        return None
    return {"en": en, "bn": bn}


_SEX_VALUES = {"male", "female", "other"}


def apply_demographics(db: Session, visit: Visit, extracted: dict) -> None:
    """P2-2: harvest ``patient_demographics`` from an M3/M8 extraction onto the
    patients row — FILL-ONLY-WHEN-EMPTY, so a staff-entered (or earlier) value is
    NEVER overwritten by the AI (the staff PATCH is the correction path).
    Best-effort: absent or malformed data is simply ignored.

    S39 (ADR-0064): every field this writes is now AUDITED. Before, a model could
    put a name into a permanent medical record and leave no trace at all — the row
    simply had a name in it afterwards, indistinguishable from one a human typed and
    with nothing saying which visit it came from. ``actor_id`` stays NULL because
    there is no human actor; that NULL is precisely the fact worth recording. The
    audit row is what ``services/identity.name_provenance`` reads back, so this is a
    provenance trail, not decoration.
    """
    demo = extracted.get("patient_demographics")
    if not isinstance(demo, dict) or visit.patient_id is None:
        return
    patient = db.get(Patient, visit.patient_id)
    if patient is None:
        return
    filled: dict = {}
    name = str(demo.get("name") or "").strip()
    if name and not (patient.display_name or "").strip():
        patient.display_name = name  # exactly as the patient stated it
        filled["display_name"] = name
    sex = str(demo.get("sex") or "").strip().lower()
    if sex in _SEX_VALUES and not (patient.sex or "").strip():
        patient.sex = sex
        filled["sex"] = sex
    age = demo.get("age_years")
    if (
        patient.birth_year is None
        and isinstance(age, (int, float))
        and not isinstance(age, bool)
        and 0 < int(age) < 130
    ):
        patient.birth_year = datetime.now(timezone.utc).year - int(age)
        filled["age_years"] = int(age)
    if filled:
        db.commit()
        audit(
            db,
            action=IDENTITY_AI_FILL_ACTION,
            entity_type="patient",
            entity_id=patient.id,
            actor_id=None,                       # no human wrote this — that is the point
            clinic_id=patient.clinic_id,
            detail={"fields": filled, "visit_uuid": visit.uuid},
        )


def run_intake(db: Session, visit: Visit) -> CaseProfile:
    """M3 -> M4 -> M6 over the visit's conversation; upserts the case_profile.

    Each module call logs its own module_events row (provider/latency/fallback)
    via llm_client. Raises LLMCallError/ValueError upward for the route to map.
    """
    conversation = _conversation_text(db, visit)
    if not conversation.strip():
        raise ValueError("Visit has no utterances yet — nothing to extract.")

    # M3 — structured extraction (Flash-Lite bucket).
    extracted_raw = call_module(
        db, visit_id=visit.id, module_code="M3", system=_EXTRACT_SYSTEM, user=conversation
    )
    extracted = _parse_json(extracted_raw)
    summary_fields = _to_summary_fields(extracted)
    apply_demographics(db, visit, extracted)  # P2-2: name/age/sex -> patients row

    # M4 — chief-complaint summary (Flash bucket).
    summary = call_module(
        db, visit_id=visit.id, module_code="M4", system=_SUMMARY_SYSTEM, user=conversation
    )

    # M6 — present-vs-missing checklist (Groq bucket).
    gaps_user = f"CONVERSATION:\n{conversation}\n\nEXTRACTED FIELDS:\n{extracted_raw}"
    try:
        gaps = _parse_json(
            call_module(db, visit_id=visit.id, module_code="M6", system=_GAPS_SYSTEM, user=gaps_user)
        )
    except json.JSONDecodeError:
        logger.warning("M6 returned non-JSON for visit %s; storing empty gaps", visit.id)
        gaps = {"present": [], "missing": []}

    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    if profile is None:
        profile = CaseProfile(visit_id=visit.id)
        db.add(profile)
    # F4: keep whatever else already lives in entities (suggested_condition, a
    # previously found problem_area) — this used to REPLACE the dict wholesale.
    entities = dict(profile.entities or {})
    entities["summary_fields"] = summary_fields.model_dump(mode="json")
    area = problem_area(extracted)
    if area is not None:                      # never overwrite a found area with none
        entities["problem_area"] = area
    profile.entities = entities
    profile.summary = summary
    profile.gaps = gaps
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile
