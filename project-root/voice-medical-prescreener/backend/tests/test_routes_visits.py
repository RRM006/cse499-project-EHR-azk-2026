"""BE-1 route checks — fully offline (in-memory DB via dependency override).

Covers the kiosk identification flow (phone lookup -> stub OTP -> open visit),
the visit aggregate routes, per-visit utterance ordering, raw immutability of
stored turns, and the guard rails (bad phone 400, bad OTP 401, closed-visit 409,
unknown visit 404).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.repository_visits import normalize_phone
from backend.app.main import app


@pytest.fixture()
def client():
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
    # No `with` -> don't trigger the app lifespan (which would migrate the real DB).
    yield TestClient(app)
    app.dependency_overrides.clear()
    # Expose the engine for direct DB assertions.


def test_normalize_phone_variants():
    assert normalize_phone("01715984632") == "+8801715984632"
    assert normalize_phone("8801715984632") == "+8801715984632"
    assert normalize_phone("+880 1715-984632") == "+8801715984632"
    with pytest.raises(ValueError):
        normalize_phone("12345")


def test_kiosk_flow_lookup_otp_visit_and_turns(client):
    # 1) phone lookup creates the patient (stub OTP "sent")
    r = client.post("/api/patients/lookup", json={"phone": "01715984632"})
    assert r.status_code == 200
    body = r.json()
    assert body["created"] is True and body["otp_sent"] is True
    assert body["patient"]["external_ref"] == "+8801715984632"

    # Same phone again -> found, not re-created.
    r = client.post("/api/patients/lookup", json={"phone": "+880 1715 984632"})
    assert r.json()["created"] is False

    # 2) wrong OTP rejected; right (DEV_OTP default) opens a visit
    assert client.post(
        "/api/patients/verify-otp", json={"phone": "01715984632", "otp": "999999"}
    ).status_code == 401
    r = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    assert r.status_code == 200
    visit = r.json()["visit"]
    assert visit["status"] == "in_progress" and visit["patient_id"] == body["patient"]["id"]

    # Re-verify reuses the SAME open visit (kiosk re-entry, no duplicates).
    r2 = client.post("/api/patients/verify-otp", json={"phone": "01715984632", "otp": "000000"})
    assert r2.json()["visit"]["uuid"] == visit["uuid"]

    # 3) conversation turns append in order, system + patient
    uuid = visit["uuid"]
    q = client.post(
        f"/api/visits/{uuid}/utterances",
        json={"raw_text": "আপনার সমস্যাটি খুলে বলুন তো।", "role": "system", "source": "tts", "stt_provider": None},
    )
    a = client.post(
        f"/api/visits/{uuid}/utterances",
        json={"raw_text": "চার দিন ধরে বুকে জ্বালাপোড়া ব্যথা", "role": "patient"},
    )
    assert q.status_code == a.status_code == 200
    assert (q.json()["seq"], a.json()["seq"]) == (0, 1)
    assert a.json()["raw_text"] == "চার দিন ধরে বুকে জ্বালাপোড়া ব্যথা"  # verbatim (rule #1)

    # 4) detail returns the conversation in turn order
    detail = client.get(f"/api/visits/{uuid}").json()
    assert [u["role"] for u in detail["utterances"]] == ["system", "patient"]

    # list + filter
    assert len(client.get("/api/visits", params={"status": "in_progress"}).json()) == 1
    assert client.get("/api/visits", params={"status": "reviewed"}).json() == []


def test_guard_rails(client):
    assert client.post("/api/patients/lookup", json={"phone": "12345"}).status_code == 400
    assert client.get("/api/visits/no-such-uuid").status_code == 404
    assert client.post(
        "/api/visits/no-such-uuid/utterances", json={"raw_text": "x"}
    ).status_code == 404


def test_no_utterances_after_in_progress(client):
    r = client.post("/api/patients/verify-otp", json={"phone": "01712345678", "otp": "000000"})
    uuid = r.json()["visit"]["uuid"]

    # Flip the visit past in_progress directly in the test DB.
    override = app.dependency_overrides[get_db]
    db = next(override())
    db.execute(text("UPDATE visits SET status='awaiting_review' WHERE uuid=:u"), {"u": uuid})
    db.commit()

    r = client.post(f"/api/visits/{uuid}/utterances", json={"raw_text": "late turn"})
    assert r.status_code == 409
