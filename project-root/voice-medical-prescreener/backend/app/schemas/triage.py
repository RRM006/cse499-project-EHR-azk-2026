"""S37 — API contracts for the medic's operational views (ADR-0058).

Codes on the wire, labels in the frontend — the same rule the risk tiers follow
(ADR-0030 f). ``HandoffCheckOut.code`` is a stable key like ``vitals_missing``; the
bilingual sentence a medic reads lives in the portal's own label map, so the server
never ships display text and the two languages can never drift apart per-endpoint.
"""

from pydantic import BaseModel, Field


class HandoffCheckOut(BaseModel):
    """One advisory finding about a case that is about to be forwarded."""

    code: str = Field(..., description="Stable key, e.g. 'identity_incomplete'.")
    severity: str = Field(..., description="'warn' = a medic could still fix it; 'info' = context.")
    detail: str | None = Field(
        None, description="Comma-joined specifics (field keys, red-flag phrases) or null."
    )


class HandoffOut(BaseModel):
    """Medic pre-forward readiness. ADVISORY — see services/triage.handoff_checks.

    ``ready`` False never blocks ``POST /assign``; it means the doctor will be
    missing something the medic is still able to supply.
    """

    visit_uuid: str
    ready: bool = Field(..., description="True when no 'warn' check is outstanding.")
    checks: list[HandoffCheckOut] = []


class QueueStatsOut(BaseModel):
    """Load figures for one staff queue — derived per request, nothing stored."""

    role: str
    waiting: int = Field(..., description="How many cases are in this queue right now.")
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    unassessed: int = Field(0, description="Submitted but with no risk assessment yet.")
    red_flagged: int = Field(0, description="Cases whose latest assessment carries red flags.")
    longest_wait_minutes: int | None = None
    average_wait_minutes: int | None = None
