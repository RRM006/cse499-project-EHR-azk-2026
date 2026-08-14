"""DB gates for rev 0014 (patients.blood_glucose_mmol_l + context — S39, ADR-0064).

Same throwaway-SQLite-file approach as test_migration_0003/0010/0011/0012/0013.
Proves:
  * a fresh DB builds to head with BOTH columns, and both nullable — an unrecorded
    reading must be NULL, never 0, because 0 mmol/L is a value a chart would classify;
  * a 0013 DB with existing patient data upgrades IN PLACE and keeps its rows;
  * the CHECK constraint bites at the DATABASE level, so a context the reference module
    does not publish cannot be stored by any future caller that forgets to validate;
  * **no interpretation column exists under any spelling** — no band, class, flag or
    "is_diabetic". That absence is the rule #2 decision and is exactly the kind of
    thing a later "convenience column" would quietly undo;
  * the downgrade removes both columns cleanly.
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


def test_fresh_db_has_both_glucose_columns_nullable(tmp_path):
    engine = _fresh(tmp_path)
    cols = {c["name"]: c for c in inspect(engine).get_columns("patients")}
    assert "blood_glucose_mmol_l" in cols
    assert "blood_glucose_context" in cols
    assert cols["blood_glucose_mmol_l"]["nullable"] is True, (
        "an unrecorded reading must be NULL — 0 mmol/L is a value, not an absence"
    )
    assert cols["blood_glucose_context"]["nullable"] is True


def test_no_interpretation_is_ever_stored(tmp_path):
    """Rule #2 / ADR-0060: the value is stored, the published chart is displayed, and a
    clinician reads one against the other. Nothing persists a verdict."""
    engine = _fresh(tmp_path)
    cols = {c["name"].lower() for c in inspect(engine).get_columns("patients")}
    for banned in ("band", "diabet", "glucose_class", "glucose_level", "is_high",
                   "interpretation", "glucose_status"):
        assert not any(banned in c for c in cols), f"a '{banned}' column appeared"


#: One patient INSERT with every NOT NULL column supplied, so the ONLY thing that can
#: make it fail is the CHECK constraint under test. Two earlier drafts of this test
#: passed for the wrong reason — a missing ``created_at`` raised IntegrityError and
#: ``pytest.raises`` was satisfied without the constraint ever being consulted.
_INSERT_PATIENT = (
    "INSERT INTO patients (id, clinic_id, consent, created_at, "
    "blood_glucose_mmol_l, blood_glucose_context) "
    "VALUES (:id, 1, 0, '2026-08-14 00:00:00', :value, :context)"
)


def test_the_context_check_constraint_bites(tmp_path):
    engine = _fresh(tmp_path)
    # Migration 0003 already seeds the single-tenant clinic; reuse it rather than
    # colliding with its primary key.
    with engine.begin() as conn:
        conn.execute(text(_INSERT_PATIENT),
                     {"id": 1, "value": 6.4, "context": "fasting"})

    for bad_context in ("after lunch", "hba1c"):
        # HbA1c is published on the chart but is a PERCENTAGE, not mmol/L — the
        # database refuses it in this column for the same reason the schema does.
        with pytest.raises(IntegrityError) as excinfo:
            with engine.begin() as conn:
                conn.execute(text(_INSERT_PATIENT),
                             {"id": 99, "value": 6.5, "context": bad_context})
        assert "ck_patients_glucose_context" in str(excinfo.value), (
            f"'{bad_context}' was refused, but not by the CHECK constraint"
        )

    # A NULL context alongside a NULL value is legitimate — most patients have no
    # reading, and the constraint must not turn that into an error.
    with engine.begin() as conn:
        conn.execute(text(_INSERT_PATIENT),
                     {"id": 2, "value": None, "context": None})


def test_upgrade_in_place_keeps_existing_patient_rows(tmp_path):
    url = f"sqlite:///{(tmp_path / 'existing.db').as_posix()}"
    cfg = _cfg(url)
    command.upgrade(cfg, "0013_height_and_clinical_notes")
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        # Migration 0003 already seeds the single-tenant clinic; reuse it rather
        # than colliding with its primary key.
        conn.execute(text(
            "INSERT OR IGNORE INTO clinics (id, name, created_at) "
            "VALUES (1, 'C', '2026-08-14 00:00:00')"
        ))
        conn.execute(text(
            "INSERT INTO patients (id, clinic_id, external_ref, display_name, "
            "weight_kg, height_cm, consent, created_at) "
            "VALUES (1, 1, '+8801700000000', 'Existing', 61.5, 158.0, 0, "
            "'2026-08-14 00:00:00')"
        ))
    command.upgrade(cfg, "head")

    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        row = conn.execute(text(
            "SELECT display_name, weight_kg, height_cm, blood_glucose_mmol_l, "
            "blood_glucose_context FROM patients WHERE id = 1"
        )).one()
    assert row[0] == "Existing" and row[1] == 61.5 and row[2] == 158.0
    assert row[3] is None and row[4] is None, "an upgrade must not invent a reading"


def test_downgrade_removes_both_columns(tmp_path):
    url = f"sqlite:///{(tmp_path / 'down.db').as_posix()}"
    cfg = _cfg(url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0013_height_and_clinical_notes")
    cols = {c["name"] for c in inspect(create_engine(url, future=True)).get_columns("patients")}
    assert "blood_glucose_mmol_l" not in cols
    assert "blood_glucose_context" not in cols
    assert "height_cm" in cols, "the downgrade must not take rev 0013 with it"
