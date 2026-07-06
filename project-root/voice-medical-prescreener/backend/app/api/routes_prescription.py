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
from backend.app.services.documents import generate_prescription_document

router = APIRouter(prefix="/api", tags=["prescription"])


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
    Diagnosis is taken verbatim from the payload and never AI-filled (rule #2)."""
    visit = repo.get_visit_by_uuid(db, visit_uuid)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_uuid} not found")
    doctor = _require_doctor(db, body.doctor_id)

    prescription = generate_prescription_document(
        db, visit, doctor_id=doctor.id, payload=body.payload
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
