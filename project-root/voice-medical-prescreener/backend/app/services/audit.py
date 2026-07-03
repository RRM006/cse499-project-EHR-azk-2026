"""BE-7 — one-line audit writer. Every state-changing route calls this (rule #4 +
medical accountability). Append-only; auditing a new thing = a new action string.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.db.models import AuditLog


def audit(
    db: Session,
    *,
    action: str,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    actor_id: int | None = None,
    clinic_id: int | None = None,
    detail: dict | None = None,
) -> None:
    """Best-effort append (commits with the caller's transaction)."""
    db.add(
        AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            actor_id=actor_id,
            clinic_id=clinic_id,
            detail=detail,
        )
    )
    db.commit()
