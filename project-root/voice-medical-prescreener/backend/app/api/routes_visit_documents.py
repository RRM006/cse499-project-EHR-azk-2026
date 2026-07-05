"""Visit-grain document exports (rev 0010, ADR-0032).

POST /api/visits/{uuid}/documents/{kind} — generate + store a visit-level .docx:
  * kind "transcript"      — the full RAW conversation, verbatim (KIOSK-4, rule #1);
  * kind "summary_report"  — the staff pre-screening summary from the stored M12
                             report (MEDIC-7); generated locally, no API call.
Download reuses the existing GET /api/documents/{id}/download.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import repository_visits as repo
from backend.app.db.database import get_db
from backend.app.schemas.document import DocumentOut
from backend.app.services.documents import VISIT_DOCUMENT_KINDS, generate_visit_document

router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/visits/{visit_uuid}/documents/{kind}", response_model=DocumentOut)
def create_visit_document(
    visit_uuid: str, kind: str, db: Session = Depends(get_db)
) -> DocumentOut:
    if kind not in VISIT_DOCUMENT_KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown document kind '{kind}'. Expected one of: "
            f"{', '.join(VISIT_DOCUMENT_KINDS)}.",
        )
    visit = repo.get_visit_by_uuid(db, visit_uuid)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_uuid} not found")
    return generate_visit_document(db, visit, kind=kind)
