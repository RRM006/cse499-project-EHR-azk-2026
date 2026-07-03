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

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.models import CaseProfile, FollowupQuestion, Visit
from backend.app.db.repository_visits import add_utterance
from backend.app.services.intake import _conversation_text, _parse_json
from backend.app.services.llm_client import call_module

logger = logging.getLogger(__name__)

_QUESTION_SYSTEM = (
    "You generate ONE follow-up question for a medical pre-screening conversation in "
    "Bangladesh. The patient answers by voice. You NEVER diagnose and NEVER alarm or "
    "falsely reassure the patient.\n"
    "You are given the conversation, the list of missing data points, and the "
    "questions already asked. Pick the single most clinically important missing item "
    "that has NOT been asked about yet, and write one short, conversational question "
    "in BANGLA (Bangla script), followed by the same question in English in "
    "parentheses.\n"
    "Return ONLY a JSON object: {\"target_gap\": \"<the missing item you chose>\", "
    "\"priority\": <1 = most important>, "
    "\"question\": \"<Bangla question> (<English question>)\"}"
)


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


def generate_next_question(
    db: Session, visit: Visit, profile: CaseProfile
) -> FollowupQuestion | None:
    """Ask M7 for the next question, or return None when the loop should stop
    (max turns reached, or nothing left to ask). Re-serves an open unanswered
    question instead of generating a duplicate.
    """
    settings = get_settings()

    open_q = unanswered_question(db, visit_id=visit.id)
    if open_q is not None:
        return open_q

    asked = questions_asked(db, visit_id=visit.id)
    if len(asked) >= settings.followup_max_questions:
        return None  # turn limit — avoid patient fatigue (M9 guardrail)

    missing = list((profile.gaps or {}).get("missing") or [])
    asked_gaps = {q.target_gap for q in asked if q.target_gap}
    remaining = [m for m in missing if m not in asked_gaps]
    if not remaining:
        return None  # nothing left to ask

    user = (
        f"CONVERSATION:\n{_conversation_text(db, visit)}\n\n"
        f"MISSING DATA POINTS:\n{json.dumps(remaining, ensure_ascii=False)}\n\n"
        f"ALREADY ASKED (do not repeat):\n"
        f"{json.dumps([q.question_text for q in asked], ensure_ascii=False)}"
    )
    reply = call_module(
        db, visit_id=visit.id, module_code="M7", system=_QUESTION_SYSTEM, user=user
    )
    try:
        data = _parse_json(reply)
        question_text = str(data["question"]).strip()
        target_gap = str(data.get("target_gap") or remaining[0])
        priority = int(data.get("priority") or 1)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # Salvage: use the raw reply as the question rather than losing the turn.
        logger.warning("M7 returned non-JSON for visit %s; using raw text", visit.id)
        question_text, target_gap, priority = reply.strip(), remaining[0], 1

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
