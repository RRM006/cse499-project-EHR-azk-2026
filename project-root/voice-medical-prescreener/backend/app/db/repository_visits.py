"""Repository for the visit aggregate (visits, patients, per-visit utterances).

Kept separate from repository.py (the utterance/document session-grain writers) so the
existing flat-transcript paths stay untouched. Same rule applies here: raw_text is
write-once — add_utterance() inserts, nothing updates it (rule #1).
"""

import unicodedata
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.db.models import Clinic, Patient, Utterance, Visit


def to_ascii_digits(text: str) -> str:
    """Keep only decimal digits, folding every script's form to ASCII 0-9.

    F5 (ADR-0053): "a Unicode decimal digit IS a digit" — a patient reading their
    number aloud in Bangla, or typing on a Bangla keyboard, produces
    ``০১৭১৫৯৮৪৬৩২``, and refusing that is refusing the language the kiosk is built
    for. This replaces ``re.sub(r"\\D", "", ...)``, which was subtly wrong rather
    than merely strict: Python's ``\\d`` is Unicode-aware, so it KEPT ``০১৭…``
    unchanged and let the ASCII ``startswith("880")`` / length checks below fail on
    an otherwise perfectly valid number.

    ``unicodedata.decimal`` (not ``str.isdigit``) is the right filter: it accepts
    exactly the Nd category — Bangla, Devanagari, Arabic-Indic, fullwidth — while
    rejecting things like superscript ``²`` that are "digits" to ``isdigit()`` but
    carry no positional value.
    """
    return "".join(
        str(unicodedata.decimal(ch))
        for ch in text
        if unicodedata.decimal(ch, None) is not None
    )


def normalize_phone(phone: str) -> str:
    """Normalize a Bangladeshi mobile number to ``+8801XXXXXXXXX``.

    Accepts '01715984632', '8801715984632', '+880 1715-984632', the Bangla-digit
    forms of all of those, and any mix of the two scripts.
    Raises ValueError for anything that doesn't reduce to a valid BD mobile.
    """
    digits = to_ascii_digits(phone)
    if digits.startswith("880"):
        digits = digits[3:]
    digits = digits.lstrip("0") if digits.startswith("0") else digits
    if len(digits) != 10 or not digits.startswith("1"):
        raise ValueError(f"Not a valid Bangladeshi mobile number: {phone!r}")
    return f"+880{digits}"


def get_default_clinic(db: Session) -> Clinic:
    """The single-tenant clinic (seeded in 0003). Created on the fly for test DBs."""
    clinic = db.query(Clinic).order_by(Clinic.id).first()
    if clinic is None:
        clinic = Clinic(name="Demo Clinic")
        db.add(clinic)
        db.commit()
        db.refresh(clinic)
    return clinic


def get_or_create_patient_by_phone(
    db: Session, *, clinic_id: int, phone: str, display_name: str | None = None
) -> tuple[Patient, bool]:
    """Find the patient by normalized phone (external_ref), creating if absent."""
    normalized = normalize_phone(phone)
    patient = (
        db.query(Patient)
        .filter(Patient.clinic_id == clinic_id, Patient.external_ref == normalized)
        .first()
    )
    if patient is not None:
        return patient, False
    patient = Patient(clinic_id=clinic_id, external_ref=normalized, display_name=display_name)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient, True


def create_visit(
    db: Session, *, clinic_id: int, patient_id: int | None = None, language: str = "bn-BD"
) -> Visit:
    visit = Visit(clinic_id=clinic_id, patient_id=patient_id, language=language)
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


def get_visit_by_uuid(db: Session, visit_uuid: str) -> Visit | None:
    return db.query(Visit).filter(Visit.uuid == visit_uuid).first()


def get_open_visit_for_patient(db: Session, *, patient_id: int) -> Visit | None:
    """The patient's current in-progress visit, if one exists (kiosk re-entry)."""
    return (
        db.query(Visit)
        .filter(Visit.patient_id == patient_id, Visit.status == "in_progress")
        .order_by(Visit.started_at.desc())
        .first()
    )


def list_visits(db: Session, *, status: str | None = None, limit: int = 50) -> list[Visit]:
    q = db.query(Visit)
    if status:
        q = q.filter(Visit.status == status)
    return q.order_by(Visit.started_at.desc()).limit(limit).all()


def list_visit_utterances(db: Session, *, visit_id: int) -> list[Utterance]:
    """The conversation in turn order."""
    return (
        db.query(Utterance)
        .filter(Utterance.visit_id == visit_id)
        .order_by(Utterance.seq, Utterance.id)
        .all()
    )


def add_utterance(
    db: Session,
    *,
    visit_id: int,
    raw_text: str,
    role: str = "patient",
    source: str = "mic",
    stt_provider: str | None = None,
) -> Utterance:
    """Append one raw turn to a visit (write-once; seq auto-increments per visit)."""
    next_seq = (
        db.query(func.coalesce(func.max(Utterance.seq), -1))
        .filter(Utterance.visit_id == visit_id)
        .scalar()
    ) + 1
    utterance = Utterance(
        visit_id=visit_id,
        role=role,
        seq=next_seq,
        raw_text=raw_text,
        source=source,
        stt_provider=stt_provider,
    )
    db.add(utterance)
    db.commit()
    db.refresh(utterance)
    return utterance


def set_visit_status(db: Session, *, visit: Visit, status: str) -> Visit:
    """Transition a visit's workflow status; stamps submitted_at on awaiting_review
    (P3-1 — the patient's "Confirm & Submit" moment) and completed_at on reviewed/closed."""
    visit.status = status
    if status == "awaiting_review" and visit.submitted_at is None:
        visit.submitted_at = datetime.now(timezone.utc)
    if status in ("reviewed", "closed") and visit.completed_at is None:
        visit.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(visit)
    return visit
