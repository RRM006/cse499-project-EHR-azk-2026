"""S38 (C3/C4) — API contracts for recalls and the doctor→medic back-channel.

Codes on the wire, labels in the frontend (ADR-0030 f): ``kind``, ``status`` and
``recipient_role`` are stable keys, and the bilingual sentence a user reads lives in
the portals' own label maps.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field

from backend.app.services.notes import MAX_BODY_CHARS


class NoteCreateRequest(BaseModel):
    """Write a recall or a handover note against one visit.

    ``due_date`` belongs to a recall (when should this patient come back) and is
    validated as a SCHEDULED-FORWARD date — today or later, never the past (ADR-0061).
    A handover note has no due date: it is for the next person at the desk, now.
    """

    kind: str = Field(..., description="'recall' | 'handover_note'.")
    body: str = Field(..., min_length=1, max_length=MAX_BODY_CHARS,
                      description="What is being asked or scheduled. Human-authored.")
    author_id: int = Field(..., description="users.id of the staff author (auth is stubbed).")
    due_date: str | None = Field(
        None, description="Recall only, YYYY-MM-DD. Must not be in the past."
    )
    recipient_role: str | None = Field(
        None, description="Which ROLE should act on it — never an individual person."
    )


class NoteResolveRequest(BaseModel):
    status: str = Field(..., description="'done' | 'cancelled'.")
    actor_id: int = Field(..., description="users.id of whoever is closing it.")


class NoteOut(BaseModel):
    """One note. ``body`` is human-authored workflow text — never a clinical finding,
    never model output (rule #2), and nothing downstream parses it."""

    id: int
    visit_uuid: str
    patient_id: int | None = None
    patient_name: str | None = None
    kind: str
    recipient_role: str | None = None
    body: str
    due_date: date | None = None
    status: str
    author_id: int
    author_name: str | None = None
    author_role: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by_name: str | None = None


class ReferralOut(BaseModel):
    """S38 (C1) — one referral a medic made, derived from ``audit_log``.

    ⚠ ``attributed`` exists because this is honest rather than complete: referrals made
    BEFORE S37 taught ``POST /assign`` to record its actor carry no medic, so they can
    never appear in any medic's list. Inventing an owner for them would be worse than
    omitting them, and a silent omission would look like lost work — so the list says
    how many it cannot attribute.
    """

    visit_uuid: str
    patient_name: str | None = None
    patient_phone: str | None = None
    referred_at: datetime
    doctor_id: int | None = None
    doctor_name: str | None = None
    tier: str | None = None
    main_problem: str | None = None
    visit_status: str


class ReferralHistoryOut(BaseModel):
    medic_id: int
    referrals: list[ReferralOut] = []
    unattributed_total: int = Field(
        0,
        description="Referrals in this clinic with no recorded medic (pre-S37). Reported "
                    "so the count is not silently understated.",
    )
