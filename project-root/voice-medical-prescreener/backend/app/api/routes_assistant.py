"""P3-3: the doctor portal's AI drug-information assistant (module M16).

POST /api/visits/{uuid}/assistant/drug-info — visit-scoped so every call lands in
module_events against the case the doctor is reviewing (visit_id is NOT NULL
there, and the audit linkage is wanted anyway). Doctor-triggered only; the reply
always carries the server-attached "verify before prescribing" disclaimer
(rule #2 — informational, never a prescribing decision).
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
        return DrugInfoOut(**answer_drug_question(db, visit, payload.question))
    except LLMCallError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
