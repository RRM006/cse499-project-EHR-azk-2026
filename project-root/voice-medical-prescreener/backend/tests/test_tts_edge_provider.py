"""TTS-2 (ADR-0050) — the natural neural Bangla voice, and the fallback that keeps a
kiosk speaking when it fails.

The S29 live listen rejected espeak-ng on quality ("Too robotic"). espeak-ng is a
formant synthesizer, so that is inherent, not tunable — the fix is a different
PROVIDER, which is exactly what the ADR-0049 seam was built for.

These tests are **offline by default**: every one of them monkeypatches the network
call, because a suite that needs the internet is a suite that fails in a lab with no
wifi. The single real network test is opt-in via TTS_LIVE=1.

What they defend, in order of importance:
  1. **The seam is preserved** — adding a provider stayed one factory entry, and
     espeak-ng is still selectable and still the fallback.
  2. **Failure is never silence** — a network error falls back to the local engine, and
     if that fails too the error names BOTH providers rather than hiding one.
  3. **Nothing patient-identifying reaches the provider** — it takes one question
     string and nothing else (rule #1/#4 boundary).
"""

import os

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import TTS_PROVIDERS, Settings, get_settings
from backend.app.main import app
from backend.app.services.tts import TtsUnavailable, server_tts_available, synthesize
from backend.app.services.tts.base import MAX_TEXT_CHARS
from backend.app.services.tts.edge import EdgeTtsProvider
from backend.app.services.tts.espeak import EspeakNgProvider
from backend.app.services.tts.service import (
    PROVIDER_FACTORIES,
    get_fallback_provider,
    get_provider,
)

client = TestClient(app)

BANGLA_QUESTION = "আপনার সমস্যাটি কত দিন ধরে হচ্ছে?"
# A real MP3 frame header, long enough to clear the MIN_AUDIO_BYTES silence guard.
FAKE_MP3 = b"\xff\xf3\x64\xc4" + b"\x00" * 2000


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _use(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key.upper(), str(value))
    get_settings.cache_clear()


def _edge_returns(monkeypatch, audio: bytes):
    monkeypatch.setattr(EdgeTtsProvider, "synthesize", lambda self, text, lang: audio)


def _edge_fails(monkeypatch, message="edge-tts failed: ClientError: no route to host"):
    def boom(self, text, lang):
        raise TtsUnavailable(message)
    monkeypatch.setattr(EdgeTtsProvider, "synthesize", boom)


# --------------------------- the seam is intact ---------------------------

def test_adding_a_provider_stayed_one_registry_entry():
    """The seam's promise (ADR-0049): a new voice is a subclass + a name, not a rewrite.
    If this ever needs a route or frontend change, the seam has been broken."""
    assert set(PROVIDER_FACTORIES) == {"espeak", "edge"}
    assert "edge" in TTS_PROVIDERS and "espeak" in TTS_PROVIDERS


def test_the_neural_voice_is_the_default_but_espeak_is_one_env_value_away(monkeypatch):
    assert isinstance(get_provider(), EdgeTtsProvider)
    _use(monkeypatch, tts_provider="espeak")
    assert isinstance(get_provider(), EspeakNgProvider)
    _use(monkeypatch, tts_provider="browser")
    assert get_provider() is None


def test_a_typo_still_degrades_to_browser_rather_than_breaking_startup(monkeypatch):
    _use(monkeypatch, tts_provider="edgetts")
    assert get_settings().resolved_tts_provider == "browser"


def test_bangladeshi_voices_are_the_default_not_indian_bengali():
    """bn-IN is a noticeably different accent for a Dhaka clinic."""
    settings = Settings()
    assert settings.tts_edge_voice_bn.startswith("bn-BD-")


def test_each_language_maps_to_its_own_voice(monkeypatch):
    """An English question in a Bengali neural voice is nonsense, and vice versa."""
    _use(monkeypatch, tts_edge_voice_bn="bn-BD-PradeepNeural", tts_edge_voice_en="en-GB-SoniaNeural")
    provider = get_provider()
    assert provider._voices == {"bn": "bn-BD-PradeepNeural", "en": "en-GB-SoniaNeural"}


def test_an_unconfigured_language_raises_rather_than_guessing():
    with pytest.raises(TtsUnavailable):
        EdgeTtsProvider(voice_bn="").synthesize(BANGLA_QUESTION, "bn")


# --------------------------- MP3, and why nothing else had to change ---------------------------

def test_the_media_type_travels_with_the_provider(monkeypatch):
    """Microsoft returns MP3 where espeak returns WAV. The seam carries media_type per
    provider, which is the ONLY reason this needed no route or frontend change."""
    _edge_returns(monkeypatch, FAKE_MP3)
    audio, media_type = synthesize(BANGLA_QUESTION, "bn")
    assert media_type == "audio/mpeg"
    assert audio == FAKE_MP3


def test_the_endpoint_serves_the_providers_own_content_type(monkeypatch):
    _edge_returns(monkeypatch, FAKE_MP3)
    resp = client.get("/api/tts", params={"text": BANGLA_QUESTION, "lang": "bn"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/mpeg")
    assert "private" in resp.headers.get("cache-control", "")


# --------------------------- failure is never silence ---------------------------

def test_a_network_failure_falls_back_to_the_local_engine(monkeypatch):
    """The human's choice: a robotic question beats a silent kiosk. Proven by the
    media type flipping back to WAV — i.e. espeak actually produced the audio."""
    _edge_fails(monkeypatch)
    monkeypatch.setattr(EspeakNgProvider, "synthesize", lambda self, text, lang: b"RIFFfake")
    audio, media_type = synthesize(BANGLA_QUESTION, "bn")
    assert media_type == "audio/wav"
    assert audio == b"RIFFfake"


def test_the_fallback_can_be_switched_off(monkeypatch):
    """Some deployments prefer ADR-0049's original contract: fail loudly, show text."""
    _use(monkeypatch, tts_local_fallback="false")
    _edge_fails(monkeypatch)
    with pytest.raises(TtsUnavailable, match="edge-tts failed"):
        synthesize(BANGLA_QUESTION, "bn")


def test_espeak_does_not_fall_back_to_itself(monkeypatch):
    """Retrying the same failing engine would only slow down an honest error."""
    _use(monkeypatch, tts_provider="espeak")
    assert get_fallback_provider(get_provider()) is None


def test_when_both_fail_the_error_names_both(monkeypatch):
    """A clinic debugging silent audio must not be told only about the fallback — the
    primary's failure is the actual cause."""
    _edge_fails(monkeypatch)
    _use(monkeypatch, tts_espeak_path="C:/definitely/not/espeak-ng.exe")
    with pytest.raises(TtsUnavailable) as excinfo:
        synthesize(BANGLA_QUESTION, "bn")
    detail = str(excinfo.value)
    assert "edge" in detail and "espeak" in detail


def test_total_failure_is_still_a_503_not_a_500(monkeypatch):
    _edge_fails(monkeypatch)
    _use(monkeypatch, tts_espeak_path="C:/definitely/not/espeak-ng.exe")
    resp = client.get("/api/tts", params={"text": BANGLA_QUESTION, "lang": "bn"})
    assert resp.status_code == 503


def test_an_empty_response_is_treated_as_failure_not_played_as_audio(monkeypatch):
    """A 200 with no audible audio is indistinguishable from working TTS at the UI."""
    edge_tts = pytest.importorskip("edge_tts")
    provider = EdgeTtsProvider()
    monkeypatch.setattr(
        edge_tts, "Communicate", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
    )
    with pytest.raises(TtsUnavailable):
        provider.synthesize(BANGLA_QUESTION, "bn")


def test_blank_and_oversized_text_are_refused_before_any_network_call():
    """The cap is what stops an unauthenticated endpoint being a free proxy to
    Microsoft's TTS service."""
    provider = EdgeTtsProvider()
    for blank in ("", "   ", "\n\t"):
        with pytest.raises(TtsUnavailable):
            provider.synthesize(blank, "bn")
    with pytest.raises(TtsUnavailable):
        provider.synthesize("ক" * (MAX_TEXT_CHARS + 1), "bn")


# --------------------------- availability stays cheap ---------------------------

def test_availability_never_touches_the_network(monkeypatch):
    """server_tts_available() runs on EVERY kiosk page load. If it probed Microsoft it
    would add latency to every load and still not predict the moment of the question."""
    edge_tts = pytest.importorskip("edge_tts")
    called = []
    monkeypatch.setattr(edge_tts, "Communicate", lambda *a, **k: called.append(1))
    assert server_tts_available() is True
    assert called == []


def test_config_reports_a_capability_not_the_provider_name(monkeypatch):
    """The public /api/config must never disclose which vendor or binary is in use."""
    _use(monkeypatch, tts_edge_voice_bn="bn-BD-PradeepNeural")
    body = client.get("/api/config").json()
    assert body["server_tts"] is True
    raw = client.get("/api/config").text.lower()
    for leak in ("edge", "microsoft", "neural", "espeak", "bn-bd-"):
        assert leak not in raw


def test_server_tts_is_false_only_when_nothing_at_all_can_speak(monkeypatch):
    _use(monkeypatch, tts_provider="browser")
    assert server_tts_available() is False


# --------------------------- the privacy boundary ---------------------------

def test_the_provider_receives_one_question_and_nothing_else(monkeypatch):
    """Rule #4 boundary. Whatever was decided about sending text to Microsoft, what
    leaves must be ONLY the question — never a transcript, raw_text, or any identity."""
    seen = {}

    def capture(self, text, lang):
        seen["text"] = text
        seen["lang"] = lang
        return FAKE_MP3

    monkeypatch.setattr(EdgeTtsProvider, "synthesize", capture)
    client.get("/api/tts", params={"text": BANGLA_QUESTION, "lang": "bn"})
    assert seen == {"text": BANGLA_QUESTION, "lang": "bn"}


def test_the_local_only_provider_was_demoted_not_deleted(monkeypatch):
    """ADR-0050's escape hatch: a deployment that cannot export patient-derived text
    must still have a working, fully offline voice."""
    _use(monkeypatch, tts_provider="espeak")
    provider = get_provider()
    assert isinstance(provider, EspeakNgProvider)
    assert provider.media_type == "audio/wav"


# --------------------------- opt-in: the real network ---------------------------

@pytest.mark.skipif(os.getenv("TTS_LIVE") != "1", reason="set TTS_LIVE=1 to hit the network")
def test_live_bangla_renders_real_mp3_audio():
    """Opt-in, because CI and a lab bench may have no internet. Proves real MP3 bytes
    come back — it does NOT prove the voice sounds natural. Only the human's ears can."""
    audio, media_type = synthesize(BANGLA_QUESTION, "bn")
    assert media_type == "audio/mpeg"
    assert audio[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"ID3")
    assert len(audio) > 5000
