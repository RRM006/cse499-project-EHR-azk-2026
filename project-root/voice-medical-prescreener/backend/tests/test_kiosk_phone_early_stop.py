"""S36 / Finding 4 (ADR-0057) — a complete phone number ends its own turn.

The phone number is the ONE answer in this kiosk whose completeness is knowable the
instant it arrives: eleven digits starting 01, and there is nothing more to say. Every
other answer is prose, where only silence can suggest the patient has finished — which
is exactly what the S4 endpointer's `countdown_ms` window is for.

Applying that same wait to a phone number was a defect, not a design. After the last
digit the mic stayed open for the whole window and whatever arrived in it joined the
SAME utterance. Trailing words ("এটাই আমার নম্বর") add no digits and were merely untidy;
a patient who repeats a digit pushes the count past eleven, and `phoneFromSpeech()` then
returns null for a number that had already been said correctly — so the kiosk tells them
it did not understand and asks for the whole number again.

⚠ What this deliberately does NOT do is skip the read-back. ADR-0053's reason still
holds — a wrong digit here does not annoy the patient, it sends their verification code
to a stranger's handset — and S35 already made that step require no button: it accepts
itself after `phone_confirm_ms`. The patient still hears their number and still reaches
OTP without touching anything. What is removed is a silence timer that had nothing left
to wait for.

⚠ Scope: static-source assertions plus the SHIPPED `onresult` handler driven in a real
browser engine with scripted results (S33's method), fed word-by-word the way a bn-BD
recogniser delivers "শূন্য এক সাত এক পাঁচ নয় আট চার ছয় তিন দুই":

    valid + trailing words   stopped at chunk 11, mic closed, 1715984632, countdown never ran
    valid + extra digits     stopped at chunk 11 — the two extra digits never reached it
    valid then silence       stopped immediately, no countdown wait
    incomplete (9 digits)    still listening, countdown running   (no early stop)
    invalid (starts 0 2)     still listening, countdown running   (no early stop)

  and for one-verification-only, each racing case sending EXACTLY ONE lookup:
    three taps on the read-back = 1 · three Enters on the typed path = 1 ·
    tap racing the countdown = 1 · a deliberate later retry still sends its own = 1

⚠ NO MICROPHONE was used for this finding: the digit vocabulary is fed to the shipped
handler directly. What a real recogniser returns for these words is the live run.
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


def code_only(src: str) -> str:
    """Source with comments removed — for "this call does NOT appear" assertions, which
    a prose mention of the same name would otherwise fail."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


# --- where the decision is made ---


def test_the_completeness_check_runs_inside_the_recognition_handler():
    """"Do not simply truncate an already corrupted string after the fact if recognition
    can be stopped earlier." The check therefore sits in `onresult`, where the digits
    arrive — not in applySpokenPhone(), which only ever sees a finished turn."""
    js = kiosk_js()
    handler = js.split("r.onresult = (event) => {")[1].split("\n  };")[0]
    assert "if (maybeCompletePhone(live)) return;" in handler


def test_it_is_checked_before_the_silence_window_is_restarted():
    """Restarting the endpointer first would arm a countdown for a turn that is already
    over — and everything after that point belongs to a turn that no longer exists."""
    js = kiosk_js()
    handler = js.split("r.onresult = (event) => {")[1].split("\n  };")[0]
    assert handler.index("maybeCompletePhone(live)") < handler.index("restartSilenceWindow();")


def test_it_reads_the_interim_text_not_just_the_finalised_buffer():
    """The eleventh digit is usually still interim when it arrives. Waiting for the
    recogniser to finalise it is the very delay this removes."""
    js = kiosk_js()
    handler = js.split("r.onresult = (event) => {")[1].split("\n  };")[0]
    assert "const live = finalBuffer + interim;" in handler
    assert "maybeCompletePhone(live)" in handler


# --- when it fires, and when it must not ---


def test_it_fires_only_on_the_phone_dock():
    """The OTP dock has its own completeness rule (six digits, applySpokenOtp) and a
    clinical answer has none at all — prose is never 'complete'."""
    body = fn_body("maybeCompletePhone")
    assert "state.identifyStep !== 'phone'" in body


def test_it_never_fires_twice_for_one_number():
    """A late final chunk from the engine arrives AFTER stopListening() has run. Both
    guards make it a no-op: `listening` is already false and a read-back is pending."""
    body = fn_body("maybeCompletePhone")
    assert "state.pendingPhone" in body
    assert "!listening" in body
    assert "endingTurn" in body


def test_an_incomplete_or_invalid_number_is_left_alone():
    """The ONLY trigger is `phoneFromSpeech()` returning a number — the same function
    that produces the value, so 'complete enough to stop' and 'complete enough to use'
    can never disagree. Nine digits, or eleven starting 02, keep listening."""
    body = fn_body("maybeCompletePhone")
    assert "if (!phoneFromSpeech(live)) return false;" in body


def test_it_exits_through_the_ordinary_turn_path():
    """One route in, one route out (ADR-0048). It commits the shown words and then takes
    the SAME exit a tap takes, so applySpokenPhone() and the read-back run unchanged —
    no second phone pipeline exists."""
    body = fn_body("maybeCompletePhone")
    assert "cancelCountdown();" in body
    assert "finalBuffer = live;" in body
    assert "stopListening(true);" in body
    code = code_only(body)
    assert "sendOtp()" not in code, "the early stop must not bypass the read-back"
    assert "applySpokenPhone" not in code, "it must not call the handler directly"


def test_the_read_back_still_gates_the_number():
    """ADR-0053 is amended by S35's window, not repealed by this finding. The number is
    still shown, still spoken digit by digit, and still cancellable."""
    body = fn_body("applySpokenPhone")
    assert "showPhoneConfirm(national);" in body
    assert "speakDigits('0' + national);" in fn_body("showPhoneConfirm")


# --- exactly one verification request ---


def test_the_lookup_cannot_be_sent_twice_by_a_race():
    """FOUR things reach sendOtp() — the button, Enter, the read-back's ✔, and the phone
    countdown accepting itself — and each one sends a real SMS. The read-back path was
    already single-shot; the typed path was not, and because each new code invalidates
    the last (ADR-0045, single-use) a double send left the patient reading out a code the
    server had already replaced."""
    js = kiosk_js()
    assert "let otpSending = false;" in js
    body = fn_body("sendOtp")
    assert "if (otpSending) return;" in body
    assert "otpSending = true;" in body
    assert body.index("if (otpSending) return;") < body.index("otpSending = true;")


def test_the_guard_is_released_rather_than_latched():
    """It collapses simultaneous calls into one SMS. A deliberate retry after a failed
    lookup is a different request and must still work."""
    body = fn_body("sendOtp")
    assert "} finally {" in body
    assert "otpSending = false;" in body.split("} finally {")[1]


def test_an_empty_field_does_not_consume_the_guard():
    """The blank-input early return happens BEFORE the flag is set, or the first stray
    Enter on an empty box would lock the patient out of ever sending a code."""
    body = fn_body("sendOtp")
    assert body.index("Enter your mobile number.") < body.index("otpSending = true;")


def test_the_guard_is_released_for_the_next_patient():
    """S36's session boundary owns every re-entry flag — a latched `otpSending` would
    make the kiosk silently refuse the NEXT patient's number."""
    assert "otpSending = false;" in fn_body("endSession")


# --- typing must not have been broken ---


def test_the_typed_path_is_untouched():
    """The early stop lives entirely inside the recognition handler, so a patient who
    types their number never meets it. Enter still sends."""
    js = kiosk_js()
    assert "wire('phone-input', sendOtp);" in js
    assert "maybeCompletePhone" not in fn_body("initTypedInputs")
