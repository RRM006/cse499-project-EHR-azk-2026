"""S34 — hearing the review, and the floating assistant that presents it.

Everything on the review screen asks the patient to CHECK their pre-screening before it
goes to the doctor, and until this session checking it meant READING it. A patient who
cannot read that screen — no glasses, low literacy, a language they speak but do not
read — had no way to review their own record at the exact moment they are asked to
approve it. So every filled card can now be heard, individually or in one pass.

The avatar half is a THIRD mount of the P1 component, not a second robot: same derived
state machine (ADR-0054), so it can no more lie on this screen than on the conversation
screen. It steps aside when the KIOSK-7 resume dock — which carries its own avatar —
opens, so the patient is never looking at two assistants wondering which one is talking.

⚠ Scope (the S28 convention): static-source assertions over the served kiosk.js /
kiosk.html, plus geometry-independent CSS checks. The screen was ALSO rendered in a real
browser engine at 730x694 and 375x812: 10 cards each with a 44px 🔊, the clock beside the
heading with no overlap (measured: title 28-568, clock 582-687), the floating assistant
sticky on the left, and no horizontal overflow at either size. See the session notes.
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
    """The page CSS with every @media block removed — what applies at any size."""
    css = kiosk_html().split("<style>")[1].split("</style>")[0]
    return re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)


# --- "what did I say?" on the review screen ---


def test_every_filled_card_can_be_heard():
    render = fn_body("renderSummary")
    assert "hear.onclick = () => speakSummaryField(key, text);" in render
    # …and only a card that HAS something to say gets the control.
    assert "if (text) {" in render
    assert render.index("if (text) {") < render.index("hear.onclick")


def test_the_card_speaker_is_a_full_size_touch_target_like_every_other_replay():
    """P2's 44px minimum. The 🔊 is the control an elderly patient reaches for most."""
    render = fn_body("renderSummary")
    assert "hear.className = 'bubble-speak';" in render      # the 44px class (test_kiosk_avatar)
    css = top_level_css()
    assert ".summary-item-head .bubble-speak { margin-left: auto; }" in css


def test_the_card_read_back_is_labelled_so_the_patient_knows_which_answer_it_is():
    """A value read out with no label is a sentence with no subject — "None" tells a
    patient nothing about which of the ten items it belongs to."""
    body = fn_body("speakSummaryField")
    assert "const label = t(FIELD_LABELS[key].en, FIELD_LABELS[key].bn);" in body
    assert "speak(`${label}. ${text" in body


def test_summary_values_are_spoken_verbatim_so_the_bilingual_split_cannot_halve_them():
    """TTS-1's split is for M7's "<Bangla> (<English>)" questions. A summary VALUE is
    not one, and letting that regex near it could read back half an answer."""
    for name in ("speakSummaryField", "toggleSummaryReadAloud"):
        assert "verbatim: true" in fn_body(name)


def test_the_whole_review_can_be_heard_in_one_pass_and_stopped_again():
    """An elderly patient who started a long read-through must be able to end it without
    hunting for a different control, so the same button stops it."""
    body = fn_body("toggleSummaryReadAloud")
    assert "if (summaryReadAloudActive()) {" in body
    assert "ttsCancel();" in body
    assert "setReadAloudLabel(false);" in body
    assert "onend: next" in body            # one card after another, never overlapping
    html = kiosk_html()
    assert 'id="read-summary-btn"' in html and 'onclick="toggleSummaryReadAloud()"' in html
    assert 'data-bn="🔊 আমার উত্তরগুলো শুনুন"' in html


def test_a_single_card_wins_over_a_running_read_through():
    """speak() cancels the previous utterance, so without a queue token the killed
    utterance's `onend` would keep walking the list UNDERNEATH the card the patient
    just tapped — two voices, one of them invisible."""
    assert "readAloudQueue = null;   // one card wins" in kiosk_js()
    body = fn_body("toggleSummaryReadAloud")
    assert "if (readAloudQueue !== queue) return;" in body


def test_an_empty_review_says_so_rather_than_playing_silence():
    body = fn_body("toggleSummaryReadAloud")
    assert "Nothing has been recorded yet." in body
    assert "এখনো কিছু রেকর্ড করা হয়নি।" in body


def test_the_stop_label_follows_the_language_toggle():
    """P1-2: it is written by JS, so it must go through setBilingualText or it would
    freeze in whichever language it was last set in."""
    body = fn_body("setReadAloudLabel")
    assert "setBilingualText('read-summary-btn'," in body
    assert "⏹ Stop" in body and "⏹ থামান" in body


def test_the_review_read_back_never_opens_the_microphone():
    """Reviewing is not answering. askAloud() here would arm the mic while the kiosk
    reads the patient's own summary back at them."""
    for name in ("speakSummaryField", "toggleSummaryReadAloud"):
        assert "askAloud" not in fn_body(name)


def test_the_correction_route_is_named_on_the_screen():
    """"Provide an easy way to correct" — the patient must be TOLD that 🔊 plays a card
    and that Speak Again fixes it, in their own language."""
    html = kiosk_html()
    assert 'data-en="Tap 🔊 on any card to hear it. If anything is wrong, tap Speak Again."' in html
    assert "যেকোনো কার্ডের 🔊 চেপে শুনুন" in html


# --- the floating assistant ---


def test_the_review_screen_carries_the_same_derived_avatar_not_a_second_one():
    """ADR-0054 stands: state is DERIVED, never pushed. A third mount must join the ONE
    list so refreshAvatar() drives it — a mount outside AVATAR_IDS is a robot that
    silently freezes, which is worse than no robot."""
    js, html = kiosk_js(), kiosk_html()
    assert "'summary-avatar'" in js.split("const AVATAR_IDS = [")[1].split("];")[0]
    assert 'id="summary-avatar"' in html
    assert 'id="summary-float"' in html
    # no per-screen state machine crept in with it
    pushed = set(re.findall(r"setAvatarOverride\('(\w+)'", js))
    assert pushed <= {"done", "error"}


def test_the_status_lines_are_written_to_every_mount():
    """`doctor-substatus` used to be a hard-coded id. With three mounts that would have
    left the review screen's secondary line permanently reading "Your AI health
    assistant" while the avatar above it was listening."""
    js = kiosk_js()
    assert "const AVATAR_STATUS_IDS = ['doctor-status', 'summary-status'];" in js
    assert "const AVATAR_SUBSTATUS_IDS = ['doctor-substatus', 'summary-substatus'];" in js
    body = fn_body("applyAvatarState")
    assert "AVATAR_SUBSTATUS_IDS.forEach" in body
    assert "setBilingualText('doctor-substatus'" not in body


def test_exactly_one_assistant_is_on_screen_at_a_time():
    """The KIOSK-7 resume dock has its own avatar. Two robots on one screen leaves the
    patient guessing which one is talking to them."""
    body = fn_body("setResumeMode")
    assert "float.style.display = state.resumeActive ? 'none' : '';" in body


def test_the_assistant_floats_rather_than_sitting_still():
    """It should read as a companion, not as a logo. The bob is on the CARD, never on
    .doctor-avatar — the avatar's own transform belongs to the speaking state, and
    animating both would make the two fight."""
    css = top_level_css()
    assert "@keyframes doctor-hover" in css
    inner = css.split(".doctor-float-inner {")[1].split("}")[0]
    assert "animation: doctor-hover" in inner
    assert "position: sticky" in css.split(".doctor-float {")[1].split("}")[0]
    # the avatar's own rule must not gain a competing animation
    avatar = re.search(r"(?m)^\s*\.doctor-avatar \{([^}]*)\}", css)
    assert avatar and "animation:" not in avatar.group(1)


def test_the_float_and_the_clock_stop_moving_for_a_patient_who_asked_for_less_motion():
    """Both are decoration on top of information that survives without them — the status
    text, and a number that changes once a second."""
    css = kiosk_html()
    block = css.split("@media (prefers-reduced-motion: reduce) {")[1].split("\n    }")[0]
    assert ".doctor-float-inner, .kiosk-clock, .kiosk-clock-value { animation: none !important; }" in block


def test_the_assistant_uses_no_external_asset():
    """CPU-only hardware and an offline kiosk (ADR-0054) — the same rule as the other
    two mounts, re-asserted for the new one."""
    html = kiosk_html()
    block = html.split('id="summary-float"')[1].split('id="summary-grid"')[0]
    for forbidden in ("<img", "<canvas", "<video", "background-image", "url("):
        assert forbidden not in block, f"the floating assistant depends on {forbidden}"


# --- layout ---


def test_the_review_is_two_columns_that_can_actually_shrink():
    """`minmax(0, 1fr)`, not a bare `1fr`: an auto-min track refuses to go below its
    content's min-content width, so one wide card would push the whole review sideways
    instead of wrapping inside its column.

    S40 flipped WHICH track is which: the patient's answers now take the wide FIRST
    column and the review rail (assistant, still-missing notice, the three buttons)
    the fixed second one, so the thing the patient must DO sits beside their
    information instead of below all of it. The property this test exists for is
    unchanged - the flexible track is still minmax(0, 1fr) and can still shrink."""
    css = top_level_css()
    body = css.split(".summary-body {")[1].split("}")[0]
    assert "grid-template-columns: minmax(0, 1fr) 300px" in body
    narrow = kiosk_html().split("@media (max-width: 620px) {")[1]
    assert ".summary-body { grid-template-columns: minmax(0, 1fr); }" in narrow
    assert ".doctor-float { position: static; }" in narrow


def test_the_two_wide_cards_stop_spanning_when_there_is_only_one_column():
    """PRE-EXISTING defect, measured not assumed: renderSummary() sets `grid-column:
    span 2` INLINE on two cards. In the single-column narrow grid, spanning 2 creates an
    IMPLICIT second column and the review scrolled sideways inside its own box at 375px
    (497px of content in a 375px viewport). `!important` is what beats an inline style."""
    narrow = kiosk_html().split("@media (max-width: 620px) {")[1]
    assert ".summary-grid .summary-item { grid-column: span 1 !important; }" in narrow
    # the inline span itself is unchanged — it is correct at two columns
    assert "cell.style.gridColumn = 'span 2';" in kiosk_js()


def test_no_selector_is_sized_twice_at_the_same_specificity():
    """The S33 regression, extended to this session's new selectors: a second rule at
    equal specificity loses to the later one, i.e. dead CSS that reads as applied."""
    css = top_level_css()
    for selector in (".summary-body", ".doctor-float", ".doctor-float-inner",
                     ".kiosk-clock", ".kiosk-clock-value", ".answer-confirm",
                     ".answer-text", ".digit-preview", ".summary-head", ".confirm-say"):
        hits = re.findall(rf"(?m)^\s*{re.escape(selector)}\s*\{{", css)
        assert len(hits) == 1, f"{selector} declared {len(hits)}x outside @media"
