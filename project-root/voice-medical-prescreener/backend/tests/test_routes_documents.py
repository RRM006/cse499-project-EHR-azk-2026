"""End-to-end route checks for the two-document workflow — fully offline.

Uses an in-memory DB (via a dependency override), a temp-dir document storage, and
a fake corrector, so there is no network, no real .env, and no writes to the real
documents directory. Covers: save raw -> raw .docx -> detail -> correct ->
corrected .docx -> download both, plus the guard rails (404 / 400).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.main import app
from backend.app.services.documents.storage import FilesystemStorage


class _FakeCorrector:
    provider = "fake"
    model = "fake-1"

    def correct(self, raw_text: str) -> str:
        return raw_text.strip() + " (corrected)"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # StaticPool => one shared connection, so the in-memory DB survives across the
    # threadpool TestClient runs sync endpoints in.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Keep generated files out of the real documents dir.
    test_storage = FilesystemStorage(tmp_path)
    monkeypatch.setattr(
        "backend.app.services.documents.build_storage", lambda *a, **k: test_storage
    )
    monkeypatch.setattr(
        "backend.app.api.routes_documents.build_storage", lambda *a, **k: test_storage
    )
    # No live LLM call.
    monkeypatch.setattr(
        "backend.app.api.routes_transcripts.build_corrector", lambda *a, **k: _FakeCorrector()
    )

    # No `with` → don't trigger the app lifespan (which would migrate the real DB).
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_full_two_document_workflow(client):
    # 1) save RAW
    r = client.post(
        "/api/transcripts",
        json={"raw_text": "ami jor", "stt_provider": "browser_webspeech", "source": "mic"},
    )
    assert r.status_code == 200
    uid = r.json()["id"]

    # 2) generate the RAW .docx
    r = client.post(f"/api/transcripts/{uid}/documents/raw")
    assert r.status_code == 200
    raw_doc = r.json()
    assert raw_doc["kind"] == "raw"
    assert raw_doc["download_url"].endswith("/download")

    # 3) detail shows the raw doc; nothing corrected yet
    body = client.get(f"/api/transcripts/{uid}").json()
    assert body["raw_document"]["id"] == raw_doc["id"]
    assert body["corrected_document"] is None
    assert body["corrected_text"] is None

    # 4) corrected export before correction is rejected
    assert client.post(f"/api/transcripts/{uid}/documents/corrected").status_code == 400

    # 5) correct → corrected text + corrected doc; RAW unchanged (rule #1)
    detail = client.post("/api/correct", json={"utterance_id": uid}).json()
    assert detail["raw_text"] == "ami jor"
    assert detail["corrected_text"] == "ami jor (corrected)"
    assert detail["corrected_document"]["kind"] == "corrected"
    corrected_id = detail["corrected_document"]["id"]

    # 6) both files download independently as Word docs
    for doc_id in (raw_doc["id"], corrected_id):
        d = client.get(f"/api/documents/{doc_id}/download")
        assert d.status_code == 200
        assert d.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument"
        )


def test_unknown_ids_return_404(client):
    assert client.get("/api/transcripts/999999").status_code == 404
    assert client.post("/api/transcripts/999999/documents/raw").status_code == 404
    assert client.post("/api/correct", json={"utterance_id": 999999}).status_code == 404
