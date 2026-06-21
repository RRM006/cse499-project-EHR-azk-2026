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


def _alembic_config():
    """Alembic config wired to the SAME database URL the app uses (no hardcoding)."""
    from alembic.config import Config

    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", _db_url)
    return cfg


def run_migrations() -> None:
    """Bring the schema to ``head`` in place, preserving existing data.

    Handles three states:
      * fresh DB (no tables)      -> run 0001 (create tables) + 0002 (add columns);
      * legacy DB (tables exist,  -> stamp the baseline so upgrade does NOT try to
        but no alembic_version)       re-create them, then apply only 0002;
      * already-migrated DB       -> upgrade is a no-op.
    """
    from alembic import command

    cfg = _alembic_config()
    tables = set(inspect(engine).get_table_names())
    if "alembic_version" not in tables and "utterances" in tables:
        command.stamp(cfg, _BASELINE_REVISION)
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
