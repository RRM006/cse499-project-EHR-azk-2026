"""S38 (C1/C3/C4) — recalls, the doctor→medic back-channel, and a medic's own
completed-referral history.

    POST  /api/visits/{uuid}/notes   create a recall or a handover note
    GET   /api/visits/{uuid}/notes   everything attached to one case
    GET   /api/notes                 the inbox / recall list a role should act on
    PATCH /api/notes/{id}            close one (done | cancelled)
    GET   /api/medics/{id}/referrals the cases this medic forwarded (derived)

Three properties hold across all of them:

  * **Every write names a human.** ``author_id`` / ``actor_id`` is required and must be
    staff; there is no path by which an LLM or an anonymous caller writes a note.
  * **A due date is a SCHEDULED-FORWARD date** and goes through the same policy as a
    follow-up (ADR-0061) — a recall in the past is a typo, not a plan.
  * **The referral history is derived**, never stored: it reads ``audit_log`` rows that
    ``POST /assign`` already writes (ADR-0058 / S37).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db import repository_visits as repo
from backend.app.db.database import get_db
from backend.app.db.models import ClinicalNote, User, Visit
from backend.app.schemas.notes import (
    NoteCreateRequest,
    NoteOut,
    NoteResolveRequest,
    ReferralHistoryOut,
)
from backend.app.services import notes as notes_service
from backend.app.services.audit import audit
from backend.app.services.clinical_dates import (
    INVALID_DATE,
    PAST_DATE,
    check_scheduled,
    dhaka_today_iso,
    parse_iso_date,
)
from backend.app.services.triage import completed_referrals

router = APIRouter(prefix="/api", tags=["notes"])

#: Who may author a note. 'desk' is included: a receptionist recording "patient rang to
#: move the recall" is a legitimate author, and excluding them would push that note into
#: someone else's name.
_AUTHOR_ROLES = ("doctor", "medic", "desk", "admin")


def _get_visit_or_404(db: Session, visit_uuid: str) -> Visit:
    visit = repo.get_visit_by_uuid(db, visit_uuid)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_uuid} not found")
    return visit


def _require_staff(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or user.role not in _AUTHOR_ROLES:
        raise HTTPException(status_code=403, detail="Must be a member of clinic staff.")
    return user


def _due_date_or_400(kind: str, raw: str | None) -> date | None:
    """Validate a recall's due date, and refuse one on a handover note.

    A handover note is for the next person at the desk NOW; a due date on it would
    imply a queue nobody works.
    """
    if kind != notes_service.KIND_RECALL:
        if str(raw or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Only a recall carries a due date — a handover note is for now.",
            )
        return None
    violation = check_scheduled(raw)
    if violation == PAST_DATE:
        raise HTTPException(
            status_code=400,
            detail=f"A recall cannot be scheduled in the past — use {dhaka_today_iso()} "
                   f"or later (Bangladesh time).",
        )
    if violation == INVALID_DATE:
        raise HTTPException(status_code=400, detail="due_date must be a YYYY-MM-DD date.")
    return parse_iso_date(raw)


@router.post("/visits/{visit_uuid}/notes", response_model=NoteOut)
def create_note(
    visit_uuid: str, payload: NoteCreateRequest, db: Session = Depends(get_db)
) -> NoteOut:
    """Write a recall (C3) or a handover note back to the medic (C4)."""
    visit = _get_visit_or_404(db, visit_uuid)
    author = _require_staff(db, payload.author_id)
    if payload.kind not in notes_service.KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"kind must be one of: {', '.join(notes_service.KINDS)}.",
        )
    due = _due_date_or_400(payload.kind, payload.due_date)
    try:
        note = notes_service.create_note(
            db, visit=visit, author=author, kind=payload.kind, body=payload.body,
            due_date=due, recipient_role=payload.recipient_role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    audit(db, action=f"note.{payload.kind}.create", entity_type="clinical_note",
          entity_id=note.id, actor_id=author.id, clinic_id=visit.clinic_id,
          detail={"visit_uuid": visit.uuid, "recipient_role": payload.recipient_role})
    db.refresh(note)
    return NoteOut(**notes_service.note_row(db, note))


@router.get("/visits/{visit_uuid}/notes", response_model=list[NoteOut])
def list_visit_notes(visit_uuid: str, db: Session = Depends(get_db)) -> list[NoteOut]:
    visit = _get_visit_or_404(db, visit_uuid)
    return [NoteOut(**notes_service.note_row(db, n))
            for n in notes_service.notes_for_visit(db, visit)]


@router.get("/notes", response_model=list[NoteOut])
def list_notes(
    recipient_role: str | None = Query(None, description="Which role should act on it."),
    kind: str | None = Query(None, description="'recall' | 'handover_note'."),
    status: str | None = Query("open", description="Default 'open' — the work list."),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[NoteOut]:
    """The inbox. ``recipient_role=medic&status=open`` is the medic's; ``kind=recall``
    is the recall list. Ordered by due date, then oldest first."""
    if kind and kind not in notes_service.KINDS:
        raise HTTPException(status_code=400, detail=f"Unknown kind '{kind}'.")
    if status and status not in notes_service.STATUSES:
        raise HTTPException(status_code=400, detail=f"Unknown status '{status}'.")
    rows = notes_service.inbox(db, recipient_role=recipient_role, kind=kind,
                               status=status, limit=limit)
    return [NoteOut(**notes_service.note_row(db, n)) for n in rows]


@router.patch("/notes/{note_id}", response_model=NoteOut)
def resolve_note(
    note_id: int, payload: NoteResolveRequest, db: Session = Depends(get_db)
) -> NoteOut:
    """Close a note. Re-closing an already-closed one is a 409, not a silent overwrite:
    the first person to act on it is the one who acted on it."""
    note = db.get(ClinicalNote, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
    actor = _require_staff(db, payload.actor_id)
    try:
        notes_service.resolve_note(db, note, actor=actor, status=payload.status)
    except ValueError as exc:
        raise HTTPException(
            status_code=409 if "already" in str(exc) else 400, detail=str(exc)
        )
    audit(db, action="note.resolve", entity_type="clinical_note", entity_id=note.id,
          actor_id=actor.id, clinic_id=note.clinic_id, detail={"status": payload.status})
    db.refresh(note)
    return NoteOut(**notes_service.note_row(db, note))


@router.get("/medics/{medic_id}/referrals", response_model=ReferralHistoryOut)
def medic_referrals(
    medic_id: int, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)
) -> ReferralHistoryOut:
    """S38 (C1) — the cases this medic forwarded. Derived from audit_log; nothing new
    is stored. See services/triage.completed_referrals for why the count can be
    incomplete and why that is reported rather than hidden."""
    medic = db.get(User, medic_id)
    if medic is None or medic.role != "medic":
        raise HTTPException(status_code=404, detail=f"Medic {medic_id} not found")
    return ReferralHistoryOut(**completed_referrals(db, medic_id=medic_id, limit=limit))
