"""S38 (C3/C4, ADR-0060) — recalls and the doctor→medic back-channel, on ONE table.

Two requested features, one shape. A **recall** ("bring this patient back on the 3rd to
recheck the BP") and a **handover note** ("please take her weight before I see her
again") are both: a short piece of text, written by a named person, attached to a case,
optionally due on a date, and eventually closed. That is one table with a ``kind``
column, not two tables — see the migration for the alternatives that were rejected.

--------------------------------------------------------------------------------
WHY A BACK-CHANNEL AT ALL, AND WHY NOT A CHAT
--------------------------------------------------------------------------------

The status flow runs one way by design: patient → medic → doctor. That is correct for
the CASE, and it is why S37 refused to build this. What it leaves the doctor with is no
way to ask the desk for anything at all — and "please repeat the BP, this reading looks
wrong" is a real, frequent, low-stakes request that currently happens by shouting across
a room.

So this is deliberately the smallest thing that solves it, and the brief says so:
*"Do not build a chat application."* Concretely:

  * a note is addressed to a **ROLE**, not to a person — whoever is on the triage desk
    this shift is the right recipient, and routing to an individual would break the
    moment they went home;
  * there is **no thread and no reply**. The medic marks it done. If they need to say
    something back, that is a different note, and in practice it is a conversation;
  * there is **no unread count, no notification, no realtime**. It appears in the
    medic's inbox on the queue's existing refresh.

--------------------------------------------------------------------------------
WHAT A NOTE MAY NOT BE
--------------------------------------------------------------------------------

⚠ A note is WORKFLOW text and never clinical output. It is written by a human (no code
path lets an LLM author one), it is stored and displayed separately from
``prescriptions`` (the treatment) and ``risk_assessments`` (the tier), and nothing reads
it back into the pipeline. Rule #2 holds because a note cannot become a diagnosis: it is
never parsed, never coded, and never surfaced as a finding about the patient.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from backend.app.db.models import ClinicalNote, Patient, User, Visit

#: The two kinds. Adding a third is a product decision, not a refactor — the CHECK
#: constraint in rev 0013 is the authority and this mirrors it.
KIND_RECALL = "recall"
KIND_HANDOVER = "handover_note"
KINDS = (KIND_RECALL, KIND_HANDOVER)

STATUS_OPEN = "open"
STATUS_DONE = "done"
STATUS_CANCELLED = "cancelled"
STATUSES = (STATUS_OPEN, STATUS_DONE, STATUS_CANCELLED)

#: Who may be addressed. A note to "doctor" is possible but nothing builds one today —
#: the asymmetry is the point: the case already flows medic → doctor on its own.
RECIPIENT_ROLES = ("doctor", "medic", "desk", "admin")

MAX_BODY_CHARS = 1000


def create_note(
    db: Session,
    *,
    visit: Visit,
    author: User,
    kind: str,
    body: str,
    due_date: date | None = None,
    recipient_role: str | None = None,
) -> ClinicalNote:
    """Write one note. Validation is the CALLER's job for anything user-facing
    (the route turns a bad value into a 400 with a reason); this asserts the
    invariants the table itself depends on.
    """
    if kind not in KINDS:
        raise ValueError(f"Unknown note kind '{kind}'. Expected one of: {', '.join(KINDS)}.")
    text = str(body or "").strip()
    if not text:
        raise ValueError("A note cannot be empty.")
    if recipient_role is not None and recipient_role not in RECIPIENT_ROLES:
        raise ValueError(f"Unknown recipient role '{recipient_role}'.")

    note = ClinicalNote(
        clinic_id=visit.clinic_id,
        visit_id=visit.id,
        # Denormalised ON PURPOSE and only this once: the medic's inbox lists notes
        # across cases and needs the patient without walking every visit. It is a
        # foreign key to the same row the visit points at, not a copy of any patient
        # DATA — ADR-0058 h forbids copying identity, not referencing it.
        patient_id=visit.patient_id,
        author_id=author.id,
        kind=kind,
        recipient_role=recipient_role,
        body=text[:MAX_BODY_CHARS],
        due_date=due_date,
        status=STATUS_OPEN,
    )
    db.add(note)
    db.flush()
    return note


def resolve_note(db: Session, note: ClinicalNote, *, actor: User, status: str) -> ClinicalNote:
    """Close a note (done / cancelled), recording WHO closed it and when.

    Re-resolving is refused rather than silently overwritten: the first person to act
    on a note is the one who acted on it, and letting a later click rewrite that would
    make the record of who did the work unreliable.
    """
    if status not in (STATUS_DONE, STATUS_CANCELLED):
        raise ValueError(f"A note can only be closed as done or cancelled, not '{status}'.")
    if note.status != STATUS_OPEN:
        raise ValueError(f"This note is already '{note.status}'.")
    note.status = status
    note.resolved_at = datetime.now(timezone.utc)
    note.resolved_by = actor.id
    db.flush()
    return note


def notes_for_visit(db: Session, visit: Visit) -> list[ClinicalNote]:
    """Everything attached to one case, newest first."""
    return (
        db.query(ClinicalNote)
        .filter(ClinicalNote.visit_id == visit.id)
        .order_by(ClinicalNote.created_at.desc(), ClinicalNote.id.desc())
        .all()
    )


def inbox(
    db: Session,
    *,
    recipient_role: str | None = None,
    kind: str | None = None,
    status: str | None = STATUS_OPEN,
    clinic_id: int | None = None,
    limit: int = 50,
) -> list[ClinicalNote]:
    """The list one role should act on.

    Ordering is by DUE DATE first (a recall due today outranks one due next month) and
    then oldest-first, which is the same fairness rule the triage queue uses inside a
    tier. Notes with no due date sort after dated ones rather than jumping the queue —
    "no deadline" is not "most urgent".
    """
    query = db.query(ClinicalNote)
    if recipient_role:
        query = query.filter(ClinicalNote.recipient_role == recipient_role)
    if kind:
        query = query.filter(ClinicalNote.kind == kind)
    if status:
        query = query.filter(ClinicalNote.status == status)
    if clinic_id is not None:
        query = query.filter(ClinicalNote.clinic_id == clinic_id)
    rows = query.limit(limit * 4).all()
    rows.sort(key=lambda n: (n.due_date is None, n.due_date or date.max, n.created_at))
    return rows[:limit]


def note_row(db: Session, note: ClinicalNote) -> dict:
    """One note as the API shape: names resolved, dates as-is.

    Names are looked up per request rather than stored on the note — the same
    ownership rule the queue follows (ADR-0058 h): one source of truth, read twice.
    """
    author = db.get(User, note.author_id)
    resolver = db.get(User, note.resolved_by) if note.resolved_by else None
    patient = db.get(Patient, note.patient_id) if note.patient_id else None
    visit = db.get(Visit, note.visit_id)
    return {
        "id": note.id,
        "visit_uuid": visit.uuid if visit else "",
        "patient_id": note.patient_id,
        "patient_name": patient.display_name if patient else None,
        "kind": note.kind,
        "recipient_role": note.recipient_role,
        "body": note.body,
        "due_date": note.due_date,
        "status": note.status,
        "author_id": note.author_id,
        "author_name": author.name if author else None,
        "author_role": author.role if author else None,
        "created_at": note.created_at,
        "resolved_at": note.resolved_at,
        "resolved_by_name": resolver.name if resolver else None,
    }
