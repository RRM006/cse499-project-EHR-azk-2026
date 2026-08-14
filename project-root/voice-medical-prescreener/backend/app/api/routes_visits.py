"""Visit routes (BE-1): the aggregate-root API from architecture.md §4, plus the
kiosk phone + OTP identification flow (ADR-0030; real OTP since P4-1, ADR-0045).

The existing flat routes in routes_transcripts.py stay as-is (aliases during
migration); nothing here touches raw/corrected transcript logic or .docx export.

Kiosk flow:
  1. POST /api/patients/lookup      — phone -> find-or-create patient + ISSUE an OTP
                                      (hashed in otp_codes; sent via OTP_CHANNEL)
  2. POST /api/patients/verify-otp  — DB-verified code (or the dev-only 000000
                                      bypass) -> open (or reuse) an in_progress visit
  3. POST /api/visits/{uuid}/utterances — append raw turns (patient AND system questions)
  4. GET  /api/visits/{uuid}        — visit + full conversation in turn order
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db import repository_visits as repo
from backend.app.db.database import get_db
from backend.app.db.models import CaseProfile, Patient, Visit
from backend.app.schemas.profile import CaseProfileOut
from backend.app.services.audit import audit
from backend.app.services.identity import name_provenance
from backend.app.services.intake import run_intake
from backend.app.services.llm_client import LLMCallError
from backend.app.services.otp import OtpSendError, issue_otp, verify_otp_code
from backend.app.services.requirements import missing_requirements
from backend.app.schemas.patient import (
    NameProvenanceOut,
    OtpVerifyOut,
    OtpVerifyRequest,
    PatientLookupOut,
    PatientLookupRequest,
    PatientOut,
    VisitDetailWithPatientOut,
)
from backend.app.schemas.visit import (
    ReadinessOut,
    StoreVisitUtteranceRequest,
    VisitCreate,
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
    """Find or create the patient, then ISSUE a real OTP (P4-1, ADR-0045).

    The code is stored hashed in otp_codes and handed to the configured sender
    (OTP_CHANNEL: dev = server log, textbee = real SMS). Re-lookups inside the
    resend cooldown do NOT send again — ``otp_sent`` is False and the previous
    code stays valid (``retry_after_seconds`` says when a resend is allowed).
    """
    clinic = repo.get_default_clinic(db)
    try:
        patient, created = repo.get_or_create_patient_by_phone(
            db, clinic_id=clinic.id, phone=payload.phone
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    try:
        issued = issue_otp(db, phone=patient.external_ref, patient_id=patient.id)
    except OtpSendError as exc:
        raise HTTPException(status_code=502, detail=f"Could not send the verification code: {exc}")
    if issued.sent:
        audit(
            db,
            action="otp_issued",
            entity_type="patient",
            entity_id=patient.id,
            clinic_id=clinic.id,
            detail={"channel": get_settings().otp_channel},
        )
    return PatientLookupOut(
        patient=PatientOut.model_validate(patient),
        created=created,
        otp_sent=issued.sent,
        retry_after_seconds=issued.retry_after_seconds,
    )


@router.post("/patients/verify-otp", response_model=OtpVerifyOut)
def verify_otp(payload: OtpVerifyRequest, db: Session = Depends(get_db)) -> OtpVerifyOut:
    """DB-backed verification (P4-1): hashed compare, 5-min expiry, single-use,
    max-attempt lockout. The 000000 bypass works only on the dev channel.

    On success, returns the patient's open in_progress visit — creating one if none
    exists — so the kiosk lands directly in the voice conversation.
    """
    try:
        normalized = repo.normalize_phone(payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    outcome = verify_otp_code(db, phone=normalized, code=payload.otp)
    if outcome == "locked":
        raise HTTPException(
            status_code=429, detail="Too many wrong attempts — request a new code."
        )
    if outcome != "ok":
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


@router.get("/visits/{visit_uuid}", response_model=VisitDetailWithPatientOut)
def get_visit(visit_uuid: str, db: Session = Depends(get_db)) -> VisitDetailWithPatientOut:
    visit = _get_visit_or_404(db, visit_uuid)
    detail = VisitDetailWithPatientOut.model_validate(visit)
    detail.utterances = [
        VisitUtteranceOut.model_validate(u)
        for u in repo.list_visit_utterances(db, visit_id=visit.id)
    ]
    if visit.patient_id:
        patient = db.get(Patient, visit.patient_id)
        detail.patient = PatientOut.model_validate(patient) if patient else None
        # S39 (ADR-0064): the name and the answer to "where did it come from?" leave
        # the server together. Derived from audit_log — nothing new is stored.
        detail.name_provenance = NameProvenanceOut(**name_provenance(db, patient, visit))
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


@router.get("/visits/{visit_uuid}/readiness", response_model=ReadinessOut)
def get_visit_readiness(visit_uuid: str, db: Session = Depends(get_db)) -> ReadinessOut:
    """F3 — may the patient proceed to the final review, or is required info still owed?

    Public like the rest of the kiosk flow, and READ-ONLY: it asks
    ``services/requirements`` and reports. The kiosk gates its Confirm & Submit on
    this, and ``POST /submit?require_complete=true`` enforces the same answer, so the
    screen and the server can never disagree about what "complete" means.
    """
    visit = _get_visit_or_404(db, visit_uuid)
    missing = missing_requirements(db, visit)
    return ReadinessOut(complete=not missing, missing=missing)


@router.get("/visits/{visit_uuid}/profile", response_model=CaseProfileOut)
def get_visit_profile(visit_uuid: str, db: Session = Depends(get_db)) -> CaseProfileOut:
    visit = _get_visit_or_404(db, visit_uuid)
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile yet — run intake first.")
    return profile
