"""P3-3: the doctor portal's AI clinical-information assistant (module M16).

POST /api/visits/{uuid}/assistant/drug-info — visit-scoped so every call lands in
module_events against the case the doctor is reviewing (visit_id is NOT NULL
there, and the audit linkage is wanted anyway). Doctor-triggered only; the reply
always carries a server-attached disclaimer (rule #2 — informational, never a
prescribing decision).

S38 (B6): the assistant now covers medicines, diagnostic tests, and — only on the
doctor's explicit ``use_case_context`` opt-in — which tests might be useful for the
patient in front of them. The PATH is unchanged on purpose: one endpoint, one seam,
one round-trip. Its name is kept for compatibility with the shipped portal.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import repository_visits as repo
from backend.app.db.database import get_db
from backend.app.schemas.assistant import DrugInfoOut, DrugInfoRequest
from backend.app.services.assistant import answer_drug_question
from backend.app.services.llm_client import LLMCallError

router = APIRouter(prefix="/api", tags=["assistant"])


@router.post("/visits/{visit_uuid}/assistant/drug-info", response_model=DrugInfoOut)
def drug_info(
    visit_uuid: str, payload: DrugInfoRequest, db: Session = Depends(get_db)
) -> DrugInfoOut:
    visit = repo.get_visit_by_uuid(db, visit_uuid)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_uuid} not found")
    try:
        return DrugInfoOut(**answer_drug_question(
            db, visit, payload.question, use_case_context=payload.use_case_context
        ))
    except LLMCallError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
