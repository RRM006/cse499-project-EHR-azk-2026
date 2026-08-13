"""S36 / Finding 2 (ADR-0057) — one patient's screening may never reach the next one.

The report: at the final-question area, text or speech from a PREVIOUS patient sometimes
appeared inside the current patient's information. This is a privacy boundary, so it is
fixed at the mechanism rather than at the symptom.

The kiosk is ONE long-lived page serving patient after patient. `resetState()` builds a
fresh `state` object and empties the chat thread, which LOOKS like a reset. It is not
one — everything that lives outside `state` survived it:

  1. **The recognition engine, still running.** `r.onend` restarts it while `listening`
     is true and `r.onresult` writes into `activeDock()`, so a patient still talking when
     the kiosk reset had their voice transcribed into the NEXT patient's phone dock.
  2. **`finalBuffer`**, still holding the previous patient's captured words.
  3. **Every in-flight `api()` promise.** `state` is a module-level variable that
     resetState() REPLACES, so a late response does not write into a dead object — it
     writes into the live one.
  4. The review read-through, the phone countdown, and the rendered summary cards.

(3) is the dangerous one, and clearing variables cannot fix it: a promise that has
already resolved is going to run. The only defence is for the continuation to identify
itself as stale, which is what the session epoch is for — the same shape as S3's
`armToken`, which already solves exactly this for the microphone.

⚠ Scope: static-source assertions over the served kiosk.js, plus the shipped functions
executed in a real browser engine. Measured there, patient A → reset → patient B:

    stale token valid        false      finalBuffer          ""      (was A's words)
    thread / grid / dock /   no A text  recognition object   null    (was a live engine)
    phone / answer panel                state.visitUuid      null

  and with a REAL in-flight response resolving 250 ms AFTER the reset:
    late followup/answer -> next question NOT spoken into B's thread, activeQuestion null
    late verify-otp      -> A's visit.uuid NOT installed; B still on screen-phone
    late profile fetch   -> A's cards NOT drawn on B's review; B still on screen-phone

  CONTROL, same three flows with NO reset in the middle: all three complete normally
  (uuid installed, both bubbles added, summary rendered, screen-summary reached) — the
  guard rejects stale sessions, not slow ones. No microphone is involved in this finding.
"""

import re

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def kiosk_js() -> str:
    resp = client.get("/kiosk.js")
    assert resp.status_code == 200
    return resp.text


def fn_body(name: str) -> str:
    js = kiosk_js()
    marker = f"function {name}("
    assert marker in js, f"{name}() is gone from the shipped kiosk"
    return js.split(marker)[1].split("\n}")[0]


# --- the boundary itself ---


def test_the_session_has_an_epoch_that_stale_work_can_be_measured_against():
    js = kiosk_js()
    assert "let sessionEpoch = 0;" in js
    token = fn_body("sessionToken")
    assert "const epoch = sessionEpoch;" in token
    assert "return () => epoch === sessionEpoch;" in token


def test_ending_a_session_invalidates_in_flight_work_before_anything_else():
    """The bump is FIRST on purpose. If any teardown line below it throws, the responses
    still in flight are already invalidated — and those are the half that can move data
    between patients. A visual clear that runs first would protect nothing."""
    body = fn_body("endSession")
    assert "sessionEpoch += 1;" in body
    # the first line carrying actual code, past the signature tail and any comment
    code_lines = [
        line.strip() for line in body.splitlines()
        if line.strip() and not line.strip().startswith(("//", "/*", "*", ") {"))
    ]
    assert code_lines[0] == "sessionEpoch += 1;", (
        f"the epoch bump is not the first thing endSession() does (found {code_lines[0]!r})")


def test_a_new_patient_always_gets_the_teardown_before_the_fresh_state():
    body = fn_body("startNewSession")
    assert "endSession();" in body and "resetState();" in body
    assert body.index("endSession();") < body.index("resetState();")


def test_the_logout_reset_goes_through_the_one_session_boundary():
    """The hand-written teardown that used to live in confirmSubmit was the bug: it was
    maintained by remembering. It cancelled three timers but not the phone one, cleared
    `state` but never the recognition engine or `finalBuffer`, and could do nothing about
    a response in flight."""
    submit = kiosk_js().split("async function confirmSubmit() {")[1].split("\n}\n")[0]
    assert "startNewSession();" in submit
    assert "resetState();" not in submit, "the reset must go through the session boundary"


def test_end_session_is_never_called_from_reset_state():
    """resetState() also runs at MODULE LOAD, where `recognition`, `finalBuffer`,
    `phoneTicker` and `DOCKS` are all still in their temporal dead zone. Calling the
    teardown from there is a ReferenceError that kills the whole kiosk — exactly how
    S33 lost it once."""
    assert "endSession()" not in fn_body("resetState")


# --- what the teardown actually stops ---


def test_the_recognition_engine_is_torn_down_and_cannot_restart_itself():
    """`r.onend` restarts the engine while `listening` is true, so simply calling stop()
    would have it come straight back — still transcribing the previous patient into the
    next patient's dock. The handlers are detached BEFORE the abort, and abort() rather
    than stop() DISCARDS what was captured instead of delivering it."""
    body = fn_body("endSession")
    assert "listening = false;" in body
    for handler in ("recognition.onresult = null;", "recognition.onend = null;",
                    "recognition.onerror = null;"):
        assert handler in body, f"{handler} — a live handler outlives the session"
    assert "recognition.abort();" in body
    assert "recognition.stop();" not in body, "stop() delivers the buffered result; abort() drops it"
    assert body.index("recognition.onend = null;") < body.index("recognition.abort();")
    assert "recognition = null;" in body   # the next patient builds a fresh engine


def test_the_previous_patients_captured_words_do_not_survive():
    body = fn_body("endSession")
    assert "finalBuffer = '';" in body
    assert "heardSpeech = false;" in body


def test_every_countdown_is_stopped_including_the_one_the_old_list_forgot():
    body = fn_body("endSession")
    for cancel in ("cancelPendingMic();", "cancelCountdown();",
                   "cancelPhoneTimer();", "cancelReviewTimer();"):
        assert cancel in body, f"endSession() does not stop {cancel}"
    assert "clearTimeout(flushTimer);" in body


def test_audio_from_the_previous_patient_stops_in_both_directions():
    """ttsCancel() (ADR-0049) also stops the server <audio>, which speechSynthesis.cancel()
    does not. The review read-through is a QUEUE that re-arms itself on every `onend`, so
    cancelling the audio alone would let the next item start."""
    body = fn_body("endSession")
    assert "readAloudQueue = null;" in body
    assert "ttsCancel();" in body


def test_the_re_entry_guards_are_released_so_the_next_patient_is_not_locked_out():
    """A stuck `otpVerifying` makes the kiosk silently refuse every code the next patient
    enters — a dead kiosk with no error message."""
    body = fn_body("endSession")
    assert "otpVerifying = false;" in body
    assert "submitting = false;" in body


def test_the_previous_patients_words_are_removed_not_merely_hidden():
    """Hiding a panel leaves the text in the DOM, where the next render, a language
    toggle or a screen change can bring it back. The text itself goes."""
    body = fn_body("endSession")
    assert "hideAnswerConfirm();" in body
    assert "hidePhoneConfirm();" in body
    assert "clearDigitPreview();" in body
    assert "setBilingualText(dock.transcript, '', '');" in body
    assert "grid.innerHTML = '';" in body
    assert "resumeQ.textContent = '';" in body


# --- the stale-response guard on every patient-facing await ---


def test_every_async_patient_path_captures_the_session_before_it_awaits():
    """The list is the point. Each of these writes to `state` or the DOM after an await,
    so each needs to know whether the patient it belongs to is still on screen."""
    for name in ("sendOtp", "verifyOtp", "submitPatientTurn", "submitResumeAnswer",
                 "finishConversation", "refreshResumeLoop", "loadReadiness",
                 "confirmSubmit"):
        assert "const mine = sessionToken();" in fn_body(name), \
            f"{name}() can still write into a session that has ended"


def test_the_verified_otp_cannot_install_a_previous_patients_visit():
    """The single most dangerous stale write in the kiosk: without the guard, every
    answer the NEW patient gives is POSTed onto the OLD patient's visit."""
    body = fn_body("verifyOtp")
    assert "if (!mine()) return;" in body
    assert body.index("if (!mine()) return;") < body.index("state.visitUuid = res.visit.uuid;")


def test_a_late_profile_is_never_drawn_onto_the_next_patients_review():
    for name in ("submitResumeAnswer", "finishConversation"):
        body = fn_body(name)
        assert "renderSummary(profile);" in body
        before = body.split("renderSummary(profile);")[0]
        assert "if (!mine()) return;" in before, \
            f"{name}() renders a profile without checking whose session it is"


def test_a_stale_error_does_not_interrupt_the_next_patient():
    """An error banner and a released `busy` flag both belong to the visit that produced
    them. Showing the previous patient's failure to the new one is confusing at best."""
    for name in ("submitPatientTurn", "submitResumeAnswer", "finishConversation"):
        body = fn_body(name)
        catch = body.split("} catch (e) {")[1]
        assert "if (!mine()) return;" in catch.split("}")[0] + catch.split("}")[1], \
            f"{name}() shows an error from a finished session"


def test_the_language_preference_is_not_treated_as_patient_data():
    """localStorage holds the kiosk's EN/BN choice and nothing else. It is a property of
    the machine in the waiting room, not of the patient, so the boundary deliberately
    leaves it alone — clearing it would flip an elderly-focused Bangla kiosk back to
    English between patients."""
    js = kiosk_js()
    assert "localStorage" not in js
    assert "localStorage" not in fn_body("endSession")
