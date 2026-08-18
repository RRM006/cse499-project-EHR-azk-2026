"""S36 / Finding 7 (ADR-0057) — two gaps a patient actually feels, and nothing else.

The brief listed ten possible usability improvements and then said the important part:
inspect what exists first, and only build what is not already solved. Most of the list
already IS solved, and re-solving it would have been the worse outcome:

  * "clearer listening-now indication" — S35 Finding 3 (the mic pulse and the dock hint
    going large and red, driven by `body[data-kiosk-state]`);
  * "visible confirmation of accepted answer" — S34's read-back panel, verbatim;
  * "reduced accidental double submission" — the S34 submit guard, plus the three added
    THIS session (`otpSending`, the phone read-back, the once-only auto-download);
  * "voice-first error recovery" — reAskPhone/reAskOtp/reAskUnclearAnswer.

Two gaps were real:

  1. **The completion was silent.** Every question in this kiosk is spoken (ADR-0028),
     and then the single most important moment of the visit — "your information reached
     the doctor" — was text on a screen and nothing else. The patient who cannot read
     that screen is precisely the patient this project exists for, and they were left to
     guess whether it had worked.
  2. **The conversation screen answered "how much longer?" with nothing.** For an
     elderly, often anxious patient, an interview of unknown length is its own reason to
     give up partway.

⚠ The progress chip is shown ONLY during the scripted opening, and that restriction is
the honest half of the feature. INTAKE_SCRIPT has a known length, so "প্রশ্ন ২ / ৪" is a
fact. The M7 loop that follows ends on completeness and a turn cap, not on a count known
in advance — so rather than invent a denominator that would drift, the chip goes away.

⚠ **S5 IS NOT IMPLEMENTED BY THIS FILE OR THIS SESSION.** Verified by inspection at the
end of S36: `no_speech_ms` and `max_answer_ms` are still marked "(not used yet)" in
kiosk.js and are read by nothing, and there is no `visibilitychange` handler and no
permission-recovery path anywhere in the kiosk. The one S5 item that Finding 7 brushes
against — recovery when microphone permission is interrupted mid-answer — was left
deliberately: it cannot be built without deciding what happens to the half-captured
answer in `finalBuffer`, and discarding a patient's words is the open rule #1 decision
current_task.md reserves for the human. A test asserting S5 is absent is included below
so no later session can quietly assume it landed here.

⚠ Scope: static-source assertions plus the shipped kiosk driven in a browser engine:
    scripted opening   Question 1 of 4 … 4 of 4, and প্রশ্ন ৪ / ৪ under the BN toggle
    after the opening  hidden (no invented denominator)
    layout             avatar and status line move 0px when the chip appears
    completion         exactly ONE spoken line
    after reset        chip hidden and empty, scriptIndex back to -1
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


def code_only(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


# --- 1. the completion says so out loud ---


def test_the_submission_is_announced_in_both_languages():
    js = kiosk_js()
    block = js.split("const SUBMITTED_ALOUD = {")[1].split("};")[0]
    assert "en:" in block and "bn:" in block
    assert "doctor" in block, "it must say where the information went"
    assert "ডাক্তার" in block


def test_it_tells_the_patient_what_to_do_next_not_just_thank_you():
    """"Thank you" alone leaves a patient standing at a kiosk wondering whether they are
    allowed to walk away."""
    block = kiosk_js().split("const SUBMITTED_ALOUD = {")[1].split("};")[0]
    assert "wait" in block.lower()
    assert "অপেক্ষা" in block


def test_it_is_spoken_on_the_success_path_only():
    submit = kiosk_js().split("async function confirmSubmit() {")[1].split("\n}\n")[0]
    after_success = submit.split("setAvatarOverride('done');")[1]
    assert "speak(t(SUBMITTED_ALOUD.en, SUBMITTED_ALOUD.bn));" in after_success


def test_the_announcement_never_opens_the_microphone():
    """askAloud() arms the mic when it finishes speaking. On a submitted visit there is
    nothing left to answer, and an open mic on a finished screening is how the NEXT
    patient's voice would end up in this one (Finding 2)."""
    submit = code_only(kiosk_js().split("async function confirmSubmit() {")[1].split("\n}\n")[0])
    assert "askAloud(t(SUBMITTED_ALOUD" not in submit
    assert "speak(t(SUBMITTED_ALOUD" in submit


# --- 2. the progress chip, and the honesty of its denominator ---


def test_the_conversation_screen_has_a_progress_chip():
    html = kiosk_html()
    assert 'id="convo-progress"' in html
    stage = html.split('<div class="doctor-stage">')[1].split("</div>\n      <div class=\"chat-thread\"")[0]
    assert 'id="convo-progress"' in stage, "it belongs to the assistant row, not the thread"


def test_it_reuses_the_one_chip_style_rather_than_inventing_a_second():
    html = kiosk_html()
    chip = html.split('id="convo-progress"')[0].split("<span")[-1]
    assert 'class="progress-chip"' in chip


def test_the_denominator_is_the_script_length_not_a_guess():
    """"Question 2 of 4" is a fact because INTAKE_SCRIPT has four entries. If the count
    were ever hard-coded it would silently lie the day a question is added."""
    body = fn_body("renderConvoProgress")
    assert "INTAKE_SCRIPT.length" in body
    assert not re.search(r"of \d+", body), "a literal total would drift from the script"


def test_no_progress_is_claimed_once_the_m7_loop_starts():
    """The loop ends on completeness and a turn cap, not on a count known in advance. A
    progress bar that lies is worse than no progress bar."""
    body = fn_body("renderConvoProgress")
    assert "if (!inScriptedOpening() && state.scriptIndex < 0)" in body
    assert "hideConvoProgress();" in fn_body("submitPatientTurn")


def test_the_chip_is_cleared_rather_than_merely_hidden():
    """The same rule endSession() follows: a hidden element still holding text is one
    language toggle away from reappearing on the wrong screen."""
    body = fn_body("hideConvoProgress")
    assert "chip.style.display = 'none';" in body
    assert "chip.textContent = '';" in body
    assert "chip.dataset.en = '';" in body


def test_the_next_patient_does_not_inherit_a_question_count():
    assert "hideConvoProgress();" in fn_body("endSession")


def test_it_follows_the_language_toggle():
    """data-en/data-bn is what applyLanguage() re-renders on toggle — a chip written once
    in English would stay English on a Bangla kiosk."""
    body = fn_body("renderConvoProgress")
    assert "chip.dataset.en =" in body and "chip.dataset.bn =" in body
    assert "bnDigits(step)" in body, "Bangla numerals under the BN toggle"


def test_the_chip_cannot_squeeze_the_avatar_or_its_status():
    """Measured: the avatar and the status line move 0px when the chip appears."""
    css = kiosk_html().split("<style>")[1].split("</style>")[0]
    rule = css.split(".doctor-stage .progress-chip {")[1].split("}")[0]
    assert "margin-left: auto" in rule
    assert "flex: none" in rule


# --- S5: still not implemented, and this test exists to keep that true ---


def test_step_s5_is_still_not_implemented():
    """⚠ Deliberate. S5 is the `no_speech_ms` watchdog, the `max_answer_ms` cap and
    permission/visibility recovery. S36 implemented NONE of them, and this asserts the
    honest state so a later session cannot assume otherwise from the changelog.

    The one item Finding 7 brushes against — recovery when microphone permission is
    interrupted mid-answer — was left ON PURPOSE: it cannot be built without deciding
    what happens to the half-captured answer in `finalBuffer`, and discarding a patient's
    words is the open rule #1 decision current_task.md reserves for the human."""
    js = kiosk_js()
    assert "no_speech_ms: 10000,     // S5 (not used yet)" in js
    assert "max_answer_ms: 120000,   // S5 (not used yet)" in js
    code = code_only(js)
    for absent in ("navigator.permissions", "no_speech_ms;", "max_answer_ms;"):
        assert absent not in code, (
            f"{absent} appeared — if S5 was implemented, update its status in "
            "milestone_log.md and current_task.md rather than letting this test pass silently")
    # the two knobs are still served (S1's seam), just still unused by the kiosk
    assert "no_speech_ms" in client.get("/api/config").json()
    assert "max_answer_ms" in client.get("/api/config").json()
    # ⚠ The two S5 timings must be READ by nothing. Served, yes; used, no.
    for knob in ("no_speech_ms", "max_answer_ms"):
        assert code.count(knob) == 1, (
            f"{knob} is referenced more than once — the config default and a USE. "
            "That is S5 being built; update milestone_log.md and current_task.md.")


def test_the_s42_visibility_handler_is_a_stuck_mic_guard_and_not_step_s5():
    """⚠ S42 added a `visibilitychange` handler. S5 also needs one, so the boundary
    between them is pinned here rather than left to a future reader's judgement.

    What S42's handler is allowed to be: when the tab is hidden while the microphone is
    open, stop the recogniser so the restart loop in `r.onend` cannot spin against a
    recogniser that cannot hear, leaving the red "speak now" banner up on a kiosk that
    is not listening. It calls the EXISTING `stopListening(false)` — the identical call
    `setInputMode('type')` and `finishConversation()` already make — so it introduces no
    new rule about the patient's captured words.

    What it must NOT become without a decision from the human: a `finalBuffer`
    disposition of its own, a timing watchdog, or a permission-recovery path. Those are
    S5, and the `finalBuffer` half is BLOCKED on the open rule #1 decision."""
    body = fn_body("handleVisibilityChange")

    # It does the one safe thing, through the path that already exists.
    assert "stopListening(false);" in body
    assert "cancelPendingMic();" in body
    assert "if (!listening) return;" in body, "it must do nothing when no mic is open"

    # It takes NO position on the patient's half-captured words.
    for forbidden in ("finalBuffer", "submitPatientTurn", "submitResumeAnswer",
                      "submitFinalTurn", "acceptAnswer", "/utterances"):
        assert forbidden not in body, (
            f"handleVisibilityChange references {forbidden} — that decides the fate of a "
            "half-captured answer, which is the open rule #1 decision reserved for the "
            "human (current_task.md). It is not this handler's to take.")

    # …and it is not a watchdog: no timer, no S5 timing.
    for forbidden in ("setTimeout", "setInterval", "no_speech_ms", "max_answer_ms"):
        assert forbidden not in body, f"{forbidden} in the visibility handler is S5, not S42"


def test_the_visibility_handler_tells_the_patient_what_happened_in_both_languages():
    """A microphone that stops on its own is only safe if the patient is told. The
    kiosk is bilingual, so the notice is too — an English-only sentence on a Bangla
    screen is the half-translated failure the project's bilingual rule exists to stop."""
    js = kiosk_js()
    block = js.split("const INTERRUPTED_BY_HIDE = {")[1].split("};")[0]
    assert "en:" in block and "bn:" in block
    # Bangla script, not transliteration.
    assert any("ঀ" <= ch <= "৿" for ch in block), "the bn string is not Bangla"
    assert "t(INTERRUPTED_BY_HIDE.en, INTERRUPTED_BY_HIDE.bn)" in fn_body("handleVisibilityChange")
