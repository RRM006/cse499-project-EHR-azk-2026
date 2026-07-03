"""Report + doctor-review + feedback routes (BE-6).

POST /api/visits/{uuid}/report   — M12: assemble/refresh the structured report.
GET  /api/visits/{uuid}/report   — latest report (JSON sections).
POST /api/visits/{uuid}/review   — M14: doctor accept / override -> 'reviewed'.
POST /api/visits/{uuid}/feedback — M15: rating + correctness signal.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.app.db import repository_visits as repo
from backend.app.db.database import get_db
from backend.app.db.models import DoctorReview, Feedback, User, Visit
from backend.app.services.audit import audit
from backend.app.services.report import generate_report, latest_report
from backend.app.services.risk import TIERS

router = APIRouter(prefix="/api", tags=["report"])


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    risk_assessment_id: int | None
    sections: dict | None
    created_at: datetime


class ReviewRequest(BaseModel):
    reviewer_id: int = Field(..., description="users.id of the doctor (auth is stubbed).")
    override_tier: str | None = Field(
        None, description="Set to override the AI tier (e.g. 'low' for Override to Low-Risk)."
    )
    disposition: str | None = Field(None, description="e.g. 'accept', 'refer', 'routine'.")
    notes: str | None = None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    reviewer_id: int
    override_tier: str | None
    disposition: str | None
    notes: str | None
    created_at: datetime


class FeedbackRequest(BaseModel):
    author_id: int
    rating: int | None = Field(None, ge=1, le=5)
    correct: bool | None = None
    comment: str | None = None


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    author_id: int
    rating: int | None
    correct: bool | None
    comment: str | None
    created_at: datetime


def _get_visit_or_404(db: Session, visit_uuid: str) -> Visit:
    visit = repo.get_visit_by_uuid(db, visit_uuid)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_uuid} not found")
    return visit


@router.post("/visits/{visit_uuid}/report", response_model=ReportOut)
def create_report(visit_uuid: str, db: Session = Depends(get_db)) -> ReportOut:
    visit = _get_visit_or_404(db, visit_uuid)
    if not any(u.role == "patient" for u in repo.list_visit_utterances(db, visit_id=visit.id)):
        raise HTTPException(status_code=400, detail="Visit has no patient speech — nothing to report.")
    report = generate_report(db, visit)
    audit(db, action="report.generate", entity_type="report", entity_id=report.id,
          clinic_id=visit.clinic_id, detail={"visit_uuid": visit.uuid})
    return report


@router.get("/visits/{visit_uuid}/report", response_model=ReportOut)
def get_report(visit_uuid: str, db: Session = Depends(get_db)) -> ReportOut:
    visit = _get_visit_or_404(db, visit_uuid)
    report = latest_report(db, visit_id=visit.id)
    if report is None:
        raise HTTPException(status_code=404, detail="No report yet — POST /report first.")
    return report


@router.post("/visits/{visit_uuid}/review", response_model=ReviewOut)
def review_visit(visit_uuid: str, payload: ReviewRequest, db: Session = Depends(get_db)) -> ReviewOut:
    """Doctor's final action: 'Accept & Write to EHR' (no override) or
    'Override to Low-Risk' (override_tier='low'). Appends a doctor_reviews row and
    moves the visit to 'reviewed' (the DB IS the EHR — reconciliation f8)."""
    visit = _get_visit_or_404(db, visit_uuid)
    if visit.status not in ("awaiting_review", "awaiting_doctor"):
        raise HTTPException(status_code=409, detail=f"Visit is '{visit.status}' — not reviewable.")
    reviewer = db.get(User, payload.reviewer_id)
    if reviewer is None or reviewer.role != "doctor":
        raise HTTPException(status_code=403, detail="Reviewer must be a doctor.")
    if payload.override_tier is not None and payload.override_tier not in TIERS:
        raise HTTPException(status_code=400, detail=f"override_tier must be one of {TIERS}.")

    review = DoctorReview(
        visit_id=visit.id,
        reviewer_id=reviewer.id,
        override_tier=payload.override_tier,
        disposition=payload.disposition,
        notes=payload.notes,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    repo.set_visit_status(db, visit=visit, status="reviewed")
    audit(db, action="visit.review", entity_type="visit", entity_id=visit.uuid,
          actor_id=reviewer.id, clinic_id=visit.clinic_id,
          detail={"override_tier": payload.override_tier, "disposition": payload.disposition})
    return review


@router.post("/visits/{visit_uuid}/feedback", response_model=FeedbackOut)
def give_feedback(visit_uuid: str, payload: FeedbackRequest, db: Session = Depends(get_db)) -> FeedbackOut:
    visit = _get_visit_or_404(db, visit_uuid)
    author = db.get(User, payload.author_id)
    if author is None or author.role not in ("doctor", "medic", "admin"):
        raise HTTPException(status_code=403, detail="Author must be staff.")
    fb = Feedback(
        visit_id=visit.id, author_id=author.id,
        rating=payload.rating, correct=payload.correct, comment=payload.comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    audit(db, action="feedback.create", entity_type="feedback", entity_id=fb.id,
          actor_id=author.id, clinic_id=visit.clinic_id)
    return fb
