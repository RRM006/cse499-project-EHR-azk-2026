"""S37 — API contract for the doctor's patient-history panel (ADR-0058).

Codes on the wire (``status``, ``tier``), labels in the frontend — the ADR-0030 f
rule. Deliberately absent: any prior raw or corrected transcript. The doctor opens a
previous visit through the existing ``GET /api/visits/{uuid}`` to read the patient's
words from the one immutable copy (rule #1).
"""

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.schemas.patient import PatientOut


class HistoryVisitOut(BaseModel):
    """One prior encounter, as a row in the timeline."""

    visit_uuid: str
    status: str
    started_at: datetime
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    tier: str | None = Field(None, description="Latest risk tier for that visit; null if none.")
    red_flags: list | None = None
    main_problem: str | None = None
    assigned_doctor_id: int | None = None
    assigned_doctor_name: str | None = None
    prescription_count: int = 0


class HistoryPrescriptionOut(BaseModel):
    """One prior prescription. ``diagnosis`` is doctor-authored text, echoed back
    unchanged — the AI never wrote it and nothing here re-interprets it (rule #2)."""

    prescription_id: int
    visit_uuid: str
    created_at: datetime
    doctor_id: int
    doctor_name: str | None = None
    diagnosis: str | None = None
    medicines: list[str] = Field(
        default_factory=list, description="Name preview only; the .docx holds the full detail."
    )
    document_id: str | None = None
    filename: str | None = None
    download_url: str | None = None


class PatientHistoryOut(BaseModel):
    """Everything the doctor's timeline panel needs, in one call."""

    patient: PatientOut
    visits: list[HistoryVisitOut] = []
    prescriptions: list[HistoryPrescriptionOut] = []
