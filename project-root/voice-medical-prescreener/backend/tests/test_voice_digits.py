"""F5a (ADR-0053) — a decimal digit is a digit, in either script and either language.

This pins the HALF of F5 that has no microphone in it: the vocabulary. Before this,
the two languages disagreed about a Bangla-digit phone number in opposite directions —

  * **Python** `re.sub(r"\\D", "", ...)` is Unicode-aware, so it KEPT all 11 Bangla
    digits, and the ASCII `startswith("880")` / length checks below it then failed on a
    perfectly valid number -> `ValueError` -> HTTP 400.
  * **JS** `replace(/\\D/g, '')` is ASCII-only, so the same digits were SILENTLY DELETED
    as the patient typed them into an OTP box.

Neither was a strictness decision; both were accidents of a regex escape meaning
different things in the two languages. `to_ascii_digits()` and `asciiDigits()` now fold
every digit to ASCII instead.

Bangla words are written here as `\\u` escapes wherever the test is ABOUT codepoints
(`\\u09df` vs `\\u09af\\u09bc` render identically but are different strings), and
compared under NFC everywhere else — see
test_both_encodings_of_the_ya_phala_words_resolve.

⚠ Scope, stated honestly (the S28 convention, unchanged): the frontend half of this file
is **static-source assertion over the served kiosk.js**. It proves the vocabulary and
the wiring; it cannot prove browser behaviour, and it cannot prove what Chrome's
recogniser returns for a spoken Bangla number — that needs a human at a real mic. The
shipped functions were additionally executed in a real browser engine (no mic required);
see the session notes.
"""

import re
import unicodedata

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.repository_visits import normalize_phone, to_ascii_digits
from backend.app.main import app

BN = "০১২৩৪৫৬৭৮৯"  # Bangla 0-9

PHONE_ASCII = "01715984632"
PHONE_BANGLA = "".join(BN[int(d)] for d in PHONE_ASCII)
EXPECTED = "+8801715984632"

# The ten digit words, as they must be looked up (NFC).
BANGLA_DIGIT_WORDS = [
    "শূন্য",          # shunno   0
    "এক",                            # ek       1
    "দুই",                      # dui      2
    "তিন",                      # tin      3
    "চার",                      # char     4
    "পাঁচ",                # paanch   5
    "ছয়",                      # chhoy    6  (ya + nukta = NFC)
    "সাত",                      # saat     7
    "আট",                            # aat      8
    "নয়",                      # noy      9  (ya + nukta = NFC)
]


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def kiosk_js() -> str:
    resp = TestClient(app).get("/kiosk.js")
    assert resp.status_code == 200
    return resp.text


# --- the server half: normalize_phone accepts what a Bangla speaker produces ---


def test_bangla_digit_phone_was_rejected_and_now_normalizes():
    """The exact defect recorded in current_task.md, as an executable statement."""
    assert normalize_phone(PHONE_BANGLA) == EXPECTED


def test_every_bangla_form_reaches_the_same_patient_key():
    """external_ref IS the patient identity, so two scripts of one number must not
    become two patients."""
    bn_880 = BN[8] + BN[8] + BN[0]
    forms = [
        PHONE_ASCII,
        PHONE_BANGLA,
        bn_880 + PHONE_BANGLA[1:],                  # 880 + 1715984632, all Bangla
        "+" + bn_880 + " " + PHONE_BANGLA[1:],      # +880 with a space
        PHONE_BANGLA[:4] + "-" + PHONE_BANGLA[4:],  # Bangla digits with punctuation
    ]
    assert {normalize_phone(f) for f in forms} == {EXPECTED}


def test_mixed_script_number_is_accepted():
    """A half-typed, half-pasted number is still one number."""
    mixed = PHONE_BANGLA[:5] + PHONE_ASCII[5:]
    assert normalize_phone(mixed) == EXPECTED


def test_ascii_behaviour_is_unchanged():
    """Regression guard: the fix is strictly MORE accepting, never different."""
    assert normalize_phone("01715984632") == EXPECTED
    assert normalize_phone("8801715984632") == EXPECTED
    assert normalize_phone("+880 1715-984632") == EXPECTED


def test_an_invalid_bangla_number_is_still_invalid():
    """Accepting the script must not accept the number — a short code stays a 400."""
    with pytest.raises(ValueError):
        normalize_phone(BN[1] + BN[2] + BN[3])
    with pytest.raises(ValueError):
        normalize_phone(BN[0] + BN[2] + PHONE_BANGLA[2:])  # 02… is not a mobile prefix


def test_to_ascii_digits_ignores_digits_with_no_positional_value():
    """`str.isdigit()` is True for superscript squared — using it would read a '2' out
    of 'm2'. unicodedata.decimal() accepts exactly the Nd category, which is the intent."""
    assert to_ascii_digits("m² ⁵") == ""
    assert to_ascii_digits("abc") == ""
    assert to_ascii_digits(PHONE_BANGLA) == PHONE_ASCII


def test_lookup_route_accepts_a_bangla_number(client):
    """End of the chain: the HTTP 400 the patient used to get is now a 200, and the
    ASCII spelling of the same number finds the patient that Bangla created."""
    r = client.post("/api/patients/lookup", json={"phone": PHONE_BANGLA})
    assert r.status_code == 200, r.text
    assert r.json()["created"] is True
    assert r.json()["patient"]["external_ref"] == EXPECTED

    again = client.post("/api/patients/lookup", json={"phone": PHONE_ASCII})
    assert again.json()["created"] is False


# --- the kiosk half: the shipped spoken-digit vocabulary ---


def shipped_spoken_digits() -> dict[str, str]:
    """Parse SPOKEN_DIGITS out of the served kiosk.js rather than restating it here —
    a copy in the test would drift, and it is the SHIPPED map that has to be right."""
    js = kiosk_js()
    block = js.split("const SPOKEN_DIGITS = {")[1].split("};")[0]
    pairs = re.findall(r"'([^']+)'\s*:\s*'(\d)'", block)
    assert pairs, "SPOKEN_DIGITS parsed empty — has the literal's shape changed?"
    return dict(pairs)


def test_all_ten_bangla_digit_words_are_spoken_vocabulary():
    shipped = shipped_spoken_digits()
    assert [shipped.get(w) for w in BANGLA_DIGIT_WORDS] == [str(i) for i in range(10)]


def test_both_encodings_of_the_ya_phala_words_resolve():
    """`chhoy` (6) and `noy` (9) each have two encodings that RENDER IDENTICALLY —
    precomposed U+09DF, or ya U+09AF + nukta U+09BC — and they are unequal as strings.
    Whichever spelling the recogniser returns must reach the same digit, so the shipped
    keys must be NFC and the lookup must normalise. This file caught it: on the first
    run, written with the precomposed spelling, index 6 read None.

    Note NFC resolves TOWARD the decomposed pair — U+09DF is a Unicode composition
    exclusion — so the NFC form is the two-codepoint one."""
    shipped = shipped_spoken_digits()
    for precomposed, digit in (("ছয়", "6"), ("নয়", "9")):
        nfc = unicodedata.normalize("NFC", precomposed)
        assert precomposed != nfc, "the two spellings must really be different strings"
        assert shipped.get(nfc) == digit, "the shipped keys must be NFC"
        assert precomposed not in shipped, "a non-NFC key could never be hit after the fold"
    # …and the fold itself must be in the shipped tokenizer, or the keys' form is moot.
    # S35 moved the tokenizer into speechTokens(), which digitsFromSpeech() and the new
    # yes/no parser now share — one fold, one split, for every spoken vocabulary.
    lookup = kiosk_js().split("function speechTokens(text) {")[1].split("\n}")[0]
    assert ".normalize('NFC')" in lookup
    assert "for (const token of speechTokens(text))" in kiosk_js()


def test_all_ten_english_digit_words_are_spoken_vocabulary():
    words = ["zero", "one", "two", "three", "four",
             "five", "six", "seven", "eight", "nine"]
    shipped = shipped_spoken_digits()
    assert [shipped.get(w) for w in words] == [str(i) for i in range(10)]


def test_recogniser_spelling_variants_are_covered():
    """These are what the recogniser actually returns — not typos."""
    shipped = shipped_spoken_digits()
    assert shipped.get("শুন্য") == "0"  # shunno, no hoshonto
    assert shipped.get("পাচ") == "5"              # paach, no chandrabindu
    assert shipped.get("oh") == "0"                              # "oh-one-seven…"


# --- S34: the English digit words as a bn-BD recogniser actually writes them ---

# What Chrome returns for spoken English digits when `lang='bn-BD'`: the Bangla
# TRANSLITERATION, not Latin script. Written as literals because that is exactly the
# form that has to be matched.
ENGLISH_DIGITS_AS_BANGLA = [
    "জিরো",      # zero
    "ওয়ান",     # one
    "টু",        # two
    "থ্রি",      # three
    "ফোর",       # four
    "ফাইভ",      # five
    "সিক্স",     # six
    "সেভেন",     # seven
    "এইট",       # eight
    "নাইন",      # nine
]


def test_english_digit_words_are_covered_in_the_script_the_recogniser_returns():
    """S34, and the whole reason a spoken English phone number produced NOTHING.

    The kiosk listens at `lang='bn-BD'` — it must, because every clinical answer is
    Bangla — and a Bangla-language recogniser handed "one two three" does not return
    Latin text. It returns `ওয়ান টু থ্রি`. So the Latin keys in SPOKEN_DIGITS could
    never be hit by a patient speaking English digits ALOUD; they only ever matched
    typed or pasted text. Ten missing entries, not a design decision."""
    shipped = shipped_spoken_digits()
    assert [shipped.get(w) for w in ENGLISH_DIGITS_AS_BANGLA] == [str(i) for i in range(10)]


def test_the_transliterations_are_all_loan_words_not_ordinary_bangla():
    """The safety test for the new keys, and it is the same one every other key passes:
    a mapping is only safe if the word cannot arise in ordinary speech. `ও` — "and",
    "he/she", one of the commonest words in Bangla — is what an English "oh" is
    transliterated to, and it is deliberately NOT mapped: a missed digit is caught by
    the read-back, an INVENTED one reads as correct."""
    shipped = shipped_spoken_digits()
    for ordinary in ("ও", "না", "হ্যাঁ", "আমি", "তিনি", "এটা", "কি"):
        assert ordinary not in shipped, f"{ordinary!r} is ordinary Bangla and would invent a digit"


def test_no_english_homophone_is_mapped_to_a_digit():
    """The dangerous direction. A missed digit shows up in the read-back and the patient
    fixes it; an INVENTED digit reads as correct. 'for the number' must stay four-free."""
    shipped = shipped_spoken_digits()
    for trap in ("to", "too", "for", "fore", "won", "ate", "sex", "tree", "wan"):
        assert trap not in shipped, f"{trap!r} would invent a digit from ordinary speech"


def test_compound_number_words_are_deliberately_absent():
    """egaro (11) / teish (23) are out of scope: a patient reading a phone number says
    single digits, and a compound would silently insert TWO digits."""
    shipped = shipped_spoken_digits()
    assert "এগারো" not in shipped     # egaro = 11
    assert "তেইশ" not in shipped           # teish = 23


def test_spoken_words_are_matched_whole_not_as_substrings():
    """`tini` ('he/she') contains `tin` ('three'). Whole-token lookup is what stops a
    pronoun from becoming a digit, so the tokenising split is part of the contract."""
    js = kiosk_js()
    assert "split(/[^\\p{L}\\p{N}\\p{M}]+/u)" in js
    assert "const word = SPOKEN_DIGITS[token];" in js


def test_the_tokeniser_keeps_combining_marks_inside_a_word():
    """REGRESSION, found by executing the shipped function in a browser rather than by
    any assertion in this file: without `\\p{M}` the split class treated a Bangla word's
    OWN vowel signs as separators and shredded it. The whole eleven-digit sentence
    `shunno ek saat ek paanch noy aat char chhoy tin dui` returned "118" — ek/ek/aat
    being the only three digit words that contain no combining mark.

    The reason is executable, so this proves it rather than asserting it: every one of
    these characters really is category M, which is exactly why the class must list
    \\p{M} alongside \\p{L} and \\p{N}."""
    marks = [
        "ূ",  # BENGALI VOWEL SIGN UU   (shunno)
        "ি",  # BENGALI VOWEL SIGN I    (tin)
        "া",  # BENGALI VOWEL SIGN AA   (char, saat)
        "্",  # BENGALI SIGN VIRAMA     (shunno)
        "়",  # BENGALI SIGN NUKTA      (chhoy, noy)
        "ঁ",  # BENGALI SIGN CANDRABINDU(paanch)
    ]
    assert all(unicodedata.category(ch).startswith("M") for ch in marks)
    assert not any(ch.isalnum() for ch in marks), "so \\p{L}/\\p{N} alone cannot match them"

    # 8 of the 10 Bangla digit words carry such a mark and so depend on this; only
    # `ek` (1) and `aat` (8) do not — which is precisely why the broken tokeniser
    # returned "118" from an eleven-digit sentence instead of returning nothing at all.
    at_risk = [w for w in BANGLA_DIGIT_WORDS
               if any(unicodedata.category(c).startswith("M") for c in w)]
    assert len(at_risk) == 8, "8 of the 10 Bangla digit words contain a combining mark"
    # S35: the split lives in speechTokens(), the ONE tokenizer digitsFromSpeech() and
    # the yes/no parser both call. The rule is unchanged and now covers strictly more:
    # a shredded word would break the confirmation vocabulary the same way.
    assert "\\p{M}" in kiosk_js().split("function speechTokens(text) {")[1][:300]


def test_zero_width_joiners_are_stripped_before_lookup():
    """ZWJ/ZWNJ are invisible and legal inside Bangla text; left in place they would
    break an otherwise exact map hit with no visible cause. Written as escapes in the
    shipped source for the same reason — an invisible literal is unreviewable."""
    js = kiosk_js()
    assert "replace(/[\\u200C\\u200D]/g, '')" in js


# --- the kiosk half: the ASCII-only regex is gone from the digit paths ---


def test_otp_typing_folds_unicode_digits_instead_of_deleting_them():
    js = kiosk_js()
    assert "const digits = asciiDigits(box.value);" in js
    assert "box.value.replace(/\\D/g, '')" not in js


def test_otp_paste_folds_unicode_digits():
    js = kiosk_js()
    assert "const digits = asciiDigits((e.clipboardData || window.clipboardData).getData('text'))" in js
    assert ".getData('text').replace(/\\D/g, '')" not in js


def test_unicode_digit_covers_the_whole_bangla_block():
    """One contiguous range, so the constant plus the two bounds IS the coverage."""
    js = kiosk_js()
    assert "const BN_ZERO = 0x09E6;" in js
    assert "if (code >= BN_ZERO && code <= BN_ZERO + 9) return String(code - BN_ZERO);" in js
    assert "if (code >= 0x30 && code <= 0x39) return String(code - 0x30);" in js


# --- S34: the patient SEES digits, not the words they said ---


def test_the_identification_docks_show_the_digits_the_words_mean():
    """The reported symptom: the screen showed "one two…" where the patient expected
    "1 2…". The transcript SHOULD show what was heard — that is the evidence, and it is
    never rewritten (rule #1). What was missing is the derived reading: the same
    digitsFromSpeech() that will produce the value, rendered live, so the patient can
    check a phone number one digit at a time instead of parsing their own sentence."""
    js = kiosk_js()
    body = js.split("function renderDigitPreview(live) {")[1].split("\n}")[0]
    assert "const digits = digitsFromSpeech(live);" in body
    assert "spacedDigits(digits)" in body                 # '0 1 7 1 5', not '01715'
    assert "renderDigitPreview(live);" in js              # called from r.onresult
    html = TestClient(app).get("/kiosk.html").text
    for element_id in ("phone-digit-preview", "otp-digit-preview"):
        assert f'id="{element_id}"' in html


def test_the_digit_preview_is_display_only_and_never_stored():
    """It is a reading of the utterance, not a replacement for it. Nothing here touches
    the transcript element, an utterance, or the server."""
    body = kiosk_js().split("function renderDigitPreview(live) {")[1].split("\n}")[0]
    for forbidden in ("api(", "dock.transcript", "raw_text"):
        assert forbidden not in body


def test_the_preview_follows_the_language_toggle_like_every_other_number():
    """P1-2 and the F5b read-back's own convention: Bangla numerals under the BN
    toggle. The value that is stored and sent is ASCII either way — phoneFromSpeech()
    and the server's to_ascii_digits() see to that."""
    body = kiosk_js().split("function renderDigitPreview(live) {")[1].split("\n}")[0]
    assert "box.dataset.en = spacedDigits(digits);" in body
    assert "box.dataset.bn = spacedDigits(bnDigits(digits));" in body


def test_the_preview_is_cleared_when_the_turn_ends():
    """A stale digit string under the next question would be a number the patient never
    said, sitting exactly where they were told to check one."""
    js = kiosk_js()
    assert "function clearDigitPreview()" in js
    assert "clearDigitPreview();                                 // S34" in js


def test_phone_from_speech_mirrors_the_server_rule():
    """The kiosk may only PREVIEW the number; the server stays the authority. These are
    normalize_phone()'s own steps, in its order — if one drifts, the read-back would show
    the patient a number the server would then reject."""
    js = kiosk_js()
    body = js.split("function phoneFromSpeech(text) {")[1].split("\n}")[0]
    assert "if (d.startsWith('880')) d = d.slice(3);" in body
    assert "if (d.startsWith('0')) d = d.replace(/^0+/, '');" in body
    assert "if (d.length !== 10 || !d.startsWith('1')) return null;" in body
