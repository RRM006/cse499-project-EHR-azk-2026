"""Follow-up loop routes (BE-3): M7 question -> voice answer -> M8 merge -> M9 check.

POST /api/visits/{uuid}/followup/next    — next prioritized question (text; the
                                           frontend also speaks it via TTS).
POST /api/visits/{uuid}/followup/answer  — accept the voice answer, update the
                                           profile, return {complete, next?}.

Both accept ?scope=fields (KIOSK-7 resume loop on the kiosk summary screen): the
0.7-threshold gate does NOT apply — "complete" then means every one of the 10
summary fields carries text, the shared question cap was reached, or every empty
field has already been asked once ("নেই / জানি না" counts as answered).

P1-3 (2.0 build): the MAIN loop additionally has a question FLOOR — it is not
"complete" until at least `followup_min_questions` (4) were asked, even when the
completeness threshold is already met; when the M6 gap list runs out, M7 asks
history-grounded DEEPENING questions instead. The cap (5) still always wins.
The `scope=fields` resume loop is unaffected by the floor.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db import repository_visits as repo
from backend.app.db.database import get_db
from backend.app.db.models import CaseProfile, FollowupQuestion, Visit
from backend.app.schemas.followup import AnswerOut, AnswerRequest, NextQuestionOut
from backend.app.services.completion import completeness_score
from backend.app.services.followup import generate_next_question, missing_summary_fields
from backend.app.services.llm_client import LLMCallError
from backend.app.services.profile_update import process_answer

router = APIRouter(prefix="/api", tags=["followup"])


def _visit_and_profile(db: Session, visit_uuid: str) -> tuple[Visit, CaseProfile]:
    visit = repo.get_visit_by_uuid(db, visit_uuid)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_uuid} not found")
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    if profile is None:
        raise HTTPException(status_code=400, detail="No profile yet — run intake first.")
    return visit, profile


def _loop_state(db: Session, visit: Visit, profile: CaseProfile) -> tuple[float, bool]:
    """(score, complete?) for the MAIN loop. P1-3: completeness alone is no longer
    enough — the patient must also have been asked >= followup_min_questions, so the
    doctor always gets 4–5 answers' worth of history. The cap exit (generator
    returning None) is handled by the callers."""
    settings = get_settings()
    score = completeness_score(profile)
    asked_count = (
        db.query(FollowupQuestion).filter(FollowupQuestion.visit_id == visit.id).count()
    )
    complete = (
        score >= settings.completeness_threshold
        and asked_count >= settings.followup_min_questions
    )
    return score, complete


def _fields_scope_step(
    db: Session, visit: Visit, profile: CaseProfile
) -> tuple[bool, float, FollowupQuestion | None]:
    """One resume-loop step: (complete, score, question). Complete when all 10
    fields are filled, or the generator stops (shared cap / everything asked)."""
    score = completeness_score(profile)
    missing = missing_summary_fields(profile)
    if not missing:
        return True, score, None
    try:
        question = generate_next_question(db, visit, profile, missing=missing)
    except LLMCallError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return question is None, score, question


@router.post("/visits/{visit_uuid}/followup/next", response_model=NextQuestionOut)
def next_question(
    visit_uuid: str,
    scope: Literal["fields"] | None = None,
    db: Session = Depends(get_db),
) -> NextQuestionOut:
    visit, profile = _visit_and_profile(db, visit_uuid)
    if scope == "fields":  # KIOSK-7 resume loop — no threshold gate
        complete, score, question = _fields_scope_step(db, visit, profile)
        return NextQuestionOut(complete=complete, completeness_score=score, question=question)
    score, loop_complete = _loop_state(db, visit, profile)
    if loop_complete:
        return NextQuestionOut(complete=True, completeness_score=score)
    try:
        question = generate_next_question(db, visit, profile)
    except LLMCallError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if question is None:  # max turns reached or nothing left to ask
        return NextQuestionOut(complete=True, completeness_score=score)
    return NextQuestionOut(complete=False, completeness_score=score, question=question)


@router.post("/visits/{visit_uuid}/followup/answer", response_model=AnswerOut)
def answer_question(
    visit_uuid: str,
    payload: AnswerRequest,
    scope: Literal["fields"] | None = None,
    db: Session = Depends(get_db),
) -> AnswerOut:
    visit, _ = _visit_and_profile(db, visit_uuid)
    if visit.status != "in_progress":
        raise HTTPException(
            status_code=409,
            detail=f"Visit is '{visit.status}' — answers can only be added while in_progress.",
        )
    question = db.get(FollowupQuestion, payload.question_id)
    if question is None or question.visit_id != visit.id:
        raise HTTPException(status_code=404, detail=f"Question {payload.question_id} not found for this visit")
    if question.answered_at is not None:
        raise HTTPException(status_code=409, detail="Question already answered.")

    # The answer IS an utterance — verbatim, write-once (rule #1, ADR-0027).
    answer = repo.add_utterance(
        db, visit_id=visit.id, raw_text=payload.raw_text,
        role="patient", source=payload.source, stt_provider=payload.stt_provider,
    )
    try:
        profile = process_answer(db, visit=visit, question=question, answer=answer)
    except LLMCallError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if scope == "fields":  # KIOSK-7 resume loop — no threshold gate
        complete, score, next_q = _fields_scope_step(db, visit, profile)
        return AnswerOut(complete=complete, completeness_score=score, next_question=next_q)

    score, loop_complete = _loop_state(db, visit, profile)
    if loop_complete:
        return AnswerOut(complete=True, completeness_score=score)
    try:
        next_q = generate_next_question(db, visit, profile)
    except LLMCallError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if next_q is None:
        return AnswerOut(complete=True, completeness_score=score)
    return AnswerOut(complete=False, completeness_score=score, next_question=next_q)
