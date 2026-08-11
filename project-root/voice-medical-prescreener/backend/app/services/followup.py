"""M7 — dynamic follow-up question generation (Groq bucket, ADR-0026).

Each question targets the highest-priority missing item, avoids repeating anything
already asked (the followup_questions table is the no-repeat memory), and is stored
BOTH as a followup_questions row and as a role='system' utterance so the verbatim
conversation record is complete. The frontend shows the text AND speaks it via TTS
simultaneously (ADR-0028); the patient answers by voice only (ADR-0027).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.models import CaseProfile, FollowupQuestion, Patient, Visit
from backend.app.db.repository_visits import add_utterance
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services.completion import field_has_text
from backend.app.services.intake import _conversation_text, _parse_json
from backend.app.services.llm_client import call_module

logger = logging.getLogger(__name__)

_QUESTION_SYSTEM = (
    "You generate ONE follow-up question for a medical pre-screening conversation in "
    "Bangladesh. The patient answers by voice. You NEVER diagnose and NEVER alarm or "
    "falsely reassure the patient.\n"
    "You are given the conversation, a list of missing data points (may be empty), "
    "and the questions already asked.\n"
    "If any missing data points remain, pick the single most clinically important one "
    "that has NOT been asked about yet and ask about it.\n"
    "A PATIENT CONTEXT block may give the patient's age and the body/health area "
    "they came about. When it does, honor it: keep the question inside that area "
    "unless a missing data point takes you elsewhere, and make it AGE-APPROPRIATE — "
    "never ask an elderly patient about school or adolescent concerns, never ask a "
    "child or teenager about age-related conditions, pregnancy questions only where "
    "they could plausibly apply, and use simpler wording for an elderly patient. "
    "Never mention the patient's age back to them as a reason for the question.\n"
    "If the list is empty, ask ONE short DEEPENING question grounded in what the "
    "patient already said — the clinical detail a doctor would want next (for "
    "example: severity on a 1-10 scale, exact location or spread, what triggers or "
    "relieves it, how it has changed since it started, effect on sleep/eating/daily "
    "activities, similar past episodes, or family history of the same problem). "
    "Never repeat or rephrase an already-asked question.\n"
    "Write the question in BANGLA (Bangla script), followed by the same question in "
    "English in parentheses.\n"
    "Return ONLY a JSON object: {\"target_gap\": \"<the missing item, or a 2-4 word "
    "label for the new detail>\", \"priority\": <1 = most important>, "
    "\"question\": \"<Bangla question> (<English question>)\"}"
)


#: F2 — what each of the 10 canonical fields (``SUMMARY_FIELD_KEYS``) means, in the
#: words M7 needs to write a question about it. Used ONLY by the resume scope, where
#: the server names the field instead of letting the model choose: the key alone
#: ("recent_changes_exposures") is not enough for a good Bangla question.
#: A test pins this to exactly the 10 keys, so a contract change cannot silently
#: leave a field undescribed.
FIELD_PROMPTS: dict[str, str] = {
    "main_problem": "the main problem or chief complaint that brought them in today",
    "onset_duration": "when the problem started and how long it has lasted",
    "symptom_details": (
        "the symptom itself in detail — where it is, what it feels like, and what "
        "makes it better or worse"
    ),
    "associated_symptoms": "any OTHER symptoms happening alongside the main problem",
    "medical_history": "past or ongoing medical conditions they have",
    "current_medicines": "medicines they are taking at the moment",
    "allergies": "allergies to any medicine, food or anything else",
    "recent_changes_exposures": (
        "recent changes or exposures — travel, unusual food, a new medicine, contact "
        "with someone ill, or a change at work or home"
    ),
    "treatments_tried": "what they have already tried for this problem",
    "current_concern": "what worries them most, or what they want to ask the doctor",
}


def unanswered_question(db: Session, *, visit_id: int) -> FollowupQuestion | None:
    """The currently open (asked, not yet answered) question, if any."""
    return (
        db.query(FollowupQuestion)
        .filter(FollowupQuestion.visit_id == visit_id, FollowupQuestion.answered_at.is_(None))
        .order_by(FollowupQuestion.asked_at.desc())
        .first()
    )


def questions_asked(db: Session, *, visit_id: int) -> list[FollowupQuestion]:
    return (
        db.query(FollowupQuestion)
        .filter(FollowupQuestion.visit_id == visit_id)
        .order_by(FollowupQuestion.asked_at)
        .all()
    )


def patient_context(db: Session, visit: Visit, profile: CaseProfile) -> str:
    """F4 — the age + area block handed to M7, or '' when nothing is known.

    Age comes from the patients row (filled by ``apply_demographics`` from what the
    patient themselves said, never guessed) and the area from
    ``entities["problem_area"]``. Both are what make questions age-appropriate and
    on-topic instead of a generic questionnaire.

    Returns '' rather than a block of empty labels when nothing is known — an empty
    "Age:" line invites the model to invent one.
    """
    bits: list[str] = []
    patient = db.get(Patient, visit.patient_id) if visit.patient_id else None
    if patient is not None and patient.birth_year:
        age = datetime.now(timezone.utc).year - patient.birth_year
        if 0 < age < 130:
            bits.append(f"Age: {age} years")
        if patient.sex:
            bits.append(f"Sex: {patient.sex}")
    area = (profile.entities or {}).get("problem_area") or {}
    area_text = str(area.get("en") or area.get("bn") or "").strip()
    if area_text:
        bits.append(f"Area the patient came about: {area_text}")
    if not bits:
        return ""
    return "PATIENT CONTEXT:\n" + "\n".join(bits) + "\n\n"


def missing_summary_fields(profile: CaseProfile) -> list[str]:
    """The keys (of the fixed 10 summary fields) still empty in EVERY language slot —
    the KIOSK-7 resume loop's checklist."""
    fields = ((profile.entities or {}).get("summary_fields")) or {}
    return [k for k in SUMMARY_FIELD_KEYS if not field_has_text(fields.get(k))]


def generate_next_question(
    db: Session, visit: Visit, profile: CaseProfile, *, missing: list[str] | None = None
) -> FollowupQuestion | None:
    """Ask M7 for the next question, or return None when the loop should stop
    (max turns reached; or — in the fields scope only — nothing left to ask).
    In the MAIN loop an exhausted gap list switches M7 to DEEPENING questions
    (P1-3) instead of stopping. Re-serves an open unanswered question instead
    of generating a duplicate.

    ``missing`` overrides the M6 gap list (KIOSK-7 resume scope passes the empty
    summary-field keys). The per-visit question cap is SHARED across both scopes,
    and the no-repeat memory (target_gap of already-asked questions) is what makes
    a "নেই / No / জানি না" answer count as answered: the field may stay empty, but
    it is never asked again.
    """
    settings = get_settings()

    open_q = unanswered_question(db, visit_id=visit.id)
    if open_q is not None:
        return open_q

    fields_scope = missing is not None
    asked = questions_asked(db, visit_id=visit.id)
    # F3: the resume loop gets its OWN budget on TOP of the main loop's. The two used
    # to share one cap of 5, which the main loop's 4-5 questions consumed entirely —
    # so the resume loop had nothing left to ask and the patient reached the review
    # page with required fields still empty and no way to fill them. Both remain hard
    # caps: the loop ends because the budget ends, never because the patient gave up
    # (M9 guardrail, and the "never trap the patient" fail-safe below).
    cap = settings.followup_max_questions
    if fields_scope:
        cap += settings.followup_resume_max_questions
    if len(asked) >= cap:
        return None  # turn limit — avoid patient fatigue (M9 guardrail)

    if missing is None:
        missing = list((profile.gaps or {}).get("missing") or [])
    asked_gaps = {q.target_gap for q in asked if q.target_gap}
    remaining = [m for m in missing if m not in asked_gaps]
    if not remaining and fields_scope:
        return None  # resume loop: every empty field was asked once — stop
    # P1-3: in the MAIN loop an empty gap list no longer stops the conversation —
    # M7 asks a history-grounded DEEPENING question instead (the route's min/cap
    # gates decide when the loop actually ends).

    # F2: in the RESUME scope the SERVER names the field; the model does not choose it.
    # Before, M7 picked, and its `target_gap` was trusted to echo an exact field key
    # back. When it didn't (a label, different case, a phrase), the code silently
    # recorded the question against `remaining[0]` instead — so the field actually
    # ASKED about stayed "unasked" and got asked again, while a field nobody had asked
    # was marked answered and never revisited. That is the question/answer mismatch.
    # Naming the field up front makes the pairing true by construction.
    target_key = remaining[0] if fields_scope else None

    field_directive = ""
    if target_key is not None:
        field_directive = (
            f"ASK ABOUT EXACTLY THIS ONE FIELD, nothing else: {target_key} — "
            f"{FIELD_PROMPTS.get(target_key, target_key)}\n\n"
        )
    user = (
        f"{patient_context(db, visit, profile)}"
        f"CONVERSATION:\n{_conversation_text(db, visit)}\n\n"
        f"{field_directive}"
        f"MISSING DATA POINTS:\n{json.dumps(remaining, ensure_ascii=False)}\n\n"
        f"ALREADY ASKED (do not repeat):\n"
        f"{json.dumps([q.question_text for q in asked], ensure_ascii=False)}"
    )
    reply = call_module(
        db, visit_id=visit.id, module_code="M7", system=_QUESTION_SYSTEM, user=user
    )
    fallback_gap = remaining[0] if remaining else "deepening detail"  # P1-3: may be empty
    try:
        data = _parse_json(reply)
        question_text = str(data["question"]).strip()
        target_gap = str(data.get("target_gap") or fallback_gap)
        priority = int(data.get("priority") or 1)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # Salvage: use the raw reply as the question rather than losing the turn.
        logger.warning("M7 returned non-JSON for visit %s; using raw text", visit.id)
        question_text, target_gap, priority = reply.strip(), fallback_gap, 1

    if target_key is not None:
        # The field we ASKED the model to cover is the field we record — always, and
        # on the JSON-salvage path too. Whatever the model echoed back is ignored.
        target_gap = target_key

    question = FollowupQuestion(
        visit_id=visit.id, target_gap=target_gap, question_text=question_text, priority=priority
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    # Keep the verbatim record complete: the spoken question is a system utterance.
    add_utterance(
        db, visit_id=visit.id, raw_text=question_text, role="system", source="tts",
        stt_provider=None,
    )
    return question
