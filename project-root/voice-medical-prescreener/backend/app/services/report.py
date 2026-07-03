"""M12 — structured clinical report assembly. LOCAL and deterministic (no API):
every section is drawn from data already stored by M1–M11, so generating a report
never spends quota and never invents content. Contains NO diagnosis (rule #2);
the Red Flags section comes straight from M10 (ADR-0024).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.db.models import (
    CaseProfile,
    FollowupQuestion,
    ModuleEvent,
    Patient,
    Report,
    Utterance,
    Visit,
    XaiExplanation,
)
from backend.app.db.repository_visits import list_visit_utterances
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services.risk import latest_assessment

DISCLAIMER = (
    "This is an AI-assisted pre-screening report. It is NOT a diagnosis. "
    "It narrows the search space for the doctor; the doctor decides."
)


def generate_report(db: Session, visit: Visit) -> Report:
    """Assemble the report from stored pipeline outputs and append a reports row."""
    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    assessment = latest_assessment(db, visit_id=visit.id)
    xai = None
    if assessment is not None:
        xai = (
            db.query(XaiExplanation)
            .filter(XaiExplanation.risk_assessment_id == assessment.id)
            .first()
        )

    patient = db.get(Patient, visit.patient_id) if visit.patient_id else None
    fields = ((profile.entities if profile else None) or {}).get("summary_fields") or {}

    qa = []
    answers = {u.id: u for u in list_visit_utterances(db, visit_id=visit.id)}
    for q in (
        db.query(FollowupQuestion)
        .filter(FollowupQuestion.visit_id == visit.id)
        .order_by(FollowupQuestion.asked_at)
        .all()
    ):
        answer: Utterance | None = answers.get(q.answer_utterance_id)
        qa.append(
            {
                "question": q.question_text,
                "target_gap": q.target_gap,
                "answer_raw": answer.raw_text if answer else None,  # verbatim (rule #1)
            }
        )

    sections = {
        "patient_profile": {
            "display_name": patient.display_name if patient else None,
            "phone": patient.external_ref if patient else None,
            "sex": patient.sex if patient else None,
            "birth_year": patient.birth_year if patient else None,
        },
        "chief_complaint": profile.summary if profile else None,
        "summary_fields": {k: fields.get(k) for k in SUMMARY_FIELD_KEYS},
        "followup_qa": qa,
        "risk": {
            "tier": assessment.tier if assessment else None,
            "rule_overrode": assessment.rule_overrode if assessment else None,
        },
        "red_flags": (assessment.red_flags if assessment else None) or [],
        "xai": xai.reason_text if xai else None,
        "gaps": profile.gaps if profile else None,
        "disclaimer": DISCLAIMER,
    }

    report = Report(
        visit_id=visit.id,
        risk_assessment_id=assessment.id if assessment else None,
        sections=sections,
    )
    db.add(report)
    # M12 ran locally — still observable in module_events (provider 'local').
    db.add(
        ModuleEvent(visit_id=visit.id, module_code="M12", status="ok", provider="local")
    )
    db.commit()
    db.refresh(report)
    return report


def latest_report(db: Session, *, visit_id: int) -> Report | None:
    return (
        db.query(Report)
        .filter(Report.visit_id == visit_id)
        .order_by(Report.created_at.desc(), Report.id.desc())
        .first()
    )
