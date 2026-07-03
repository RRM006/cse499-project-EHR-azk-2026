"""Visit routes (BE-1): the aggregate-root API from architecture.md §4, plus the
kiosk phone + stub-OTP identification flow (ADR-0030).

The existing flat routes in routes_transcripts.py stay as-is (aliases during
migration); nothing here touches raw/corrected transcript logic or .docx export.

Kiosk flow:
  1. POST /api/patients/lookup      — phone -> find-or-create patient (stub "sends" OTP)
  2. POST /api/patients/verify-otp  — code == DEV_OTP -> open (or reuse) an in_progress visit
  3. POST /api/visits/{uuid}/utterances — append raw turns (patient AND system questions)
  4. GET  /api/visits/{uuid}        — visit + full conversation in turn order
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db import repository_visits as repo
from backend.app.db.database import get_db
from backend.app.db.models import CaseProfile, Visit
from backend.app.schemas.profile import CaseProfileOut
from backend.app.services.intake import run_intake
from backend.app.services.llm_client import LLMCallError
from backend.app.schemas.patient import (
    OtpVerifyOut,
    OtpVerifyRequest,
    PatientLookupOut,
    PatientLookupRequest,
    PatientOut,
)
from backend.app.schemas.visit import (
    StoreVisitUtteranceRequest,
    VisitCreate,
    VisitDetailOut,
    VisitOut,
    VisitUtteranceOut,
)

router = APIRouter(prefix="/api", tags=["visits"])


def _get_visit_or_404(db: Session, visit_uuid: str) -> Visit:
    visit = repo.get_visit_by_uuid(db, visit_uuid)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_uuid} not found")
    return visit


# --- patient identification (kiosk screens 1–2) ---


@router.post("/patients/lookup", response_model=PatientLookupOut)
def lookup_patient(payload: PatientLookupRequest, db: Session = Depends(get_db)) -> PatientLookupOut:
    """Find or create the patient for a phone number. The OTP 'send' is a stub."""
    clinic = repo.get_default_clinic(db)
    try:
        patient, created = repo.get_or_create_patient_by_phone(
            db, clinic_id=clinic.id, phone=payload.phone, display_name=payload.display_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return PatientLookupOut(patient=PatientOut.model_validate(patient), created=created)


@router.post("/patients/verify-otp", response_model=OtpVerifyOut)
def verify_otp(payload: OtpVerifyRequest, db: Session = Depends(get_db)) -> OtpVerifyOut:
    """STUB verification: the code must equal the DEV_OTP setting (no SMS in the demo).

    On success, returns the patient's open in_progress visit — creating one if none
    exists — so the kiosk lands directly in the voice conversation.
    """
    if payload.otp != get_settings().dev_otp:
        raise HTTPException(status_code=401, detail="Invalid verification code.")
    clinic = repo.get_default_clinic(db)
    try:
        patient, _ = repo.get_or_create_patient_by_phone(
            db, clinic_id=clinic.id, phone=payload.phone
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    visit = repo.get_open_visit_for_patient(db, patient_id=patient.id)
    if visit is None:
        visit = repo.create_visit(db, clinic_id=clinic.id, patient_id=patient.id)
    return OtpVerifyOut(verified=True, visit=VisitOut.model_validate(visit))


# --- visits (aggregate root) ---


@router.post("/visits", response_model=VisitOut)
def create_visit(payload: VisitCreate, db: Session = Depends(get_db)) -> VisitOut:
    """Start a visit directly (walk-in / dev path — the kiosk normally uses verify-otp)."""
    clinic = repo.get_default_clinic(db)
    return repo.create_visit(
        db, clinic_id=clinic.id, patient_id=payload.patient_id, language=payload.language
    )


@router.get("/visits", response_model=list[VisitOut])
def list_visits(
    status: str | None = None, limit: int = 50, db: Session = Depends(get_db)
) -> list[VisitOut]:
    return repo.list_visits(db, status=status, limit=limit)


@router.get("/visits/{visit_uuid}", response_model=VisitDetailOut)
def get_visit(visit_uuid: str, db: Session = Depends(get_db)) -> VisitDetailOut:
    visit = _get_visit_or_404(db, visit_uuid)
    detail = VisitDetailOut.model_validate(visit)
    detail.utterances = [
        VisitUtteranceOut.model_validate(u)
        for u in repo.list_visit_utterances(db, visit_id=visit.id)
    ]
    return detail


@router.post("/visits/{visit_uuid}/utterances", response_model=VisitUtteranceOut)
def store_visit_utterance(
    visit_uuid: str, payload: StoreVisitUtteranceRequest, db: Session = Depends(get_db)
) -> VisitUtteranceOut:
    """Append one raw conversation turn to a visit (write-once — rule #1)."""
    visit = _get_visit_or_404(db, visit_uuid)
    if visit.status != "in_progress":
        raise HTTPException(
            status_code=409,
            detail=f"Visit is '{visit.status}' — utterances can only be added while in_progress.",
        )
    return repo.add_utterance(
        db,
        visit_id=visit.id,
        raw_text=payload.raw_text,
        role=payload.role,
        source=payload.source,
        stt_provider=payload.stt_provider,
    )


# --- intake pipeline (M3 -> M4 -> M6) + profile ---


@router.post("/visits/{visit_uuid}/intake", response_model=CaseProfileOut)
def run_visit_intake(visit_uuid: str, db: Session = Depends(get_db)) -> CaseProfileOut:
    """Run extraction (M3), summary (M4) and gap analysis (M6) over the collected
    utterances, writing the visit's case_profile. Each module run logs a
    module_events row (provider + latency + fallback)."""
    visit = _get_visit_or_404(db, visit_uuid)
    try:
        return run_intake(db, visit)
    except ValueError as exc:  # no utterances / unparseable extraction
        raise HTTPException(status_code=400, detail=str(exc))
    except LLMCallError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/visits/{visit_uuid}/profile", response_model=CaseProfileOut)
def get_visit_profile(visit_uuid: str, db: Session = Depends(get_db)) -> CaseProfileOut:
    visit = _get_visit_or_404(db, visit_uuid)
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile yet — run intake first.")
    return profile
