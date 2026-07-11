"""P4-1 (ADR-0045) — real OTP: issue/verify security properties + the sender seam.

Fully offline (in-memory DB via dependency override; the sender is a recording
fake — no SMS, no network). Covers: the happy path with a REAL code (hash-only
storage + audit), expiry, wrong-code attempts, single-use, the bypass matrix
(dev-only — structurally impossible under textbee), max-attempt lockout,
resend throttling, send-failure voiding, sender selection, and the TextBee
HTTP contract.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings
from backend.app.db.database import Base, get_db
from backend.app.db.models import AuditLog, OtpCode
from backend.app.main import app
from backend.app.services.otp import (
    DevLogSender,
    OtpSendError,
    TextBeeSender,
    get_sender,
)

PHONE = "01712345678"
NORM = "+8801712345678"


class RecordingSender:
    channel = "fake"

    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send(self, phone: str, code: str) -> None:
        self.sent.append((phone, code))


@pytest.fixture()
def env(monkeypatch):
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
    sender = RecordingSender()
    monkeypatch.setattr(
        "backend.app.services.otp.service.get_sender", lambda settings=None: sender
    )
    # No `with` -> don't trigger the app lifespan (which would migrate the real DB).
    yield TestClient(app), TestSession, sender
    app.dependency_overrides.clear()


def _settings(monkeypatch, **overrides):
    fake = get_settings().model_copy(update=overrides)
    monkeypatch.setattr("backend.app.services.otp.service.get_settings", lambda: fake)
    return fake


def _lookup(client, phone=PHONE):
    r = client.post("/api/patients/lookup", json={"phone": phone})
    assert r.status_code == 200
    return r.json()


def _verify(client, otp, phone=PHONE):
    return client.post("/api/patients/verify-otp", json={"phone": phone, "otp": otp})


def _backdate(TestSession, *, created_by: int | None = None, expire: bool = False):
    """Shift the newest outstanding code back in time (SQLite stores naive UTC)."""
    db = TestSession()
    row = db.query(OtpCode).order_by(OtpCode.id.desc()).first()
    if created_by is not None:
        row.created_at = datetime.now(timezone.utc) - timedelta(seconds=created_by)
    if expire:
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    db.close()


# --- happy path -----------------------------------------------------------------


def test_real_code_verifies_and_only_a_hash_is_stored(env):
    client, TestSession, sender = env
    body = _lookup(client)
    assert body["otp_sent"] is True and body["retry_after_seconds"] is None

    # Exactly one send, to the normalized phone, with a 6-digit non-bypass code.
    assert len(sender.sent) == 1
    phone, code = sender.sent[0]
    assert phone == NORM
    assert code.isdigit() and len(code) == 6 and code != "000000"

    db = TestSession()
    row = db.query(OtpCode).one()
    assert row.phone == NORM and row.patient_id == body["patient"]["id"]
    assert code not in (row.code_hash, row.salt)  # plaintext never persisted
    assert row.consumed_at is None
    # The issue is audited — but the audit row must never contain the code.
    issued = db.query(AuditLog).filter(AuditLog.action == "otp_issued").all()
    assert len(issued) == 1 and code not in str(issued[0].detail)
    db.close()

    r = _verify(client, code)
    assert r.status_code == 200
    assert r.json()["visit"]["status"] == "in_progress"

    db = TestSession()
    assert db.query(OtpCode).one().consumed_at is not None
    db.close()


# --- wrong code / expiry / single-use --------------------------------------------


def test_wrong_code_401_increments_attempts_then_correct_code_still_works(env):
    client, TestSession, sender = env
    _lookup(client)
    code = sender.sent[0][1]
    wrong = "999999" if code != "999999" else "888888"

    assert _verify(client, wrong).status_code == 401

    db = TestSession()
    assert db.query(OtpCode).one().attempts == 1
    db.close()

    assert _verify(client, code).status_code == 200


def test_expired_code_is_rejected(env):
    client, TestSession, sender = env
    _lookup(client)
    code = sender.sent[0][1]
    _backdate(TestSession, expire=True)
    assert _verify(client, code).status_code == 401


def test_code_is_single_use(env):
    client, TestSession, sender = env
    _lookup(client)
    code = sender.sent[0][1]
    assert _verify(client, code).status_code == 200
    assert _verify(client, code).status_code == 401  # consumed


# --- the 000000 bypass matrix -----------------------------------------------------


def test_bypass_works_on_dev_channel_even_without_an_issued_code(env):
    client, _, _ = env  # default settings: otp_channel=dev, otp_dev_bypass=true
    assert _verify(client, "000000").status_code == 200


def test_bypass_rejected_when_flag_disabled(env, monkeypatch):
    client, _, _ = env
    _settings(monkeypatch, otp_dev_bypass=False)
    assert _verify(client, "000000").status_code == 401


def test_bypass_structurally_impossible_on_textbee_channel(env, monkeypatch):
    client, _, _ = env
    # Even with the bypass flag ON, a non-dev channel must reject 000000.
    _settings(monkeypatch, otp_channel="textbee", otp_dev_bypass=True)
    assert _verify(client, "000000").status_code == 401


# --- lockout ----------------------------------------------------------------------


def test_lockout_after_max_attempts_even_for_the_correct_code(env):
    client, TestSession, sender = env
    _lookup(client)
    code = sender.sent[0][1]
    wrong = "999999" if code != "999999" else "888888"

    for i in range(4):
        assert _verify(client, wrong).status_code == 401
    assert _verify(client, wrong).status_code == 429  # 5th wrong attempt locks
    assert _verify(client, code).status_code == 429  # locked for the RIGHT code too

    # A fresh code (after the resend cooldown) unlocks the phone.
    _backdate(TestSession, created_by=61)
    body = _lookup(client)
    assert body["otp_sent"] is True
    new_code = sender.sent[-1][1]
    assert _verify(client, new_code).status_code == 200


# --- resend throttling ------------------------------------------------------------


def test_resend_throttled_then_new_code_invalidates_the_old_one(env):
    client, TestSession, sender = env
    _lookup(client)
    old_code = sender.sent[0][1]

    body = _lookup(client)  # inside the 60s cooldown
    assert body["otp_sent"] is False
    assert 1 <= body["retry_after_seconds"] <= 60
    assert len(sender.sent) == 1  # nothing was sent again

    _backdate(TestSession, created_by=61)
    body = _lookup(client)
    assert body["otp_sent"] is True and len(sender.sent) == 2
    new_code = sender.sent[1][1]

    if old_code != new_code:  # 1-in-a-million collision guard
        assert _verify(client, old_code).status_code == 401  # old code voided
    assert _verify(client, new_code).status_code == 200


def test_send_failure_returns_502_and_voids_the_code(env, monkeypatch):
    client, TestSession, _ = env

    class FailingSender:
        channel = "fake"

        def send(self, phone, code):
            raise OtpSendError("gateway down")

    monkeypatch.setattr(
        "backend.app.services.otp.service.get_sender", lambda settings=None: FailingSender()
    )
    r = client.post("/api/patients/lookup", json={"phone": PHONE})
    assert r.status_code == 502

    db = TestSession()
    row = db.query(OtpCode).one()
    assert row.expires_at <= row.created_at  # undelivered -> not verifiable
    db.close()


# --- sender selection + TextBee contract -------------------------------------------


def test_get_sender_selects_by_channel():
    base = get_settings()
    assert isinstance(get_sender(base.model_copy(update={"otp_channel": "dev"})), DevLogSender)
    assert isinstance(
        get_sender(
            base.model_copy(
                update={
                    "otp_channel": "textbee",
                    "textbee_api_key": "k",
                    "textbee_device_id": "d1",
                }
            )
        ),
        TextBeeSender,
    )
    with pytest.raises(OtpSendError):  # textbee without credentials -> clear error
        get_sender(base.model_copy(update={"otp_channel": "textbee"}))
    with pytest.raises(ValueError):
        get_sender(base.model_copy(update={"otp_channel": "smoke-signals"}))


def test_textbee_builds_the_documented_request(monkeypatch):
    captured = {}

    class OkResponse:
        status_code = 200
        text = ""

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json)
        return OkResponse()

    monkeypatch.setattr("backend.app.services.otp.textbee.httpx.post", fake_post)
    sender = TextBeeSender(
        api_key="k", device_id="d1", base_url="https://api.textbee.dev/api/v1/", ttl_minutes=5
    )
    sender.send(NORM, "123456")

    assert captured["url"] == "https://api.textbee.dev/api/v1/gateway/devices/d1/send-sms"
    assert captured["headers"] == {"x-api-key": "k"}
    assert captured["json"]["recipients"] == [NORM]
    assert "123456" in captured["json"]["message"] and "5 minutes" in captured["json"]["message"]


def test_textbee_maps_http_and_network_errors_to_otp_send_error(monkeypatch):
    class Rejected:
        status_code = 500
        text = "boom"

    monkeypatch.setattr(
        "backend.app.services.otp.textbee.httpx.post", lambda *a, **k: Rejected()
    )
    sender = TextBeeSender(api_key="k", device_id="d1", base_url="http://x", ttl_minutes=5)
    with pytest.raises(OtpSendError):
        sender.send(NORM, "123456")

    def explode(*a, **k):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr("backend.app.services.otp.textbee.httpx.post", explode)
    with pytest.raises(OtpSendError):
        sender.send(NORM, "123456")
