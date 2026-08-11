"""F5b (ADR-0053) — the patient identifies themselves BY VOICE, on the existing engine.

The human's explicit regression rule for this step was "do NOT build a second
recognizer". So most of what these tests defend is *structural*: identification is two
more entries in the `DOCKS` map and two more branches at the ONE routing point in
`stopListening()`, which is why the S3 echo guard, the S4 confirmation countdown, the S2
Speak/Type switch and S31's terminal-error handling all apply to the phone and OTP
screens without a line of new logic.

The one asymmetry between the two screens is deliberate and is pinned here:

  * a spoken PHONE NUMBER is read back and must be CONFIRMED — a wrong digit sends the
    patient's verification code to a stranger's handset, and nothing about that is
    self-correcting;
  * a spoken OTP is filled straight into the six boxes and handed to F1's existing
    `maybeAutoVerify()` — a wrong code is rejected by the server, cleared and re-asked,
    so a confirmation step would add a tap and buy no safety (ADR-0048).

⚠ Scope, honestly (the S28 convention): these are static-source assertions over the
served kiosk.js/kiosk.html. They prove the wiring, not browser behaviour, and they
CANNOT prove anything about real speech — no microphone was ever involved. The flows
were separately executed in a real browser engine by driving the recogniser's own buffer
(spoken Bangla-word phone number -> read-back -> confirm -> OTP screen -> spoken
Bangla-word code -> verified -> conversation); see the session notes.
"""

import re

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


def dock_block(name: str) -> str:
    """The DOCKS entry for one dock, straight out of the served file."""
    js = kiosk_js()
    body = js.split("const DOCKS = {")[1].split("\n};")[0]
    block = body.split(f"  {name}: {{")[1].split("},")[0]
    assert block.strip(), f"DOCKS.{name} parsed empty"
    return block


# --- one engine: identification is more docks, not more pipelines ---


def test_there_is_still_exactly_one_recognizer():
    """The human's regression rule. `new SR()` appears once, in initRecognition()."""
    js = kiosk_js()
    assert js.count("new SR()") == 1
    assert js.count("function initRecognition()") == 1
    assert js.count("window.SpeechRecognition || window.webkitSpeechRecognition") == 1


def test_the_identification_docks_exist_in_the_one_docks_map():
    js = kiosk_js()
    body = js.split("const DOCKS = {")[1].split("\n};")[0]
    for name in ("conversation", "resume", "phone", "otp"):
        assert f"  {name}: {{" in body, f"DOCKS.{name} missing"


def test_identify_docks_declare_the_elements_the_engine_dereferences_unguarded():
    """toggleListening()/stopListening() do getElementById(dock.mic).classList and
    r.onresult does getElementById(dock.transcript).dataset with NO null check, so a
    dock that can become active without these two keys is a TypeError waiting for a
    patient to tap the mic."""
    for name in ("phone", "otp"):
        block = dock_block(name)
        assert "mic:" in block, f"DOCKS.{name} has no mic"
        assert "transcript:" in block, f"DOCKS.{name} has no transcript"


def test_identify_docks_deliberately_have_no_fallback_row():
    """The number field and the OTP boxes ARE the typed path and also the display of
    what was heard, so they must stay visible in voice mode. setInputMode() hides
    `dock.fallback`; omitting the key is how these docks say "nothing to hide"."""
    for name in ("phone", "otp"):
        assert "fallback:" not in dock_block(name)
    # …while the two clinical docks still have theirs.
    for name in ("conversation", "resume"):
        assert "fallback:" in dock_block(name)


def test_every_dock_element_id_exists_in_the_markup():
    js, html = kiosk_js(), kiosk_html()
    body = js.split("const DOCKS = {")[1].split("\n};")[0]
    ids = re.findall(r"(?:transcript|mic|hint|input|voiceBtn|typeBtn|countdown|countdownDigit):"
                     r" ?'([^']+)'", body)
    assert len(ids) >= 28, f"expected 4 docks' worth of ids, parsed {len(ids)}"
    for element_id in ids:
        assert f'id="{element_id}"' in html, f"#{element_id} named by DOCKS but not in kiosk.html"


# --- the routing point: identification is checked FIRST ---


def test_active_dock_prefers_identification_over_the_clinical_docks():
    body = kiosk_js().split("function activeDock() {")[1].split("\n}")[0]
    assert "if (state.identifyStep) return DOCKS[state.identifyStep];" in body
    # …and it is the FIRST thing checked, before the resume/conversation choice.
    assert body.index("identifyStep") < body.index("resumeActive")


def test_a_spoken_turn_is_routed_by_identify_step_before_any_visit_call():
    """Identification runs BEFORE state.visitUuid exists. If a spoken phone number
    reached submitPatientTurn() it would be POSTed as a clinical utterance to a visit
    that has not been created — so the order of these branches is the contract."""
    body = kiosk_js().split("function stopListening(sendTurn) {")[1].split("\n}")[0]
    assert "if (state.identifyStep === 'phone') applySpokenPhone(text);" in body
    assert "else if (state.identifyStep === 'otp') applySpokenOtp(text);" in body
    assert body.index("applySpokenPhone") < body.index("submitResumeAnswer")
    assert body.index("applySpokenOtp") < body.index("submitPatientTurn")


# --- the phone screen: never send on the recogniser's say-so ---


def test_a_spoken_phone_number_is_confirmed_not_sent():
    """applySpokenPhone must not call sendOtp(). The ONLY caller is confirmPhone(),
    i.e. the patient's own tap on "Yes"."""
    body = kiosk_js().split("function applySpokenPhone(rawText) {")[1].split("\n}\n")[0]
    assert "sendOtp" not in body, "a spoken number must never be submitted directly"
    assert "showPhoneConfirm(national)" in body
    confirm = kiosk_js().split("function confirmPhone() {")[1].split("\n}")[0]
    assert "sendOtp();" in confirm


def test_an_unparseable_number_keeps_what_was_heard_and_sends_nothing():
    """Nine correct digits are a head start for the typed repair, and the patient can
    see where recognition went wrong. The read-back stays hidden."""
    body = kiosk_js().split("function applySpokenPhone(rawText) {")[1].split("\n}\n")[0]
    assert "input.value = heard;" in body
    assert "hidePhoneConfirm();" in body


def test_editing_the_field_by_hand_retracts_a_pending_read_back():
    """Otherwise the patient could change the number, tap "Yes", and send the OLD one —
    the read-back must never outlive the value it vouches for."""
    assert "phoneInput.addEventListener('input', hidePhoneConfirm);" in kiosk_js()


def test_the_read_back_is_shown_in_the_local_11_digit_form_and_follows_the_toggle():
    body = kiosk_js().split("function renderPhoneReadback() {")[1].split("\n}")[0]
    assert "const local = '0' + state.pendingPhone;" in body
    assert "el.dataset.en = grouped;" in body and "el.dataset.bn = bnDigits(grouped);" in body


def test_the_read_back_is_spoken_as_separate_digits():
    """Handed '01715984632' whole, a synthesizer says "one billion, seven hundred…",
    which cannot be checked against a phone number."""
    body = kiosk_js().split("function speakDigits(ascii) {")[1].split("\n}")[0]
    assert "shown.split('').join(' ')" in body


def test_the_read_back_panel_is_scrolled_into_view_after_layout():
    """It opens below the fold on a 720px screen. The forced reflow is load-bearing:
    in the same tick as display='flex' the layout is stale and scrollIntoView is a
    no-op (measured)."""
    body = kiosk_js().split("function showPhoneConfirm(national) {")[1].split("\n}")[0]
    assert "void panel.offsetHeight;" in body
    # anchor on the CALL, not the word — the comment above it names scrollIntoView too
    assert body.index("void panel.offsetHeight;") < body.index("panel.scrollIntoView({")


# --- the OTP screen: reuse F1, do not reimplement it ---


def test_a_spoken_code_is_handed_to_the_existing_auto_verify():
    body = kiosk_js().split("function applySpokenOtp(rawText) {")[1].split("\n}\n")[0]
    assert "maybeAutoVerify();" in body
    assert "verify-otp" not in body, "there must be no second verify path"
    assert "otpBoxes().forEach((box, i) => { box.value = digits[i]; });" in body


def test_a_wrong_length_spoken_code_clears_and_re_asks_without_submitting():
    body = kiosk_js().split("function applySpokenOtp(rawText) {")[1].split("\n}\n")[0]
    assert "if (digits.length !== OTP_LENGTH) {" in body
    assert "clearOtpInputs({ focus: false });" in body
    assert body.index("reAskOtp();") < body.index("maybeAutoVerify();")


def test_a_rejected_code_re_asks_aloud_in_voice_mode():
    """F1 already clears the boxes and keeps the server's reason; F5b adds the voice
    half, so retrying is speaking rather than hunting for the boxes."""
    assert "if (!res) { reAskOtp(); return; }" in kiosk_js()


def test_re_asking_is_voice_mode_only():
    """A patient who chose typing has already been told what to fix by the banner;
    speaking at them and reopening the mic would be undoing their choice."""
    for fn in ("reAskPhone", "reAskOtp"):
        body = kiosk_js().split(f"function {fn}() {{")[1].split("\n}")[0]
        assert "state.inputMode !== 'voice'" in body
        assert "return;" in body


# --- the step machine ---


def test_the_kiosk_opens_on_the_phone_identification_step():
    assert "identifyStep: 'phone'," in kiosk_js()
    assert "pendingPhone: null," in kiosk_js()


def test_sending_the_code_moves_the_step_before_speaking():
    """askAloud() resolves activeDock() immediately, so the step must already say 'otp'
    or the arming hint and the mic would land on the phone dock."""
    body = kiosk_js().split("async function sendOtp() {")[1].split("\n}")[0]
    assert "state.identifyStep = 'otp';" in body
    assert body.index("state.identifyStep = 'otp';") < body.index("askAloud(")


def test_verification_hands_the_mic_back_to_the_conversation():
    body = kiosk_js().split("async function verifyOtp() {")[1].split("\n}")[0]
    assert "state.identifyStep = null;" in body
    assert body.index("state.identifyStep = null;") < body.index("askScriptedQuestion(0)")


# --- hints: no dock may tell a patient to press a control it does not have ---


def test_identification_docks_override_the_typing_hint():
    """The identification screens have no Send button and nothing on them is an
    "answer" — MODE_HINTS' "Type your answer, then press Send" reads as a broken kiosk."""
    js = kiosk_js()
    assert "const IDENTIFY_HINTS = {" in js
    for name in ("phone", "otp"):
        assert "hints: IDENTIFY_HINTS," in dock_block(name)
    for name in ("conversation", "resume"):
        assert "hints:" not in dock_block(name), "the clinical docks keep MODE_HINTS"


def test_identify_hints_are_declared_before_docks_uses_them():
    """const is not hoisted-initialised: declaring IDENTIFY_HINTS after DOCKS throws a
    ReferenceError at load and the whole kiosk is dead. Caught exactly that way."""
    js = kiosk_js()
    assert js.index("const IDENTIFY_HINTS = {") < js.index("const DOCKS = {")


def test_mode_hint_is_dock_aware_at_every_call_site():
    js = kiosk_js()
    assert "function modeHint(dock) {" in js
    assert "const hints = (dock && dock.hints) || MODE_HINTS;" in js
    assert "modeHint()" not in js.replace("function modeHint(dock)", ""), \
        "a dock-less modeHint() call would silently fall back to the clinical wording"


# --- markup ---


def test_both_identification_docks_are_in_the_markup():
    html = kiosk_html()
    assert 'id="phone-dock"' in html and 'id="otp-dock"' in html
    assert 'id="phone-confirm"' in html and 'id="phone-readback"' in html
    assert 'onclick="confirmPhone()"' in html and 'onclick="rejectPhone()"' in html


def test_the_first_otp_box_is_addressable_for_the_typing_focus():
    assert 'class="otp-input" id="otp-input-1"' in kiosk_html()


def test_identification_screens_are_bilingual():
    """P1-2: every string a patient reads here carries both languages."""
    html = kiosk_html()
    dock = html.split('id="phone-dock"')[1].split('id="phone-confirm"')[0]
    assert dock.count("data-en=") == dock.count("data-bn="), "unpaired data-en/data-bn"
    assert dock.count("data-bn=") >= 5
    confirm = html.split('id="phone-confirm"')[1].split("</div>\n      </div>")[0]
    assert confirm.count("data-en=") == confirm.count("data-bn=")
