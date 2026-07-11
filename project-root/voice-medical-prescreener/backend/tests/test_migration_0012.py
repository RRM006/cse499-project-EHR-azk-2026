"""DB gates for rev 0012 (otp_codes — P4-1 real OTP, ADR-0045).

Same throwaway-SQLite-file approach as test_migration_0003/0010/0011. Proves:
  * a fresh DB builds to head with the otp_codes table (hash column, no
    plaintext column, attempts NOT NULL default 0);
  * a 0011 DB with existing data upgrades in place — rows survive and the new
    empty otp_codes table appears.
"""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from backend.app.db.database import _ALEMBIC_INI


def _cfg(url: str) -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_fresh_db_has_otp_codes_table(tmp_path):
    url = f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    command.upgrade(_cfg(url), "head")
    engine = create_engine(url, future=True)
    cols = {c["name"]: c for c in inspect(engine).get_columns("otp_codes")}
    assert set(cols) == {
        "id",
        "phone",
        "patient_id",
        "code_hash",
        "salt",
        "attempts",
        "created_at",
        "expires_at",
        "consumed_at",
    }
    # Only a HASH is ever stored — there must be no plaintext code column.
    assert "code" not in cols
    assert cols["phone"]["nullable"] is False
    assert cols["attempts"]["nullable"] is False
    assert cols["consumed_at"]["nullable"] is True


def test_0011_db_upgrades_in_place(tmp_path):
    url = f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}"
    engine = create_engine(url, future=True)
    command.upgrade(_cfg(url), "0011_visit_submitted_at")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO visits (uuid, clinic_id, status, language, started_at) "
                "VALUES ('v-old', 1, 'in_progress', 'bn-BD', '2026-07-10 09:00:00')"
            )
        )

    command.upgrade(_cfg(url), "head")

    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM visits")).scalar_one() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM otp_codes")).scalar_one() == 0
