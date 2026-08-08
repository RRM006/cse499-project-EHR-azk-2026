"""ADR-0049 — the frontend side of the Bangla TTS fallback.

Static-source assertions (the human's S28 decision (2)), same honest scope as the other
kiosk frontend tests: they prove the provider chain and — critically — the widened echo
guard are still WIRED. They cannot prove audio plays or that the guard silences a real
room; only the live Chrome run can.

The echo-guard assertions here are the most important in the file. Server TTS plays
through an <audio> element, and `speechSynthesis.speaking` is FALSE the whole time it
does. If the guard ever reverts to that predicate, the microphone opens while the AI is
still audible and the AI's own question lands in the patient's verbatim record — a
rule #1 defect.
"""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def kiosk_js() -> str:
    resp = client.get("/kiosk.js")
    assert resp.status_code == 200
    return resp.text


def tts_js() -> str:
    resp = client.get("/shared/tts.js")
    assert resp.status_code == 200
    return resp.text


# --------------------------- the echo guard (rule #1) ---------------------------

def test_the_echo_guard_covers_server_audio_not_just_speech_synthesis():
    js = kiosk_js()
    guard = js.split("function openMicWhenQuiet(token)")[1].split("function setInputMode")[0]
    assert "ttsSpeaking()" in guard
    # The old predicate must be GONE from the guard: it is blind to <audio>.
    assert "speechSynthesis.speaking" not in guard


def test_tts_speaking_is_true_while_the_request_is_still_in_flight():
    """Not just while audio is audible: between `new Audio(url)` and the first sample
    there is a network round-trip. If that window reports 'not speaking', the mic opens
    into the START of the question."""
    js = tts_js()
    speaking = js.split("function ttsSpeaking()")[1].split("function ttsCancel")[0]
    assert "_audio !== null" in speaking
    assert "speechSynthesis.speaking" in speaking   # still honors the browser path


def test_tapping_the_mic_silences_every_provider():
    """A deliberate tap must stop server audio too, or the tap itself creates echo."""
    js = kiosk_js()
    assert "ttsCancel();" in js
    cancel = tts_js().split("function ttsCancel()")[1].split("function _releaseAudio")[0]
    assert "speechSynthesis.cancel()" in cancel
    assert "_releaseAudio();" in cancel


def test_a_superseded_question_cannot_fire_a_stale_callback_on_either_path():
    """The S3 generation token must still gate BOTH providers."""
    js = tts_js()
    assert "generation !== _speechGeneration" in js
    assert "_releaseAudio();" in js.split("const finish = ()")[1].split("};")[0]


# --------------------------- the provider chain ---------------------------

def test_an_installed_browser_voice_still_wins():
    """Server TTS is a FALLBACK, not a replacement — Arch already works via ADR-0040."""
    js = tts_js()
    order = js.index("provider 1") < js.index("provider 2")
    assert order
    chain = js.split("provider 1")[1].split("provider 2")[0]
    assert "window.speechSynthesis.speak(u)" in chain


def test_the_server_is_only_used_when_it_can_actually_speak():
    js = tts_js()
    assert "if (_serverTts) {" in js
    assert "/api/tts?lang=" in js
    assert "encodeURIComponent(text)" in js   # Bangla + '&' safe in the query


def test_nothing_available_returns_false_instead_of_faking_audio():
    """The old code returned true whenever speechSynthesis merely EXISTED, so a Bangla
    question with no Bangla voice looked like success. That is what this fixes."""
    js = tts_js()
    tail = js.split("provider 2")[1]
    assert "return false;" in tail


def test_a_failed_request_releases_the_caller():
    """A 503 must not strand a kiosk waiting to open the mic."""
    js = tts_js()
    assert "audio.onerror = finish;" in js
    assert "started.catch(finish)" in js


# --------------------------- language correctness ---------------------------

def test_the_voice_follows_the_ui_language():
    """An English question spoken by a Bengali voice is nonsense, and vice versa."""
    js = tts_js()
    assert "_uiLang()" in js
    # Read from the same localStorage key shared.js owns, NOT from a shared.js helper:
    # a browser holding a cached shared.js otherwise sends every question down the
    # wrong language path, which is a real bug this cost us once already.
    assert "localStorage.getItem('lang') === 'bn'" in js
    assert "function currentLang()" not in client.get("/shared/shared.js").text


def test_only_bangla_requires_a_matching_voice():
    """English must still speak with the DEFAULT voice — insisting on a matching voice
    breaks audio during Chrome's asynchronous getVoices() load, when the list is empty."""
    js = tts_js()
    assert "if (voice || short === 'en')" in js


def test_a_patient_bubble_replays_in_bangla_regardless_of_ui_language():
    """STT captured it at lang='bn-BD', so the words are Bangla even if the patient has
    since switched the interface to English."""
    js = kiosk_js()
    assert "role === 'patient' ? 'bn-BD' : null" in js


# --------------------------- config plumbing + honesty ---------------------------

def test_the_kiosk_learns_the_capability_from_the_server():
    js = kiosk_js()
    assert "server_tts: false" in js               # safe default if /api/config fails
    assert "configureTts({ serverTts: voiceConfig.server_tts });" in js


def test_the_no_bangla_voice_banner_stops_lying_once_a_fallback_exists():
    js = kiosk_js()
    assert "banglaAudioAvailable()" in js
    hint = js.split("function updateVoiceHint()")[1].split("if (window.speechSynthesis)")[0]
    assert "banglaVoiceAvailable()" not in hint    # too narrow now
    assert "banglaAudioAvailable() ? 'none' : 'block'" in hint


def test_the_banner_is_re_evaluated_after_the_config_arrives():
    """It is rendered before /api/config resolves, so it must be refreshed afterwards."""
    js = kiosk_js()
    loader = js.split("async function loadKioskConfig()")[1].split("let state = null;")[0]
    assert "updateVoiceHint();" in loader
