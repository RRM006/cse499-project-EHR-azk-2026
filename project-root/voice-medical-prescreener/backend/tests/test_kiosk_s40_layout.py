"""S40 — the kiosk redesign: two columns, one loud thing at a time, and no second
voice implementation.

The reported problem was not "it is ugly". It was that the screen is *not understandable*
for the people this kiosk exists for — a child, an elderly patient, someone with little
schooling, someone who has never used a computer. The old conversation screen was one
tall column: the robot, then the whole conversation, then a dock holding the live
transcript, the read-back, the countdown, three buttons, a hint, a mode switch and a text
box. "Where the assistant is" and "where I speak" were the same place, stacked, and the
patient's own words sat in the middle of the pile.

What these tests pin is the part that would regress silently:

  * **The two columns, and which side is whose.** Collapsing back to one column would
    not look broken — it would just quietly restore the congestion.
  * **One emphasised thing at a time.** The confirmation step is the moment the patient
    is asked to check a machine's guess about their own words. Everything else standing
    down is the whole point, and an added `opacity: 1` somewhere would undo it invisibly.
  * **Dimmed is NOT disabled.** A patient reaching for the mouse must still be able to
    use it. `pointer-events: none` here would trap someone mid-turn, and nothing on
    screen would show it.
  * **No second turn-taking path.** Every layout cue is read from the attributes the
    kiosk already publishes from its ONE derived state. A cue with its own state machine
    could tell a patient the mic is open when it is not — the exact failure ADR-0054 was
    written to prevent.
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


def top_level_css() -> str:
    """The page CSS with every @media block removed — what applies at any size."""
    css = kiosk_html().split("<style>")[1].split("</style>")[0]
    return re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)


def fn_body(name: str) -> str:
    js = kiosk_js()
    return js.split(f"function {name}(")[1].split("\n}\n")[0]


# --- 1. two columns: the assistant on one side, the patient on the other -------------


def test_the_conversation_is_two_columns():
    css = top_level_css()
    layout = css.split(".convo-layout {")[1].split("}")[0]
    assert "display: grid" in layout
    assert "grid-template-columns: minmax(0, 1fr) minmax(330px, 400px)" in layout


def test_the_assistant_is_on_one_side_and_the_patient_on_the_other():
    """The split is by WHOSE side of the conversation it is. If the dock ever shares a
    column with the thread the screen is one stack again, which is the reported defect."""
    css = top_level_css()
    assert ".convo-layout > .doctor-stage { grid-column: 1; grid-row: 1; }" in css
    assert ".convo-layout > .chat-thread  { grid-column: 1; grid-row: 2; }" in css
    assert ".convo-layout > .voice-dock   { grid-column: 2; grid-row: 1 / -1; }" in css


def test_the_two_columns_are_built_without_touching_the_dom():
    """Grid PLACEMENT, not wrapper divs. The DOM order is what a screen reader and the
    keyboard follow, and the doctor-stage/chat-thread adjacency is read by other tests —
    a wrapper would have changed both for a purely visual result."""
    html = kiosk_html()
    stage = html.split('<div class="doctor-stage">')[1]
    assert stage.split("</div>\n      <div class=")[1].startswith('"chat-thread"'), (
        "a wrapper element was introduced between the assistant row and the thread"
    )


def test_it_returns_to_one_column_when_there_is_no_room_for_two():
    """Below this width two columns stop helping: the conversation gets too narrow to
    read and the patient's panel too narrow to hold the read-back."""
    html = kiosk_html()
    assert "@media (max-width: 1000px) {" in html
    block = html.split("@media (max-width: 1000px) {")[1].split("\n    }")[0]
    assert "grid-template-columns: minmax(0, 1fr);" in block
    assert ".convo-layout > .voice-dock { grid-column: 1; grid-row: 3; }" in block


# --- 2. the patient's own words are the loudest thing on the screen ------------------


def test_the_conversation_transcript_is_larger_than_the_identity_docks():
    """It is the one thing on screen that is REAL — what the machine believes the patient
    just said, on its way into a medical record."""
    css = top_level_css()
    rule = css.split(".voice-dock .dock-transcript {")[1].split("}")[0]
    assert "font-size: 1.3rem" in rule
    assert "font-style: normal" in rule, "italic grey reads as 'placeholder, not real yet'"
    assert "min-height: 118px" in rule


def test_the_bigger_transcript_is_a_more_specific_rule_not_a_duplicate():
    """A second EQUAL-specificity `.dock-transcript` rule would silently lose to whichever
    came last — the dead-CSS bug the S33 regression test exists to catch. The phone/OTP
    docks keep the compact original, so this MUST be the more specific selector."""
    css = top_level_css()
    assert len(re.findall(r"(?m)^\s*\.dock-transcript\s*\{", css)) == 1


def test_the_box_is_labelled_because_it_is_emptied_between_turns():
    """`setBilingualText(dock.transcript, '', '')` clears the box, so its own placeholder
    is gone after the first answer. A caption above it is what keeps it explained."""
    html = kiosk_html()
    assert 'class="dock-caption"' in html
    assert 'class="dock-title"' in html


def test_listening_is_visible_on_the_box_the_patient_is_filling():
    css = top_level_css()
    assert 'body[data-kiosk-state="listening"] .voice-dock .dock-transcript {' in css


# --- 3. one emphasised thing at a time ----------------------------------------------


def test_the_confirming_stage_is_set_and_cleared_by_the_gate_itself():
    """Not a second state machine: it is set in the ONE function that opens the read-back
    gate and cleared in the ONE that closes it, so it cannot drift from reality."""
    assert "document.body.dataset.kioskStage = 'confirming';" in fn_body("showAnswerConfirm")
    assert "delete document.body.dataset.kioskStage;" in fn_body("hideAnswerConfirm")


def test_everything_else_steps_back_while_an_answer_waits_to_be_checked():
    """The reported confusion: the read-back, "just say yes or no", two buttons, "tap the
    mic when you are ready" and the mic were all presented as if all were live."""
    css = top_level_css()
    assert 'body[data-kiosk-stage="confirming"] .voice-dock .dock-row,' in css
    assert 'body[data-kiosk-stage="confirming"] #listening-hint,' in css


def test_stepping_back_never_means_being_switched_off():
    """Dimmed, never disabled. A patient who reaches for the mouse must still be able to
    use it, and hiding controls mid-turn is how a kiosk traps someone."""
    css = top_level_css()
    # Every rule whose SELECTOR mentions the confirming stage, with its own
    # declarations — bounded by the rule itself rather than by a character count, so
    # CSS added later can neither be swept in nor push the check off the end.
    rules = [
        m.group(0)
        for m in re.finditer(r"[^{}]*\{[^{}]*\}", css)
        if 'data-kiosk-stage="confirming"' in m.group(0).split("{")[0]
    ]
    assert rules, "the confirming stage drives no CSS at all"
    for rule in rules:
        declarations = rule.split("{")[1]
        assert "pointer-events: none" not in declarations, (
            f"a dimmed control must still be clickable:\n{rule.strip()}"
        )
        assert "display: none" not in declarations, (
            f"a control must not vanish mid-turn:\n{rule.strip()}"
        )


def test_the_three_steps_are_lit_only_by_state_the_kiosk_already_publishes():
    """The strip must never be able to say the mic is open when it is not — so it reads
    `data-kiosk-state` (the ONE derived avatar state, S35) and `data-kiosk-stage` (the
    read-back gate), and nothing of its own."""
    html = kiosk_html()
    for step in ("step-ask", "step-speak", "step-check"):
        assert f'id="{step}"' in html
    js = kiosk_js()
    assert "step-ask" not in js and "step-speak" not in js and "step-check" not in js, (
        "the step strip grew a JS driver — it must stay CSS-only over existing state"
    )


# --- 4. the review: answers in column 1, what to DO about them in column 2 -----------


def test_the_review_actions_live_in_the_rail_beside_the_answers():
    """They used to be a full-width bar at the very BOTTOM, so the patient scrolled past
    every answer card to reach the one action the screen exists for."""
    html = kiosk_html()
    rail = html.split('<div class="review-rail">')[1].split('<div class="summary-grid"')[0]
    assert 'id="confirm-submit-btn"' in rail
    assert 'id="required-notice"' in rail
    assert 'id="summary-float"' in rail


def test_the_answers_come_first_and_the_rail_second():
    """Placed by `order`, NOT `grid-column`: an explicit column would create an implicit
    second track the moment a single-column rule applies — the exact class of bug S36
    fixed on this grid."""
    css = top_level_css()
    assert ".review-rail { order: 2;" in css
    assert ".summary-grid { order: 1;" in css
    body = css.split(".summary-body {")[1].split("}")[0]
    assert "grid-column" not in body


def test_the_primary_action_is_the_obvious_one():
    css = top_level_css()
    assert ".summary-actions #confirm-submit-btn {" in css
    assert ".summary-actions .btn { width: 100%; }" in css


def test_the_rail_stays_on_screen_while_the_answers_scroll():
    css = top_level_css()
    assert "position: sticky" in css.split(".review-rail {")[1].split("}")[0]


# --- 5. automatic movement, without a page that jumps -------------------------------


def test_the_page_moves_only_when_something_is_actually_out_of_view():
    """`block: 'nearest'` is the whole restraint: an element already on screen does not
    move at all. Anything else ('start'/'center') would yank the page on every turn."""
    body = fn_body("bringIntoView")
    assert "block = 'nearest'" in body
    assert "'start'" not in body and "'center'" not in body


def test_automatic_movement_respects_a_patient_who_asked_for_less_motion():
    body = fn_body("bringIntoView")
    assert "prefers-reduced-motion: reduce" in body
    assert "reduced ? 'auto' : 'smooth'" in body


def test_the_microphone_opening_brings_its_own_dock_into_view():
    """ONE call site for both paths — a tap and the S3 auto-open both arrive in
    toggleListening(), which is the 'one code path, not two' that function relies on."""
    assert "bringIntoView(activeDock().mic);" in fn_body("toggleListening")


def test_nothing_scrolls_on_every_recognition_result():
    """Scrolling on each interim chunk is how a page becomes unusable while someone is
    talking — and the dock is already in view from the moment the mic opened."""
    js = kiosk_js()
    onresult = js.split("r.onresult = (event) => {")[1].split("\n  };")[0]
    assert "bringIntoView" not in onresult
    assert "scrollIntoView" not in onresult


def test_a_newly_shown_screen_starts_at_its_own_top():
    """`.screen` is the scroll container (S34) and keeps its scroll position across an
    activate/deactivate cycle, so returning to the review used to drop the patient
    wherever they had last scrolled to."""
    assert "shown.scrollTop = 0;" in fn_body("showScreen")


# --- 6. nothing about the voice pipeline changed -------------------------------------


def test_the_redesign_added_no_second_recogniser_and_no_second_speak():
    """The instruction was explicit: reuse the existing speak()/voice seams. One
    SpeechRecognition construction, and TTS still goes through the shared tts.js."""
    js = kiosk_js()
    assert js.count("new SR()") == 1
    assert "new SpeechRecognition(" not in js
    assert "new webkitSpeechRecognition(" not in js
    assert "speechSynthesis.speak(" not in js, "TTS must stay behind the shared speak()"


def test_the_patients_live_words_still_survive_a_language_toggle():
    """Rule #1 in the display layer: the live transcript is mirrored into BOTH language
    slots, so tapping বাংলা mid-answer cannot replace the patient's words with a
    placeholder. Pre-existing (P1-2) and re-asserted because S40 made this box the
    focal point of the screen."""
    js = kiosk_js()
    onresult = js.split("r.onresult = (event) => {")[1].split("\n  };")[0]
    assert "el.dataset.en = live;" in onresult
    assert "el.dataset.bn = live;" in onresult
