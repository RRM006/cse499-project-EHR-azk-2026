"""Migration checks — the fix for the live ``no column named stt_provider`` bug.

These run against throwaway SQLite FILES (not :memory:, because each Alembic command
opens its own connection). They prove both paths:
  * a LEGACY DB (old schema + data) is migrated in place, keeping its rows;
  * a FRESH DB is built from scratch to the same final schema.
"""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from backend.app.db.database import _ALEMBIC_INI


def _cfg(url: str) -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _cols(engine, table):
    return [c["name"] for c in inspect(engine).get_columns(table)]


# The exact pre-Alembic schema (what create_all produced before stt_provider/kind).
_OLD_UTTERANCES = """
CREATE TABLE utterances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_text TEXT NOT NULL,
    corrected_text TEXT,
    source VARCHAR(16) NOT NULL,
    correction_provider VARCHAR(32),
    correction_model VARCHAR(64),
    created_at DATETIME NOT NULL,
    corrected_at DATETIME
)
"""
_OLD_DOCUMENTS = """
CREATE TABLE documents (
    id VARCHAR(36) PRIMARY KEY,
    utterance_id INTEGER NOT NULL,
    format VARCHAR(8) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    rel_path VARCHAR(512) NOT NULL,
    created_at DATETIME NOT NULL
)
"""


def test_legacy_db_gains_columns_and_keeps_rows(tmp_path):
    url = f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}"
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        conn.execute(text(_OLD_UTTERANCES))
        conn.execute(text(_OLD_DOCUMENTS))
        conn.execute(
            text(
                "INSERT INTO utterances (raw_text, source, created_at) "
                "VALUES ('জ্বর তিন দিন', 'mic', '2026-06-21 09:00:00')"
            )
        )

    # Bug repro: the old table has no stt_provider yet.
    assert "stt_provider" not in _cols(engine, "utterances")

    # Mimic run_migrations()'s legacy branch: stamp baseline, then upgrade.
    cfg = _cfg(url)
    command.stamp(cfg, "0001_baseline")
    command.upgrade(cfg, "head")

    assert "stt_provider" in _cols(engine, "utterances")
    assert "kind" in _cols(engine, "documents")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM utterances")).scalar() == 1
        assert conn.execute(text("SELECT raw_text FROM utterances")).scalar() == "জ্বর তিন দিন"


def test_fresh_db_builds_full_schema(tmp_path):
    url = f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    command.upgrade(_cfg(url), "head")  # no stamp: 0001 creates, 0002 alters

    engine = create_engine(url, future=True)
    tables = set(inspect(engine).get_table_names())
    assert {"utterances", "documents", "alembic_version"} <= tables
    assert "stt_provider" in _cols(engine, "utterances")
    assert "kind" in _cols(engine, "documents")
