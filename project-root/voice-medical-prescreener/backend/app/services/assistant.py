"""M16 — the doctor-side AI clinical-information assistant (P3-3, broadened in S38/B6).

Web search (ddgs/DuckDuckGo — free, no key) + ONE LLM call on the Flash bucket,
answering the DOCTOR's question from the fetched snippets. Informational only
(rule #2): the MANDATORY disclaimer is attached SERVER-SIDE on every answer — never
trusted to the model — and the prompt forbids patient-specific prescribing decisions.

--------------------------------------------------------------------------------
S38 (B6) — WHAT WIDENED, AND WHAT DID NOT
--------------------------------------------------------------------------------

The module answered drug questions only. It now covers three things, on the SAME
service, the SAME seam and the SAME single round-trip (the brief: *"Do not create a
second AI service if the existing one can be extended"*):

  1. **Drugs** — what it is used for, typical dosing context, age-related
     considerations, who should avoid it or use caution, common adverse reactions,
     important contraindications and precautions.
  2. **Diagnostic tests** — what the test is, why it is used, what it measures, and
     the preparation or sample conditions that make the result mean anything.
  3. **Patient-specific TEST suggestions** — "what test might be useful for this
     patient?", answered against this visit's own clinical picture.

⚠ Only the third one may see patient data, and only when the doctor explicitly asks for
it (``use_case_context``). Everything about that path is deliberately narrow:

  * **The web search NEVER receives patient data.** :func:`_search` is called with the
    doctor's typed question and nothing else, always — a structural guarantee, not a
    prompt instruction, because DuckDuckGo is a third party (rule #4). A test pins it.
  * **The context is DE-IDENTIFIED.** It reuses the existing
    ``question_tools.get_patient_context`` (age, sex, body area — the minimum that
    module already justified) plus the derived 10-field summary. No name, no phone, no
    visit id, and **no raw transcript** — the patient's own words are not shipped to a
    model for a doctor's convenience question.
  * **It is off by default.** A doctor asking "what is metformin?" sends no patient data
    at all.

--------------------------------------------------------------------------------
WHAT IT STILL CANNOT DO
--------------------------------------------------------------------------------

It never diagnoses, never prescribes, and never ORDERS anything. Suggested tests come
back as a plain list the doctor may click to insert into the Required Tests field they
are writing — the order exists only once a human generates a prescription. The
:func:`unsafe_answer_reason` guard checks the model's output on the way out for
patient-directed prescribing or diagnosis, and when it fires the answer is delivered
with a STRONGER server-authored warning rather than silently.

⚠ That guard is HIGH-PRECISION / LOW-RECALL, exactly like ``question_tools``' one, and
for the opposite reason: here a dosage range **is the correct answer** ("500 mg every
6 hours" is what a drug-information tool exists to say), so it must NOT reuse M7's
dosage rule. It catches patient-DIRECTED instructions and assertions only.
"""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy.orm import Session

from backend.app.db.models import CaseProfile, Visit
from backend.app.services.intake import _parse_json
from backend.app.services.llm_client import call_module

logger = logging.getLogger(__name__)

ASSISTANT_DISCLAIMER = "AI-generated information. Please verify before prescribing."
ASSISTANT_DISCLAIMER_BN = "এআই-উৎপাদিত তথ্য। প্রেসক্রাইব করার আগে অনুগ্রহ করে যাচাই করুন।"

#: Swapped in when :func:`unsafe_answer_reason` fires. The answer is still delivered —
#: deleting it would hide from the doctor what the model actually said — but the
#: framing is corrected by the server, which the model cannot talk its way out of.
ASSISTANT_FLAGGED_DISCLAIMER = (
    "⚠ This reply reads like a patient-specific instruction. This assistant provides "
    "INFORMATION ONLY — it does not diagnose, prescribe, or decide anything for a "
    "patient. Treat the content as reference material and verify it."
)
ASSISTANT_FLAGGED_DISCLAIMER_BN = (
    "⚠ এই উত্তরটি নির্দিষ্ট রোগীর জন্য নির্দেশের মতো শোনাচ্ছে। এই সহকারী শুধু তথ্য দেয় — "
    "রোগনির্ণয়, প্রেসক্রিপশন বা রোগীর জন্য কোনো সিদ্ধান্ত নেয় না। তথ্যটি রেফারেন্স হিসেবে "
    "দেখুন এবং যাচাই করুন।"
)

_MAX_RESULTS = 5
_SNIPPET_CHARS = 400  # per-result cap keeps the prompt small (quota discipline)

#: How many suggested tests are carried back. A list longer than this stops being a
#: suggestion and starts being a shotgun panel, which is the opposite of useful.
MAX_SUGGESTED_TESTS = 8

#: Longest single collected field included in the case context.
_CONTEXT_VALUE_CHARS = 160

_ANSWER_SYSTEM = (
    "You are a clinical information assistant for a licensed physician in Bangladesh. "
    "You answer questions in three areas and nothing else:\n"
    "(1) MEDICINES — what a drug is used for, typical adult and paediatric dosing "
    "ranges, age-related considerations, who should avoid it or use caution, common "
    "side effects and allergies, important contraindications, interactions and "
    "monitoring/precautions;\n"
    "(2) DIAGNOSTIC TESTS — what a test is, why it is used, what it measures, and any "
    "preparation or sample conditions needed for the result to be interpretable;\n"
    "(3) WHICH TESTS MIGHT BE USEFUL for the patient described in PATIENT CONTEXT, "
    "when the doctor asks that.\n\n"
    "Use the WEB SEARCH RESULTS provided, falling back to established clinical "
    "knowledge when they are thin. You provide INFORMATION ONLY: never state or imply "
    "a diagnosis for the patient, never tell the doctor what to prescribe for this "
    "patient, and never say a test has been ordered — you are describing options, and "
    "the physician decides. Dosing RANGES and standard indications are information and "
    "are expected; instructions aimed at this specific patient are not. If the question "
    "is outside those three areas, say that you only answer medicine and diagnostic-test "
    "questions.\n\n"
    "Return ONLY a JSON object with these keys and no others:\n"
    '{"answer_en": "<concise answer in English, plain sentences>", '
    '"answer_bn": "<the same answer in Bangla script>", '
    '"suggested_tests": ["<test name>", ...]}\n'
    "suggested_tests must be an empty list unless the doctor asked which tests could be "
    "useful; when present, list only the test names, in English, with no reasoning."
)


def _search(question: str) -> list[dict]:
    """Top DuckDuckGo hits for the doctor's question — {title, url, snippet} each.

    ⚠ Takes the QUESTION and nothing else, by signature. Patient context is never a
    parameter here, so no future edit can accidentally send clinical data to a third
    party (rule #4). A test asserts this property.

    Best-effort: any failure (offline dev box, rate limit, API change) returns []
    so the assistant degrades to general-knowledge answers instead of erroring.
    """
    try:
        from ddgs import DDGS

        raw = DDGS().text(question, max_results=_MAX_RESULTS) or []
    except Exception as exc:  # noqa: BLE001 — search is optional by design
        logger.warning("M16 web search unavailable: %s", exc)
        return []
    results = []
    for r in raw:
        title = str(r.get("title") or "").strip()
        url = str(r.get("href") or "").strip()
        snippet = str(r.get("body") or "").strip()[:_SNIPPET_CHARS]
        if title or snippet:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


def build_case_context(db: Session, visit: Visit) -> str:
    """A DE-IDENTIFIED description of this visit, for a test-suggestion question.

    Reuses ``question_tools.get_patient_context`` (age / sex / body area) rather than
    assembling a second one: S35's lesson, restated in ADR-0057 — two context builders
    are two things that can disagree, one of them silently.

    Deliberately ABSENT: name, phone, patient id, visit id, and the raw transcript. A
    convenience question from a doctor is not a reason to ship a patient's own words to
    a model (rule #4); the derived 10-field summary carries the clinical picture that
    the question actually needs.

    Returns "" when there is nothing usable, so the caller sends no context block at
    all rather than an empty labelled one that invites the model to fill it in.
    """
    from backend.app.services.completion import field_has_text
    from backend.app.services.question_tools import get_patient_context
    from backend.app.schemas.profile import SUMMARY_FIELD_KEYS

    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    if profile is None:
        return ""

    identity = get_patient_context(db, visit, profile)
    lines: list[str] = []
    if identity.get("age_years"):
        lines.append(f"Age: {identity['age_years']} years")
    if identity.get("sex"):
        lines.append(f"Sex: {identity['sex']}")
    if identity.get("area"):
        lines.append(f"Body area: {identity['area']}")

    from backend.app.db.models import Patient

    patient = db.get(Patient, visit.patient_id) if visit.patient_id else None
    if patient is not None:
        # Vitals are clinically relevant to a test question (renal dosing, BP work-up)
        # and identify nobody on their own.
        if patient.weight_kg is not None:
            lines.append(f"Weight: {patient.weight_kg} kg")
        if patient.height_cm is not None:
            lines.append(f"Height: {patient.height_cm} cm")
        if (patient.bp or "").strip():
            lines.append(f"Blood pressure: {patient.bp}")

    fields = (profile.entities or {}).get("summary_fields") or {}
    for key in SUMMARY_FIELD_KEYS:
        field = fields.get(key)
        if not field_has_text(field):
            continue
        for slot in ("value_en", "value", "value_bn"):
            value = str((field or {}).get(slot) or "").strip()
            if value:
                lines.append(f"{key.replace('_', ' ')}: {value[:_CONTEXT_VALUE_CHARS]}")
                break

    return "\n".join(lines)


# --- the output guard ---------------------------------------------------------
#
# ⚠ Scope, stated honestly: HIGH PRECISION, LOW RECALL. It catches replies that address
# THIS PATIENT with an instruction or an assertion. It is not a medical-safety
# classifier, and rule #2 rests on the whole design — no diagnosis is ever requested,
# stored or displayed as one — not on this function.
#
# ⚠ It deliberately does NOT reuse ``question_tools.unsafe_question_reason``. That guard
# bans dosage amounts, because a follow-up QUESTION never needs to state one. Here a
# dosage range is the correct answer to the most common question this module receives,
# so reusing it would delete the module's entire purpose.

_PATIENT_DIRECTED = (
    # prescribing FOR this patient
    "prescribe this patient", "prescribe for this patient", "give this patient",
    "start this patient on", "you should prescribe", "i recommend prescribing",
    "this patient should take", "the patient should take", "put the patient on",
    "i have ordered", "i have prescribed", "order this test for the patient",
    # diagnosing this patient
    "this patient has", "the patient has been diagnosed", "the diagnosis is",
    "this patient is suffering from", "the patient clearly has",
    "confirms the diagnosis of", "diagnostic of",
)


def unsafe_answer_reason(text: str) -> str | None:
    """Why this answer must be delivered with a stronger warning, or None.

    Returns a short machine-ish reason so a flag is never silent — a guard nobody can
    see fire is a guard nobody discovers is misfiring.
    """
    lowered = str(text or "").lower()
    for phrase in _PATIENT_DIRECTED:
        if phrase in lowered:
            return f"patient_directed:{phrase}"
    return None


def _clean_suggested_tests(value) -> list[str]:
    """Whatever the model returned, as a bounded list of plain test names.

    Defensive because ``suggested_tests`` is free-form model output: a string, a list of
    dicts, or nonsense must all degrade to a usable (possibly empty) list rather than
    raising inside a doctor's request.
    """
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    names: list[str] = []
    seen: set[str] = set()
    for entry in value:
        name = str(entry.get("name") if isinstance(entry, dict) else entry or "").strip()
        # A "suggestion" that is a paragraph is the model explaining rather than naming.
        if not name or len(name) > 120:
            continue
        name = re.sub(r"^[\-\*\d\.\)\s]+", "", name).strip()
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            names.append(name)
    return names[:MAX_SUGGESTED_TESTS]


def answer_drug_question(
    db: Session,
    visit: Visit,
    question: str,
    language: str = "en",
    *,
    use_case_context: bool = False,
) -> dict:
    """One M16 round-trip: search -> LLM -> answer dict with the disclaimer.

    ``use_case_context`` is the doctor's EXPLICIT opt-in to include this visit's
    de-identified clinical picture (S38/B6). Default False: a general drug question
    sends no patient data anywhere.

    Raises LLMCallError when the whole provider chain fails (route -> 502).
    """
    # ⚠ The question ONLY. Patient context must never reach a third-party search.
    sources = _search(question)
    if sources:
        blocks = [
            f"[{i + 1}] {s['title']}\n{s['url']}\n{s['snippet']}"
            for i, s in enumerate(sources)
        ]
        context = "WEB SEARCH RESULTS:\n\n" + "\n\n".join(blocks)
    else:
        context = "WEB SEARCH RESULTS: (search unavailable — answer from established knowledge)"

    parts = [f"DOCTOR'S QUESTION:\n{question}", context]
    if use_case_context:
        case = build_case_context(db, visit)
        if case:
            parts.insert(1, "PATIENT CONTEXT (de-identified — no name or contact details):\n" + case)
    user = "\n\n".join(parts)

    reply = call_module(db, visit_id=visit.id, module_code="M16",
                        system=_ANSWER_SYSTEM, user=user)
    suggested: list[str] = []
    try:
        data = _parse_json(reply)
        answer_en = str(data.get("answer_en") or "").strip()
        answer_bn = str(data.get("answer_bn") or "").strip()
        suggested = _clean_suggested_tests(data.get("suggested_tests"))
    except (json.JSONDecodeError, AttributeError):
        # Salvage a non-JSON reply as the English answer rather than failing the doctor.
        answer_en, answer_bn = reply.strip(), ""

    flagged = unsafe_answer_reason(f"{answer_en}\n{answer_bn}")
    if flagged:
        logger.warning("M16 answer flagged for visit %s: %s", visit.uuid, flagged)

    return {
        "answer_en": answer_en,
        "answer_bn": answer_bn,
        "sources": sources,
        "suggested_tests": suggested,
        # Rule #2: attached HERE on every response — never left to the model.
        "disclaimer": ASSISTANT_FLAGGED_DISCLAIMER if flagged else ASSISTANT_DISCLAIMER,
        "disclaimer_bn": ASSISTANT_FLAGGED_DISCLAIMER_BN if flagged else ASSISTANT_DISCLAIMER_BN,
        "flagged_reason": flagged,
        "used_case_context": bool(use_case_context),
    }
