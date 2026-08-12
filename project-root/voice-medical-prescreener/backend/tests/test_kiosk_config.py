"""S1 of faculty Requirement 3 + 3b (ADR-0048) — the public GET /api/config route.

The kiosk reads its voice-loop mode and timings from here so a clinic can tune them
from `backend/.env` without editing JavaScript. Needs no DB and no auth, so a plain
TestClient is enough (same shape as test_routes_static.py).
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import app

client = TestClient(app)

# The COMPLETE contract. Kept explicit so that adding a secret to Settings can never
# silently start leaking through this unauthenticated endpoint.
EXPECTED_KEYS = {
    "voice_loop",
    "countdown_ms",
    "tts_guard_ms",
    "no_speech_ms",
    "max_answer_ms",
    # ADR-0049: a boolean CAPABILITY (can /api/tts actually speak?), never the
    # provider's name or its path — see test_tts_provider.py.
    "server_tts",
    # S34 (ADR-0055): read a captured SPOKEN answer back and wait for the patient to
    # accept it before storing anything.
    "answer_confirm",
    # S34 (ADR-0055): how long the review screen waits before submitting itself.
    "review_timeout_ms",
    # S35 (ADR-0056): how long the spoken phone number is read back before it is
    # accepted on its own.
    "phone_confirm_ms",
}


def _settings(monkeypatch, **overrides):
    """Repo pattern (test_otp.py): swap get_settings in the module under test."""
    fake = get_settings().model_copy(update=overrides)
    monkeypatch.setattr("backend.app.api.routes_config.get_settings", lambda: fake)


def test_config_is_public_and_returns_the_voice_first_defaults():
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    # Voice is the PRIMARY interaction (ADR-0048) — the default must be hands-free.
    assert body["voice_loop"] == "auto"
    # The visible 3-2-1 countdown IS the silence window (human's S28 decision).
    assert body["countdown_ms"] == 3000
    assert body["tts_guard_ms"] == 400
    assert body["no_speech_ms"] == 10000
    assert body["max_answer_ms"] == 120000
    # S34 (ADR-0055): a spoken answer is read back and confirmed by default — the
    # patient's one chance to hear what the machine understood before it is stored.
    assert body["answer_confirm"] is True
    # …and an unattended finished review submits itself after a minute.
    assert body["review_timeout_ms"] == 60000


def test_config_exposes_exactly_the_behavioural_knobs_and_no_secrets():
    body = client.get("/api/config").json()
    assert set(body) == EXPECTED_KEYS
    # Belt and braces: no API key or DB URL can appear under any name.
    blob = str(body).lower()
    for leaked in ("key", "token", "secret", "url", "password", "sqlite", "otp"):
        assert leaked not in blob, f"/api/config must not expose '{leaked}'"


def test_env_override_reaches_the_kiosk(monkeypatch):
    """A clinic lengthens the countdown for elderly patients — no code change."""
    _settings(monkeypatch, voice_countdown_ms=5000, voice_no_speech_ms=15000)
    body = client.get("/api/config").json()
    assert body["countdown_ms"] == 5000
    assert body["no_speech_ms"] == 15000


def test_the_read_back_gate_can_be_turned_off_by_a_clinic(monkeypatch):
    """S34 (ADR-0055): the read-back costs one tap per spoken turn. A clinic that wants
    the S25-era hands-free flow must be able to choose it from .env — the ADR-0045
    pattern: the previous behaviour is kept selectable, never deleted."""
    _settings(monkeypatch, voice_answer_confirm=False)
    assert client.get("/api/config").json()["answer_confirm"] is False


def test_the_review_auto_submit_can_be_disabled_and_never_goes_negative(monkeypatch):
    """0 means "never auto-submit" — a clinic that wants the patient to press the button
    themselves must be able to say so. A negative .env value would otherwise reach the
    kiosk as an instantly-expired timer, i.e. submit-on-arrival."""
    _settings(monkeypatch, voice_review_timeout_ms=0)
    assert client.get("/api/config").json()["review_timeout_ms"] == 0
    _settings(monkeypatch, voice_review_timeout_ms=-5000)
    assert client.get("/api/config").json()["review_timeout_ms"] == 0
    _settings(monkeypatch, voice_review_timeout_ms=90000)
    assert client.get("/api/config").json()["review_timeout_ms"] == 90000


def test_manual_mode_is_selectable(monkeypatch):
    """ADR-0045 pattern: the original tap-to-talk path stays reachable from .env."""
    _settings(monkeypatch, voice_loop="manual")
    assert client.get("/api/config").json()["voice_loop"] == "manual"


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("AUTO", "auto"),        # case-insensitive
        ("  manual  ", "manual"),  # padded .env value
        ("halfway", "auto"),     # typo -> safe voice-first default, no crash
        ("", "auto"),            # blank -> default
    ],
)
def test_voice_loop_is_normalized_and_never_breaks_startup(monkeypatch, configured, expected):
    _settings(monkeypatch, voice_loop=configured)
    assert client.get("/api/config").json()["voice_loop"] == expected
