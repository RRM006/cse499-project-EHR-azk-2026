"""API data contracts for the staff side (BE-5): queues, field edits, assignment.

Tier values stay schema codes (low/medium/high/critical) — display labels live in
the frontend TIER_LABELS map (ADR-0030 item e).
"""

from datetime import datetime

from pydantic import BaseModel, Field


class DashboardItemOut(BaseModel):
    """One case row in a staff queue (mockup: time, badge, name, main problem)."""

    visit_uuid: str
    visit_status: str
    started_at: datetime
    submitted_at: datetime | None = Field(
        None, description="When the patient hit Confirm & Submit; null pre-0011/unsubmitted."
    )
    patient_id: int | None
    patient_name: str | None
    patient_phone: str | None
    assigned_doctor_id: int | None
    tier: str | None = Field(None, description="Latest risk tier; null if not assessed yet.")
    red_flags: list | None = None
    main_problem: str | None = Field(None, description="summary_fields.main_problem value.")
    summary: str | None = None
    # S37 (ADR-0058) — derived operational columns. Nothing new is stored: the wait
    # is computed from submitted_at and the counts from the same summary_fields the
    # detail screen renders, so a queue row can never disagree with the case it opens.
    waiting_minutes: int | None = Field(
        None, description="Whole minutes since the patient submitted (started_at as fallback)."
    )
    fields_filled: int = Field(0, description="How many of the 10 summary fields carry text.")
    fields_total: int = Field(10, description="Size of the fixed summary-field contract.")
    fields_verified: int = Field(0, description="How many of the 10 a human has confirmed.")
    # S38: WHICH of the ten are empty, so the queue's completeness meter can say what is
    # actually missing instead of only how many. Same ``empty_field_keys`` call the row
    # already made for the count — the list was computed and then thrown away.
    fields_empty: list[str] = Field(
        default_factory=list, description="Canonical keys of the summary fields with no text."
    )
    assigned_doctor_name: str | None = Field(
        None, description="Resolved name for the assigned doctor; null when unassigned."
    )


class FieldEditRequest(BaseModel):
    """A staff (medic/doctor) correction of one AI-extracted field.

    Edits the DERIVED profile only — the raw transcript is untouchable (rule #1).
    """

    value: str
    editor_id: int = Field(..., description="users.id of the staff editor (auth is stubbed).")


class FieldVerifyRequest(BaseModel):
    """S38 (C2) — a staff member confirming one AI-extracted field is correct.

    Carries no value: verifying is not editing. The whole point is that a medic can
    say "I read this and it is right" without retyping the model's words, which was
    the only way to signal it before S38 and left a false edit in the record.
    """

    verified: bool = Field(True, description="False removes a verification (a mis-click).")
    editor_id: int = Field(..., description="users.id of the staff verifier (auth is stubbed).")


class VitalsEditRequest(BaseModel):
    """A staff edit of the patient's vitals (MEDIC-6: weight is medic-editable;
    BP rides along for the DOCTOR-3 details card). At least one field required.

    P2-2: identity fields ride along too — Name/Age/Gender are staff-editable and,
    once set (by staff OR the auto-fill), the AI never overwrites them."""

    weight_kg: float | None = Field(None, gt=0, lt=500, description="Weight in kilograms.")
    bp: str | None = Field(None, max_length=32, description="Free-form reading, e.g. '120/80'.")
    # S38: bounds mirror services/clinical_reference's plausible-human range, so a value
    # the BMI calculator would refuse can never be stored either — otherwise a saved
    # height of 17 would sit in the record forever showing a blank BMI with no reason.
    height_cm: float | None = Field(None, ge=30, le=260, description="Height in centimetres.")
    display_name: str | None = Field(None, min_length=1, max_length=120,
                                     description="Patient name as recorded by staff.")
    sex: str | None = Field(None, pattern="^(male|female|other)$",
                            description="Schema codes; display labels live in the frontend.")
    age_years: int | None = Field(None, gt=0, lt=130,
                                  description="Age in years; the server stores birth_year.")
    editor_id: int = Field(..., description="users.id of the staff editor (auth is stubbed).")


class ConditionEditRequest(BaseModel):
    """A staff edit/replacement of the C1 suggested condition (MEDIC-4, ADR-0036).

    Staff-facing only — the result NEVER pre-fills the doctor's prescription
    Diagnosis field (rule #2). The server re-attaches the disclaimer itself.
    """

    condition: str = Field(..., min_length=1, description="Replacement condition text.")
    reasoning: str = Field("", description="Why — free text shown beside the condition.")
    editor_id: int = Field(..., description="users.id of the staff editor (auth is stubbed).")


class AssignRequest(BaseModel):
    doctor_id: int = Field(..., description="users.id of the doctor to forward the case to.")
    # S37: OPTIONAL on purpose — every other staff write already identifies its actor,
    # but the referral (the one hand-off between two humans) did not, so audit_log
    # recorded which doctor received a case and never which medic sent it. Optional
    # keeps the walk-in / dev callers that never had an editor working unchanged.
    editor_id: int | None = Field(
        None, description="users.id of the forwarding medic; recorded as the audit actor."
    )
