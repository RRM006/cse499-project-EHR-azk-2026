"""S41 — nothing the patient says may escape the box it is shown in, and the microphone
must say it is open in words.

Found during the human's real-microphone run:

  * the patient's own speech ran OUTSIDE the red transcript card. Bangla and Banglish
    arrive from the recogniser as long runs with few break opportunities, and the box
    had no wrapping rule and no height bound at all;
  * assistant messages were being visually cut;
  * "the microphone is open" was carried by a red mic icon, a pulse, and the sentence
    "Listening...". None of those tell someone who has never used a computer that it is
    their turn to talk.

The properties pinned here are the ones that would regress silently — a CSS rule is easy
to drop in a later edit and nothing on screen announces that a wrap rule is gone until a
patient says something long.

⚠ Rule #1 note: none of this touches what is STORED. The transcript element is a display
of `finalBuffer`; the raw text is unchanged by wrapping, bounding or scrolling it. What
these tests protect is the patient's ability to SEE what the machine believes they said,
which is the only moment they can catch a mis-recognition.
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
    """The page CSS with comments and every @media block removed.

    Comments are stripped FIRST and deliberately: these rules are heavily commented, and
    the prose explains the very declarations being asserted against ("...a flex container
    with `align-items: center`..."). Matching a comment would make a test pass on an
    explanation of the bug rather than on the fix.
    """
    css = kiosk_html().split("<style>")[1].split("</style>")[0]
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)


def rule(selector: str) -> str:
    """The declarations of the rule whose selector is EXACTLY `selector`.

    Anchored at a line start so `.dock-transcript` cannot accidentally return the body of
    the more specific `.voice-dock .dock-transcript` (or vice versa) — they carry
    deliberately different declarations and confusing them would silently invert a test.
    """
    css = top_level_css()
    match = re.search(rf"(?m)^\s*{re.escape(selector)}\s*\{{([^}}]*)\}}", css)
    assert match, f"{selector} has no top-level rule"
    return match.group(1)


# --- 1. the patient's words stay inside their box ------------------------------------


def test_every_dock_transcript_wraps_unbreakable_text():
    """Applies to ALL four docks (phone, OTP, conversation, resume). A spoken phone
    number or a Banglish run has almost no break opportunities, and without this it
    left the card sideways."""
    base = rule(".dock-transcript")
    assert "overflow-wrap: anywhere" in base
    assert "word-break: break-word" in base


def test_the_transcript_can_shrink_inside_its_flex_column():
    """`min-width: 0` is the other half of the same escape: a flex item defaults to
    `min-width: auto` and refuses to go below its content's min-content width."""
    assert "min-width: 0" in rule(".dock-transcript")


def test_the_conversation_transcript_is_bounded_and_scrolls_itself():
    """It GROWS to fit, then STOPS. Without a bound, a long answer pushed the microphone
    and the buttons under it off a short screen."""
    r = rule(".voice-dock .dock-transcript")
    assert "max-height" in r
    assert "overflow-y: auto" in r
    assert "overflow-x: hidden" in r


def test_the_bounded_transcript_is_not_a_flex_centred_box():
    """⚠ MEASURED, and the reason this is a test rather than a comment: a flex container
    with `align-items: center` and overflowing content pushes the TOP of that content
    above the scroll origin, where it cannot be scrolled back to. The patient would lose
    the beginning of their own answer — invisible and unreachable."""
    r = rule(".voice-dock .dock-transcript")
    assert "display: block" in r
    assert "align-items: center" not in r


def test_the_transcript_is_not_shrunk_back_to_its_minimum():
    """It is a flex item in the dock column; the default `flex-shrink: 1` squeezed it to
    its min-height the moment the answer got long, so the patient saw two lines of their
    own sentence while the box had room for six."""
    assert "flex: none" in rule(".voice-dock .dock-transcript")


def test_the_newest_words_are_scrolled_into_view_inside_the_box():
    js = kiosk_js()
    assert "function scrollTranscriptToEnd(" in js
    body = js.split("function scrollTranscriptToEnd(")[1].split("\n}\n")[0]
    assert "scrollTop" in body
    assert "scrollHeight" in body


def test_the_live_write_scrolls_the_box_and_only_the_box():
    """This is the ONE thing that legitimately runs on every recognition result, and it
    is safe precisely because it moves nothing outside the transcript element. A
    page-level scroll here is what makes a kiosk unusable while someone is talking."""
    onresult = kiosk_js().split("r.onresult = (event) => {")[1].split("\n  };")[0]
    assert "scrollTranscriptToEnd(el);" in onresult
    assert "bringIntoView" not in onresult
    assert "scrollIntoView" not in onresult


def test_the_live_words_still_survive_a_language_toggle():
    """Pre-existing (P1-2) and re-asserted because S41 changed this element: the live
    text is mirrored into BOTH language slots, so tapping বাংলা mid-answer cannot
    replace the patient's own words with a placeholder."""
    onresult = kiosk_js().split("r.onresult = (event) => {")[1].split("\n  };")[0]
    assert "el.dataset.en = live;" in onresult
    assert "el.dataset.bn = live;" in onresult


# --- 2. an assistant message is never cut --------------------------------------------


def test_a_chat_bubble_sizes_to_its_content_and_wraps():
    r = rule(".chat-turn")
    assert "overflow-wrap: anywhere" in r
    assert "height: auto" in r
    assert "min-width: 0" in r


def test_no_chat_rule_caps_a_bubble_height():
    """A fixed or capped height is exactly what hides the end of a question. The THREAD
    is the thing that scrolls; a bubble is not."""
    for selector in (".chat-turn", ".chat-turn.ai", ".chat-turn.patient"):
        css = top_level_css()
        if f"{selector} {{" not in css:
            continue
        r = rule(selector)
        assert "max-height" not in r, f"{selector} caps its height and will clip a question"
        assert "overflow: hidden" not in r, f"{selector} clips its own content"
        assert "text-overflow: ellipsis" not in r, f"{selector} truncates a question"


# --- 3. "the microphone is open", in words ------------------------------------------


def test_the_listening_hint_says_the_patient_may_speak_now():
    """Not "Listening..." — that describes the machine. Someone who has never used a
    computer needs to be told what THEY should do, in the first two words."""
    js = kiosk_js()
    assert "🎤 You can speak now" in js
    assert "🎤 এখন কথা বলুন" in js


def test_the_wording_lives_in_one_constant_that_every_dock_reads():
    """One constant, four docks — the phone screen, the OTP screen, the conversation and
    the resume dock. Four copies of the wording is how they start disagreeing."""
    js = kiosk_js()
    assert js.count("You can speak now") == 2, "expected exactly the auto and manual forms"
    assert "function listeningHint()" in js
    assert "LISTENING_HINT[autoVoiceMode() ? 'auto' : 'manual']" in js


def test_listening_is_a_filled_banner_not_only_coloured_text():
    """Colour is never the only carrier of a state a patient must not get wrong."""
    css = kiosk_html()
    block = css.split('body[data-kiosk-state="listening"] #listening-hint,')[1].split("}")[0]
    for other in ("#resume-hint", "#phone-hint", "#otp-hint"):
        assert other in block, f"{other} does not get the open-microphone banner"
    assert "background: var(--danger-color)" in block
    assert "border:" in block
    assert "font-weight: 800 !important" in block


def test_speaking_and_processing_do_not_look_like_listening():
    """The distinction that actually matters across a room: "wait" must not look like
    "talk"."""
    css = kiosk_html()
    assert 'body[data-kiosk-state="speaking"] #listening-hint,' in css
    assert 'body[data-kiosk-state="processing"] #listening-hint,' in css


def test_the_open_microphone_claim_is_retracted_when_listening_stops():
    """The UI must communicate state, never fake it. stopListening() rewrites the hint
    back to the tap-to-start wording in the same call that clears the listening class,
    so the banner can never outlive the open microphone."""
    body = kiosk_js().split("function stopListening(")[1].split("\n}\n")[0]
    assert "classList.remove('listening')" in body
    assert "modeHint(activeDock()).en" in body
    assert body.index("classList.remove('listening')") < body.index("modeHint(activeDock()).en")
