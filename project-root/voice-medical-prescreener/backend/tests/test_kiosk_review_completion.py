"""S36 / Finding 5 (ADR-0057) — "ঠিক আছে" finishes the review.

Once rejectReview() has opened "কোন তথ্যটি ঠিক করতে চান? নিজের ভাষায় বলুন।", the patient
has one more thing they may reasonably want to say, and it is not a correction: that
there is nothing to correct after all. They looked, or listened, and it is fine.

Before this, that sentence had nowhere to go. "ঠিক আছে" fell through to the ordinary
clinical path, was read back as though it were a symptom, and on ✔ was STORED as the
patient's answer to `review_correction` — then the same question was asked again. On a
voice-first kiosk, a patient who cannot leave a loop by speaking cannot leave it at all.

Two halves, and the vocabulary half was the bigger surprise. Measured against the
SHIPPED parser before this session:

    ঠিক আছে      yes      সব ঠিক আছে   null   ← the most natural way to say it
    okay / ok    yes      সবকিছু ঠিক আছে null
    yes / হ্যাঁ   yes      সব ঠিক        null
                          all right     null
                          alright       null
                          that's all    null

`all` and `সব` are YES words rather than filler, and that distinction is load-bearing:
a filler-only utterance has no YES token, so parseConfirmation() would still return null
for "that's all". The orphan `s` left by the apostrophe in "that's" is filler — a
fragment, not a word.

⚠ Everything reuses `parseConfirmation()`. There is no second confirmation system, so a
phrase added for the read-back works here and vice versa, and the safety rule is
inherited rather than re-implemented: an utterance is a verdict only when EVERY word in
it is known.

⚠ Scope: static-source assertions plus the shipped functions driven end to end in a real
browser engine on the open correction question:

    ঠিক আছে · সব ঠিক আছে · all right · alright · okay · that's all
        -> 1 submit each, dock closed, logout modal shown, NO read-back
    "আমার বয়স ভুল আছে, আমি ষাট বছর"  -> 0 submits, read-back shown verbatim, dock open
    "আমার নাম রহিম না মানে রহিমা"      -> 0 submits, ambiguous, review NOT finished
    three completion phrases in a row -> exactly 1 submit

⚠ NO MICROPHONE: the phrases are fed to the shipped routing directly.
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


def shipped_set(name: str) -> set[str]:
    """Parse the vocabulary OUT of the served kiosk.js — a copy restated here would
    drift, and it is the SHIPPED set that has to be right."""
    js = kiosk_js()
    block = js.split(f"const {name} = new Set([")[1].split("]);")[0]
    words = set(re.findall(r"'([^']+)'", block))
    assert words, f"{name} parsed empty — has the literal's shape changed?"
    return words


# --- the vocabulary ---


def test_the_natural_ways_to_say_everything_is_fine_are_all_known():
    yes = shipped_set("CONFIRM_YES")
    for word in ("ঠিক", "সব", "সবকিছু", "all", "alright", "okay", "ok", "right", "হ্যাঁ"):
        assert word in yes, f"{word!r} is missing — a patient saying it is not understood"


def test_all_and_sob_are_yes_words_not_filler():
    """Load-bearing. parseConfirmation() returns null unless SOME token said yes, so if
    `all` were filler then "that's all" — filler + filler — would still be ambiguous."""
    yes, filler = shipped_set("CONFIRM_YES"), shipped_set("CONFIRM_FILLER")
    for word in ("all", "সব"):
        assert word in yes and word not in filler


def test_the_apostrophe_fragment_is_filler():
    """speechTokens() splits on every non-letter, so "that's all" tokenises to
    ['that', 's', 'all'] and the orphan `s` made the whole utterance ambiguous."""
    assert "s" in shipped_set("CONFIRM_FILLER")


def test_the_new_words_cannot_turn_ordinary_speech_into_approval():
    """The safety rule is inherited, not re-implemented: an unknown word anywhere makes
    the utterance ambiguous. So "all my body hurts" and "সব সময় ব্যথা" are still asked
    again rather than read as "everything is fine" — verified in a browser."""
    body = fn_body("parseConfirmation")
    assert "return null;   // an ordinary word" in body
    yes, no, filler = (shipped_set("CONFIRM_YES"), shipped_set("CONFIRM_NO"),
                       shipped_set("CONFIRM_FILLER"))
    for ordinary in ("my", "body", "hurts", "সময়", "ব্যথা", "বয়স", "ওষুধ"):
        assert ordinary not in (yes | no | filler), \
            f"{ordinary!r} became a confirmation word — ordinary speech can now approve a record"


# --- the routing ---


def test_a_completion_phrase_is_checked_before_the_read_back_gate():
    """Otherwise the kiosk reads "ঠিক আছে" back as though it were a symptom, and stores
    it as one when the patient agrees that yes, that is what they said."""
    js = kiosk_js()
    stop = fn_body("stopListening")
    assert "maybeFinishReview(text)" in stop
    assert stop.index("maybeFinishReview(text)") < stop.index("holdForConfirmation(text)")
    del js


def test_it_only_applies_to_the_review_correction_question():
    """A real field question ("what medicines are you taking?") must never be finished by
    an answer that happens to parse as yes — `নেই` there is an ANSWER, not approval."""
    body = fn_body("maybeFinishReview")
    assert "if (!reviewCorrectionOpen()) return false;" in body
    guard = fn_body("reviewCorrectionOpen")
    assert "state.resumeScripted.key === REVIEW_CORRECTION.key" in guard
    assert "state.resumeActive" in guard


def test_only_a_yes_finishes_and_everything_else_reaches_the_normal_pipeline():
    """An ordinary sentence is null and is therefore a real correction — the common case,
    which must be untouched. `no` is deliberately left to that same pipeline too: on THIS
    question it is genuinely unclear, and ending a screening on an unclear signal is the
    one direction that cannot be undone."""
    body = fn_body("maybeFinishReview")
    assert "if (parseConfirmation(text) !== 'yes') return false;" in body


def test_the_finish_goes_through_the_one_guarded_submit():
    """The spoken finish, the tap and the 60-second review clock all pass the SAME
    re-entry guard, so the visit is sent exactly once whichever arrives first — measured:
    three completion phrases in a row produced exactly 1 submit."""
    body = fn_body("maybeFinishReview")
    assert "confirmSubmit();" in body
    assert "api(" not in body, "the spoken finish must not submit on its own"


def test_the_finish_stops_the_microphone_and_the_audio():
    """"Do not continue recording after completion." The turn is already closed by
    stopListening(), so what is left is the mic the question had ARMED to open next."""
    body = fn_body("maybeFinishReview")
    assert "cancelPendingMic();" in body
    assert "ttsCancel();" in body


def test_closing_the_dock_cannot_re_ask_the_question_it_just_answered():
    """setResumeMode(null) runs updateSubmitVisibility(), which re-arms the spoken review
    approval. Without the `submitting` guard the kiosk would speak "is everything
    correct?" over the submit that answer had just triggered — an infinite loop with
    audio. confirmSubmit() sets the flag synchronously, before its first await, which is
    why it is called FIRST."""
    body = fn_body("maybeFinishReview")
    assert body.index("confirmSubmit();") < body.index("setResumeMode(null);")
    vis = fn_body("updateSubmitVisibility")
    assert "if (blocked || submitting) { cancelReviewTimer(); stopReviewConfirmation(); }" in vis


def test_the_correction_pipeline_itself_is_unchanged():
    """The whole point of routing at this seam is that a REAL correction still reaches
    the existing path — read back, then stored as an ordinary utterance, then intake
    re-runs. Measured: 0 submits, the read-back panel open, the words verbatim."""
    body = fn_body("submitResumeAnswer")
    assert "maybeFinishReview" not in body
    assert "parseConfirmation" not in body


def test_the_review_approval_prompt_still_accepts_the_same_words():
    """One vocabulary, two places (ADR-0056). A phrase added for the correction question
    works at "সবকিছু কি ঠিক আছে?" too, because both call the same parser."""
    assert "parseConfirmation(rawText)" in fn_body("applyReviewConfirmation")
    assert "parseConfirmation(rawText)" in fn_body("applySpokenConfirmation")
