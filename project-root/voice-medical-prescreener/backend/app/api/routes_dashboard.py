"""Staff routes (BE-5): kiosk submit, queues, field edits, doctor assignment.

Status flow (ADR-0030): in_progress -> (patient submit) -> awaiting_review (medic
queue) -> (medic assigns + forwards) -> awaiting_doctor (doctor queue). Doctor
accept/review is BE-6.

Field edits touch ONLY the derived summary_fields JSON (source becomes 'human',
which the M8 merge then protects) — never the raw transcript (rule #1). The
append-only audit_log row per edit arrives with G6/BE-7; until then the edit
provenance itself (edited_by/edited_at) is the record.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db import repository_visits as repo
from backend.app.db.database import get_db
from backend.app.db.models import CaseProfile, Patient, User, Visit
from backend.app.schemas.dashboard import (
    AssignRequest,
    ConditionEditRequest,
    DashboardItemOut,
    FieldEditRequest,
    VitalsEditRequest,
)
from backend.app.schemas.patient import PatientOut
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS, CaseProfileOut, SuggestedCondition
from backend.app.schemas.visit import VisitOut
from backend.app.services.audit import audit
from backend.app.services.risk import assess_visit, latest_assessment
from backend.app.services.suggestion import (
    CONDITION_DISCLAIMER,
    CONDITION_DISCLAIMER_BN,
    suggest_condition,
)

router = APIRouter(prefix="/api", tags=["staff"])

logger = logging.getLogger(__name__)


def _get_visit_or_404(db: Session, visit_uuid: str) -> Visit:
    visit = repo.get_visit_by_uuid(db, visit_uuid)
    if visit is None:
        raise HTTPException(status_code=404, detail=f"Visit {visit_uuid} not found")
    return visit


def _to_item(db: Session, visit: Visit) -> DashboardItemOut:
    patient = db.get(Patient, visit.patient_id) if visit.patient_id else None
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    assessment = latest_assessment(db, visit_id=visit.id)
    main_problem = None
    if profile and profile.entities:
        main_problem = (
            (profile.entities.get("summary_fields") or {}).get("main_problem") or {}
        ).get("value")
    return DashboardItemOut(
        visit_uuid=visit.uuid,
        visit_status=visit.status,
        started_at=visit.started_at,
        patient_id=patient.id if patient else None,
        patient_name=patient.display_name if patient else None,
        patient_phone=patient.external_ref if patient else None,
        assigned_doctor_id=visit.assigned_doctor_id,
        tier=assessment.tier if assessment else None,
        red_flags=assessment.red_flags if assessment else None,
        main_problem=main_problem,
        summary=profile.summary if profile else None,
    )


class UserOut(BaseModel):
    id: int
    name: str
    role: str


@router.get("/users", response_model=list[UserOut])
def list_users(role: str | None = None, db: Session = Depends(get_db)) -> list[UserOut]:
    """Staff list (e.g. role=doctor for the medic's Assign dropdown). Auth is stubbed."""
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    return [UserOut(id=u.id, name=u.name, role=u.role) for u in q.order_by(User.name).all()]


# --- kiosk hand-off ---


def _post_submit_assessment(engine, visit_id: int) -> None:
    """P1-5 (ADR-0042b): the submit-time M10/M11/M10C work (up to 3 LLM round-trips)
    runs AFTER the response, on its OWN session — the request session closes with
    the response. Bound to the same engine the request used (so tests with an
    overridden in-memory DB exercise the same path). Fire-and-forget by design:
    a failure here must never touch the already-submitted visit, and the LOCAL
    red-flag rule inside assess_visit still forces Critical even when every LLM
    is down (rule #3). The staff queues pick the tier up on their 15s refresh."""
    session = Session(bind=engine, autoflush=False, future=True)
    try:
        visit = session.get(Visit, visit_id)
        if visit is None:
            return
        profile = session.query(CaseProfile).filter(CaseProfile.visit_id == visit_id).first()
        if latest_assessment(session, visit_id=visit_id) is None:
            assess_visit(session, visit, profile)  # internal LLM failures already swallowed
        suggest_condition(session, visit, profile)  # C1 — idempotent (once per visit)
    except Exception:  # noqa: BLE001 — background job: log, never crash the worker
        logger.exception("Post-submit assessment failed for visit %s", visit_id)
    finally:
        session.close()


@router.post("/visits/{visit_uuid}/submit", response_model=VisitOut)
def submit_visit(
    visit_uuid: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> VisitOut:
    """Patient's "Confirm & Submit": in_progress -> awaiting_review INSTANTLY.

    P1-5 (ADR-0042b): the risk assessment + C1 suggestion (reconciliation f6 — M10
    runs before staff review) moved to a BackgroundTasks job so the patient never
    waits on LLM latency; status + audit stay synchronous, so the case is in the
    medic queue the moment this returns (tier fills in on the queue's refresh)."""
    visit = _get_visit_or_404(db, visit_uuid)
    if visit.status != "in_progress":
        raise HTTPException(status_code=409, detail=f"Visit is already '{visit.status}'.")
    if not any(
        u.role == "patient" for u in repo.list_visit_utterances(db, visit_id=visit.id)
    ):
        raise HTTPException(status_code=400, detail="Nothing to submit — no patient speech yet.")

    updated = repo.set_visit_status(db, visit=visit, status="awaiting_review")
    audit(db, action="visit.submit", entity_type="visit", entity_id=visit.uuid,
          clinic_id=visit.clinic_id)
    background_tasks.add_task(_post_submit_assessment, db.get_bind(), visit.id)
    return updated


# --- staff queues ---


@router.get("/dashboard", response_model=list[DashboardItemOut])
def dashboard(
    role: str = "medic",
    doctor_id: int | None = None,
    phone: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[DashboardItemOut]:
    """Case queues. role=medic -> awaiting_review; role=doctor -> awaiting_doctor
    (optionally filtered to one doctor's assignments). phone= looks a patient up
    across statuses (the staff search box in the mockup)."""
    if phone:
        try:
            normalized = repo.normalize_phone(phone)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        patient = (
            db.query(Patient).filter(Patient.external_ref == normalized).first()
        )
        if patient is None:
            return []
        visits = (
            db.query(Visit)
            .filter(Visit.patient_id == patient.id)
            .order_by(Visit.started_at.desc())
            .limit(limit)
            .all()
        )
        return [_to_item(db, v) for v in visits]

    if role == "medic":
        visits = repo.list_visits(db, status="awaiting_review", limit=limit)
    elif role == "doctor":
        q = db.query(Visit).filter(Visit.status == "awaiting_doctor")
        if doctor_id is not None:
            q = q.filter(Visit.assigned_doctor_id == doctor_id)
        visits = q.order_by(Visit.started_at.desc()).limit(limit).all()
    else:
        raise HTTPException(status_code=400, detail="role must be 'medic' or 'doctor'.")
    return [_to_item(db, v) for v in visits]


# --- field verification / edit (medic + doctor detail screens) ---


@router.patch("/visits/{visit_uuid}/profile/fields/{field_key}", response_model=CaseProfileOut)
def edit_profile_field(
    visit_uuid: str, field_key: str, payload: FieldEditRequest, db: Session = Depends(get_db)
) -> CaseProfileOut:
    """Staff correction of one of the 10 fields: value + human provenance. The M8
    merge never overwrites 'human'-sourced fields afterwards."""
    if field_key not in SUMMARY_FIELD_KEYS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown field '{field_key}'. Expected one of: {', '.join(SUMMARY_FIELD_KEYS)}",
        )
    visit = _get_visit_or_404(db, visit_uuid)
    editor = db.get(User, payload.editor_id)
    if editor is None or editor.role not in ("medic", "doctor", "admin"):
        raise HTTPException(status_code=403, detail="Editor must be a medic, doctor, or admin.")
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    if profile is None:
        raise HTTPException(status_code=400, detail="No profile yet — run intake first.")

    fields = dict((profile.entities or {}).get("summary_fields") or {})
    # A staff edit is authoritative for BOTH display languages: the typed text goes
    # into every slot untranslated (Session 9 decision — staff text is never machine-
    # translated, and no quota is spent on edits). M8 never overwrites 'human' fields.
    fields[field_key] = {
        "value": payload.value,
        "value_en": payload.value,
        "value_bn": payload.value,
        "source": "human",
        "edited_by": editor.id,
        "edited_at": datetime.now(timezone.utc).isoformat(),
    }
    entities = dict(profile.entities or {})
    entities["summary_fields"] = fields
    profile.entities = entities
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    audit(db, action="profile.field_edit", entity_type="visit", entity_id=visit.uuid,
          actor_id=editor.id, clinic_id=visit.clinic_id,
          detail={"field": field_key, "new_value": payload.value})
    return profile


@router.patch("/patients/{patient_id}/vitals", response_model=PatientOut)
def edit_patient_vitals(
    patient_id: int, payload: VitalsEditRequest, db: Session = Depends(get_db)
) -> PatientOut:
    """MEDIC-6: weight (and BP) are staff-recorded vitals, not something the AI
    infers — so this touches the patients row directly, audit-logged. The raw
    transcript and derived profile are untouched.
    P2-2: Name/Age/Gender ride along (staff-editable identity; a staff value is
    final — the AI auto-fill only ever writes EMPTY identity fields)."""
    editor = db.get(User, payload.editor_id)
    if editor is None or editor.role not in ("medic", "doctor", "admin"):
        raise HTTPException(status_code=403, detail="Editor must be a medic, doctor, or admin.")
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    updates = (payload.weight_kg, payload.bp, payload.display_name, payload.sex, payload.age_years)
    if all(v is None for v in updates):
        raise HTTPException(
            status_code=400,
            detail="Nothing to update — send weight_kg, bp, display_name, sex, or age_years.",
        )

    if payload.weight_kg is not None:
        patient.weight_kg = payload.weight_kg
    if payload.bp is not None:
        patient.bp = payload.bp.strip()
    if payload.display_name is not None:
        patient.display_name = payload.display_name.strip()
    if payload.sex is not None:
        patient.sex = payload.sex
    if payload.age_years is not None:
        patient.birth_year = datetime.now(timezone.utc).year - payload.age_years
    db.commit()
    db.refresh(patient)
    # Audit only what was actually edited (None = field not sent).
    detail = {k: v for k, v in {
        "weight_kg": payload.weight_kg, "bp": payload.bp,
        "display_name": payload.display_name, "sex": payload.sex,
        "age_years": payload.age_years,
    }.items() if v is not None}
    audit(db, action="patient.vitals_edit", entity_type="patient", entity_id=patient.id,
          actor_id=editor.id, clinic_id=patient.clinic_id, detail=detail)
    return patient


@router.patch("/visits/{visit_uuid}/profile/condition", response_model=CaseProfileOut)
def edit_suggested_condition(
    visit_uuid: str, payload: ConditionEditRequest, db: Session = Depends(get_db)
) -> CaseProfileOut:
    """C1 staff edit (MEDIC-4, ADR-0036): replace the AI's suggested condition.

    Same rules as the 10-field edit: staff text fills every language slot
    untranslated and source becomes 'human'. The disclaimer is re-attached
    server-side so no payload can strip it; this value never flows into the
    doctor's prescription Diagnosis field (rule #2)."""
    visit = _get_visit_or_404(db, visit_uuid)
    editor = db.get(User, payload.editor_id)
    if editor is None or editor.role not in ("medic", "doctor", "admin"):
        raise HTTPException(status_code=403, detail="Editor must be a medic, doctor, or admin.")
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    if profile is None:
        raise HTTPException(status_code=400, detail="No profile yet — run intake first.")

    suggestion = SuggestedCondition(
        condition=payload.condition,
        condition_en=payload.condition,
        condition_bn=payload.condition,
        reasoning_en=payload.reasoning,
        reasoning_bn=payload.reasoning,
        source="human",
        edited_by=editor.id,
        edited_at=datetime.now(timezone.utc).isoformat(),
        disclaimer=CONDITION_DISCLAIMER,
        disclaimer_bn=CONDITION_DISCLAIMER_BN,
    ).model_dump()
    entities = dict(profile.entities or {})
    entities["suggested_condition"] = suggestion
    profile.entities = entities
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    audit(db, action="profile.condition_edit", entity_type="visit", entity_id=visit.uuid,
          actor_id=editor.id, clinic_id=visit.clinic_id,
          detail={"condition": payload.condition})
    return profile


# --- medic -> doctor hand-off ---


@router.post("/visits/{visit_uuid}/assign", response_model=VisitOut)
def assign_doctor(
    visit_uuid: str, payload: AssignRequest, db: Session = Depends(get_db)
) -> VisitOut:
    """Medic "Submit & Forward": set the assigned doctor and move the case to the
    doctor queue (awaiting_review -> awaiting_doctor)."""
    visit = _get_visit_or_404(db, visit_uuid)
    if visit.status != "awaiting_review":
        raise HTTPException(
            status_code=409,
            detail=f"Visit is '{visit.status}' — only awaiting_review cases can be forwarded.",
        )
    doctor = db.get(User, payload.doctor_id)
    if doctor is None or doctor.role != "doctor":
        raise HTTPException(status_code=400, detail=f"User {payload.doctor_id} is not a doctor.")
    visit.assigned_doctor_id = doctor.id
    db.commit()
    updated = repo.set_visit_status(db, visit=visit, status="awaiting_doctor")
    audit(db, action="visit.assign", entity_type="visit", entity_id=visit.uuid,
          clinic_id=visit.clinic_id, detail={"doctor_id": doctor.id})
    return updated
