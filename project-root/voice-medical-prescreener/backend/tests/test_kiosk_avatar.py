"""P1/P2 — the robotic doctor, and the elderly-friendly sizing around it.

The avatar exists to answer one question without words: **"is it my turn?"** That is only
useful if it can never be wrong, so the design rule this file defends is that every
visual state is DERIVED from the variables the rest of the kiosk already acts on —
`listening`, `ttsSpeaking()`, `state.busy` — rather than pushed from call sites that
could drift out of sync with what the microphone is actually doing.

The precedence is the contract, not a preference:

  1. **listening** outranks everything — a patient who believes the kiosk stopped
     listening stops talking mid-answer, which is a rule #1 defect, not a UX nit;
  2. **speaking** outranks **processing**, because `state.busy` stays true across
     `assistantSays()`; testing busy first would show "please wait" over a talking
     doctor;
  3. **processing** last, which makes it the honest meaning of busy — work with no
     audible output.

Only `done` and `error` may be pushed (no live variable can express "finished" or
"failed"), and `error` therefore carries an expiry.

⚠ Scope (the S28 convention): static-source assertions over the served kiosk.js /
kiosk.html plus geometry-independent CSS checks. They prove the wiring and the values.
The state machine was ALSO executed in a real browser engine — all six states, both
avatar elements, the precedence cases, the poll and the expiry — and the elderly sizing
was measured live at 1280x900, 1280x720, 1024x600 and 375x812; see the session notes.
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


def derived_state_body(*, code_only: bool = False) -> str:
    body = kiosk_js().split("function currentAvatarState() {")[1].split("\n}")[0]
    if code_only:
        # strip // comments — the body deliberately NAMES the API it must not use
        body = "\n".join(line.split("//")[0] for line in body.splitlines())
    return body


def top_level_css() -> str:
    """The page CSS with every @media block removed — what applies at any size."""
    css = kiosk_html().split("<style>")[1].split("</style>")[0]
    return re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)


# --- the avatar tells the truth ---


def test_the_avatar_state_is_derived_from_real_signals():
    body = derived_state_body()
    assert "if (listening) return 'listening';" in body
    assert "ttsSpeaking()" in body
    assert "state.busy || state.finishing" in body


def test_listening_outranks_every_other_state():
    """The one state a patient must never be wrong about."""
    body = derived_state_body()
    assert body.index("listening") < body.index("ttsSpeaking")
    assert body.index("listening") < body.index("state.busy")


def test_speaking_outranks_processing_because_busy_spans_the_speech():
    """submitPatientTurn() sets state.busy = true and only clears it AFTER
    assistantSays() has spoken — so a busy-first test would caption a talking doctor
    with "please wait". This pins both halves: the order here, and the overlap there."""
    body = derived_state_body()
    assert body.index("ttsSpeaking") < body.index("state.busy")

    submit = kiosk_js().split("async function submitPatientTurn(rawText, source) {")[1] \
                       .split("\n}")[0]
    assert submit.index("state.busy = true;") < submit.index("assistantSays(")
    assert submit.index("assistantSays(") < submit.rindex("state.busy = false;")


def test_speaking_is_read_through_the_tts_helper_not_speech_synthesis():
    """ADR-0049: speechSynthesis.speaking is FALSE while the server-TTS <audio> plays,
    which is the entire Bangla path on Windows. The avatar must ask the same predicate
    the S3 echo guard asks, or the face and the microphone will disagree."""
    body = derived_state_body(code_only=True)
    assert "speechSynthesis.speaking" not in body
    assert "ttsSpeaking()" in body


def test_the_only_pushed_states_are_done_and_error():
    """Everything else must be derived. If a setAvatarOverride('listening') ever appears,
    the avatar has become capable of lying about the microphone."""
    js = kiosk_js()
    pushed = set(re.findall(r"setAvatarOverride\('(\w+)'", js))
    assert pushed <= {"done", "error"}, f"non-terminal state pushed: {pushed - {'done', 'error'}}"


def test_the_error_face_expires_with_its_banner():
    """showError() auto-hides after 8 s (shared.js). An error face outliving the message
    would tell a recovered patient the kiosk is still broken."""
    js = kiosk_js()
    assert "setAvatarOverride('error', { clearAfterMs: 8000 })" in js
    handler = js.split("r.onerror = (e) => {")[1].split("\n  };")[0]
    assert "setAvatarOverride('error'" in handler


def test_the_done_face_is_set_on_submit_and_cleared_for_the_next_patient():
    """⚠ S36 (ADR-0057) moved the CLEAR, not the rule. It used to be one line of a
    hand-written teardown inside confirmSubmit's logout timer; it now lives in
    startNewSession(), the single seam that hands the kiosk to the next patient. The
    reason is the reason for the whole session-boundary work: a teardown maintained by
    remembering had already forgotten the phone ticker, the recognition engine and
    `finalBuffer`. There is nothing left for a caller to forget."""
    js = kiosk_js()
    body = js.split("async function confirmSubmit() {")[1].split("\n}\n")[0]
    assert "setAvatarOverride('done');" in body
    assert "startNewSession();" in body
    assert body.index("setAvatarOverride('done');") < body.index("startNewSession();")

    handover = js.split("function startNewSession() {")[1].split("\n}")[0]
    assert "setAvatarOverride(null);" in handover, "the next patient must not inherit 'All done'"
    # …and the clear still happens only AFTER the previous session is torn down
    assert handover.index("endSession();") < handover.index("setAvatarOverride(null);")


def test_reset_state_never_touches_the_override():
    """resetState() runs at module load, where `avatarOverride` is still in its temporal
    dead zone — assigning it there is a ReferenceError that kills the whole kiosk. The
    clear is done in the logout timer instead, which runs at runtime."""
    body = kiosk_js().split("function resetState() {")[1].split("\n}")[0]
    assert "avatarOverride" not in body
    assert "setAvatarOverride" not in body


def test_the_state_is_polled_because_speech_has_no_progress_event():
    js = kiosk_js()
    assert "const AVATAR_POLL_MS = 200;" in js
    assert "setInterval(refreshAvatar, AVATAR_POLL_MS);" in js


def test_an_unchanged_state_writes_nothing_to_the_dom():
    """Re-applying the same data-attribute restarts every CSS animation, so a 200 ms poll
    that always wrote would leave the mouth and rings permanently stuttering."""
    body = kiosk_js().split("function refreshAvatar() {")[1].split("\n}")[0]
    assert "if (next === avatarState) return;" in body


# --- both docks, both languages, and a screen reader ---


def test_every_screen_that_talks_to_the_patient_carries_the_avatar():
    """Conversation dock, KIOSK-7 resume dock, and (S34) the floating assistant on the
    review screen. One list, one state machine — a mount that is not in AVATAR_IDS is a
    robot that silently stops reacting, which is worse than no robot at all."""
    js, html = kiosk_js(), kiosk_html()
    mounts = re.search(r"const AVATAR_IDS = \[([^\]]*)\];", js)
    assert mounts, "AVATAR_IDS is no longer a plain literal"
    ids = re.findall(r"'([^']+)'", mounts.group(1))
    assert ids == ["doctor-avatar", "resume-avatar", "summary-avatar"]
    for element_id in ids:
        assert f'id="{element_id}"' in html, f"#{element_id} is in AVATAR_IDS but not in the markup"
    # The status lines the same states write must exist too, or applyAvatarState()
    # would silently no-op on that screen.
    for element_id in ("doctor-status", "summary-status",
                       "doctor-substatus", "summary-substatus"):
        assert f'id="{element_id}"' in html


def test_every_avatar_state_is_bilingual():
    """P1-2: a half-translated turn cue is worse than none — the patient reads the one
    line that tells them to speak."""
    block = kiosk_js().split("const AVATAR_STATES = {")[1].split("\n};")[0]
    for name in ("idle", "speaking", "listening", "processing", "done", "error"):
        entry = block.split(f"{name}: {{")[1].split("},")[0]
        assert "en:" in entry and "bn:" in entry, f"{name} is not bilingual"
        assert "sub:" in entry, f"{name} has no secondary line"


def test_the_language_toggle_re_renders_the_avatar():
    body = kiosk_js().split("function onLanguageChange() {")[1].split("\n}")[0]
    assert "applyAvatarState(avatarState)" in body


def test_the_state_is_announced_to_screen_readers():
    html = kiosk_html()
    assert 'id="doctor-status" aria-live="polite"' in html
    assert 'role="img"' in html
    assert "el.setAttribute('aria-label', t(entry.en, entry.bn));" in kiosk_js()


# --- the CSS that carries the meaning ---


def test_the_state_lamp_is_driven_by_custom_properties():
    """REGRESSION, found by measuring computed styles in a browser: per-state rules on
    `.doctor-antenna::after` applied their box-shadow but silently kept the base
    `background`, so the lamp stayed grey in all six states. A custom property inherits
    into the pseudo-element and cannot half-apply."""
    css = kiosk_html()
    assert "--lamp: var(--text-muted);" in css and "--lamp-glow: none;" in css
    assert "background: var(--lamp); box-shadow: var(--lamp-glow);" in css
    for state in ("speaking", "listening", "processing", "done", "error"):
        assert f'[data-avatar-state="{state}"] {{ --lamp:' in css, f"{state} sets no lamp colour"
    assert ".doctor-antenna::after { background: var(--text-muted)" not in css


def test_each_state_has_a_distinct_non_colour_cue():
    """Colour alone fails a colour-blind or low-vision patient, and the antenna is small.
    Each state also changes SHAPE or MOTION: mouth, rings, eyes, mouth flip."""
    css = kiosk_html()
    assert '[data-avatar-state="speaking"] .doctor-mouth { animation: doctor-talk' in css
    assert '[data-avatar-state="listening"] .doctor-ring { animation: doctor-pulse' in css
    assert '[data-avatar-state="processing"] .doctor-eye { animation: doctor-think' in css
    assert '[data-avatar-state="error"] .doctor-mouth { transform: rotate(180deg); }' in css


def test_reduced_motion_keeps_the_information():
    """Motion is the primary cue, so removing it must not remove the meaning — the lamp
    colour and the always-present status text carry it."""
    css = kiosk_html()
    block = css.split("@media (prefers-reduced-motion: reduce) {")[1].split("\n    }")[0]
    assert "animation: none" in block
    assert '[data-avatar-state="listening"] .doctor-ring { opacity: .85; }' in block


def test_the_avatar_is_real_3d_not_a_flat_badge():
    css = kiosk_html()
    assert "perspective: 700px;" in css
    assert "transform-style: preserve-3d;" in css
    assert "translateZ" in css


def test_no_external_asset_is_needed_for_the_avatar():
    """CPU-only hardware and an offline kiosk: the doctor must not depend on a model
    file, a sprite or a WebGL context that a clinic PC may not have."""
    html = kiosk_html()
    avatar = html.split('id="doctor-avatar"')[1].split("</div>\n        </div>")[0]
    for forbidden in ("<img", "<canvas", "<video", "background-image", "url("):
        assert forbidden not in avatar, f"avatar depends on {forbidden}"


# --- P2: elderly-friendly sizing ---


def test_primary_controls_meet_the_touch_target_minimum():
    css = top_level_css()
    assert "min-height: 52px" in css      # .btn
    assert "min-height: 54px" in css      # .input-field
    assert "min-width: 44px; min-height: 44px" in css   # .bubble-speak
    assert "min-height: 48px" in css      # .mode-btn


def test_the_replay_button_is_no_longer_a_20px_target():
    """Measured at 30x20 before this — the control an elderly patient reaches for most
    was the smallest thing on the screen."""
    css = kiosk_html()
    block = css.split(".bubble-speak {")[1].split("}")[0]
    assert "min-width: 44px" in block and "min-height: 44px" in block
    assert "padding: 2px 4px" not in block


def test_keyboard_focus_is_visible_on_every_control():
    css = kiosk_html()
    assert "button:focus-visible, input:focus-visible, a:focus-visible {" in css
    assert "outline: 3px solid var(--border-focus)" in css


def test_the_otp_boxes_shrink_instead_of_overflowing_a_narrow_screen():
    """Six fixed-width boxes overflow a 375px phone sideways; flex + min-width:0 is what
    lets them fit. Measured: 47x50 at 375px wide, no horizontal page overflow."""
    block = kiosk_html().split(".otp-input {")[1].split("}")[0]
    assert "flex: 1" in block and "min-width: 0" in block


def test_both_responsive_axes_are_handled():
    """Short screens run out of VERTICAL room (the primary action drops under the fold);
    narrow screens run out of HORIZONTAL room (OTP boxes, two-column summary). Different
    problems, so they get different rules."""
    css = kiosk_html()
    assert "@media (max-height: 820px)" in css
    assert "@media (max-width: 620px)" in css
    narrow = css.split("@media (max-width: 620px) {")[1]
    assert "grid-template-columns: 1fr;" in narrow, "the 2-column summary is unreadable at 375px"


def test_no_selector_is_sized_twice_at_the_same_specificity():
    """REGRESSION on a bug introduced and caught in this session: the elderly-sizing block
    re-declared .welcome-title / .welcome-sub / .summary-label, which already had rules
    LATER in the same file. Equal specificity means the later rule wins, so the new sizes
    were dead CSS that read as though it applied. Sizes are now raised in place."""
    css = top_level_css()
    for selector in (".welcome-title", ".welcome-sub", ".summary-label", ".chat-turn",
                     ".dock-transcript", ".bubble-speak", ".otp-input"):
        # Anchored at line start so a genuinely MORE specific rule
        # (`.identify-dock .dock-transcript`) is not counted — that one legitimately
        # wins on specificity. Only equal-specificity duplicates are the bug.
        hits = re.findall(rf"(?m)^\s*{re.escape(selector)}\s*\{{", css)
        assert len(hits) == 1, f"{selector} declared {len(hits)}x outside @media — later one wins"
