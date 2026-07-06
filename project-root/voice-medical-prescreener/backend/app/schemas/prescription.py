"""API data contract for the prescription module (DOCTOR-4/5, rev 0010).

The context endpoint returns letterhead ONLY — the patient details and the 10 symptom
fields are assembled client-side from the already-loaded case, so they are not resent
here. There is deliberately no Diagnosis field on this payload: the prescription
Diagnosis is authored by the human doctor and is NEVER pre-filled from the AI suggested
condition (constitution rule #2, human decision C1 / ADR-0036).
"""

from pydantic import BaseModel, Field

from backend.app.schemas.document import DocumentOut


class ClinicLetterheadOut(BaseModel):
    name: str
    address: str | None = None
    logo_path: str | None = None


class DoctorLetterheadOut(BaseModel):
    id: int
    name: str
    qualification: str | None = None
    registration_no: str | None = None
    specialization: str | None = None
    signature_path: str | None = None


class PrescriptionContextOut(BaseModel):
    """Prefill for the prescription form: the clinic + doctor letterhead."""

    clinic: ClinicLetterheadOut
    doctor: DoctorLetterheadOut


class PrescriptionCreateIn(BaseModel):
    """DOCTOR-6 Submit. ``payload`` is the whole form as built client-side by
    ``collectPrescriptionPayload()`` — stored as-is (JSON) so the shape can evolve
    without migrations. ``doctor_id`` is the authoring doctor (validated + audited).
    The payload's Diagnosis is doctor-typed; the server never fills it (rule #2)."""

    doctor_id: int
    payload: dict = Field(..., description="The full prescription form payload (JSON).")


class PrescriptionCreatedOut(BaseModel):
    """What Submit returns: the new prescription id + its generated .docx (with the
    ``download_url`` the UI clicks to auto-download)."""

    prescription_id: int
    document: DocumentOut
