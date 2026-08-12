"""S34 (ADR-0055) — "this is what I heard": the spoken-answer read-back, and the rule
that an unusable capture is asked again rather than guessed at.

The gap this closes is not cosmetic. Between S4 and S34 a spoken answer went from the
recogniser straight into the patient's permanent record, and the only way to discover a
mis-recognition was to READ it off a chat bubble — which the target patient (elderly,
possibly not literate, quite possibly without their glasses) cannot be assumed to do.
Three properties are what make the read-back trustworthy, and they are what this file
defends:

  1. **Nothing is stored until the patient accepts.** A rejected capture never became an
     utterance, so rejecting it edits nothing (rule #1 is about what is RECORDED).
  2. **The words shown and spoken back are the patient's own, verbatim** — never a
     tidied paraphrase, never half of them.
  3. **An unusable capture is never guessed at.** Silence is not an answer: the SAME
     question is asked again.

⚠ Scope, stated honestly (the S28 convention, unchanged): these are **static-source
assertions** over the served kiosk.js / kiosk.html. They prove the gate exists, that it
sits at exactly one place, and that the pipeline below it is unchanged. They cannot
prove browser behaviour. The gate WAS additionally executed in a real browser engine by
feeding the recogniser's own buffer — panel shown / nothing stored / accept stores and
advances / reject re-asks and stores nothing / silence and punctuation-only both re-ask
— and the panel was measured to be fully inside a 694px viewport; see the session notes.
No microphone was involved anywhere.
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
    """One function's body straight out of the served file."""
    js = kiosk_js()
    marker = f"function {name}("
    assert marker in js, f"{name}() is gone from the shipped kiosk"
    return js.split(marker)[1].split("\n}")[0]


def code_only(source: str) -> str:
    """Drop both comment styles. Needed wherever a test asserts that an API is ABSENT:
    this codebase's comments deliberately name the very things the code must NOT call
    ("scrollIntoView would move the whole document"), so an un-stripped comment reads as
    a violation of the rule it is explaining."""
    without_blocks = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return "\n".join(line.split("//")[0] for line in without_blocks.splitlines())


# --- the gate sits at ONE place, and the pipeline under it is unchanged ---


def test_the_gate_is_on_the_spoken_path_only_and_typed_answers_are_never_held():
    """A patient who typed is already looking at their own text; making them confirm it
    would be an extra tap that buys nothing (ADR-0048's "minimize clicks"). The gate is
    therefore in stopListening()'s spoken branch, not inside the submit functions —
    which is also why sendTypedFallback()/sendResumeTyped() need no exception."""
    stop = fn_body("stopListening")
    assert "else if (holdForConfirmation(text))" in stop
    for typed in ("sendTypedFallback", "sendResumeTyped"):
        assert "holdForConfirmation" not in fn_body(typed), f"{typed} must not be gated"


def test_the_gate_precedes_the_clinical_submits_but_not_identification():
    """Order is the contract. Identification (phone/OTP digits) must stay AHEAD of the
    gate — those turns are not clinical answers and have their own read-back — and the
    two clinical submits must stay BEHIND it."""
    stop = fn_body("stopListening")
    assert stop.index("applySpokenPhone") < stop.index("holdForConfirmation")
    assert stop.index("applySpokenOtp") < stop.index("holdForConfirmation")
    assert stop.index("holdForConfirmation") < stop.index("submitResumeAnswer")
    assert stop.index("holdForConfirmation") < stop.index("submitPatientTurn")


def test_accepting_re_enters_the_same_single_pipeline():
    """ADR-0048: one question/answer path, differing only in `source`. The accept handler
    must call the SAME functions with the SAME arguments the un-gated path used — a
    second submit path is exactly what this project's regression rule forbids."""
    accept = fn_body("acceptAnswer")
    assert "submitResumeAnswer(text, 'mic');" in accept
    assert "submitPatientTurn(text, 'mic');" in accept
    # …and it must not invent its own HTTP call.
    for endpoint in ("api('POST'", "/utterances", "/followup/"):
        assert endpoint not in accept, "acceptAnswer must not talk to the server itself"


def test_nothing_reaches_the_server_or_the_transcript_before_acceptance():
    """The whole point: a captured answer is INERT until the patient approves it."""
    hold = fn_body("holdForConfirmation")
    offer = fn_body("offerSpokenAnswer")
    for body in (hold, offer):
        assert "api(" not in body
        assert "addBubble" not in body
        assert "submitPatientTurn" not in body and "submitResumeAnswer" not in body


def test_rejecting_stores_nothing_and_re_asks_the_same_question():
    """"No, say it again" must not advance the interview. The previous question is still
    unanswered, and moving on would answer it with something the patient never said."""
    reject = fn_body("rejectAnswer")
    assert "hideAnswerConfirm();" in reject
    assert "currentQuestionText()" in reject
    assert "askAloud(question)" in reject      # re-ask AND (auto mode) reopen the mic
    assert "submitPatientTurn" not in reject and "submitResumeAnswer" not in reject
    assert "api(" not in reject


# --- what is shown and spoken is the patient's own words ---


def test_the_read_back_text_is_never_translated_or_rewritten():
    """It is a quotation of the patient (rule #1). data-en/data-bn would hand it to
    applyLanguage(), which would then overwrite their words on a language toggle."""
    show = fn_body("showAnswerConfirm")
    assert "box.textContent = text;" in show
    assert "dataset.en" not in show and "dataset.bn" not in show
    html = kiosk_html()
    for element_id in ("dock-answer-text", "resume-answer-text"):
        block = html.split(f'id="{element_id}"')[1].split(">")[0]
        assert "data-en" not in block, f"#{element_id} must not carry a translation"


def test_the_read_back_is_spoken_verbatim_and_in_the_capture_language():
    """`verbatim: true` opts out of the TTS-1 bilingual split — reading back HALF of an
    answer is a rule #1 defect. bn-BD because that is the language STT captured it in."""
    speak_back = fn_body("speakAnswerBack")
    assert "verbatim: true" in speak_back
    assert "lang: 'bn-BD'" in speak_back


def test_the_read_back_never_opens_the_microphone():
    """It is not a question. An auto-opening mic here would transcribe the kiosk reading
    the patient's own words back at them — straight into the next verbatim record."""
    speak_back = fn_body("speakAnswerBack")
    assert "cancelPendingMic();" in speak_back
    assert "askAloud" not in speak_back, "askAloud() would arm the mic behind the read-back"


def test_the_confirmation_question_cannot_talk_over_the_read_back():
    """speak() cancels whatever is playing, so the follow-up prompt is chained on
    `onend` — and guarded, so a patient who has already decided is not spoken at."""
    speak_back = fn_body("speakAnswerBack")
    assert "onend: () => { if (state && state.pendingAnswer) speak(prompt); }" in speak_back


# --- silence is not an answer ---


def test_an_unclear_capture_is_decided_locally_with_no_model_and_no_threshold():
    """"Unclear" must be something the kiosk can be RIGHT about offline: at least one
    letter or digit. Anything richer would be the kiosk judging the patient's answer,
    which is the doctor's job, not a heuristic's (rule #2)."""
    assert "function isUnclearAnswer(text) {" in kiosk_js()
    body = fn_body("isUnclearAnswer")
    assert "/[\\p{L}\\p{N}]/u.test" in body


def test_an_empty_turn_re_asks_instead_of_storing_or_inventing():
    """Before S34 an empty spoken turn simply fell through `if (sendTurn && text)` and
    did nothing at all: the mic closed, no question was repeated, and the patient was
    left waiting for a kiosk that had silently given up."""
    stop = fn_body("stopListening")
    assert "} else if (sendTurn && !state.identifyStep) {" in stop
    assert "reAskUnclearAnswer();" in stop
    hold = fn_body("holdForConfirmation")
    assert "if (isUnclearAnswer(text)) { reAskUnclearAnswer(); return true; }" in hold


def test_the_re_ask_puts_the_SAME_question_again():
    """Not the next one. currentQuestionText() resolves whichever dock owns the turn —
    an M7 row, a re-asked scripted requirement, or the conversation's last question."""
    body = fn_body("currentQuestionText")
    assert "state.resumeQuestion" in body and "state.resumeScripted" in body
    assert "state.lastQuestionText" in body
    re_ask = fn_body("reAskUnclearAnswer")
    assert "askAloud(question)" in re_ask


def test_a_typing_patient_is_not_spoken_at_when_a_capture_fails():
    """Same rule F5b's reAskPhone/reAskOtp follow: someone who chose the keyboard has
    already been told what to fix by the banner; speaking at them and reopening the mic
    would be undoing their choice."""
    re_ask = fn_body("reAskUnclearAnswer")
    assert "state.inputMode !== 'voice'" in re_ask
    assert re_ask.index("return;") < re_ask.index("askAloud(")


# --- the panel cannot outlive the turn it belongs to ---


def test_the_panel_is_retracted_by_every_action_that_ends_its_turn():
    """A stale "I heard you say" is worse than none: it invites the patient to accept an
    answer to a question that has moved on — or, after the logout reset, to accept the
    PREVIOUS patient's words."""
    js = kiosk_js()
    assert "hideAnswerConfirm();   // S34: speaking again IS" in js   # a new mic turn
    assert "if (typing) hideAnswerConfirm();" in js                   # switching to typing
    assert "hideAnswerConfirm();" in fn_body("finishConversation")    # "Done"
    assert js.count("hideAnswerConfirm()") >= 5                       # incl. the logout reset


def test_the_reset_clears_the_panels_by_id_because_docks_is_still_in_its_dead_zone():
    """resetState() runs at module load, BEFORE `const DOCKS`. Reaching DOCKS from there
    is a ReferenceError that kills the whole kiosk — exactly how S33 lost it once."""
    body = fn_body("resetState")
    assert "document.getElementById('dock-answer-confirm').style.display = 'none';" in body
    assert "document.getElementById('resume-answer-confirm').style.display = 'none';" in body
    code = code_only(body)
    assert "hideAnswerConfirm" not in code and "DOCKS" not in code


def test_the_panel_is_brought_above_the_fold_after_layout_is_current():
    """Measured, not assumed: with the panel open the dock is taller than a 694px
    viewport and both buttons landed below the fold. The forced reflow is load-bearing —
    in the same tick as display='flex' the layout is stale and scrollIntoView is a
    silent no-op (the same defect and the same fix as F5b's phone read-back)."""
    show = fn_body("showAnswerConfirm")
    assert "void panel.offsetHeight;" in show
    assert show.index("void panel.offsetHeight;") < show.index("panel.scrollIntoView({")


# --- both docks, both languages, and a way out ---


def test_both_clinical_docks_have_a_read_back_panel_and_the_identity_docks_do_not():
    """The phone and OTP screens have their OWN read-back (F5b) with different rules —
    a phone number must be confirmed, an OTP must not. They must not get a second one."""
    js = kiosk_js()
    body = js.split("const DOCKS = {")[1].split("\n};")[0]
    for name in ("conversation", "resume"):
        block = body.split(f"  {name}: {{")[1].split("},")[0]
        assert "confirmPanel:" in block and "confirmText:" in block
    for name in ("phone", "otp"):
        block = body.split(f"  {name}: {{")[1].split("},")[0]
        assert "confirmPanel:" not in block
    html = kiosk_html()
    for element_id in ("dock-answer-confirm", "dock-answer-text",
                       "resume-answer-confirm", "resume-answer-text"):
        assert f'id="{element_id}"' in html


def test_the_two_choices_are_bilingual_and_unmistakable():
    """P1-2 plus the elderly-UI rule: a tick, a cross, and words — not "OK"/"Cancel"."""
    html = kiosk_html()
    assert 'data-en="✔ Yes — that is right"' in html and 'data-bn="✔ হ্যাঁ — এটাই ঠিক"' in html
    assert 'data-en="✖ No — say it again"' in html and 'data-bn="✖ না — আবার বলি"' in html
    assert 'data-en="I heard you say:"' in html and 'data-bn="আমি শুনেছি আপনি বলেছেন:"' in html
    assert html.count('onclick="acceptAnswer()"') == 2      # one per clinical dock
    assert html.count('onclick="rejectAnswer()"') == 2


def test_a_clinic_can_turn_the_gate_off_without_touching_javascript():
    """ADR-0045's pattern: the previous behaviour stays selectable, never deleted. With
    answer_confirm=false the kiosk must fall through to the S25-era capture->submit."""
    js = kiosk_js()
    assert "answer_confirm: true," in js                    # the safe default
    hold = fn_body("holdForConfirmation")
    assert "if (!voiceConfig.answer_confirm) return false;" in hold
    # …and the unclear guard is checked BEFORE the opt-out, so "never invent an answer"
    # is not something a clinic can switch off.
    assert hold.index("isUnclearAnswer") < hold.index("voiceConfig.answer_confirm")


def test_the_countdown_caption_stops_promising_a_submit_that_no_longer_happens():
    """With the gate on, the S4 countdown ends in a read-back, not in "sending". The
    markup keeps the honest caption for the answer_confirm=false deployment and the
    kiosk rewrites it once /api/config has told it which one it is."""
    js = kiosk_js()
    caption = fn_body("applyCountdownCaption")
    assert "if (!voiceConfig.answer_confirm) return;" in caption
    assert "Finishing your answer" in caption
    assert "applyCountdownCaption();" in js
    html = kiosk_html()
    assert 'data-en="Sending your answer' in html, "the un-gated wording must stay shipped"


# --- P5: the conversation follows itself down the screen ---


def test_new_turns_scroll_the_thread_and_never_the_page():
    """scrollIntoView() on a bubble moves the whole DOCUMENT, which yanks the mic and the
    typing box out from under a patient mid-interaction. The thread is its own scroll
    container precisely so it can move without the page moving."""
    add_bubble = kiosk_js().split("function addBubble(")[1].split("function scrollThreadToEnd")[0]
    assert "scrollThreadToEnd(thread);" in add_bubble
    # comments stripped: the block below deliberately NAMES the API it must not use
    assert "scrollIntoView" not in code_only(add_bubble)
    scroll = fn_body("scrollThreadToEnd")
    assert "thread.scrollTo({ top: thread.scrollHeight, behavior: 'smooth' });" in scroll
    assert "thread.scrollTop = thread.scrollHeight;" in scroll   # the always-correct fallback


def test_the_smooth_scroll_is_dropped_for_a_patient_who_asked_for_less_motion():
    scroll = fn_body("scrollThreadToEnd")
    assert "'(prefers-reduced-motion: reduce)'" in scroll
    assert "if (!reduced && thread.scrollTo)" in scroll


def test_the_page_itself_cannot_grow_so_the_dock_stays_reachable():
    """REGRESSION, measured rather than assumed: shared.css gives body `min-height: 100vh`
    but no height, so a handful of chat bubbles grew the document to 1538px in a 694px
    viewport, `.chat-thread` was handed unbounded space by `flex: 1` and never scrolled,
    and the entire voice dock — mic, Done, read-back — sat below the fold. Auto-scrolling
    a thread that is not the scroll container cannot help.

    `min-height: 0` is the other half: a flex item defaults to `min-height: auto` and
    refuses to shrink below its content, which is why the bounding never took effect."""
    css = kiosk_html().split("<style>")[1].split("</style>")[0]
    assert "html, body { height: 100%; }" in css
    screen_rule = css.split(".screen {")[1].split("}")[0]
    assert "min-height: 0" in screen_rule
    assert "overflow-y: auto" in screen_rule
