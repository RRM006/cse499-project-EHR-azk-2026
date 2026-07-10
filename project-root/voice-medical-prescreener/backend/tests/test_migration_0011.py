"""DB gates for rev 0011 (visits.submitted_at — P3-1, 2.0 build).

Same throwaway-SQLite-file approach as test_migration_0003/0010. Proves:
  * a fresh DB builds to head with the nullable visits.submitted_at column;
  * a 0010 DB with an existing visit upgrades in place — the row survives with
    submitted_at NULL (the frontend falls back to started_at for such rows).
"""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from backend.app.db.database import _ALEMBIC_INI


def _cfg(url: str) -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_fresh_db_has_nullable_submitted_at(tmp_path):
    url = f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    command.upgrade(_cfg(url), "head")
    engine = create_engine(url, future=True)
    cols = {c["name"]: c for c in inspect(engine).get_columns("visits")}
    assert "submitted_at" in cols
    assert cols["submitted_at"]["nullable"] is True


def test_0010_db_with_visits_upgrades_in_place(tmp_path):
    url = f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}"
    engine = create_engine(url, future=True)
    command.upgrade(_cfg(url), "0010_prescriptions_letterhead")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO visits (uuid, clinic_id, status, language, started_at) "
                "VALUES ('v-old', 1, 'awaiting_doctor', 'bn-BD', '2026-07-05 09:00:00')"
            )
        )

    command.upgrade(_cfg(url), "head")

    with engine.connect() as conn:
        status, submitted = conn.execute(
            text("SELECT status, submitted_at FROM visits WHERE uuid = 'v-old'")
        ).one()
        assert status == "awaiting_doctor" and submitted is None
