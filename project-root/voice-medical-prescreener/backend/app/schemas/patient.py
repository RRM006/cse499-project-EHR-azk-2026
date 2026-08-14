"""API data contracts for the kiosk phone + OTP identification flow (ADR-0030).

The phone number is normalized to ``+8801XXXXXXXXX`` and stored in
``patients.external_ref``. Since P4-1 (ADR-0045) the OTP is REAL: lookup issues
a hashed, expiring, single-use code delivered by the configured sender
(OTP_CHANNEL: dev = server log, textbee = SMS); the 000000 bypass survives only
on the dev channel with OTP_DEV_BYPASS enabled.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.visit import VisitDetailOut, VisitOut


class PatientLookupRequest(BaseModel):
    phone: str = Field(..., description="Bangladeshi mobile number, any common format.")
    display_name: str | None = Field(None, description="Optional name for a new patient.")


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clinic_id: int
    external_ref: str | None
    display_name: str | None
    sex: str | None
    birth_year: int | None
    # Vitals (rev 0010) for the staff detail views; weight is medic-editable (MEDIC-6).
    weight_kg: float | None = None
    bp: str | None = None
    # S38 (rev 0013): height in centimetres — the other half of a BMI. The BMI itself
    # is NOT a field here: it is derived on demand from height + weight, so it can
    # never disagree with the two values it is made of.
    height_cm: float | None = None
    consent: bool
    created_at: datetime


class VisitDetailWithPatientOut(VisitDetailOut):
    """GET /visits/{uuid} response: the visit, its turns, AND its patient (vitals
    included) — one call serves the staff detail screens (MEDIC-6 / DOCTOR-3).
    Defined here, not in visit.py, because patient.py already imports visit.py."""

    patient: PatientOut | None = None


class PatientLookupOut(BaseModel):
    patient: PatientOut
    created: bool = Field(..., description="True if this lookup created the patient.")
    otp_sent: bool = Field(
        True,
        description="True if a code was issued and sent; False when throttled — the "
        "previously sent code is still valid.",
    )
    retry_after_seconds: int | None = Field(
        None, description="Set only when throttled: seconds until a resend is allowed."
    )


class OtpVerifyRequest(BaseModel):
    phone: str = Field(..., description="The phone number the OTP was 'sent' to.")
    otp: str = Field(..., description="The 6-digit code the patient entered.")


class OtpVerifyOut(BaseModel):
    verified: bool
    visit: VisitOut = Field(..., description="The open visit for this kiosk session.")
