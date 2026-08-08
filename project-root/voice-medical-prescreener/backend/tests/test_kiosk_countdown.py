"""S4 of ADR-0048 — the turn ends on SILENCE, behind a visible 3-2-1 confirmation
countdown that any resumed speech cancels.

⚠ Same honest scope as `test_kiosk_input_modes.py` and `test_kiosk_auto_listen.py`:
these are **static-source assertions** over the served files (the human's S28 decision
(2)). They prove the endpointer, the countdown UI and the anti-clipping guards are still
PRESENT and still wired to the config. They CANNOT prove that 3 seconds is the right
window for an elderly Bangla speaker, that a real cough cancels a real countdown, or
that Chrome flushes its last final chunk in time — only the live Chrome run
(`faculty_future_features.md` §K, items 5/6/8) can.
"""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def kiosk_js() -> str:
    resp = client.get("/kiosk.js")
    assert resp.status_code == 200
    return resp.text


def kiosk_html() -> str:
    resp = client.get("/kiosk.html")
    assert resp.status_code == 200
    return resp.text


def test_both_docks_have_a_countdown_element():
    """The conversation dock AND the KIOSK-7 resume dock — one endpointer serves both."""
    html = kiosk_html()
    for element_id in ("dock-countdown", "dock-countdown-digit",
                       "resume-countdown", "resume-countdown-digit"):
        assert f'id="{element_id}"' in html
    js = kiosk_js()
    assert "countdown: 'dock-countdown'" in js
    assert "countdown: 'resume-countdown'" in js


def test_the_countdown_is_legible_for_an_elderly_patient():
    """It is a confirmation the patient must be able to READ at a glance, not a hint."""
    html = kiosk_html()
    assert ".countdown-digit" in html
    assert "font-size: 2.2rem" in html


def test_the_countdown_length_comes_from_the_server_not_a_hardcoded_3():
    """A clinic must be able to lengthen the window for slower patients via .env."""
    js = kiosk_js()
    assert "voiceConfig.countdown_ms" in js
    assert "Math.ceil(remaining / 1000)" in js   # honest digit for any tuned value


def test_every_recognition_result_restarts_the_window():
    """Interim OR final. This is the whole anti-clipping safeguard (rule #1): the
    patient, not the timer, decides when the turn ends."""
    js = kiosk_js()
    assert "restartSilenceWindow();" in js
    onresult = js.split("r.onresult = (event) => {")[1].split("r.onend")[0]
    assert "restartSilenceWindow();" in onresult


def test_a_blank_tick_can_cancel_a_countdown_but_never_start_one():
    """Silence/noise must not arm a window that would submit an empty answer."""
    js = kiosk_js()
    assert "if (live.trim()) heardSpeech = true;" in js
    assert "!heardSpeech" in js


def test_the_countdown_only_runs_in_auto_voice_mode_and_only_while_listening():
    """`voice_loop=manual` must reproduce the passed S25 tap-to-finish run exactly."""
    js = kiosk_js()
    window = js.split("function restartSilenceWindow()")[1].split("function renderCountdown")[0]
    assert "!autoVoiceMode()" in window
    assert "!listening" in window


def test_reaching_zero_flushes_the_engine_before_reading_the_buffer():
    """stopListening() reads finalBuffer immediately, so submitting without stopping the
    engine first would silently drop words Chrome had not yet marked isFinal — the tail
    of the patient's own answer (rule #1)."""
    js = kiosk_js()
    ending = js.split("function endTurnOnSilence()")[1].split("function finishFlushedTurn")[0]
    assert "recognition.stop()" in ending
    assert "setTimeout(finishFlushedTurn, FLUSH_GRACE_MS)" in ending
    assert "const FLUSH_GRACE_MS = 600;" in js


def test_the_flushed_turn_is_submitted_exactly_once():
    """Both the engine's `onend` and the grace timer race to finish the turn; a double
    submit would store the answer twice."""
    js = kiosk_js()
    assert "if (!endingTurn) return;" in js          # whoever lost the race backs out
    assert "if (endingTurn) return;" in js           # and the turn can only end once
    assert "endingTurn = false;" in js               # cleared on the single exit


def test_zero_submits_through_the_same_path_as_a_tap():
    """One submit path, so auto and manual can never diverge in behaviour."""
    js = kiosk_js()
    flush = js.split("function finishFlushedTurn()")[1].split("/* S2:")[0]
    assert "stopListening(true);" in flush


def test_the_engine_restart_is_no_longer_unconditional():
    """The old `r.onend = () => { if (listening) r.start(); }` never ended a turn. The
    replacement arbitrates: our own flush wins over Chrome's auto-restart."""
    js = kiosk_js()
    assert "r.onend = () => { if (listening) r.start(); }" not in js
    onend = js.split("r.onend = () => {")[1].split("r.onerror")[0]
    assert "if (endingTurn) { finishFlushedTurn(); return; }" in onend
    assert "if (listening) try { r.start(); } catch (_) {}" in onend


def test_the_countdown_is_torn_down_on_every_exit_from_a_turn():
    """A countdown must never outlive its turn — a stale one would submit into the next
    question, or into the NEXT PATIENT's visit after the logout reset."""
    js = kiosk_js()
    stop = js.split("function stopListening(sendTurn)")[1].split("function sendTypedFallback")[0]
    assert "cancelCountdown();" in stop
    assert js.count("cancelCountdown();") >= 4   # window restart, zero, stop, logout reset


def test_the_listening_hint_stops_telling_an_auto_mode_patient_to_tap():
    """In auto mode the tap still works but is no longer required — asking an elderly
    patient for a needless action is exactly what this cycle is removing."""
    js = kiosk_js()
    assert "just stop speaking when you are finished" in js
    assert "বলা শেষ হলে থেমে যান" in js
    assert "tap again when done" in js               # manual mode keeps the old wording
    assert "listeningHint().en" in js


def test_the_countdown_digit_and_caption_are_bilingual():
    """P1-2: the digit uses Bangla numerals and the caption follows the EN/BN toggle."""
    js = kiosk_js()
    assert "bnDigits(secondsLeft)" in js
    html = kiosk_html()
    assert "আপনার উত্তর পাঠানো হচ্ছে" in html
    assert 'data-en="Sending your answer' in html
