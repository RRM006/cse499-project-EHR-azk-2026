"""S39 (ADR-0064) — where a patient's NAME came from, and when.

--------------------------------------------------------------------------------
THE DEFECT THIS EXISTS FOR
--------------------------------------------------------------------------------

``patients.display_name`` is **patient-scoped and permanent**: the patients row is
found by phone number (``external_ref``), so a name written during one visit is
displayed on every later visit by the same number — in the medic queue, in the case
workspace, in the referral history, in the .docx and in the FHIR bundle.

THREE things could write it before S39:

  1. ``services/intake.apply_demographics`` — the M3/M8 model, from what it believed
     the patient said about themselves;
  2. ``PATCH /api/patients/{id}/vitals`` — a medic or doctor typing it in;
  3. ``POST /api/patients/lookup`` — an optional name on the request body, which no
     client ever sent and which left no trace at all. S39 **removed** it, so identity
     is now written through exactly the two paths above, and both are audited.

Until S39 the stored string recorded **none** of that. A medic looking at a case had
no way to tell whether the name in front of them was stated by this patient in this
visit, typed by a colleague two days ago, or produced by a model from a garbled
transcription — and the reported bug was exactly that: a name appeared for a visit in
which the patient never gave one, because it had been typed by staff during an
earlier visit on the same phone number.

The name is not invented and it is not wrong to keep it — a returning patient IS the
same person. What was wrong is displaying it as though it were established *here*.

--------------------------------------------------------------------------------
DERIVED, NOT STORED (ADR-0060 boundary)
--------------------------------------------------------------------------------

Provenance needs no column. ``audit_log`` already records the staff edit with the
new name in ``detail``; S39 makes the AI auto-fill write its own row the same way
(it previously wrote nothing at all, which is a real accountability hole quite apart
from this bug). So provenance is a QUESTION asked of rows that already exist —
the same choice ADR-0060 made for the medic's referral history.

⚠ Honest by construction, like ``completed_referrals``: a name written before S39
has no audit row, so it is reported as ``unknown`` rather than guessed at. "We do not
know where this came from" is a true and useful answer; inventing "staff" would be a
lie of exactly the kind this module exists to prevent.
"""

from __future__ import annotations

from datetime import timezone

from sqlalchemy.orm import Session

from backend.app.db.models import AuditLog, Patient, User, Visit

#: The AI auto-fill's audit action (written by ``intake.apply_demographics``).
#: ``actor_id`` is NULL on these rows because no human wrote them.
IDENTITY_AI_FILL_ACTION = "patient.identity_ai_fill"

#: The staff identity/vitals edit's audit action (written by the vitals PATCH).
#: It carries ``display_name`` in ``detail`` only when a name was actually sent.
STAFF_EDIT_ACTION = "patient.vitals_edit"

#: What ``name_provenance`` can conclude. Codes on the wire, labels in the frontend
#: (ADR-0030 item e) — no display text is ever built here.
SOURCE_AI = "ai"
SOURCE_STAFF = "staff"
SOURCE_UNKNOWN = "unknown"


def name_provenance(db: Session, patient: Patient | None, visit: Visit | None = None) -> dict:
    """Answer "where did this name come from?" for one patient.

    Returns a dict shaped like :class:`schemas.patient.NameProvenanceOut`::

        {"has_name": bool, "source": "ai"|"staff"|"unknown"|None,
         "recorded_at": datetime|None, "visit_uuid": str|None,
         "actor_name": str|None, "from_this_visit": bool|None}

    ``has_name`` False means the record genuinely has no name — the portals show
    their "not provided" label and nothing else here applies.

    ``from_this_visit`` is the field the reported bug turns on — see
    :func:`_from_this_visit` for exactly when it can be answered and when it stays
    None, because a "no" that really means "we cannot tell" would be worse than
    saying nothing.
    """
    if patient is None or not (patient.display_name or "").strip():
        return {
            "has_name": False,
            "source": None,
            "recorded_at": None,
            "visit_uuid": None,
            "actor_name": None,
            "from_this_visit": None,
        }

    entry = _latest_name_write(db, patient)
    if entry is None:
        # Written before S39 (no audit row exists for it, and none can be invented).
        # Unknown is the honest answer; see the module docstring.
        return {
            "has_name": True,
            "source": SOURCE_UNKNOWN,
            "recorded_at": None,
            "visit_uuid": None,
            "actor_name": None,
            "from_this_visit": None,
        }

    detail = entry.detail or {}
    source = SOURCE_AI if entry.action == IDENTITY_AI_FILL_ACTION else SOURCE_STAFF
    origin_visit = detail.get("visit_uuid")
    actor = db.get(User, entry.actor_id) if entry.actor_id else None
    from_this_visit = _from_this_visit(entry, origin_visit, visit)
    return {
        "has_name": True,
        "source": source,
        "recorded_at": entry.created_at,
        "visit_uuid": origin_visit,
        "actor_name": actor.name if actor else None,
        "from_this_visit": from_this_visit,
    }


def _from_this_visit(entry: AuditLog, origin_visit: str | None, visit: Visit | None) -> bool | None:
    """Did this name come from the visit being viewed?

    Two ways to know, and one way not to:

      1. The AI auto-fill records the visit it ran for, so the answer is a comparison.
      2. A STAFF edit records no visit — but it does record WHEN, and a name written
         before this visit began provably did not come from it. That is the reported
         bug's own case: a colleague typed the name two days earlier and today's case
         inherited it. Deducing False from the clock is not a guess; the alternative
         is staying silent about the one situation this module exists for.

    Everything else returns None. A staff edit made DURING this visit could have come
    from the patient in the room or from a paper form, and "we cannot tell" is the
    honest answer — it prints as a neutral note rather than a warning.
    """
    if visit is None:
        return None
    if origin_visit:
        return origin_visit == visit.uuid
    recorded, started = entry.created_at, visit.started_at
    if recorded is None or started is None:
        return None
    # SQLite hands back naive datetimes; both are stored UTC, so compare in UTC.
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=timezone.utc)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return False if recorded < started else None


def _latest_name_write(db: Session, patient: Patient) -> AuditLog | None:
    """The newest audit row that actually SET this patient's name.

    A ``patient.vitals_edit`` row exists for every weight/BP change too, so the
    ``display_name`` key must be present in ``detail`` for the row to count —
    otherwise a medic correcting a weight would appear to have renamed the patient.
    """
    rows = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "patient",
            AuditLog.entity_id == str(patient.id),
            AuditLog.action.in_((IDENTITY_AI_FILL_ACTION, STAFF_EDIT_ACTION)),
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .all()
    )
    for row in rows:
        detail = row.detail or {}
        if row.action == STAFF_EDIT_ACTION:
            if detail.get("display_name"):
                return row
        elif (detail.get("fields") or {}).get("display_name"):
            return row
    return None
