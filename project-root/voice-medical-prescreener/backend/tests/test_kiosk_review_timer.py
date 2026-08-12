"""S34 (ADR-0055) — the 60-second review clock, and the ONE ticker every countdown uses.

A finished pre-screening left sitting on the review screen helps nobody: the doctor
never receives it and the kiosk stays occupied. So the review submits itself. What makes
that safe rather than reckless is a small set of rules, and this file is those rules:

  * the clock runs ONLY while Confirm & Submit is genuinely pressable — the same verdict
    the button uses, so it can never fire into a case the server would refuse, and never
    while a required question is still open;
  * any manual action cancels it (the button, Speak Again, the post-submit reset);
  * one timeout = one submit. The ticker fires `onEnd` at most once and confirmSubmit()
    carries its own re-entry guard, so a timeout racing a tap cannot send twice;
  * re-entering the review screen never stacks a second timer.

The ticker itself is extracted rather than written twice, and the 5-second auto-logout
countdown is moved onto it — which is the proof it is genuinely reusable and not a
wrapper built for one caller.

⚠ Scope, honestly (the S28 convention): static-source assertions over the served
kiosk.js. They prove the wiring and the guards. The behaviour was ALSO executed in a
real browser engine: the clock counted 60 -> 57 -> 53 -> 52, froze and hid on Speak
Again, restarted at 60 on return, went `urgent` under 10 s, and — with the timeout
firing at the same moment as TWO manual confirmSubmit() calls — produced exactly ONE
POST to /submit. The ticker itself yielded 3,2,1,0 with `onEnd` fired once, and a cancel
before zero suppressed it entirely. See the session notes.
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


def code_only(source: str) -> str:
    without_blocks = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return "\n".join(line.split("//")[0] for line in without_blocks.splitlines())


# --- the shared ticker ---


def test_there_is_one_reusable_ticker_and_the_logout_countdown_uses_it():
    """P7: not several unrelated countdown implementations. The 5-second auto-logout was
    a hand-rolled setInterval; moving it onto the shared ticker is what demonstrates the
    extraction is real."""
    js = kiosk_js()
    assert "function startTicker(totalMs, { onTick = null, onEnd = null, tickMs = 250 } = {}) {" in js
    submit = js.split("async function confirmSubmit() {")[1].split("\n}\n")[0]
    assert "startTicker(5000, {" in submit
    assert "setInterval" not in code_only(submit), "the logout countdown must not roll its own"


def test_the_ticker_fires_its_end_callback_at_most_once():
    """`onEnd` submits a visit. A second firing would submit it twice, and an onEnd that
    starts another ticker or navigates must not be able to re-enter this one — so `done`
    is set BEFORE the callback, not after."""
    body = fn_body("startTicker")
    assert "handle.cancel();          // BEFORE onEnd" in body
    assert body.index("handle.cancel();") < body.index("if (onEnd) onEnd();")
    assert "if (handle.done) return;" in body


def test_cancelling_before_zero_suppresses_the_end_callback_entirely():
    """"The patient pressed the button first" and "the patient walked away" must both
    mean the timeout never happens — not merely that its clock stopped ticking."""
    body = fn_body("startTicker")
    assert "handle.cancel = () => {" in body
    cancel = body.split("handle.cancel = () => {")[1].split("};")[0]
    assert "handle.done = true;" in cancel
    assert "clearInterval(handle.timer);" in cancel


def test_the_first_value_is_painted_immediately():
    """Otherwise the clock shows its markup default for a quarter of a second before the
    real number arrives — which on a 3-second countdown is a visible lie."""
    body = fn_body("startTicker")
    assert "tick();                     // paint the starting value now" in body
    assert body.index("tick();  ") < body.index("setInterval(tick, tickMs)")


def test_the_s4_endpointer_is_deliberately_not_folded_into_the_ticker():
    """It looks like the same thing and is not: its deadline is RESTARTED by every
    recognition result, and that restart IS the anti-clipping guarantee (rule #1).
    Rewriting a rule #1 safeguard for tidiness would trade a real guarantee for a
    smaller diff — so the S4 countdown keeps its own, test-pinned implementation."""
    js = kiosk_js()
    assert "countdownTicker = setInterval(renderCountdown, 200);" in js
    assert "function restartSilenceWindow()" in js
    window = js.split("function restartSilenceWindow()")[1].split("function renderCountdown")[0]
    assert "startTicker" not in window


# --- when the clock may run ---


def test_the_clock_and_the_submit_button_share_one_verdict():
    """A countdown toward a button that is not there — or toward a submit the server
    would refuse with a 409 — is a kiosk counting down to nothing."""
    body = fn_body("updateSubmitVisibility")
    assert "if (blocked) cancelReviewTimer(); else startReviewTimer();" in body
    # …and `blocked` is still the F3 verdict, unchanged.
    assert "state.resumeActive || (state.readiness && !state.readiness.complete)" in body


def test_re_entering_the_review_screen_never_stacks_a_second_timer():
    """updateSubmitVisibility() runs on every resume-loop turn, so start must be
    idempotent — two live tickers would mean two submits."""
    body = fn_body("startReviewTimer")
    assert "if (reviewTicker) return;" in body


def test_a_clinic_can_disable_the_auto_submit_entirely():
    """0 = the patient presses the button themselves. The route also clamps negatives,
    which would otherwise arrive as an instantly-expired timer, i.e. submit-on-arrival."""
    js = kiosk_js()
    assert "review_timeout_ms: 60000," in js
    body = fn_body("startReviewTimer")
    assert "if (!total) { hideReviewClock(); return; }" in body
    assert "Math.max(0, Number(voiceConfig.review_timeout_ms) || 0)" in fn_body("reviewTimeoutMs")


def test_leaving_the_review_screen_stops_the_clock():
    """"Speak Again" goes back to the conversation. A clock left running behind it would
    submit a review the patient had walked away from mid-correction."""
    body = fn_body("reviewSpeakAgain")
    assert "cancelReviewTimer();" in body
    assert "showScreen('screen-voice');" in body
    assert 'onclick="reviewSpeakAgain()"' in kiosk_html()
    assert "onclick=\"showScreen('screen-voice')\"" not in kiosk_html(), \
        "the bare navigation would leave the clock running"


# --- exactly one submission ---


def test_the_submit_is_guarded_against_the_timeout_racing_a_tap():
    """Two things can now ask for a submit. The visit must be sent EXACTLY once whichever
    arrives first — a double POST would submit the same visit twice."""
    js = kiosk_js()
    assert "let submitting = false;" in js
    body = js.split("async function confirmSubmit() {")[1].split("\n}\n")[0]
    assert "if (submitting) return;" in body
    assert body.index("if (submitting) return;") < body.index("submitting = true;")
    assert "cancelReviewTimer();" in body


def test_a_failed_submit_releases_the_guard_but_a_successful_one_does_not():
    """A 409 (required info missing) must leave the patient able to try again once they
    have answered. A SUCCESSFUL submit must not — there is nothing left to submit until
    resetState() hands the kiosk to the next patient."""
    body = kiosk_js().split("async function confirmSubmit() {")[1].split("\n}\n")[0]
    catch = body.split("} catch (e) {")[1].split("}")[0]
    assert "submitting = false;" in catch
    after_success = body.split("setAvatarOverride('done');")[1]
    # the only re-arm on the success path is inside the logout reset, i.e. for the NEXT patient
    assert after_success.count("submitting = false;") == 1
    assert "resetState();" in after_success
    assert after_success.index("resetState();") < after_success.index("submitting = false;")


def test_the_timeout_route_goes_through_the_same_guarded_submit():
    """One submit path. A timeout that POSTed for itself could not be protected by the
    button's guard, and the two would race."""
    body = fn_body("startReviewTimer")
    assert "confirmSubmit();" in body
    assert "api(" not in body, "the timeout must not submit on its own"
    assert "reviewTicker = null;" in body   # the handle is released before it fires


def test_no_clock_may_outlive_the_patient_it_belongs_to():
    """A stale review clock firing after the logout reset would submit into the NEXT
    patient's visit — the same class of defect the S4 countdown teardown exists for."""
    js = kiosk_js()
    logout = js.split("async function confirmSubmit() {")[1].split("\n}\n")[0]
    assert "cancelReviewTimer();        // S34" in logout
    assert "cancelPendingMic();" in logout and "cancelCountdown();" in logout
    assert "document.getElementById('review-timer').style.display = 'none';" in fn_body("resetState")


# --- what the patient sees ---


def test_the_clock_reads_as_a_countdown_in_both_languages():
    """"60s left", "59s left" … "1s left" — with Bangla numerals under the BN toggle."""
    body = fn_body("renderReviewClock")
    assert "setBilingualText('review-timer-value', `${secondsLeft}s`, bnDigits(secondsLeft))" in body
    html = kiosk_html()
    assert 'id="review-timer-value"' in html
    # The unit belongs to the LABEL: "৫৯s বাকি" was half-translated on the live page, so
    # Bangla carries the whole unit ("৫৯ সেকেন্ড বাকি") and English keeps "59s left".
    assert 'data-en="left" data-bn="সেকেন্ড বাকি"' in html


def test_the_clock_gets_visually_louder_as_it_runs_out():
    """The last ten seconds are when it matters. Urgency is carried by a CLASS so the
    CSS animation is not restarted on every 250 ms tick."""
    body = fn_body("renderReviewClock")
    assert "box.classList.toggle('urgent', secondsLeft <= 10);" in body
    css = kiosk_html()
    assert ".review-timer.urgent {" in css
    assert "@keyframes clock-urgent" in css


def test_it_looks_like_a_blinking_digital_clock():
    """The spec is a small digital display that blinks — a static number reads as a
    label, not as something that is running out."""
    css = kiosk_html()
    assert "@keyframes clock-blink" in css
    # Anchored at line start: the reduced-motion block names this selector too (in a
    # group, to switch the animation OFF), and it comes first in the file.
    block = re.search(r"(?m)^\s*\.review-timer-value \{([^}]*)\}", css)
    assert block, ".review-timer-value has no rule of its own"
    assert "animation: clock-blink" in block.group(1)
    assert "font-variant-numeric: tabular-nums" in css.split(".review-timer {")[1].split("}")[0]


def test_the_clock_never_covers_the_review_heading():
    """REGRESSION, measured: as an absolutely-positioned overlay it sat on top of the
    centred title at 730px wide. As a flex sibling it reserves its own space at every
    width, and re-centres the heading when it is hidden."""
    css = kiosk_html().split("<style>")[1].split("</style>")[0]
    head = css.split(".summary-head {")[1].split("}")[0]
    assert "display: flex" in head
    timer = css.split(".review-timer {")[1].split("}")[0]
    assert "position: absolute" not in timer
    assert "flex: none" in timer
    # …and on a narrow screen it moves above the heading rather than beside it.
    narrow = css.split("@media (max-width: 620px) {")[1]
    assert ".summary-head { flex-direction: column-reverse;" in narrow
