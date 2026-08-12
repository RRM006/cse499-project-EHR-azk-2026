"""S35 / Findings 1 + 3 + 8 (ADR-0056) — the phone read-back's 10-second window, the ONE
header clock, and the "it is listening" cues.

⚠ FIRST, A CORRECTION TO THE BRIEF. The session's finding said the phone read-back
"currently auto-accepts after approximately 10 seconds". **It did not.** There was no
timer on that panel at all: ADR-0053 deliberately required a tap, because a wrong digit
does not annoy the patient — it sends their verification code to a stranger's handset.
Verified by inspection before anything was changed. So this is a NEW behaviour, not a
repaired one, and ADR-0056 (a) records why the change is safe: the presentation is
untouched (still the largest text on the screen, still read back digit by digit), only
the DEFAULT when the patient does nothing has changed — and `VOICE_PHONE_CONFIRM_MS=0`
restores ADR-0053's tap-required rule exactly.

The clock half is Finding 8: one element, in the portal header, which sits outside the
scrolling `.screen`. That is what makes "visible without scrolling" and "cannot overlap"
structural facts rather than measurements that hold at the one width someone tried.

⚠ Scope (the S28 convention): static-source assertions plus geometry measured in a real
browser engine — no microphone. The live results are in the session notes: the clock ran
10s -> 8s -> 7s in the header; a triple tap sent EXACTLY ONE lookup and stopped the
clock; reject sent none; the timeout sent exactly one; re-showing the panel did not
stack a second ticker; and at 1280x720, 1024x600 and 375x812 the clock never overlapped
the heading, the avatar or a button and stayed visible after scrolling the review to the
bottom.
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


def fn_body(name: str) -> str:
    js = kiosk_js()
    marker = f"function {name}("
    assert marker in js, f"{name}() is gone from the shipped kiosk"
    return js.split(marker)[1].split("\n}")[0]


def top_level_css() -> str:
    css = kiosk_html().split("<style>")[1].split("</style>")[0]
    return re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)


# --- Finding 1: the 10-second window ---


def test_the_window_reuses_the_one_shared_ticker():
    """Not a fourth countdown implementation. `startTicker()` already serves the review
    clock and the auto-logout; a phone-specific timer would be the thing S34's ADR-0055
    (h) extracted the ticker to prevent."""
    body = fn_body("startPhoneTimer")
    assert "startTicker(total, {" in body
    assert "setInterval" not in body and "setTimeout" not in body


def test_it_starts_with_the_read_back_and_dies_with_it():
    """The clock belongs to the panel. One that outlived it would send a number the
    patient had already corrected."""
    assert "startPhoneTimer();             // S35" in fn_body("showPhoneConfirm")
    assert "cancelPhoneTimer();   // S35" in fn_body("hidePhoneConfirm")


def test_re_showing_the_panel_never_stacks_a_second_timer():
    assert "if (phoneTicker) return;" in fn_body("startPhoneTimer")


def test_the_timeout_and_a_tap_can_never_both_send():
    """`hidePhoneConfirm()` clears `pendingPhone`, and confirmPhone() returns early
    without it — so the guard is the state itself rather than a flag that could be left
    set. Verified live: three taps racing the timeout produced ONE lookup call."""
    body = fn_body("confirmPhone")
    assert "if (!state || !state.pendingPhone) return;" in body
    assert body.index("if (!state || !state.pendingPhone) return;") < body.index("sendOtp();")
    assert "confirmPhone();   // its own guard makes this exactly one send" in fn_body("startPhoneTimer")


def test_a_clinic_can_require_the_tap_again():
    """ADR-0045's pattern, applied to a rule this session is CHANGING: ADR-0053's
    tap-required behaviour is kept selectable rather than deleted."""
    js = kiosk_js()
    assert "phone_confirm_ms: 10000," in js
    body = fn_body("startPhoneTimer")
    assert "if (!total) { hideClock(); return; }" in body
    assert "Math.max(0, Number(voiceConfig.phone_confirm_ms) || 0)" in fn_body("phoneConfirmMs")


def test_the_patient_is_told_it_will_send_by_itself():
    """A countdown with no explanation is a threat. The panel says what will happen and
    what to press if it is wrong — and the clock's own label says "to send"."""
    html = kiosk_html()
    assert 'id="phone-confirm-hint"' in html
    assert 'data-bn="নিজে থেকেই পাঠানো হবে — ভুল হলে ✖ চাপুন"' in html
    assert "phone: { en: 'to send', bn: 'সেকেন্ড পরে যাবে' }," in kiosk_js()


def test_the_read_back_itself_is_unchanged():
    """ADR-0053's actual safety property was never the tap — it was that the patient can
    SEE and HEAR the number before it goes. That must survive the timer verbatim."""
    body = fn_body("showPhoneConfirm")
    assert "renderPhoneReadback();" in body
    assert "speakDigits('0' + national);" in body
    assert "void panel.offsetHeight;" in body      # …and is still brought above the fold


# --- Finding 8: one clock, in the header, always visible ---


def test_there_is_exactly_one_clock_element_and_it_lives_in_the_header():
    """S34 put it inside the review layout, where it could only be seen on that screen
    and only while that screen was scrolled to the top. The header sits OUTSIDE `.screen`
    — the element that scrolls — so the clock cannot be scrolled away from."""
    html = kiosk_html()
    assert html.count('id="kiosk-clock"') == 1
    assert 'id="review-timer"' not in html, "the review-scoped clock must be gone, not duplicated"
    header = html.split('class="portal-header"')[1].split("</div>\n  </div>")[0]
    assert 'id="kiosk-clock"' in header


def test_both_countdowns_write_the_same_clock_through_one_renderer():
    js = kiosk_js()
    assert js.count("function renderClock(") == 1
    for caller in ("startReviewTimer", "startPhoneTimer"):
        assert "renderClock(secondsLeft, CLOCK_LABELS." in fn_body(caller)
    assert js.count("function hideClock(") == 1


def test_the_label_is_per_countdown_not_one_string_translated():
    """"10 সেকেন্ড বাকি" and "10s to send" are different sentences. A single label would
    have made one of the two countdowns say the wrong thing in one of the languages."""
    js = kiosk_js()
    block = js.split("const CLOCK_LABELS = {")[1].split("};")[0]
    assert "review:" in block and "phone:" in block
    assert "setBilingualText('kiosk-clock-label', label.en, label.bn);" in fn_body("renderClock")


def test_the_clock_is_in_flow_and_never_positioned_over_the_page():
    """`position: fixed` is exactly how a "floating" clock ends up on top of a heading at
    some width nobody tested. As a flex item the header row RESERVES its width, which
    makes non-overlap structural instead of measured."""
    clock = top_level_css().split(".kiosk-clock {")[1].split("}")[0]
    assert "position: fixed" not in clock and "position: absolute" not in clock
    assert "flex: none" in clock


def test_it_stays_top_right_even_when_the_header_wraps():
    """Measured at 375px: the header's right-hand group exactly fills the line, so
    `margin-left:auto` had no free space and the clock — first in the group — landed at
    the LEFT of the wrapped row. Ordering it last puts it back at the right edge."""
    html = kiosk_html()
    assert "margin-left:auto;" in html.split('class="portal-header"')[1].split("kiosk-clock")[0]
    narrow = html.split("@media (max-width: 620px) {")[1]
    assert ".kiosk-clock { padding: 5px 10px; order: 1; }" in narrow


def test_the_reset_hides_the_clock_by_id_not_through_a_helper():
    """resetState() runs at module load, before the const declarations it would
    otherwise reach — the S33 temporal-dead-zone trap."""
    body = fn_body("resetState")
    assert "document.getElementById('kiosk-clock').style.display = 'none';" in body


# --- Finding 3: "is it listening?" without reading anything ---


def test_the_page_wide_state_comes_from_the_one_derived_avatar_state():
    """No second state machine. `applyAvatarState()` is the single writer, and it is
    already the function that can only ever be called with a DERIVED state (ADR-0054) —
    so the microphone, the robot's face and these cues cannot disagree."""
    js = kiosk_js()
    assert "document.body.dataset.kioskState = name;" in fn_body("applyAvatarState")
    assert js.count("dataset.kioskState") == 1, "only applyAvatarState may write it"


def test_the_microphone_pulses_while_it_is_open():
    """The single most important question an elderly patient has — "is it hearing me?" —
    answered by motion on the control they are looking at."""
    css = top_level_css()
    assert ".mic-btn.listening { animation: mic-listening" in css
    assert "@keyframes mic-listening" in css


def test_the_instruction_gets_loud_at_the_moment_it_matters():
    """The dock hint is the sentence that says what to do NOW. It is small the rest of
    the time on purpose; while listening it is the largest text near the microphone."""
    css = kiosk_html()
    block = css.split('body[data-kiosk-state="listening"] #listening-hint,')[1].split("}")[0]
    assert "#resume-hint" in block and "#phone-hint" in block and "#otp-hint" in block
    assert "font-size: 1.05rem !important" in block


def test_the_listening_cue_survives_reduced_motion():
    """Motion is an ENHANCEMENT here, never the only carrier: the button is still red,
    the hint is still large and red, and the avatar still says so in words."""
    block = kiosk_html().split("@media (prefers-reduced-motion: reduce) {")[1].split("\n    }")[0]
    assert ".mic-btn.listening { animation: none !important; }" in block
    # Counted with the opening brace: the CSS above the pulse also NAMES this block in a
    # comment, pointing at it rather than starting a second one — which is the whole
    # point. Two real blocks would mean a reader (human or test) finds only the first.
    assert kiosk_html().count("@media (prefers-reduced-motion: reduce) {") == 1, \
        "one accessibility block, or a reader finds only the first"
