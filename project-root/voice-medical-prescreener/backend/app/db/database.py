"""SQLAlchemy engine, session factory, and Base.

SQLite for Phase 0; the URL is config-driven (see config.resolved_database_url)
so swapping to Postgres later needs no code change here.
"""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.app.core.config import get_settings

_settings = get_settings()
_db_url = _settings.resolved_database_url

# check_same_thread=False is required for SQLite under a threaded ASGI server.
_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}

engine = create_engine(_db_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# backend/app/db/database.py -> parents[2] == the backend/ dir (where alembic.ini lives).
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"
_BASELINE_REVISION = "0001_baseline"
_REV_0002 = "0002_add_stt_provider_and_doc_kind"


def _alembic_config():
    """Alembic config wired to the SAME database URL the app uses (no hardcoding)."""
    from alembic.config import Config

    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", _db_url)
    return cfg


def _legacy_stamp_revision() -> str:
    """Pick the stamp for a pre-Alembic DB by looking at what columns it actually has.

    Old ``create_all`` DBs come in mixed states, because create_all built whatever the
    models looked like at the time and never altered existing tables:
      * neither stt_provider nor kind  -> true 0001 baseline;
      * both stt_provider and kind     -> already at 0002 level;
      * stt_provider but NOT kind      -> in-between (Session-3-era models): add the one
        missing column in place (same DDL as 0002), then treat it as 0002.
    Stamping 0001 blindly here crashed with ``duplicate column name: stt_provider``.
    """
    from sqlalchemy import text

    insp = inspect(engine)
    utt_cols = {c["name"] for c in insp.get_columns("utterances")}
    doc_cols = {c["name"] for c in insp.get_columns("documents")} if "documents" in insp.get_table_names() else set()

    if "stt_provider" not in utt_cols:
        return _BASELINE_REVISION
    if "kind" not in doc_cols:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE documents ADD COLUMN kind VARCHAR(16) NOT NULL DEFAULT 'combined'")
            )
    return _REV_0002


def run_migrations() -> None:
    """Bring the schema to ``head`` in place, preserving existing data.

    Handles three states:
      * fresh DB (no tables)      -> run every migration from 0001;
      * legacy DB (tables exist,  -> stamp the revision matching its ACTUAL columns
        but no alembic_version)       (see _legacy_stamp_revision), then upgrade;
      * already-migrated DB       -> upgrade applies only what's pending / no-ops.
    """
    from alembic import command

    cfg = _alembic_config()
    tables = set(inspect(engine).get_table_names())
    if "alembic_version" not in tables and "utterances" in tables:
        command.stamp(cfg, _legacy_stamp_revision())
    command.upgrade(cfg, "head")


def init_db() -> None:
    """Run pending migrations at app startup (replaces the old create_all path)."""
    from backend.app.db import models  # noqa: F401  (import registers models on Base)

    run_migrations()


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
