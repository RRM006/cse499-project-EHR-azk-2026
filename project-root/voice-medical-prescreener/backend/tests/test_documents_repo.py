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
        filename="raw-session-1.docx",
        rel_path="abc.docx",
        kind="raw",
        doc_format="docx",
    )

    assert doc.id  # a UUID was assigned
    assert doc.utterance_id == utt.id
    assert doc.kind == "raw"

    assert repo.get_document(db, doc.id) is not None
    listed = repo.list_documents(db, limit=10)
    assert [d.id for d in listed] == [doc.id]


def test_get_latest_document_returns_newest_of_each_kind(db):
    utt = repo.create_raw(db, raw_text="জ্বর", source="mic")
    repo.create_document(db, utterance_id=utt.id, filename="r1", rel_path="r1", kind="raw")
    newer_raw = repo.create_document(
        db, utterance_id=utt.id, filename="r2", rel_path="r2", kind="raw"
    )
    corrected = repo.create_document(
        db, utterance_id=utt.id, filename="c1", rel_path="c1", kind="corrected"
    )

    assert repo.get_latest_document(db, utterance_id=utt.id, kind="raw").id == newer_raw.id
    assert repo.get_latest_document(db, utterance_id=utt.id, kind="corrected").id == corrected.id


def test_generate_session_document_writes_separate_raw_and_corrected(db, tmp_path):
    storage = FilesystemStorage(tmp_path)
    utt = repo.create_raw(db, raw_text="ami jor onuvob korchi", source="mic")
    repo.set_correction(
        db, utterance_id=utt.id, corrected_text="আমি জ্বর অনুভব করছি", provider="gemini"
    )
    db.refresh(utt)

    raw_doc = generate_session_document(db, utt, kind="raw", storage=storage)
    cor_doc = generate_session_document(db, utt, kind="corrected", storage=storage)

    # Two independent rows + files, one per kind.
    assert {raw_doc.kind, cor_doc.kind} == {"raw", "corrected"}
    assert raw_doc.id != cor_doc.id
    for doc in (raw_doc, cor_doc):
        assert doc.format == "docx"
        assert doc.utterance_id == utt.id
        assert storage.exists(doc.rel_path)
        assert (tmp_path / doc.rel_path).is_file()
        assert doc.rel_path == f"{doc.id}.docx"
