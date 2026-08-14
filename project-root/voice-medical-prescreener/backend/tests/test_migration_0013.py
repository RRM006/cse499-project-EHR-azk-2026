"""DB gates for rev 0013 (patients.height_cm + clinical_notes — S38, ADR-0060).

Same throwaway-SQLite-file approach as test_migration_0003/0010/0011/0012. Proves:
  * a fresh DB builds to head with the new column and the new table;
  * a 0012 DB with existing patient data upgrades IN PLACE — the existing rows survive
    with a NULL height rather than a zero, which matters because a zero height would
    silently produce an infinite BMI;
  * **no BMI column exists anywhere.** That absence is the ADR-0060 decision: BMI is a
    pure function of two stored columns, and a persisted copy would go stale the instant
    a weight was corrected. An absence is exactly the kind of property that regresses
    quietly, so it is asserted rather than assumed;
  * the CHECK constraints on ``kind`` and ``status`` actually bite — a note with a
    made-up kind must be refused by the DATABASE, not merely by the service layer.
"""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from backend.app.db.database import _ALEMBIC_INI


def _cfg(url: str) -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _fresh(tmp_path, name="fresh.db"):
    url = f"sqlite:///{(tmp_path / name).as_posix()}"
    command.upgrade(_cfg(url), "head")
    return create_engine(url, future=True)


def test_fresh_db_has_height_but_no_stored_bmi(tmp_path):
    engine = _fresh(tmp_path)
    cols = {c["name"]: c for c in inspect(engine).get_columns("patients")}
    assert "height_cm" in cols
    assert cols["height_cm"]["nullable"] is True, "an unknown height must be NULL, not 0"
    # ADR-0060: BMI is derived, never stored — under any spelling.
    assert not {c for c in cols if "bmi" in c.lower()}


def test_fresh_db_has_the_clinical_notes_table(tmp_path):
    engine = _fresh(tmp_path)
    cols = {c["name"]: c for c in inspect(engine).get_columns("clinical_notes")}
    assert set(cols) == {
        "id", "clinic_id", "visit_id", "patient_id", "author_id", "kind",
        "recipient_role", "body", "due_date", "status", "created_at",
        "resolved_at", "resolved_by",
    }
    assert cols["author_id"]["nullable"] is False, "a note must always name its author"
    assert cols["visit_id"]["nullable"] is False, "a note must always hang off a case"
    assert cols["due_date"]["nullable"] is True, "only a recall carries a due date"


def test_the_inbox_query_is_indexed(tmp_path):
    """The medic inbox filters on (recipient_role, status, kind) on every queue refresh."""
    engine = _fresh(tmp_path)
    names = {i["name"] for i in inspect(engine).get_indexes("clinical_notes")}
    assert "ix_clinical_notes_inbox" in names
    assert "ix_clinical_notes_visit_id" in names


def test_the_database_itself_refuses_an_unknown_kind_or_status(tmp_path):
    # Clinic 1 and the staff users are seeded by the baseline migration itself.
    engine = _fresh(tmp_path, "checks.db")
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO visits (id, uuid, clinic_id, status, language, started_at) "
            "VALUES (1, 'v-1', 1, 'reviewed', 'bn-BD', '2026-08-14')"
        ))

    insert = (
        "INSERT INTO clinical_notes "
        "(clinic_id, visit_id, author_id, kind, body, status, created_at) "
        "VALUES (1, 1, 1, :kind, 'text', :status, '2026-08-14')"
    )
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text(insert), {"kind": "chat_message", "status": "open"})
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text(insert), {"kind": "recall", "status": "archived"})
    # ...and the two legitimate kinds go in.
    with engine.begin() as conn:
        conn.execute(text(insert), {"kind": "recall", "status": "open"})
        conn.execute(text(insert), {"kind": "handover_note", "status": "done"})


def test_0012_db_upgrades_in_place(tmp_path):
    url = f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}"
    engine = create_engine(url, future=True)
    command.upgrade(_cfg(url), "0012_otp_codes")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO patients (id, clinic_id, display_name, weight_kg, consent, created_at) "
                "VALUES (7, 1, 'Kamal', 68.5, 1, '2026-08-01')"
            )
        )

    command.upgrade(_cfg(url), "head")

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT display_name, weight_kg, height_cm FROM patients WHERE id = 7")
        ).one()
        assert row.display_name == "Kamal"
        assert row.weight_kg == 68.5
        assert row.height_cm is None, "an existing patient has no recorded height, not a 0"
        assert conn.execute(text("SELECT COUNT(*) FROM clinical_notes")).scalar_one() == 0


def test_downgrade_removes_both_additions(tmp_path):
    url = f"sqlite:///{(tmp_path / 'down.db').as_posix()}"
    command.upgrade(_cfg(url), "head")
    command.downgrade(_cfg(url), "0012_otp_codes")
    engine = create_engine(url, future=True)
    inspector = inspect(engine)
    assert "clinical_notes" not in inspector.get_table_names()
    assert "height_cm" not in {c["name"] for c in inspector.get_columns("patients")}
