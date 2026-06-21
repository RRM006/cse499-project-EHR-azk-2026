"""Offline checks for the documents repository + generation orchestrator.

Uses an isolated in-memory SQLite DB and a temp-dir filesystem storage, so it runs
identically on Windows and Linux with no .env, no network, and no writes into the
real documents directory.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db import repository as repo
from backend.app.db.database import Base
from backend.app.services.documents import generate_session_document
from backend.app.services.documents.storage import FilesystemStorage


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


def test_create_list_get_document_round_trip(db):
    utt = repo.create_raw(db, raw_text="জ্বর", source="mic")

    doc = repo.create_document(
        db,
        utterance_id=utt.id,
        filename="session-1.docx",
        rel_path="abc.docx",
        doc_format="docx",
    )

    assert doc.id  # a UUID was assigned
    assert doc.utterance_id == utt.id

    assert repo.get_document(db, doc.id) is not None
    listed = repo.list_documents(db, limit=10)
    assert [d.id for d in listed] == [doc.id]


def test_generate_session_document_writes_file_and_row(db, tmp_path):
    storage = FilesystemStorage(tmp_path)
    utt = repo.create_raw(db, raw_text="ami jor onuvob korchi", source="mic")
    repo.set_correction(
        db, utterance_id=utt.id, corrected_text="আমি জ্বর অনুভব করছি", provider="gemini"
    )
    db.refresh(utt)

    doc = generate_session_document(db, utt, doc_format="docx", storage=storage)

    # DB row recorded
    assert doc.format == "docx"
    assert doc.utterance_id == utt.id
    # File actually written under the (temp) storage root, named by the doc id
    assert storage.exists(doc.rel_path)
    assert (tmp_path / doc.rel_path).is_file()
    assert doc.rel_path == f"{doc.id}.docx"
