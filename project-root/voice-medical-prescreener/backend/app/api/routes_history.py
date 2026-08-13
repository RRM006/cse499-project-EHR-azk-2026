"""S37 — the doctor's patient-history route (ADR-0058).

GET /api/patients/{patient_id}/history — prior visits + prior prescriptions for one
patient, newest first.

Read-only and assembled entirely from existing rows (see services/history.py). It
carries no transcript: a previous visit is opened through the existing
GET /api/visits/{uuid}, which serves the one immutable copy of the patient's words
(rule #1).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import Patient
from backend.app.schemas.history import PatientHistoryOut
from backend.app.schemas.patient import PatientOut
from backend.app.services.history import patient_history

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/patients/{patient_id}/history", response_model=PatientHistoryOut)
def get_patient_history(
    patient_id: int,
    limit: int = Query(20, ge=1, le=100, description="How many prior visits to return."),
    db: Session = Depends(get_db),
) -> PatientHistoryOut:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    history = patient_history(db, patient, limit=limit)
    return PatientHistoryOut(patient=PatientOut.model_validate(patient), **history)
