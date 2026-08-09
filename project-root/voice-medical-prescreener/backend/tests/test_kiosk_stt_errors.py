"""The Web Speech API terminal-error fix (S31) — found by the S30 Edge verification.

The defect: `r.onerror` handled only `not-allowed` and `audio-capture`, so
`language-not-supported` (exactly what Edge emits if its speech backend rejects
`bn-BD`), `network` and `service-not-allowed` left `listening === true`. `r.onend`
then restarted the engine, forever: **start → error → end → start**, with no error
shown, no switch to typing and no countdown (the countdown arms only after real words
are captured, and none ever arrive). A silent dead end that also spins CPU.

⚠ The half of this that is easy to break: `no-speech` and `aborted` MUST stay
transient. That restart IS what keeps continuous listening alive in Chrome and is part
of the passed S29 live run — a blanket "stop on any error" would regress Chrome. The
terminal/transient split is the whole point, so the tests below pin BOTH sides.

⚠ Scope, stated honestly (the S28 decision (2), unchanged): these are **static-source
assertions** over the served file, with one narrow exception the S30 TTS-1 tests
established — the shipped `TERMINAL_STT_ERRORS` literal is extracted and its key set
compared, so the rule is read out of the code rather than asserted about in prose.
They prove the wiring exists and covers the right codes. They CANNOT prove browser
behaviour: whether Edge actually emits `language-not-supported` for `bn-BD` is still
UNPROVEN and needs a human at a real mic.
"""

import re

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

# The 8 codes in the Web Speech API spec, partitioned the way the kiosk must treat them.
TERMINAL = {
    "not-allowed",            # permission denied / revoked
    "audio-capture",          # no usable microphone device
    "network",                # the speech service is unreachable
    "service-not-allowed",    # the browser/OS refused the speech service
    "language-not-supported", # the backend rejected bn-BD  <- the Edge case
}
TRANSIENT = {
    "no-speech",   # ⚠ MUST keep restarting — silence is normal, not a failure
    "aborted",     # ⚠ MUST keep restarting — our own stop() raises this every turn
    "bad-grammar",
}


def kiosk_js() -> str:
    resp = client.get("/kiosk.js")
    assert resp.status_code == 200
    return resp.text


def terminal_error_codes() -> set[str]:
    """Read the shipped map's keys out of the served JS, rather than trusting a comment."""
    js = kiosk_js()
    block = re.search(r"const TERMINAL_STT_ERRORS = \{(.*?)\n\};", js, re.S)
    assert block, "TERMINAL_STT_ERRORS map missing from the served kiosk.js"
    return set(re.findall(r"'([a-z-]+)':", block.group(1)))


def test_every_terminal_speech_error_is_handled():
    """The 2-of-8 coverage that caused the Edge dead end is now the full terminal set."""
    assert terminal_error_codes() == TERMINAL


def test_transient_errors_are_deliberately_absent_so_chrome_keeps_listening():
    """The Chrome-regression guard. `no-speech` fires constantly during a normal pause
    and `aborted` fires on our OWN stop() at the end of every turn — treating either as
    fatal would end turns that the patient has not finished (a rule #1 defect)."""
    handled = terminal_error_codes()
    for code in TRANSIENT:
        assert code not in handled, f"{code} must stay transient or continuous listening breaks"


def test_an_unlisted_error_returns_before_touching_the_turn():
    """A transient error must fall through to onend untouched — no message, no mode
    change, and above all `listening` left true so the restart still happens."""
    js = kiosk_js()
    handler = js.split("r.onerror = (e) => {")[1].split("};")[0]
    assert "if (!message) return;" in handler
    # The early return has to come before every side effect, or transience means nothing.
    assert handler.index("return;") < handler.index("stopListening(false)")


def test_a_terminal_error_breaks_the_restart_loop_and_offers_typing():
    js = kiosk_js()
    handler = js.split("r.onerror = (e) => {")[1].split("};")[0]
    assert "showError(" in handler
    assert "stopListening(false);" in handler   # sets listening = false -> onend stops restarting
    assert "setInputMode('type');" in handler   # S2: the patient is never stranded


def test_the_onend_restart_itself_is_unchanged():
    """The fix works by flipping `listening`, NOT by touching the restart. If this line
    ever becomes conditional on an error code, the two mechanisms have been tangled."""
    js = kiosk_js()
    onend = js.split("r.onend = () => {")[1].split("r.onerror")[0]
    assert "if (listening) try { r.start(); } catch (_) {}" in onend


def test_the_messages_are_bilingual_and_do_not_blame_the_microphone_for_a_service_failure():
    """P1-2: every patient-facing string follows the EN/BN toggle. And a dead speech
    SERVICE is not a dead MIC — at a demo those need different responses, and saying
    'microphone unavailable' when Edge rejected Bangla is simply false."""
    js = kiosk_js()
    for const in ("MIC_UNAVAILABLE", "STT_SERVICE_UNAVAILABLE", "STT_LANGUAGE_UNSUPPORTED"):
        block = re.search(rf"const {const} = \{{(.*?)\}};", js, re.S)
        assert block, f"{const} missing"
        assert "en:" in block.group(1) and "bn:" in block.group(1)
    assert "cannot recognise Bangla speech" in js          # the Edge-specific wording
    assert "Speech recognition is unavailable" in js       # network / service-not-allowed
    assert "Microphone unavailable" in js                  # not-allowed / audio-capture
    assert "এই ব্রাউজারে বাংলা স্পিচ রিকগনিশন কাজ করছে না" in js
