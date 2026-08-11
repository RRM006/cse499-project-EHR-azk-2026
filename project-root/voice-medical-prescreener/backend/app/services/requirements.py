"""F3 — what a pre-screening MUST have collected before the patient reaches the
final review. The ONE definition of "required"; the kiosk gate, the readiness
endpoint and the submit guard all read it from here.

TWO KINDS OF REQUIREMENT, and the difference matters clinically.

``MUST_HAVE_VALUE`` — the field has to carry actual text. A pre-screening with no
main problem is not a pre-screening; there is nothing for the doctor to read.

``MUST_HAVE_BEEN_ASKED`` — the patient has to have been ASKED, but the field may
legitimately end up empty. "I take no medicines" and "I have no allergies" are real,
common, clinically meaningful answers. Forcing text into those fields would either
trap the patient in a loop they cannot exit or push them into inventing an answer —
and an invented answer in a medical record is worse than an empty one (rule #1 in
spirit: the record must reflect what the patient actually said).

The human's instruction, verbatim: *"Do not artificially force every one of the 10
fields to contain an answer when a field is genuinely not applicable."* This split is
how that is honored while still guaranteeing nothing important is silently skipped.

The set mirrors the kiosk's own HIGHLIGHT_FIELDS — the five it already paints with a
"Needs info" chip — so the definition of "important" does not fork between the screen
and the server.

``IDENTITY_REQUIREMENTS`` (F4) — name, age and the body/health area. These live
OUTSIDE ``summary_fields``: name and age are columns on the patients row (filled by
``apply_demographics`` from what the patient said about themselves, never guessed),
and the area sits beside ``summary_fields`` in ``case_profiles.entities``. Keeping
them out of the 10 is the human's explicit decision — the 10-field contract stays
byte-identical rather than becoming 12.

Requiring them is only safe because they are ASKABLE: the kiosk's scripted opening
asks each one directly and can re-ask it on the review screen. A requirement nothing
can ask about would trap the patient with no way forward, which is why these arrived
in the same step that taught the interview to ask for them.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.db.models import CaseProfile, FollowupQuestion, Patient, Visit
from backend.app.services.completion import field_has_text

#: Must carry text of its own.
MUST_HAVE_VALUE: tuple[str, ...] = ("main_problem",)

#: Must have been put to the patient at least once; may legitimately end empty.
MUST_HAVE_BEEN_ASKED: tuple[str, ...] = (
    "onset_duration",
    "symptom_details",
    "current_medicines",
    "allergies",
)


#: F4 — required, but not part of the 10 fields. Keys match the kiosk's INTAKE_SCRIPT
#: entries, which is what lets the kiosk re-ask exactly the right question.
IDENTITY_REQUIREMENTS: tuple[str, ...] = ("patient_name", "patient_age", "problem_area")


def _summary_fields(profile: CaseProfile | None) -> dict:
    if profile is None:
        return {}
    return ((profile.entities or {}).get("summary_fields")) or {}


def _asked_gaps(db: Session, *, visit_id: int) -> set[str]:
    """Which field keys have already been put to the patient.

    Relies on F2: in the resume scope ``target_gap`` is now guaranteed to be the
    exact field key the question actually asks about. Before F2 this set could name
    a field nobody had asked, which is precisely how a required field went missing.
    """
    return {
        q.target_gap
        for q in db.query(FollowupQuestion).filter(FollowupQuestion.visit_id == visit_id).all()
        if q.target_gap
    }


def _missing_identity(db: Session, visit: Visit, profile: CaseProfile | None) -> list[str]:
    """F4 — name, age and area, checked where each actually lives."""
    missing: list[str] = []
    patient = db.get(Patient, visit.patient_id) if visit.patient_id else None
    if patient is None or not (patient.display_name or "").strip():
        missing.append("patient_name")
    # Age is stored as a birth year; sanity-bound it so a nonsense value does not
    # silently satisfy the requirement.
    year = patient.birth_year if patient is not None else None
    age = (datetime.now(timezone.utc).year - year) if year else None
    if age is None or not (0 < age < 130):
        missing.append("patient_age")
    area = ((profile.entities or {}).get("problem_area") if profile else None) or {}
    if not str(area.get("en") or area.get("bn") or "").strip():
        missing.append("problem_area")
    return missing


def missing_requirements(db: Session, visit: Visit) -> list[str]:
    """The required items this visit still owes, as canonical keys.

    Empty list == the patient may proceed to the final review. Order is stable —
    identity first, then value-requirements, then ask-requirements — so the kiosk
    shows them predictably and re-asks identity before clinical detail.
    """
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    fields = _summary_fields(profile)
    asked = _asked_gaps(db, visit_id=visit.id)

    missing: list[str] = _missing_identity(db, visit, profile)
    missing += [
        key for key in MUST_HAVE_VALUE if not field_has_text(fields.get(key))
    ]
    missing += [
        key
        for key in MUST_HAVE_BEEN_ASKED
        if not field_has_text(fields.get(key)) and key not in asked
    ]
    return missing
