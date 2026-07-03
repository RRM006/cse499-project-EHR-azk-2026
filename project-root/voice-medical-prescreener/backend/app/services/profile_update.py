"""M8 — response processing & profile update (Flash-Lite bucket, ADR-0026).

After a voice answer lands, the whole conversation is re-extracted (same strict
prompt as M3, logged under module_code M8) and merged into the profile:
human-edited fields are NEVER overwritten by the AI; the answered gap moves from
missing -> present. Raw utterances are only read (rule #1).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.db.models import CaseProfile, FollowupQuestion, Utterance, Visit
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
from backend.app.services.completion import completeness_score
from backend.app.services.intake import (
    _EXTRACT_SYSTEM,
    _conversation_text,
    _parse_json,
    _to_summary_fields,
)
from backend.app.services.llm_client import call_module


def _merge_fields(existing: dict, fresh: dict) -> dict:
    """Merge a fresh AI extraction over the existing summary_fields: fields a human
    edited keep their human value + provenance; everything else takes the AI update."""
    merged = dict(fresh)
    for key in SUMMARY_FIELD_KEYS:
        old = existing.get(key) or {}
        if old.get("source") == "human":
            merged[key] = old
    return merged


def process_answer(
    db: Session, *, visit: Visit, question: FollowupQuestion, answer: Utterance
) -> CaseProfile:
    """Link the voice answer to its question, re-extract (M8), merge, and rescore (M9)."""
    question.answer_utterance_id = answer.id
    question.answered_at = datetime.now(timezone.utc)
    db.commit()

    profile = db.query(CaseProfile).filter(CaseProfile.visit_id == visit.id).first()
    if profile is None:
        profile = CaseProfile(visit_id=visit.id)
        db.add(profile)

    reply = call_module(
        db, visit_id=visit.id, module_code="M8",
        system=_EXTRACT_SYSTEM, user=_conversation_text(db, visit),
    )
    fresh = _to_summary_fields(_parse_json(reply)).model_dump(mode="json")
    existing = (profile.entities or {}).get("summary_fields") or {}
    profile.entities = {"summary_fields": _merge_fields(existing, fresh)}

    # The answered gap moves from missing -> present (M6 checklist upkeep).
    gaps = dict(profile.gaps or {"present": [], "missing": []})
    if question.target_gap:
        gaps["missing"] = [m for m in (gaps.get("missing") or []) if m != question.target_gap]
        present = list(gaps.get("present") or [])
        if question.target_gap not in present:
            present.append(question.target_gap)
        gaps["present"] = present
    profile.gaps = gaps

    profile.completeness_score = completeness_score(profile)  # M9, local
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile
