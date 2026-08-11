"""F1 (faculty demo cycle) — the OTP screen submits itself, and a rejected code resets.

Three defects this pins, all reported by the human:
  1. **Enter did nothing.** `initOtpInputs()` handled `input`, `Backspace` and `paste`
     but had no `Enter` branch, and `initTypedInputs()` wired only the two conversation
     text boxes — so pressing Enter on the phone screen OR the OTP screen was a no-op.
  2. **A complete code still needed a button click.** Six digits is an unambiguous
     "done" signal; making the patient find "Confirm & Login" afterwards is the extra
     tap ADR-0048 exists to remove.
  3. **A wrong code left its digits on screen**, so the patient had to clear six boxes
     by hand before retrying.

⚠ Scope, stated honestly (the S28 convention, unchanged): these are **static-source
assertions** over the served files. They prove the wiring still exists; they cannot
prove browser behaviour. The keyboard/auto-submit/clear-and-retry cycle was exercised
separately in a real browser engine — see the session notes.
"""

import re

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def kiosk_html() -> str:
    resp = client.get("/kiosk.html")
    assert resp.status_code == 200
    return resp.text


def kiosk_js() -> str:
    resp = client.get("/kiosk.js")
    assert resp.status_code == 200
    return resp.text


def shipped_otp_length() -> int:
    """Read OTP_LENGTH out of the served JS rather than hardcoding 6 here — the
    constant and the markup must agree, and this is what proves they do."""
    match = re.search(r"const OTP_LENGTH = (\d+);", kiosk_js())
    assert match, "OTP_LENGTH constant missing from kiosk.js"
    return int(match.group(1))


# --- defect 1: the Enter key ------------------------------------------------


def test_enter_submits_from_any_otp_box():
    js = kiosk_js()
    assert "if (e.key === 'Enter') { e.preventDefault(); verifyOtp(); }" in js


def test_enter_submits_the_phone_number():
    """The phone screen had no Enter handler at all — typing a number and pressing
    Enter read as a broken kiosk."""
    assert "wire('phone-input', sendOtp);" in kiosk_js()


def test_backspace_still_walks_back_before_enter_is_considered():
    """The Backspace branch must keep its early `return`, or a Backspace in an empty
    box would fall through and be re-tested against the new Enter branch."""
    js = kiosk_js()
    backspace = js.index("e.key === 'Backspace'")
    enter = js.index("e.key === 'Enter'", backspace)
    assert "return;" in js[backspace:enter], "Backspace branch lost its early return"


# --- defect 2: a complete code verifies itself ------------------------------


def test_a_complete_code_submits_without_a_button_press():
    js = kiosk_js()
    assert "function maybeAutoVerify()" in js
    assert f"if (otpDigits().length === OTP_LENGTH) verifyOtp();" in js


def test_auto_verify_fires_on_both_the_typed_and_the_pasted_path():
    """Pasting a 6-digit code is a complete code just as much as typing one, so the
    hook belongs in BOTH handlers — not only the one a developer types into."""
    js = kiosk_js()
    input_handler = js[js.index("box.addEventListener('input'"):js.index("box.addEventListener('keydown'")]
    # The paste handler is the last one in initOtpInputs(), so bound it by the call.
    paste_handler = js[js.index("box.addEventListener('paste'"):js.index("initOtpInputs();")]
    assert "maybeAutoVerify();" in input_handler
    assert "maybeAutoVerify();" in paste_handler


def test_an_incomplete_code_is_never_sent_to_the_server():
    """Clicking the button (or pressing Enter) with 4 digits must ask for the rest,
    not spend one of the 5 server-side attempts on a code the patient never finished."""
    js = kiosk_js()
    assert "if (otp.length !== OTP_LENGTH) {" in js


def test_the_markup_ships_exactly_otp_length_boxes():
    """The constant drives the completeness check, so a mismatch with the markup would
    make the code either un-submittable or submitted early."""
    assert kiosk_html().count('class="otp-input"') == shipped_otp_length()


# --- defect 3: a rejected code clears and asks again ------------------------


def test_a_rejected_code_clears_the_boxes():
    js = kiosk_js()
    assert "function clearOtpInputs(" in js
    # The clear happens on the failure path, not unconditionally.
    catch_block = js[js.index("res = await api('POST', '/api/patients/verify-otp'"):]
    assert "clearOtpInputs();" in catch_block[: catch_block.index("finally")]


def test_the_retry_prompt_is_bilingual_and_keeps_the_server_reason():
    """'Too many wrong attempts' and 'Invalid verification code' need different
    reactions from the patient, so the server's own detail is not swallowed."""
    js = kiosk_js()
    assert "Please enter the code again." in js
    assert "অনুগ্রহ করে কোডটি আবার লিখুন।" in js
    assert "${e.message}" in js


def test_a_failed_verification_keeps_the_patient_on_the_otp_screen():
    """The `if (!res)` early return is what stops a failed attempt falling through into
    showScreen('screen-voice') with no visit.

    F5b (ADR-0053) added a re-ask to that same branch — `if (!res) { reAskOtp(); return; }`
    — so this no longer matches one exact literal. The INTENT is unchanged and is now
    asserted more directly than the old string compare managed: the guard returns, and it
    returns before BOTH the screen change and the visit assignment. Verifying that
    reAskOtp() is what runs there belongs to test_kiosk_voice_identification.py."""
    body = kiosk_js().split("async function verifyOtp() {")[1].split("\n}")[0]
    guard = re.search(r"if \(!res\)[^\n]*\breturn;", body)
    assert guard, "the failed-verification early return is gone"
    assert guard.start() < body.index("showScreen('screen-voice');")
    assert guard.start() < body.index("state.visitUuid = res.visit.uuid;")


# --- the guard: a single-use code must never be submitted twice -------------


def test_one_code_can_only_be_submitted_once():
    """ADR-0045 codes are SINGLE-USE. Auto-verify, Enter and the button all reach
    verifyOtp(), so without this guard a double submit would consume the patient's own
    valid code and then reject them with 'Invalid verification code'."""
    js = kiosk_js()
    assert "let otpVerifying = false;" in js
    assert "if (otpVerifying) return;" in js
    assert "otpVerifying = true;" in js
    assert "otpVerifying = false;" in js


# --- nothing that already worked was taken away -----------------------------


def test_manual_entry_survives_in_full():
    """The human's rule: voice/auto must never remove the keyboard path."""
    html = kiosk_html()
    assert 'onclick="verifyOtp()"' in html          # the explicit button remains
    assert html.count('class="otp-input"') == 6     # still hand-typeable, box by box
    js = kiosk_js()
    assert "box.addEventListener('input'" in js     # KIOSK-1 auto-advance
    assert "boxes[i - 1].focus();" in js            # KIOSK-1 Backspace walk-back
    assert "box.addEventListener('paste'" in js     # KIOSK-1 paste-to-fill
