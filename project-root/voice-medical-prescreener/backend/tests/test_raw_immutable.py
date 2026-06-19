"""Guard test for constitution rule #1: the raw transcript is never modified.

Uses an isolated in-memory SQLite database so it runs identically on Windows and
Linux with no setup and no .env / real DB file required.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db import repository as repo
from backend.app.db.database import Base
from backend.app.db.models import Utterance


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, future=True)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


def test_create_raw_stores_text_verbatim(db):
    raw = "  Amar pet betha korche  "  # leading/trailing spaces must be preserved
    utt = repo.create_raw(db, raw_text=raw, source="manual")

    assert utt.id is not None
    assert utt.raw_text == raw  # exactly — no trim, no normalize
    assert utt.corrected_text is None
    assert utt.source == "manual"


def test_set_correction_never_touches_raw(db):
    raw = "জ্বর তিন দিন ধরে"
    utt = repo.create_raw(db, raw_text=raw)

    repo.set_correction(
        db,
        utterance_id=utt.id,
        corrected_text="জ্বর তিন দিন ধরে।",
        provider="gemini",
        model="gemini-flash-latest",
    )

    refreshed = db.get(Utterance, utt.id)
    assert refreshed.raw_text == raw  # raw is untouched
    assert refreshed.corrected_text == "জ্বর তিন দিন ধরে।"
    assert refreshed.corrected_text != refreshed.raw_text
    assert refreshed.correction_provider == "gemini"
    assert refreshed.corrected_at is not None


def test_repository_exposes_no_raw_mutator():
    """There must be no function that rewrites the raw transcript."""
    forbidden = {"update_raw", "set_raw", "edit_raw", "modify_raw", "overwrite_raw", "delete_raw"}
    public = {name for name in dir(repo) if not name.startswith("_")}
    assert forbidden.isdisjoint(public), f"raw-mutating function found: {forbidden & public}"
