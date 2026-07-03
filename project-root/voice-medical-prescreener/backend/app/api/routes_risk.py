"""Risk routes (BE-4): M10 assessment (rule-forced critical) + M11 explanation.

POST /api/visits/{uuid}/assess — append a new assessment (rule + model).
GET  /api/visits/{uuid}/risk   — latest assessment + its stored reason.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import repository_visits as repo
from backend.app.db.database import get_db
from backend.app.db.models import CaseProfile, Visit, XaiExplanation
from backend.app.schemas.risk import RiskDetailOut, XaiOut
from backend.app.services.risk import assess_visit, latest_assessment

router = APIRouter(prefix="/api", tags=["risk"])


def _get_visit_or_404(db: Session, visit_uuid: str) -> Visit:
    visit = repo.get_visit_by_uuid(db, visit_uuid)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_uuid} not found")
    return visit


def _to_detail(db: Session, assessment) -> RiskDetailOut:
    xai = (
        db.query(XaiExplanation)
        .filter(XaiExplanation.risk_assessment_id == assessment.id)
        .first()
    )
    detail = RiskDetailOut.model_validate(assessment)
    detail.explanation = XaiOut.model_validate(xai) if xai else None
    return detail


@router.post("/visits/{visit_uuid}/assess", response_model=RiskDetailOut)
def assess(visit_uuid: str, db: Session = Depends(get_db)) -> RiskDetailOut:
    """Run M10 + M11. The local red-flag rule ALWAYS runs and forces 'critical';
    a model failure degrades to tier 'medium' (never silently low), so this
    endpoint succeeds whenever the visit has any patient speech to assess."""
    visit = _get_visit_or_404(db, visit_uuid)
    utterances = repo.list_visit_utterances(db, visit_id=visit.id)
    if not any(u.role == "patient" for u in utterances):
        raise HTTPException(status_code=400, detail="Visit has no patient utterances to assess.")
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    assessment = assess_visit(db, visit, profile)
    return _to_detail(db, assessment)


@router.get("/visits/{visit_uuid}/risk", response_model=RiskDetailOut)
def get_risk(visit_uuid: str, db: Session = Depends(get_db)) -> RiskDetailOut:
    visit = _get_visit_or_404(db, visit_uuid)
    assessment = latest_assessment(db, visit_id=visit.id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="No risk assessment yet — run /assess first.")
    return _to_detail(db, assessment)
