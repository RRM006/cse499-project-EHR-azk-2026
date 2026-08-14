"""Prescription module (DOCTOR-4/5/6, rev 0010).

GET  /api/visits/{uuid}/prescription/context — letterhead prefill for the form (step 18).
POST /api/visits/{uuid}/prescription          — DOCTOR-6: save the row + render the .docx.

The Diagnosis is authored by the doctor and is NEVER filled by the AI suggested
condition (rule #2, C1 / ADR-0036) — the .docx writer only reads the submitted payload.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db import repository_visits as repo
from backend.app.db.database import get_db
from backend.app.db.models import Clinic, Document, User
from backend.app.schemas.document import DocumentOut
from backend.app.schemas.prescription import (
    ClinicLetterheadOut,
    DoctorLetterheadOut,
    PrescriptionContextOut,
    PrescriptionCreatedOut,
    PrescriptionCreateIn,
)
from backend.app.services.audit import audit
from backend.app.services.clinical_dates import (
    FUTURE_DATE,
    INVALID_DATE,
    PAST_DATE,
    check_authored_now,
    check_scheduled,
    dhaka_today_iso,
)
from backend.app.services.documents import generate_prescription_document

router = APIRouter(prefix="/api", tags=["prescription"])

#: S38 (B5) — the date policy, enforced HERE and not only in the form. The browser's
#: `min`/`max` attributes are a courtesy to the doctor; anything that reaches this
#: endpoint from a script, a replayed request or a future client would sail past them.
#:
#: Two fields, two CATEGORIES (see services/clinical_dates for the full taxonomy):
#:   * ``date``          — authored now. Must be today in Dhaka.
#:   * ``followup_date`` — scheduled forward. Must not be in the past; today is fine.
#:
#: Deliberately NOT policed: ``created_at``, ``visits.started_at``, ``submitted_at`` and
#: every other system timestamp. Those record when something happened, and a past value
#: in them is the point — the brief's "do not corrupt historical timestamps".
_DATE_MESSAGES = {
    PAST_DATE: "cannot be in the past",
    FUTURE_DATE: "cannot be in the future",
    INVALID_DATE: "is not a valid YYYY-MM-DD date",
}


def _enforce_prescription_dates(payload: dict) -> dict:
    """Validate the two human-authored dates and default a missing prescription date.

    Returns the payload to store (a copy when the date had to be stamped, so a caller's
    dict is never mutated behind its back). Raises HTTPException(400) on a violation,
    naming the field and the rule — a bare "invalid date" tells the doctor nothing.
    """
    violation = check_authored_now(payload.get("date"))
    if violation:
        raise HTTPException(
            status_code=400,
            detail=f"Prescription date {_DATE_MESSAGES[violation]}: it is dated by the "
                   f"act of writing it, so it must be today ({dhaka_today_iso()}, "
                   f"Bangladesh time).",
        )
    violation = check_scheduled(payload.get("followup_date"))
    if violation:
        raise HTTPException(
            status_code=400,
            detail=f"Follow-up date {_DATE_MESSAGES[violation]}: a follow-up is "
                   f"scheduled forward, so it must be {dhaka_today_iso()} or later "
                   f"(Bangladesh time).",
        )
    if not str(payload.get("date") or "").strip():
        # An older client that never sent one gets the correct date rather than a 400.
        return {**payload, "date": dhaka_today_iso()}
    return payload


def _require_doctor(db: Session, doctor_id: int) -> User:
    doctor = db.get(User, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=404, detail=f"Doctor {doctor_id} not found")
    if doctor.role != "doctor":
        raise HTTPException(status_code=400, detail=f"User {doctor_id} is not a doctor")
    return doctor


@router.get(
    "/visits/{visit_uuid}/prescription/context",
    response_model=PrescriptionContextOut,
)
def get_prescription_context(
    visit_uuid: str, doctor_id: int, db: Session = Depends(get_db)
) -> PrescriptionContextOut:
    """Letterhead prefill (clinic of the visit + the authoring doctor)."""
    visit = repo.get_visit_by_uuid(db, visit_uuid)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_uuid} not found")
    doctor = _require_doctor(db, doctor_id)
    clinic = db.get(Clinic, visit.clinic_id)
    if clinic is None:
        raise HTTPException(status_code=404, detail="Clinic not found for this visit")

    return PrescriptionContextOut(
        clinic=ClinicLetterheadOut(
            name=clinic.name, address=clinic.address, logo_path=clinic.logo_path
        ),
        doctor=DoctorLetterheadOut(
            id=doctor.id,
            name=doctor.name,
            qualification=doctor.qualification,
            registration_no=doctor.registration_no,
            specialization=doctor.specialization,
            signature_path=doctor.signature_path,
        ),
    )


@router.post(
    "/visits/{visit_uuid}/prescription",
    response_model=PrescriptionCreatedOut,
)
def create_prescription(
    visit_uuid: str, body: PrescriptionCreateIn, db: Session = Depends(get_db)
) -> PrescriptionCreatedOut:
    """DOCTOR-6: persist the prescription + render its .docx, then return the
    download URL. A new prescription (+ document) is created per Submit; the
    Diagnosis is taken verbatim from the payload and never AI-filled (rule #2).

    S38 (B5): the two human-authored dates are checked before anything is written, so
    a bad date never reaches the stored payload OR the generated .docx — those two
    would then disagree, and the .docx is the copy the patient walks out with."""
    visit = repo.get_visit_by_uuid(db, visit_uuid)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_uuid} not found")
    doctor = _require_doctor(db, body.doctor_id)
    payload = _enforce_prescription_dates(body.payload)

    prescription = generate_prescription_document(
        db, visit, doctor_id=doctor.id, payload=payload
    )
    audit(
        db,
        action="prescription.created",
        entity_type="prescription",
        entity_id=prescription.id,
        actor_id=doctor.id,
        clinic_id=visit.clinic_id,
        detail={"document_id": prescription.document_id},
    )  # commits the flushed prescription with the audit row
    db.refresh(prescription)
    document = db.get(Document, prescription.document_id)
    return PrescriptionCreatedOut(
        prescription_id=prescription.id,
        document=DocumentOut.model_validate(document),
    )
