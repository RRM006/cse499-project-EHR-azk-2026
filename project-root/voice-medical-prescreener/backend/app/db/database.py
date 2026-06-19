"""SQLAlchemy engine, session factory, and Base.

SQLite for Phase 0; the URL is config-driven (see config.resolved_database_url)
so swapping to Postgres later needs no code change here.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.app.core.config import get_settings

_settings = get_settings()
_db_url = _settings.resolved_database_url

# check_same_thread=False is required for SQLite under a threaded ASGI server.
_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}

engine = create_engine(_db_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    """Create tables if they do not exist. Called at app startup."""
    from backend.app.db import models  # noqa: F401  (import registers models on Base)

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
