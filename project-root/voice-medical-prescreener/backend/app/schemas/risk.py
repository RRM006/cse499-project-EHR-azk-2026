"""API data contracts for risk assessments (M10) and their XAI reasons (M11).

Tier values on the wire are always the schema codes low/medium/high/critical —
display labels (e.g. "Moderate", Bangla labels) live in ONE frontend TIER_LABELS
map (reconciliation item e / ADR-0030).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class XaiOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reason_text: str
    drivers: list | None
    created_at: datetime


class RiskAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    tier: str
    red_flags: list | None = Field(None, description="Triggered red-flag categories; [] if none.")
    rule_overrode: bool = Field(..., description="True if the local rule forced 'critical'.")
    model_provider: str | None
    created_at: datetime


class RiskDetailOut(RiskAssessmentOut):
    """The latest assessment plus its stored explanation."""

    explanation: XaiOut | None = None
