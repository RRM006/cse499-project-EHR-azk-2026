"""API data contracts for the case profile, including the ADR-0030 10-field shape.

The 10-key ``summary_fields`` object lives INSIDE ``case_profiles.entities`` (JSON —
principle 3, no column promotion per architecture.md §6.2). The fixed shape is
enforced HERE, in code. Each field carries provenance for the mockup's
AI-Extracted / Human-Edited badges.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# The canonical key order — mirrors the mockup's 10 numbered cards.
SUMMARY_FIELD_KEYS: tuple[str, ...] = (
    "main_problem",
    "onset_duration",
    "symptom_details",
    "associated_symptoms",
    "medical_history",
    "current_medicines",
    "allergies",
    "recent_changes_exposures",
    "treatments_tried",
    "current_concern",
)


class SummaryFieldValue(BaseModel):
    """One of the 10 fields, with provenance (who last set it).

    Bilingual since Session 9 (KIOSK-6/DOCTOR-2/MEDIC-1): M3/M8 fill ``value_en`` and
    ``value_bn`` in one extraction call (no separate translation quota). ``value``
    stays populated (same text as ``value_en``) so every pre-Session-9 consumer and
    stored row keeps working — readers new and old fall back across the three.
    """

    value: str = Field("", description="Canonical/legacy single text (mirrors value_en).")
    value_en: str = Field("", description="The field text in English.")
    value_bn: str = Field("", description="The same content in Bangla (Bangla script).")
    source: Literal["ai", "human"] = Field("ai", description="Who produced the current value.")
    edited_by: int | None = Field(None, description="users.id of the staff editor, if human.")
    edited_at: datetime | None = None


class SymptomDetails(BaseModel):
    """Structured sub-shape of field 3 (mockup: location/character/worse/better/severity)."""

    location: str = ""
    character: str = ""
    worse: str = ""
    better: str = ""
    pain_severity_0_10: int | None = None


class SummaryFields(BaseModel):
    """The fixed 10-field pre-screening summary (ADR-0030)."""

    main_problem: SummaryFieldValue = SummaryFieldValue()
    onset_duration: SummaryFieldValue = SummaryFieldValue()
    symptom_details: SummaryFieldValue = SummaryFieldValue()
    symptom_details_structured: SymptomDetails = SymptomDetails()
    associated_symptoms: SummaryFieldValue = SummaryFieldValue()
    medical_history: SummaryFieldValue = SummaryFieldValue()
    current_medicines: SummaryFieldValue = SummaryFieldValue()
    allergies: SummaryFieldValue = SummaryFieldValue()
    recent_changes_exposures: SummaryFieldValue = SummaryFieldValue()
    treatments_tried: SummaryFieldValue = SummaryFieldValue()
    current_concern: SummaryFieldValue = SummaryFieldValue()


class SuggestedCondition(BaseModel):
    """The C1 "Possible Condition" suggestion (ADR-0036) — staff-facing ONLY.

    The one approved exception to rule #2's no-disease-names posture: a clearly
    labeled, disclaimered, editable SUGGESTION stored at
    ``entities["suggested_condition"]``. The disclaimer constants travel INSIDE
    the object so every payload that carries the suggestion carries them.
    Never shown to the patient; never pre-fills the doctor's Diagnosis field.
    """

    condition: str = Field("", description="Canonical/legacy single text (mirrors condition_en).")
    condition_en: str = ""
    condition_bn: str = ""
    reasoning_en: str = Field("", description="Why — cites only the patient's reported symptoms.")
    reasoning_bn: str = ""
    source: Literal["ai", "human"] = "ai"
    edited_by: int | None = Field(None, description="users.id of the staff editor, if human.")
    edited_at: str | None = Field(None, description="ISO timestamp of the staff edit, if human.")
    disclaimer: str = Field(..., description="Always present — 'not a diagnosis' (rule #2).")
    disclaimer_bn: str = Field(..., description="The same disclaimer in Bangla.")


class CaseProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    entities: dict | None
    summary: str | None
    gaps: dict | None
    completeness_score: float | None
    updated_at: datetime
