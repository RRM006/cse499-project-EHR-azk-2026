"""S37 — the DOCTOR's longitudinal view of one patient (ADR-0058).

The portal has always shown exactly one visit. Every prior encounter was already in
the database, keyed by ``patients.id``, and nothing ever read it back — so "is this
the third time this month with the same complaint?" and "what did we already put
them on?" were questions the doctor could not ask the system. ``prescriptions`` was
worse than invisible: it was a write-only table, so a repeat medication was
undetectable from inside the portal.

This module answers those two questions and nothing else. It is READ-ONLY and
assembles from rows that already exist:

    visits · risk_assessments (latest per visit) · case_profiles (main problem)
    users (the assigned doctor's name) · prescriptions · documents

**Why the doctor and not the medic or the patient.** Comparing this encounter with
previous ones is a clinical judgement; the medic works a pre-consultation queue and
is looking at the case in front of them, and the patient's own portal is a kiosk that
deliberately ends at submission. Nothing here is duplicated into the medic screens.

⚠ Rule #1: prior raw transcripts are NOT included. The doctor opens a previous visit
to read it, exactly as they open the current one, and it is served by the existing
``GET /api/visits/{uuid}`` from the one immutable copy. Summarising a raw transcript
into a history row would create a second, lossy rendering of the patient's words.

⚠ Rule #2: nothing here ranks, trends or interprets. A repeated complaint is shown as
two rows with two dates; whether that means anything is the doctor's call.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.db.models import (
    CaseProfile,
    Document,
    Patient,
    Prescription,
    User,
    Visit,
)
from backend.app.services.risk import latest_assessment

#: How many medicine names one history row carries. The full prescription is a
#: click away in its .docx; this is a recognition aid, not a second copy of the
#: prescription (the payload JSON stays the single source of truth).
MAX_MEDICINE_PREVIEW = 6


def _main_problem(profile: CaseProfile | None) -> str | None:
    if profile is None or not profile.entities:
        return None
    field = (profile.entities.get("summary_fields") or {}).get("main_problem") or {}
    for slot in ("value_en", "value", "value_bn"):
        text = str(field.get(slot) or "").strip()
        if text:
            return text
    return None


def _medicine_names(payload: dict | None) -> list[str]:
    """Medicine names out of a stored prescription payload, defensively.

    ``prescriptions.payload`` is free-form JSON by design (principle 3), so this
    must survive an older or hand-written shape without raising — a history panel
    that 500s on one odd row is worse than one that shows fewer names.
    """
    medicines = (payload or {}).get("medicines")
    if not isinstance(medicines, list):
        return []
    names: list[str] = []
    for entry in medicines:
        if isinstance(entry, dict):
            name = str(entry.get("name") or "").strip()
        else:
            name = str(entry or "").strip()
        if name:
            names.append(name)
    return names[:MAX_MEDICINE_PREVIEW]


def patient_history(db: Session, patient: Patient, *, limit: int = 20) -> dict:
    """Prior encounters + prior prescriptions for one patient, newest first.

    ``limit`` caps the visits; prescriptions are returned for the visits included,
    so the two lists always describe the same window.
    """
    visits = (
        db.query(Visit)
        .filter(Visit.patient_id == patient.id)
        .order_by(Visit.started_at.desc())
        .limit(limit)
        .all()
    )
    visit_ids = [v.id for v in visits]

    prescriptions = (
        db.query(Prescription)
        .filter(Prescription.visit_id.in_(visit_ids))
        .order_by(Prescription.created_at.desc())
        .all()
        if visit_ids
        else []
    )
    per_visit: dict[int, int] = {}
    for rx in prescriptions:
        per_visit[rx.visit_id] = per_visit.get(rx.visit_id, 0) + 1

    uuid_of = {v.id: v.uuid for v in visits}
    rx_rows = []
    for rx in prescriptions:
        doctor = db.get(User, rx.doctor_id)
        document = db.get(Document, rx.document_id) if rx.document_id else None
        payload = rx.payload if isinstance(rx.payload, dict) else {}
        rx_rows.append(
            {
                "prescription_id": rx.id,
                "visit_uuid": uuid_of.get(rx.visit_id, ""),
                "created_at": rx.created_at,
                "doctor_id": rx.doctor_id,
                "doctor_name": doctor.name if doctor else None,
                # Doctor-authored text, shown back to a doctor unchanged (rule #2:
                # the AI never wrote this field and this never re-interprets it).
                "diagnosis": str(payload.get("diagnosis") or "").strip() or None,
                "medicines": _medicine_names(payload),
                "document_id": rx.document_id,
                "filename": document.filename if document else None,
                "download_url": f"/api/documents/{rx.document_id}/download" if document else None,
            }
        )

    visit_rows = []
    for visit in visits:
        profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
        assessment = latest_assessment(db, visit_id=visit.id)
        doctor = db.get(User, visit.assigned_doctor_id) if visit.assigned_doctor_id else None
        visit_rows.append(
            {
                "visit_uuid": visit.uuid,
                "status": visit.status,
                "started_at": visit.started_at,
                "submitted_at": visit.submitted_at,
                "completed_at": visit.completed_at,
                "tier": assessment.tier if assessment else None,
                "red_flags": assessment.red_flags if assessment else None,
                "main_problem": _main_problem(profile),
                "assigned_doctor_id": visit.assigned_doctor_id,
                "assigned_doctor_name": doctor.name if doctor else None,
                "prescription_count": per_visit.get(visit.id, 0),
            }
        )

    return {"visits": visit_rows, "prescriptions": rx_rows}
