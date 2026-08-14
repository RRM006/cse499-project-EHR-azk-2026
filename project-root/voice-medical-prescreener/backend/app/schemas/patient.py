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
    """S39 (ADR-0064): ``display_name`` was REMOVED from this request.

    It was an optional name that created a patient row directly, and it was the third
    writer of ``patients.display_name`` — the one that left no audit trail at all, so
    a name arriving this way could never be traced afterwards (it is why
    ``services/identity`` has an ``unknown`` source). No client in this project ever
    sent it: the kiosk posts ``{phone}`` and nothing else, and the name is captured
    either by the M3 auto-fill (audited) or by the staff PATCH (audited).

    Identity is now written through exactly those two audited paths.
    """

    phone: str = Field(..., description="Bangladeshi mobile number, any common format.")


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
    # S39 (rev 0014): the medic's blood-sugar reading and the context it was measured
    # in. Reported as stored — no band, no interpretation (rule #2, ADR-0060).
    blood_glucose_mmol_l: float | None = None
    blood_glucose_context: str | None = None
    consent: bool
    created_at: datetime


class NameProvenanceOut(BaseModel):
    """S39 (ADR-0064) — where ``patient.display_name`` came from, DERIVED from
    ``audit_log`` (see services/identity). Codes on the wire; the sentence a medic
    reads is built in the portal, like every other label (ADR-0030 item e).
    """

    has_name: bool = Field(..., description="False = the record has no name at all.")
    source: str | None = Field(
        None, description="'staff' | 'ai' | 'unknown' | null when there is no name."
    )
    recorded_at: datetime | None = Field(None, description="When the name was written.")
    visit_uuid: str | None = Field(
        None, description="The visit during which it was recorded, when that is known."
    )
    actor_name: str | None = Field(None, description="Staff member who typed it, if any.")
    from_this_visit: bool | None = Field(
        None,
        description="True when recorded during the visit being viewed; null when unknowable.",
    )


class VisitDetailWithPatientOut(VisitDetailOut):
    """GET /visits/{uuid} response: the visit, its turns, AND its patient (vitals
    included) — one call serves the staff detail screens (MEDIC-6 / DOCTOR-3).
    Defined here, not in visit.py, because patient.py already imports visit.py."""

    patient: PatientOut | None = None
    # S39: travels WITH the patient it describes, so no portal can render the name
    # without also having been handed the answer to "where did this come from?".
    name_provenance: NameProvenanceOut | None = None


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
