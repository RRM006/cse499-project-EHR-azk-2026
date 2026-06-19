"""Repository: the ONLY sanctioned write paths for utterances.

There are deliberately two writers:
  * create_raw()      -> inserts the raw transcript, write-once.
  * set_correction()  -> attaches a correction, touching ONLY the corrected_* fields.

There is intentionally NO function that updates raw_text. This enforces
constitution rule #1 (the patient's exact words are never modified) in code,
and the test in backend/tests/test_raw_immutable.py guards it.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.db.models import Utterance


def create_raw(db: Session, *, raw_text: str, source: str = "mic") -> Utterance:
    """Persist the RAW transcript exactly as given (no trimming/normalizing)."""
    utterance = Utterance(raw_text=raw_text, source=source)
    db.add(utterance)
    db.commit()
    db.refresh(utterance)
    return utterance


def set_correction(
    db: Session,
    *,
    utterance_id: int,
    corrected_text: str,
    provider: str | None = None,
    model: str | None = None,
) -> Utterance:
    """Attach a correction to an existing utterance.

    Touches only corrected_text / correction metadata — never raw_text.
    """
    utterance = db.get(Utterance, utterance_id)
    if utterance is None:
        raise ValueError(f"Utterance {utterance_id} not found")

    utterance.corrected_text = corrected_text
    utterance.correction_provider = provider
    utterance.correction_model = model
    utterance.corrected_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(utterance)
    return utterance


def get_recent(db: Session, *, limit: int = 50) -> list[Utterance]:
    """Most recent utterances first (for sample collection / verification)."""
    return (
        db.query(Utterance)
        .order_by(Utterance.created_at.desc())
        .limit(limit)
        .all()
    )
