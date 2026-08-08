"""S3 of ADR-0048 — the microphone opens itself once the question finishes speaking.

⚠ Same honest scope as `test_kiosk_input_modes.py`: these are **static-source
assertions** over the served files (the human's S28 decision (2)). They prove the
guards and the wiring are still PRESENT. They cannot prove that the mic actually opens,
that the echo guard actually silences TTS first, or that `onend` fires on a given
machine — only the live Chrome run (`faculty_future_features.md` §K, items 1/7/8) can.
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


def test_every_question_the_patient_must_answer_goes_through_askaloud():
    """The 3 call sites: the M7 loop, the KIOSK-7 resume dock, and Repeat question."""
    js = kiosk_js()
    assert "askAloud(text)" in js                       # assistantSays()
    assert "askAloud(question.question_text)" in js      # setResumeMode()
    assert "askAloud(state.lastQuestionText)" in js      # repeatQuestion()


def test_replaying_an_old_bubble_does_not_open_the_microphone():
    """The per-message 🔊 button is for review — it must stay plain speak(), never
    askAloud(). (ADR-0049 added an explicit replay language; the rule is unchanged.)"""
    js = kiosk_js()
    assert "speakBtn.onclick = () => speak(body.textContent, { lang: replayLang });" in js
    assert "askAloud(body.textContent" not in js


def test_the_mic_never_opens_while_the_ai_is_still_audible():
    """Echo guard, rule #1: AI words must never enter the patient's verbatim record.
    ADR-0049 widened the predicate to ttsSpeaking() so it also covers server-side audio,
    which `speechSynthesis.speaking` cannot see — see test_kiosk_tts_fallback.py."""
    js = kiosk_js()
    assert "ttsSpeaking()" in js
    assert "voiceConfig.tts_guard_ms" in js


def test_a_missing_or_silent_voice_cannot_freeze_the_kiosk():
    """With no installed voice, `onend` may never fire — a safety net must open the
    mic anyway, otherwise the patient waits forever for a mic that never arrives."""
    js = kiosk_js()
    assert "Math.max(3000, text.length * 80)" in js


def test_auto_listen_is_off_in_manual_mode_and_while_typing():
    js = kiosk_js()
    assert "voiceConfig.voice_loop === 'auto'" in js
    assert "state.inputMode === 'voice'" in js


def test_a_pending_auto_open_is_cancelled_by_every_deliberate_action():
    """A tap, a mode switch, Done, and the logout reset must all beat a pending arm."""
    js = kiosk_js()
    assert js.count("cancelPendingMic()") >= 6


def test_auto_open_reuses_the_same_path_as_a_tap():
    """One code path for both, so auto and manual can never diverge in behaviour."""
    js = kiosk_js()
    assert "toggleListening();   // the SAME path a tap takes" in js


def test_the_kiosk_reads_its_timings_from_the_server_but_never_depends_on_it():
    js = kiosk_js()
    assert "api('GET', '/api/config')" in js
    assert "voiceConfig = { ...VOICE_DEFAULTS };" in js   # fetch failed -> safe defaults
    assert "loadKioskConfig();" in js


def test_the_arming_hint_is_bilingual():
    """The patient must be told the mic is coming — in their language (P1-2)."""
    js = kiosk_js()
    assert "the microphone will start by itself" in js
    assert "মাইক নিজেই চালু হবে" in js


def test_a_superseded_question_can_never_open_the_microphone():
    """Chrome fires `onend` for an utterance that cancel() killed. Without the
    generation token that stale callback would open the mic during the NEXT question —
    straight into a rule #1 echo. Guarded at the single TTS entry point."""
    js = tts_js()
    assert "_speechGeneration" in js
    assert "generation !== _speechGeneration" in js


def test_a_failed_utterance_still_releases_the_caller():
    """onerror is bridged to onend so an interrupted question can't strand the mic."""
    js = tts_js()
    assert "u.onerror = finish;" in js


def test_the_onend_callback_fires_at_most_once():
    js = tts_js()
    assert "if (fired || generation !== _speechGeneration) return;" in js
