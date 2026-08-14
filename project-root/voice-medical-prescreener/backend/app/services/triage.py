"""S37 — the MEDIC's operational view of a case (ADR-0058).

Everything here is DERIVED. Not one function stores anything, and not one of them
introduces a new source of truth: the tier comes from ``risk_assessments``, the wait
from ``visits.submitted_at``, the completeness from ``case_profiles.entities`` and the
identity/vitals from ``patients``. That is deliberate — the medic's screen is a
different QUESTION asked of the data the clinic already has ("who next, and is this
case fit to hand over?"), not a second copy of it.

Why this is the medic's module and not the doctor's or the patient's:

  * **Ordering.** ``list_visits`` returns newest-submitted-first, which is the wrong
    order for a triage desk: a Critical patient who submitted 40 minutes ago sorts
    BELOW a Low-risk patient who submitted 10 seconds ago. The doctor's queue is a
    short, already-triaged, assigned-to-me list; the patient never sees a queue at
    all. Choosing who is seen next is the medic's whole job.
  * **Completeness.** The kiosk asks the patient for what is REQUIRED
    (``services/requirements``); this asks a different question — of the ten fields
    the medic is about to verify, which are empty, and has a human looked at any of
    them yet. The doctor receives the case after that work is done.
  * **Handoff.** ``handoff_checks`` is advisory ON PURPOSE (see ``ready``): a medic
    must be able to push a Critical patient to a doctor immediately, incomplete
    paperwork and all. Blocking a referral on data completeness would make the
    system less safe, not more, so nothing here can refuse a forward — it can only
    tell the medic what the doctor is about to be missing.

⚠ Timestamps: SQLite hands back OFFSET-LESS datetimes even though everything is
written as UTC, so every comparison goes through :func:`_as_utc` first. Subtracting a
naive datetime from an aware ``now`` raises TypeError, and reading a naive UTC value
as local time is the same defect the frontend fixed in P2-1.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.db.models import CaseProfile, Patient, Visit
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services.completion import field_has_text
from backend.app.services.requirements import IDENTITY_REQUIREMENTS, missing_requirements
from backend.app.services.risk import latest_assessment

#: Sort weight per tier — worst first. An unassessed case (None) sorts BETWEEN
#: high and medium rather than last: "we do not know yet" is not the same as "we
#: know it is fine", and burying it at the bottom is how an unassessed Critical
#: would be discovered late.
TIER_ORDER: dict[str | None, int] = {
    "critical": 0,
    "high": 1,
    None: 2,
    "medium": 3,
    "low": 4,
}

#: Advisory severities returned by :func:`handoff_checks`. ``warn`` means the doctor
#: will be missing something a medic could have supplied; ``info`` is context the
#: medic should see but which is not theirs to fix (red flags are the model's output,
#: not a gap). Neither one can stop a forward.
SEVERITY_WARN = "warn"
SEVERITY_INFO = "info"


def _as_utc(value: datetime | None) -> datetime | None:
    """Pin an offset-less DB timestamp to UTC (see the module docstring)."""
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def waiting_minutes(visit: Visit, *, now: datetime | None = None) -> int | None:
    """Whole minutes since the patient handed the case over.

    Measured from ``submitted_at`` — the moment the patient stopped being able to
    act on the case and started waiting on staff. ``started_at`` is the fallback
    only for pre-0011 rows that carry no ``submitted_at`` (and for a visit still
    in progress, where it is the closest honest answer). Never negative: a clock
    skew must not invent a patient who has waited "-3 minutes".
    """
    reference = _as_utc(visit.submitted_at) or _as_utc(visit.started_at)
    if reference is None:
        return None
    current = _as_utc(now) or datetime.now(timezone.utc)
    return max(0, int((current - reference).total_seconds() // 60))


def summary_fields_of(profile: CaseProfile | None) -> dict:
    """The 10-field dict, or {} — the one place that shape is unwrapped here."""
    if profile is None:
        return {}
    return ((profile.entities or {}).get("summary_fields")) or {}


def empty_field_keys(profile: CaseProfile | None) -> list[str]:
    """Which of the 10 fields carry no text in any language slot.

    Uses the same ``field_has_text`` predicate as M9's completeness score and the
    kiosk resume loop, so the medic's "6 of 10 filled" can never disagree with the
    number the patient's own review screen was gated on.
    """
    fields = summary_fields_of(profile)
    return [key for key in SUMMARY_FIELD_KEYS if not field_has_text(fields.get(key))]


def field_is_verified(field: dict | None) -> bool:
    """Has a human taken responsibility for this field?

    Two ways, and they are genuinely different acts:

      * ``source == 'human'`` — a person CHANGED the value. Written by the staff
        field-edit route; M8's merge then refuses to overwrite it.
      * ``verified_by`` — a person READ the model's value and confirmed it (S38/C2).

    Before S38 only the first existed, which meant a medic could not record "I checked
    this and it is correct" without editing it to say the same thing — the gap S37
    recorded as deliberately deferred (ADR-0058, Rejected 2). Both now count, because
    a field a person has vouched for is verified however they vouched for it.
    """
    field = field or {}
    return field.get("source") == "human" or bool(field.get("verified_by"))


def human_verified_count(profile: CaseProfile | None) -> int:
    """How many of the 10 fields a human has edited OR explicitly confirmed.

    This does NOT claim the remaining fields are wrong, only that nothing but the model
    has touched them.
    """
    fields = summary_fields_of(profile)
    return sum(1 for key in SUMMARY_FIELD_KEYS if field_is_verified(fields.get(key)))


def verified_field_keys(profile: CaseProfile | None) -> list[str]:
    """WHICH of the 10 a human has vouched for — so the queue meter can shade the
    right segments instead of shading a count from the left."""
    fields = summary_fields_of(profile)
    return [key for key in SUMMARY_FIELD_KEYS if field_is_verified(fields.get(key))]


def completed_referrals(db: Session, *, medic_id: int, limit: int = 50) -> dict:
    """S38 (C1) — the cases this medic forwarded, DERIVED from ``audit_log``.

    S37 refused this feature outright, and correctly: nothing recorded which medic sent
    a case, so any list would have shown every medic's work as one person's. S37 then
    fixed the cause — ``POST /assign`` now writes the forwarding medic into
    ``audit_log.actor_id`` — which makes the list derivable from rows that already
    exist. No new table, no new column: the same principle as the rest of the staff
    layer (ADR-0058), a different QUESTION asked of existing data.

    ⚠ Honest by construction: referrals made before that change carry no actor and
    appear in NOBODY's list. They are counted and reported as ``unattributed`` rather
    than guessed at or silently dropped — a medic seeing "12 referrals" when they made
    forty would reasonably conclude the feature is broken.
    """
    from backend.app.db.models import AuditLog, User

    medic = db.get(User, medic_id)
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.action == "visit.assign", AuditLog.actor_id == medic_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )

    referrals = []
    for entry in rows:
        visit = db.query(Visit).filter(Visit.uuid == entry.entity_id).first()
        if visit is None:      # the audit row outlives the visit it describes
            continue
        patient = db.get(Patient, visit.patient_id) if visit.patient_id else None
        doctor_id = (entry.detail or {}).get("doctor_id")
        doctor = db.get(User, doctor_id) if doctor_id else None
        profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
        assessment = latest_assessment(db, visit_id=visit.id)
        main = (summary_fields_of(profile).get("main_problem") or {})
        referrals.append({
            "visit_uuid": visit.uuid,
            "patient_name": patient.display_name if patient else None,
            "patient_phone": patient.external_ref if patient else None,
            "referred_at": entry.created_at,
            "doctor_id": doctor_id,
            "doctor_name": doctor.name if doctor else None,
            "tier": assessment.tier if assessment else None,
            "main_problem": str(main.get("value_en") or main.get("value")
                                or main.get("value_bn") or "").strip() or None,
            "visit_status": visit.status,
        })

    unattributed_query = db.query(AuditLog).filter(
        AuditLog.action == "visit.assign", AuditLog.actor_id.is_(None)
    )
    if medic is not None and medic.clinic_id is not None:
        unattributed_query = unattributed_query.filter(AuditLog.clinic_id == medic.clinic_id)

    return {
        "medic_id": medic_id,
        "referrals": referrals,
        "unattributed_total": unattributed_query.count(),
    }


def triage_sort_key(*, tier: str | None, waiting: int | None) -> tuple[int, int]:
    """Worst tier first; within a tier, longest wait first (FIFO fairness).

    Returning a plain tuple keeps the ordering testable on its own, without a DB.
    """
    return (TIER_ORDER.get(tier, TIER_ORDER[None]), -(waiting or 0))


def _identity_gaps(db: Session, visit: Visit) -> list[str]:
    """The identity items still owed, from the ONE definition in requirements.py."""
    owed = set(missing_requirements(db, visit))
    return [key for key in IDENTITY_REQUIREMENTS if key in owed]


def handoff_checks(db: Session, visit: Visit) -> dict:
    """What the doctor is about to receive — advisory, never blocking.

    Returns ``{"ready": bool, "checks": [{code, severity, detail}]}``. ``ready`` is
    False when any ``warn`` is present and means "a medic could still improve this",
    NOT "this may not be forwarded". Nothing in the assign route consults it; the
    medic decides, and a Critical patient is never held up by paperwork.
    """
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    patient = db.get(Patient, visit.patient_id) if visit.patient_id else None
    assessment = latest_assessment(db, visit_id=visit.id)
    checks: list[dict] = []

    fields = summary_fields_of(profile)
    if not field_has_text(fields.get("main_problem")):
        checks.append({"code": "main_problem_missing", "severity": SEVERITY_WARN, "detail": None})

    identity = _identity_gaps(db, visit)
    if identity:
        checks.append(
            {"code": "identity_incomplete", "severity": SEVERITY_WARN, "detail": ", ".join(identity)}
        )

    if assessment is None:
        checks.append({"code": "risk_not_assessed", "severity": SEVERITY_WARN, "detail": None})
    elif assessment.red_flags:
        # Surfaced, never "fixable": a red flag is the model's finding about the
        # patient, so it is information the medic carries forward, not a gap.
        checks.append(
            {
                "code": "red_flags_present",
                "severity": SEVERITY_INFO,
                "detail": ", ".join(str(f) for f in assessment.red_flags),
            }
        )

    if patient is not None and patient.weight_kg is None and not (patient.bp or "").strip():
        checks.append({"code": "vitals_missing", "severity": SEVERITY_INFO, "detail": None})

    empty = empty_field_keys(profile)
    if empty:
        checks.append(
            {"code": "fields_empty", "severity": SEVERITY_INFO, "detail": ", ".join(empty)}
        )

    if profile is not None and human_verified_count(profile) == 0:
        checks.append({"code": "no_field_verified", "severity": SEVERITY_INFO, "detail": None})

    return {
        "ready": not any(c["severity"] == SEVERITY_WARN for c in checks),
        "checks": checks,
    }


def queue_stats(db: Session, visits: list[Visit], *, now: datetime | None = None) -> dict:
    """Load figures for one already-scoped queue.

    Takes the visit list rather than querying, so the strip above a queue always
    describes exactly the rows below it — a stats endpoint with its own filter is
    how a dashboard starts disagreeing with the list it sits on top of.
    """
    waits: list[int] = []
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    unassessed = 0
    red_flagged = 0
    for visit in visits:
        wait = waiting_minutes(visit, now=now)
        if wait is not None:
            waits.append(wait)
        assessment = latest_assessment(db, visit_id=visit.id)
        if assessment is None:
            unassessed += 1
        else:
            if assessment.tier in counts:
                counts[assessment.tier] += 1
            if assessment.red_flags:
                red_flagged += 1
    return {
        "waiting": len(visits),
        "critical": counts["critical"],
        "high": counts["high"],
        "medium": counts["medium"],
        "low": counts["low"],
        "unassessed": unassessed,
        "red_flagged": red_flagged,
        "longest_wait_minutes": max(waits) if waits else None,
        "average_wait_minutes": round(sum(waits) / len(waits)) if waits else None,
    }
