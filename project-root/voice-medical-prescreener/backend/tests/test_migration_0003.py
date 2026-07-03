"""DB-1 gates for rev 0003 (aggregate root + ADR-0030 deltas).

Same throwaway-SQLite-file approach as test_migration.py. Proves:
  * a legacy DB (0002-level, with data) gains the new tables, legacy utterances are
    backfilled onto synthetic closed visits, and RAW text is byte-identical (rule #1);
  * a fresh DB builds to head with the CHECK constraints actually enforcing the
    'medic' role and 'awaiting_doctor' status values;
  * the seed staff exists (1 clinic, 1 medic, 2 doctors, 1 admin).
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


def _cols(engine, table):
    return [c["name"] for c in inspect(engine).get_columns(table)]


def _fresh_engine(tmp_path, name="fresh.db"):
    url = f"sqlite:///{(tmp_path / name).as_posix()}"
    command.upgrade(_cfg(url), "head")
    return create_engine(url, future=True)


def test_legacy_db_backfills_visits_and_keeps_raw(tmp_path):
    url = f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}"
    engine = create_engine(url, future=True)
    # Build a 0002-level DB with one utterance + one document row.
    command.upgrade(_cfg(url), "0002_add_stt_provider_and_doc_kind")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO utterances (raw_text, source, created_at) "
                "VALUES ('জ্বর তিন দিন', 'mic', '2026-06-21 09:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO documents (id, utterance_id, format, kind, filename, rel_path, created_at) "
                "VALUES ('doc-1', 1, 'docx', 'raw', 'f.docx', 'f.docx', '2026-06-21 09:01:00')"
            )
        )

    command.upgrade(_cfg(url), "head")

    with engine.connect() as conn:
        # RAW unchanged (rule #1).
        assert conn.execute(text("SELECT raw_text FROM utterances")).scalar() == "জ্বর তিন দিন"
        # Utterance attached to a synthetic closed visit; document follows it.
        visit_id, seq, role = conn.execute(
            text("SELECT visit_id, seq, role FROM utterances")
        ).one()
        assert visit_id is not None and seq == 0 and role == "patient"
        assert conn.execute(
            text("SELECT status FROM visits WHERE id = :v"), {"v": visit_id}
        ).scalar() == "closed"
        assert conn.execute(text("SELECT visit_id FROM documents")).scalar() == visit_id


def test_fresh_db_has_new_tables_and_seed_staff(tmp_path):
    engine = _fresh_engine(tmp_path)
    tables = set(inspect(engine).get_table_names())
    assert {"clinics", "users", "patients", "visits"} <= tables
    for col in ("visit_id", "role", "seq"):
        assert col in _cols(engine, "utterances")
    assert "visit_id" in _cols(engine, "documents")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM clinics")).scalar() == 1
        roles = dict(
            conn.execute(text("SELECT role, count(*) FROM users GROUP BY role")).fetchall()
        )
        assert roles == {"medic": 1, "doctor": 2, "admin": 1}


def test_check_constraints_medic_and_awaiting_doctor(tmp_path):
    engine = _fresh_engine(tmp_path, "checks.db")
    with engine.begin() as conn:
        # ADR-0030 values are ACCEPTED.
        conn.execute(
            text(
                "INSERT INTO visits (uuid, clinic_id, status, language, started_at) "
                "VALUES ('v-1', 1, 'awaiting_doctor', 'bn-BD', '2026-07-03 09:00:00')"
            )
        )
    # Out-of-enum values are REJECTED.
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO visits (uuid, clinic_id, status, language, started_at) "
                    "VALUES ('v-2', 1, 'bogus', 'bn-BD', '2026-07-03 09:00:00')"
                )
            )
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (clinic_id, name, role, created_at) "
                    "VALUES (1, 'X', 'nurse', '2026-07-03 09:00:00')"
                )
            )


def test_mixed_state_legacy_db_stamps_0002(tmp_path, monkeypatch):
    """Regression: a create_all-era DB that already HAS utterances.stt_provider but
    LACKS documents.kind used to crash run_migrations() with 'duplicate column name'
    (blind stamp at 0001). _legacy_stamp_revision must fix up + stamp 0002 instead.
    """
    from backend.app.db import database as db

    url = f"sqlite:///{(tmp_path / 'mixed.db').as_posix()}"
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE utterances (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "raw_text TEXT NOT NULL, corrected_text TEXT, source VARCHAR(16) NOT NULL, "
                "stt_provider VARCHAR(32), correction_provider VARCHAR(32), "
                "correction_model VARCHAR(64), created_at DATETIME NOT NULL, corrected_at DATETIME)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE documents (id VARCHAR(36) PRIMARY KEY, utterance_id INTEGER NOT NULL, "
                "format VARCHAR(8) NOT NULL, filename VARCHAR(255) NOT NULL, "
                "rel_path VARCHAR(512) NOT NULL, created_at DATETIME NOT NULL)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO utterances (raw_text, source, created_at) "
                "VALUES ('মাথা ব্যথা', 'mic', '2026-06-25 09:00:00')"
            )
        )

    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "_db_url", url)
    db.run_migrations()

    with engine.connect() as conn:
        assert conn.execute(text("SELECT raw_text FROM utterances")).scalar() == "মাথা ব্যথা"
        assert conn.execute(text("SELECT visit_id FROM utterances")).scalar() is not None
        assert "kind" in _cols(engine, "documents")
        from alembic.script import ScriptDirectory

        head = ScriptDirectory.from_config(_cfg(url)).get_current_head()
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == head
