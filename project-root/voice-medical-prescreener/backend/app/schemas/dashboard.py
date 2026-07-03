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
    patient_id: int | None
    patient_name: str | None
    patient_phone: str | None
    assigned_doctor_id: int | None
    tier: str | None = Field(None, description="Latest risk tier; null if not assessed yet.")
    red_flags: list | None = None
    main_problem: str | None = Field(None, description="summary_fields.main_problem value.")
    summary: str | None = None


class FieldEditRequest(BaseModel):
    """A staff (medic/doctor) correction of one AI-extracted field.

    Edits the DERIVED profile only — the raw transcript is untouchable (rule #1).
    """

    value: str
    editor_id: int = Field(..., description="users.id of the staff editor (auth is stubbed).")


class AssignRequest(BaseModel):
    doctor_id: int = Field(..., description="users.id of the doctor to forward the case to.")
