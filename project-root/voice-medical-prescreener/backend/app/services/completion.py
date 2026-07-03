"""M9 — case completion check. LOCAL, no API (CLAUDE.md: M9 = LOCAL / NO-API).

Completeness = the fraction of the 10 summary fields that have a non-empty value.
The loop decision (threshold / max turns) lives with the caller in followup.py.
"""

from backend.app.db.models import CaseProfile
from backend.app.schemas.profile import SUMMARY_FIELD_KEYS


def completeness_score(profile: CaseProfile | None) -> float:
    """0..1 — how many of the 10 fixed fields are filled in."""
    if profile is None or not profile.entities:
        return 0.0
    fields = profile.entities.get("summary_fields") or {}
    filled = sum(
        1
        for key in SUMMARY_FIELD_KEYS
        if str((fields.get(key) or {}).get("value") or "").strip()
    )
    return filled / len(SUMMARY_FIELD_KEYS)
