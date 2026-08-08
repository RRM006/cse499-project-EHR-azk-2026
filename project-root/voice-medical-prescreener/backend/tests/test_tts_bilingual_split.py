"""TTS-1 (3.0 cycle) — one question must be HEARD as one question.

The defect: the M7 prompt (`services/followup.py`) asks the model for
`"question": "<Bangla question> (<English question>)"`, so every question is a SINGLE
bilingual string. Handed to a synthesizer whole it is read Bangla-then-English in one
breath, which the human's S29 live listen heard as *"2 question ... at a same time"*.
Pre-existing since S25; ADR-0049 only made it audible.

The fix is TTS-ONLY (the human's decision (a): speak only the half matching the UI
language). These tests defend BOTH halves of that sentence:

  * the SPOKEN string is split, and
  * the STORED utterance and the ON-SCREEN text still carry the full bilingual string
    (rule #1 + ADR-0028 — the on-screen text is the audio fallback, so it must never
    shrink to whatever we happened to speak).

Scope, honestly: per ADR-0048 the frontend tests are static-source assertions — they
prove the wiring, not that Chrome makes a sound. The one exception is the split rule
itself, which is a regex literal; those tests EXTRACT the shipped literal out of the
served tts.js and run it, so the pattern's behaviour is genuinely exercised rather than
asserted about. Only the tiny JS wrapper around it (`spokenHalf`) is mirrored here.
"""

import re

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def tts_js() -> str:
    resp = client.get("/shared/tts.js")
    assert resp.status_code == 200
    return resp.text


def kiosk_js() -> str:
    resp = client.get("/kiosk.js")
    assert resp.status_code == 200
    return resp.text


def shipped_pattern() -> re.Pattern:
    """Compile the regex literal exactly as it ships in frontend_shared/tts.js.

    `/.../` → the source between the slashes. The pattern uses only constructs whose
    meaning is identical in JS and Python (`\\uXXXX` escapes, character classes, `\\s`,
    anchors), which is why this round-trip is trustworthy.
    """
    literal = tts_js().split("const BILINGUAL_QUESTION =")[1].strip().splitlines()[0].strip()
    assert literal.startswith("/") and literal.endswith("/;")
    return re.compile(literal[1:].rsplit("/", 1)[0])


def spoken_half(text: str, short: str) -> str:
    """The 3-line JS wrapper, mirrored. The RULE it applies is the shipped regex above."""
    m = shipped_pattern().match(text)
    if not m:
        return text
    return (m.group(1) if short == "bn" else m.group(2)).strip() or text


BILINGUAL = "আপনার জ্বর কত দিন ধরে? (How many days have you had the fever?)"
BANGLA_HALF = "আপনার জ্বর কত দিন ধরে?"
ENGLISH_HALF = "How many days have you had the fever?"


# --------------------- the split rule (the actual defect) ---------------------

def test_a_bangla_patient_hears_only_the_bangla_half():
    assert spoken_half(BILINGUAL, "bn") == BANGLA_HALF


def test_an_english_patient_hears_only_the_english_half():
    assert spoken_half(BILINGUAL, "en") == ENGLISH_HALF


def test_neither_half_leaks_the_other_language():
    """This is the defect verbatim: two languages in one breath sound like two
    questions. Whichever half is spoken, the other must be absent."""
    assert ENGLISH_HALF not in spoken_half(BILINGUAL, "bn")
    assert BANGLA_HALF not in spoken_half(BILINGUAL, "en")


def test_a_banglish_question_still_splits_on_the_trailing_parenthesis():
    """Patients mix languages, and so do the questions derived from them — a Latin word
    in the Bangla half must not defeat the split."""
    text = "আপনার fever কত দিন ধরে? (How many days of fever?)"
    assert spoken_half(text, "bn") == "আপনার fever কত দিন ধরে?"
    assert spoken_half(text, "en") == "How many days of fever?"


# --------------------- when in doubt, say everything ---------------------
# The failure mode of a splitter is speaking LESS than the question. Every shape that is
# not unambiguously "<Bangla> (<English>)" must fall through and be spoken whole.

def test_a_monolingual_english_question_with_a_parenthetical_is_never_trimmed():
    text = "Do you have a fever (temperature above 100F)"
    assert spoken_half(text, "en") == text
    assert spoken_half(text, "bn") == text


def test_a_trailing_parenthetical_that_is_not_at_the_very_end_is_not_a_split():
    text = "How severe is the pain (1-10)?"
    assert spoken_half(text, "en") == text


def test_a_bangla_parenthetical_is_not_mistaken_for_an_english_half():
    text = "আপনার কি জ্বর আছে (জ্বরের মাত্রা)"
    assert spoken_half(text, "bn") == text
    assert spoken_half(text, "en") == text


def test_nested_parentheses_fall_back_to_the_whole_string():
    """Ambiguous input must lose seconds, never words."""
    text = "আপনার ব্যথা কত? (On a scale of 1-10 (worst), how bad?)"
    assert spoken_half(text, "bn") == text


def test_a_plain_question_is_untouched():
    for text in ("আপনার নাম কি?", "Please tell me more about that."):
        assert spoken_half(text, "bn") == text
        assert spoken_half(text, "en") == text


def test_an_empty_half_never_reaches_a_provider():
    """`()` at the end must not silence the question."""
    js = tts_js()
    half = js.split("function spokenHalf(text, short)")[1].split("function _pickVoice")[0]
    assert "return half || text;" in half


# --------------------- both providers speak the SAME half ---------------------

def test_the_browser_voice_speaks_the_split_half():
    js = tts_js()
    assert "new SpeechSynthesisUtterance(speech)" in js
    assert "new SpeechSynthesisUtterance(text)" not in js


def test_the_server_provider_speaks_the_split_half_too():
    """/api/tts must receive the same string the browser path would have spoken —
    otherwise Windows (where the server path is the ONLY Bangla route, ADR-0049) keeps
    the exact defect this fixes."""
    js = tts_js()
    assert "encodeURIComponent(speech)" in js
    assert "encodeURIComponent(text)" not in js


def test_the_split_is_applied_once_at_the_single_entry_point():
    js = tts_js()
    assert "const speech = verbatim ? text : spokenHalf(text, short);" in js


# --------------------- what must NOT change (rule #1 + ADR-0028) ---------------------

def test_the_stored_system_utterance_is_still_the_full_bilingual_string():
    """followup.py stores `question_text` verbatim and the kiosk records the displayed
    text. If the split ever migrated into the recording path, the medic/doctor record
    would silently lose a language."""
    js = kiosk_js()
    says = js.split("async function assistantSays(")[1].split("function repeatQuestion")[0]
    assert "raw_text: text" in says          # the displayed string, not the spoken half
    assert "spokenHalf" not in says


def test_the_on_screen_bubble_still_shows_the_full_bilingual_string():
    """ADR-0028 makes the on-screen text the fallback for anyone who cannot hear the
    audio; it must stay bilingual even though only one language is spoken."""
    js = kiosk_js()
    add_bubble = js.split("function addBubble(")[1].split("function setBilingualText")[0]
    assert "body.textContent = text;" in add_bubble
    assert "spokenHalf" not in add_bubble


def test_the_split_is_frontend_only_and_the_m7_contract_is_unchanged():
    """Fixing this server-side would change what medic/doctor display and what is
    stored — a much bigger change the human did not authorise."""
    from backend.app.services import followup

    assert "<Bangla question> (<English question>)" in followup._QUESTION_SYSTEM


def test_a_patient_bubble_is_replayed_verbatim():
    """The patient's OWN captured words are not an AI question. Reading back only part
    of what someone said is a rule #1 defect, so that path opts out of the split."""
    js = kiosk_js()
    assert "verbatim: role === 'patient'" in js


# --------------------- S1-S4 must be unaffected ---------------------

def test_the_echo_guard_predicate_is_untouched():
    """ADR-0049: reverting `ttsSpeaking()` reopens the echo hole. The TTS-1 edit sits in
    the same file, so this stays asserted here too."""
    guard = kiosk_js().split("function openMicWhenQuiet(token)")[1].split("function setInputMode")[0]
    assert "ttsSpeaking()" in guard
    assert "speechSynthesis.speaking" not in guard


def test_the_generation_token_still_gates_the_split_path():
    """S3's token must still fire `onend` at most once and never for a superseded
    question — the mic opening depends on it."""
    js = tts_js()
    finish = js.split("const finish = ()")[1].split("};")[0]
    assert "generation !== _speechGeneration" in finish
    assert "fired" in finish


def test_auto_listen_still_arms_from_the_full_question_length():
    """askAloud's safety-net timeout is sized from the DISPLAYED text. That is
    deliberate: over-waiting is harmless, opening the mic early is a rule #1 defect."""
    js = kiosk_js()
    ask = js.split("function askAloud(text)")[1].split("function openMicWhenQuiet")[0]
    assert "text.length * 80" in ask
    assert "speak(text, { onend: () => openMicWhenQuiet(token) })" in ask
