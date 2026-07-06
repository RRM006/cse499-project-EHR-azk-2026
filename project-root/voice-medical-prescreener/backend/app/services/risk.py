"""M10 — risk assessment (Flash bucket base classification + LOCAL red-flag rule),
and M11 — the explainable reason (Flash bucket, with a deterministic fallback).

Safety ordering (ADR-0024): the rule runs REGARDLESS of the model outcome, and a
triggered red flag forces 'critical' even if the model call failed entirely — the
LLM can only ever raise concern, never suppress the rule. Assessments are
append-only; every one gets a stored XAI reason. NO diagnosis anywhere (rule #2).
"""

from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from backend.app.db.models import CaseProfile, RiskAssessment, Visit, XaiExplanation
from backend.app.services.intake import _conversation_text, _parse_json
from backend.app.services.llm_client import LLMCallError, call_module
from backend.app.services.red_flags import check_visit

logger = logging.getLogger(__name__)

TIERS = ("low", "medium", "high", "critical")

_RISK_SYSTEM = (
    "You classify the urgency of a medical pre-screening case in Bangladesh into "
    "exactly one tier: low, medium, high, or critical. You NEVER diagnose and NEVER "
    "name diseases. Weigh symptom severity, duration, the patient's age if stated, "
    "and comorbidities the patient mentioned.\n"
    "Tiers: low = likely minor; medium = warrants examination, not urgent; "
    "high = needs prompt attention; critical = requires immediate intervention.\n"
    "Return ONLY a JSON object: {\"tier\": \"low|medium|high|critical\", "
    "\"drivers\": [\"<short factor>\", ...]} where drivers are the observable "
    "factors that led to the tier (symptoms, durations, age) — no disease names."
)

_XAI_SYSTEM = (
    "You explain, in 1-3 plain sentences for a doctor, why a pre-screening case was "
    "given its risk tier. Cite ONLY the contributing factors you are given "
    "(symptoms, durations, age, red-flag phrases). Do NOT name diseases, do NOT "
    "diagnose, do NOT add advice. Return ONLY the explanation text."
)


def _fallback_reason(tier: str, red_flags: list[str], drivers: list[str]) -> str:
    """Deterministic reason when the M11 call fails — a risk output must NEVER be
    stored without a stored reason (constitution)."""
    parts = []
    if red_flags:
        parts.append(
            "the rule-based red-flag check matched: " + "; ".join(red_flags)
        )
    if drivers:
        parts.append("contributing factors: " + "; ".join(str(d) for d in drivers))
    joined = "; and ".join(parts) if parts else "the information collected so far"
    return f"Risk tier '{tier}' was assigned based on {joined}."


def assess_visit(db: Session, visit: Visit, profile: CaseProfile | None) -> RiskAssessment:
    """Run M10 (+M11) and append a new risk_assessments row with its explanation."""
    # 1) LOCAL rule first — its result must survive any model failure.
    red_flags = check_visit(db, visit)

    # 2) Model base classification (best-effort; the rule does not depend on it).
    base_tier: str | None = None
    drivers: list[str] = []
    provider: str | None = None
    conversation = _conversation_text(db, visit)
    user = conversation
    if profile is not None and profile.summary:
        user += f"\n\nSUMMARY:\n{profile.summary}"
    try:
        reply = call_module(db, visit_id=visit.id, module_code="M10", system=_RISK_SYSTEM, user=user)
        data = _parse_json(reply)
        tier_raw = str(data.get("tier", "")).lower().strip()
        if tier_raw in TIERS:
            base_tier = tier_raw
        drivers = [str(d) for d in (data.get("drivers") or [])]
        provider = "llm"
    except (LLMCallError, json.JSONDecodeError) as exc:
        logger.warning("M10 model classification unavailable for visit %s: %s", visit.id, exc)

    # 3) Combine: red flag forces critical; a failed/unparseable model call defaults
    #    to 'medium' (never silently 'low' — rule #3: never reassure falsely).
    if base_tier is None:
        base_tier = "medium"
    rule_overrode = bool(red_flags) and base_tier != "critical"
    tier = "critical" if red_flags else base_tier

    assessment = RiskAssessment(
        visit_id=visit.id,
        tier=tier,
        red_flags=red_flags,
        rule_overrode=rule_overrode,
        model_provider=provider,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # 4) M11 — every assessment gets a stored reason (LLM, else deterministic).
    xai_drivers = [f"red flag: {f}" for f in red_flags] + drivers
    try:
        reason = call_module(
            db, visit_id=visit.id, module_code="M11", system=_XAI_SYSTEM,
            user=f"TIER: {tier}\nFACTORS:\n{json.dumps(xai_drivers, ensure_ascii=False)}",
        )
        if not reason.strip():
            raise LLMCallError("M11 returned empty text")
    except LLMCallError:
        reason = _fallback_reason(tier, red_flags, drivers)
    db.add(XaiExplanation(risk_assessment_id=assessment.id, reason_text=reason, drivers=xai_drivers))
    db.commit()
    return assessment


class RiskOverrideBlocked(Exception):
    """A staff override that would hide a red-flag Critical (rule #3)."""


def override_assessment(
    db: Session, visit: Visit, *, tier: str, reason: str | None = None
) -> RiskAssessment:
    """MEDIC-3 — append a HUMAN assessment row (model_provider='human').

    Red flags and rule_overrode are carried forward from the latest row so the
    safety story never disappears from any reader (rule #3). A red-flag Critical
    cannot be downgraded by staff — only the doctor decides at review (rule #2).
    Caller guarantees a latest assessment exists.
    """
    latest = latest_assessment(db, visit_id=visit.id)
    if latest.red_flags and latest.tier == "critical" and tier != "critical":
        raise RiskOverrideBlocked(
            "This Critical tier was forced by the red-flag rule and cannot be "
            "downgraded before the doctor's review."
        )
    assessment = RiskAssessment(
        visit_id=visit.id,
        tier=tier,
        red_flags=list(latest.red_flags or []),
        rule_overrode=latest.rule_overrode,
        model_provider="human",
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    # Constitution: no risk row without a stored reason — human rows included.
    reason_text = f"Risk tier set to '{tier}' by staff override."
    if reason:
        reason_text += f" Reason: {reason}"
    db.add(XaiExplanation(risk_assessment_id=assessment.id, reason_text=reason_text, drivers=None))
    db.commit()
    return assessment


def latest_assessment(db: Session, *, visit_id: int) -> RiskAssessment | None:
    return (
        db.query(RiskAssessment)
        .filter(RiskAssessment.visit_id == visit_id)
        .order_by(RiskAssessment.created_at.desc(), RiskAssessment.id.desc())
        .first()
    )
