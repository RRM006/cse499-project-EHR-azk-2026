"""API data contracts for the kiosk phone + stub-OTP identification flow (ADR-0030).

The phone number is normalized to ``+8801XXXXXXXXX`` and stored in
``patients.external_ref``. OTP verification is a STUB for the capstone demo:
no SMS is sent; the code is compared to the ``DEV_OTP`` setting.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.visit import VisitOut


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
    consent: bool
    created_at: datetime


class PatientLookupOut(BaseModel):
    patient: PatientOut
    created: bool = Field(..., description="True if this lookup created the patient.")
    otp_sent: bool = Field(
        True, description="Always true in the demo — the stub 'sends' the DEV_OTP code."
    )


class OtpVerifyRequest(BaseModel):
    phone: str = Field(..., description="The phone number the OTP was 'sent' to.")
    otp: str = Field(..., description="The 6-digit code the patient entered.")


class OtpVerifyOut(BaseModel):
    verified: bool
    visit: VisitOut = Field(..., description="The open visit for this kiosk session.")
