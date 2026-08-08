"""ADR-0049 — the server-side Bangla TTS fallback seam.

WHY IT EXISTS: Windows ships no Bengali voice at all (verified against Microsoft's
supported-languages list), so the browser can never speak Bangla there. These tests
cover provider selection, bn/en handling, and — most importantly — that a missing or
broken engine FAILS LOUDLY (503) instead of returning silence that the UI would
present as working Bangla audio.

⚠ These tests do not and cannot prove the audio is audible or intelligible. Whether
espeak-ng's Bengali is understandable to a Bangladeshi patient is answerable only by
the human's live run.
"""

import wave
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings, get_settings
from backend.app.main import app
from backend.app.services.tts import TtsUnavailable, server_tts_available, synthesize
from backend.app.services.tts.base import MAX_TEXT_CHARS
from backend.app.services.tts.edge import EdgeTtsProvider
from backend.app.services.tts.espeak import EspeakNgProvider
from backend.app.services.tts.service import get_provider

client = TestClient(app)

BANGLA_QUESTION = "আপনার সমস্যাটি কত দিন ধরে হচ্ছে?"


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Settings are lru_cached; each test may set its own env."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _use(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key.upper(), str(value))
    get_settings.cache_clear()


# --------------------------- provider selection ---------------------------

def test_edge_is_the_default_provider_since_adr_0050():
    """TTS-2: naturalness was the whole point, so the neural voice is the default and
    espeak-ng became the offline/private option + the automatic fallback."""
    assert Settings().resolved_tts_provider == "edge"
    assert isinstance(get_provider(), EdgeTtsProvider)


def test_espeak_is_still_selectable_for_an_offline_or_private_deployment(monkeypatch):
    """ADR-0050 DEMOTED espeak-ng; it must not have been deleted — it is the only
    provider that keeps patient-derived question text on the machine (rule #4)."""
    _use(monkeypatch, tts_provider="espeak")
    assert isinstance(get_provider(), EspeakNgProvider)


def test_provider_can_be_switched_off_without_deleting_code(monkeypatch):
    """TTS_PROVIDER=browser restores the exact pre-ADR-0049 behaviour (ADR-0045
    pattern: the old path is never removed, only unselected)."""
    _use(monkeypatch, tts_provider="browser")
    assert get_provider() is None
    assert server_tts_available() is False
    with pytest.raises(TtsUnavailable):
        synthesize(BANGLA_QUESTION, "bn")


def test_a_typo_in_env_degrades_to_browser_instead_of_crashing_startup(monkeypatch):
    """Same forgiving contract as resolved_voice_loop — a bad .env value must never
    stop a clinic's kiosk from booting."""
    _use(monkeypatch, tts_provider="Espeek")
    assert get_settings().resolved_tts_provider == "browser"


def test_provider_selection_is_case_and_space_insensitive(monkeypatch):
    _use(monkeypatch, tts_provider="  ESPEAK  ")
    assert get_settings().resolved_tts_provider == "espeak"


# --------------------------- language handling ---------------------------

def test_only_bn_and_en_are_accepted():
    """An unsupported language must be refused, not silently rendered in Bangla."""
    with pytest.raises(TtsUnavailable):
        synthesize("hello", "fr")
    resp = client.get("/api/tts", params={"text": "hello", "lang": "fr"})
    assert resp.status_code == 422


def test_each_language_maps_to_its_own_configured_voice(monkeypatch):
    """An English question handed to a Bengali voice is nonsense, so the mapping is
    explicit and .env-driven rather than assumed."""
    _use(monkeypatch, tts_voice_bn="bn", tts_voice_en="en-us")
    settings = get_settings()
    provider = EspeakNgProvider(
        voice_bn=settings.tts_voice_bn, voice_en=settings.tts_voice_en
    )
    assert provider._voices == {"bn": "bn", "en": "en-us"}


def test_an_unconfigured_language_raises_rather_than_guessing():
    provider = EspeakNgProvider(voice_bn="", voice_en="en-us")
    with pytest.raises(TtsUnavailable):
        provider.synthesize(BANGLA_QUESTION, "bn")


# --------------------------- failure is loud, never silent ---------------------------

def test_a_missing_engine_raises_instead_of_returning_silence():
    """The whole point: a silent 200 is indistinguishable from working audio at the
    UI, and would hide a broken kiosk from the clinic."""
    provider = EspeakNgProvider(binary="C:/definitely/not/espeak-ng.exe")
    assert provider.resolve_binary() is None
    with pytest.raises(TtsUnavailable):
        provider.synthesize(BANGLA_QUESTION, "bn")


def test_a_missing_engine_is_reported_as_503_not_500(monkeypatch):
    """503 = valid request, engine unavailable. The kiosk then keeps the on-screen
    text (ADR-0028) instead of pretending Bangla played."""
    _use(monkeypatch, tts_provider="espeak", tts_espeak_path="C:/nope/espeak-ng.exe")
    resp = client.get("/api/tts", params={"text": BANGLA_QUESTION, "lang": "bn"})
    assert resp.status_code == 503
    assert "espeak" in resp.json()["detail"].lower()


def test_blank_text_is_refused_at_both_layers():
    provider = EspeakNgProvider()
    for blank in ("", "   ", "\n\t"):
        with pytest.raises(TtsUnavailable):
            provider.synthesize(blank, "bn")
    assert client.get("/api/tts", params={"text": "", "lang": "bn"}).status_code == 422


def test_an_unauthenticated_endpoint_bounds_how_much_work_one_caller_can_ask_for():
    """/api/tts has no auth (the kiosk needs it pre-login), so the length cap is what
    stops it being a free CPU-burning endpoint."""
    over = "ক" * (MAX_TEXT_CHARS + 1)
    assert client.get("/api/tts", params={"text": over, "lang": "bn"}).status_code == 422
    with pytest.raises(TtsUnavailable):
        EspeakNgProvider().synthesize(over, "bn")


# --------------------------- the /api/config capability flag ---------------------------

def test_config_reports_whether_audio_is_really_possible(monkeypatch):
    """server_tts must reflect the ENGINE's presence, not merely the setting — the
    kiosk uses it to decide whether a fallback exists and whether to warn the patient."""
    _use(monkeypatch, tts_provider="espeak", tts_espeak_path="C:/nope/espeak-ng.exe")
    assert client.get("/api/config").json()["server_tts"] is False
    _use(monkeypatch, tts_provider="browser")
    assert client.get("/api/config").json()["server_tts"] is False


def test_config_still_leaks_no_paths_keys_or_provider_names(monkeypatch):
    """The S1 guard, re-asserted now that TTS settings exist: /api/config is public and
    must carry behaviour only. A provider NAME or a filesystem path would be an
    infrastructure disclosure."""
    _use(monkeypatch, tts_espeak_path="C:/secret/path/espeak-ng.exe")
    body = client.get("/api/config").json()
    assert set(body) == {
        "voice_loop", "countdown_ms", "tts_guard_ms", "no_speech_ms",
        "max_answer_ms", "server_tts",
    }
    raw = client.get("/api/config").text
    for leak in ("espeak", "secret", "path", ".exe"):
        assert leak not in raw.lower()


# --------------------------- real audio, only when installed ---------------------------

def _engine_installed() -> bool:
    return EspeakNgProvider().resolve_binary() is not None


# ADR-0050 note: these pin espeak-ng EXPLICITLY. They used to rely on it being the
# default; now that `edge` is, an unpinned call would go to the network and return MP3.
# Keeping them espeak-specific is the point — this is the offline path's own proof.

@pytest.mark.skipif(not _engine_installed(), reason="espeak-ng is not installed here")
def test_bangla_renders_a_valid_non_empty_wav(monkeypatch):
    """Runs only where the engine exists. Proves the bytes are a real RIFF/WAVE with a
    non-zero duration — it does NOT prove the Bangla is intelligible."""
    _use(monkeypatch, tts_provider="espeak")
    audio, media_type = synthesize(BANGLA_QUESTION, "bn")
    assert media_type == "audio/wav"
    assert audio.startswith(b"RIFF")
    with wave.open(BytesIO(audio)) as wav:
        assert wav.getnframes() / float(wav.getframerate()) > 0.3


@pytest.mark.skipif(not _engine_installed(), reason="espeak-ng is not installed here")
def test_english_renders_too_so_the_en_ui_keeps_audio(monkeypatch):
    _use(monkeypatch, tts_provider="espeak")
    audio, _ = synthesize("How long have you had this problem?", "en")
    assert audio.startswith(b"RIFF") and len(audio) > 1000


@pytest.mark.skipif(not _engine_installed(), reason="espeak-ng is not installed here")
def test_the_endpoint_serves_playable_audio_with_a_private_cache(monkeypatch):
    _use(monkeypatch, tts_provider="espeak")
    resp = client.get("/api/tts", params={"text": BANGLA_QUESTION, "lang": "bn"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/")
    assert "private" in resp.headers.get("cache-control", "")
    assert resp.content.startswith(b"RIFF")
