"""M10C — the C1 "Possible Condition (AI Suggestion – Not a Diagnosis)" (ADR-0036).

The ONE approved exception to the no-disease-names posture (rule #2 / decision C1):
a clearly labeled, disclaimered, staff-facing SUGGESTION that narrows the doctor's
search space. Deliberately a SEPARATE LLM call from M10 — the risk prompt
hard-forbids naming diseases and must never be contaminated by this one.
Best-effort by design: a failed call means "no suggestion", never a blocked submit.
The disclaimer constants live INSIDE the stored object, so every payload that
carries the suggestion carries them. Never shown in the patient kiosk; never
pre-fills the doctor's prescription Diagnosis field (re-enforced at step 18).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.db.models import CaseProfile, Visit
from backend.app.schemas.profile import SuggestedCondition
from backend.app.services.intake import _conversation_text, _parse_json
from backend.app.services.llm_client import LLMCallError, call_module

logger = logging.getLogger(__name__)

CONDITION_DISCLAIMER = (
    "AI suggestion only — NOT a diagnosis. The doctor makes all clinical decisions."
)
CONDITION_DISCLAIMER_BN = (
    "এটি শুধুমাত্র এআই পরামর্শ — রোগনির্ণয় নয়। সকল চিকিৎসা সিদ্ধান্ত ডাক্তার নেবেন।"
)

_SUGGEST_SYSTEM = (
    "You help clinic staff in Bangladesh prepare a medical pre-screening case BEFORE "
    "the doctor sees the patient. From the patient's reported symptoms only, suggest "
    "the single most plausible possible condition. This narrows the doctor's search "
    "space — it is NOT a diagnosis; the doctor decides. Be conservative: if the "
    "information is thin, keep the condition generic (a symptom category) and say so "
    "in the reasoning. Return ONLY a JSON object: "
    '{"condition_en": "<short condition name in English>", '
    '"condition_bn": "<the same in Bangla script>", '
    '"reasoning_en": "<1-3 sentences citing only the patient\'s reported symptoms>", '
    '"reasoning_bn": "<the same in Bangla>"} — no extra keys, no advice, no drug names.'
)


def suggest_condition(db: Session, visit: Visit, profile: CaseProfile | None) -> dict | None:
    """Generate + store the M10C suggestion once per visit (best-effort).

    Returns the stored object, or None when there is nothing to work from or the
    whole provider chain failed — the caller proceeds either way.
    """
    if profile is None:
        return None
    existing = (profile.entities or {}).get("suggested_condition")
    if existing:
        return existing

    user = _conversation_text(db, visit)
    if profile.summary:
        user += f"\n\nSUMMARY:\n{profile.summary}"
    try:
        reply = call_module(
            db, visit_id=visit.id, module_code="M10C", system=_SUGGEST_SYSTEM, user=user
        )
        data = _parse_json(reply)
    except (LLMCallError, json.JSONDecodeError) as exc:
        logger.warning("M10C suggestion unavailable for visit %s: %s", visit.id, exc)
        return None

    condition_en = str(data.get("condition_en") or "").strip()
    condition_bn = str(data.get("condition_bn") or "").strip()
    if not (condition_en or condition_bn):
        logger.warning("M10C returned no condition for visit %s", visit.id)
        return None

    suggestion = SuggestedCondition(
        condition=condition_en or condition_bn,
        condition_en=condition_en,
        condition_bn=condition_bn,
        reasoning_en=str(data.get("reasoning_en") or "").strip(),
        reasoning_bn=str(data.get("reasoning_bn") or "").strip(),
        source="ai",
        disclaimer=CONDITION_DISCLAIMER,
        disclaimer_bn=CONDITION_DISCLAIMER_BN,
    ).model_dump()
    entities = dict(profile.entities or {})
    entities["suggested_condition"] = suggestion
    profile.entities = entities
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    return suggestion
