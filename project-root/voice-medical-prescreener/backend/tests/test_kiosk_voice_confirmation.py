"""S35 / Findings 2 + 7 (ADR-0056) — saying YES or NO out loud.

S34 gave the patient a read-back and two buttons. The buttons are the problem: the
target patient may not know what a mouse is, and the whole voice-first premise
(ADR-0048) collapses at the one moment they are asked to approve their own medical
record. So the confirmation is now answered by speaking, and the buttons stay as the
accessibility fallback.

The risk this creates is **asymmetric**, and that asymmetry is what shapes the design:

  * a confirmation that is MISSED costs the patient one repeat;
  * a confirmation INVENTED out of ordinary speech silently stores an answer they were
    trying to correct, or submits a whole pre-screening they had not approved.

So `parseConfirmation()` is explicit and conservative: an utterance is only a verdict
when EVERY word in it is one the vocabulary knows, and where a YES word and a negation
both appear, NO wins. Anything else is `null` — ask again, never guess.

⚠ Scope, stated honestly (the S28 convention): static-source assertions over the served
kiosk.js, plus the shipped `parseConfirmation()` executed against real utterances in a
browser engine (see the session notes). **No microphone was used**, so what a real
`bn-BD` recogniser returns for a spoken "হ্যাঁ" is still unproven — that is the live run.
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


def shipped_set(name: str) -> set[str]:
    """Parse a vocabulary OUT of the served kiosk.js rather than restating it here —
    a copy in the test would drift, and it is the SHIPPED set that has to be right."""
    js = kiosk_js()
    block = js.split(f"const {name} = new Set([")[1].split("]);")[0]
    words = set(re.findall(r"'([^']+)'", block))
    assert words, f"{name} parsed empty — has the literal's shape changed?"
    return words


# --- the vocabulary the human asked for, word by word ---


def test_every_requested_yes_word_is_accepted():
    """হ্যাঁ · জি · ঠিক আছে · ঠিক · yes · okay — the human's list, verbatim.
    ("ঠিক আছে" is two tokens: `ঠিক` carries it and `আছে` is filler.)"""
    yes = shipped_set("CONFIRM_YES")
    for word in ("হ্যাঁ", "জি", "ঠিক", "yes", "okay", "ok"):
        assert word in yes, f"{word!r} must be understood as YES"
    assert "আছে" in shipped_set("CONFIRM_FILLER"), '"ঠিক আছে" needs আছে to be neutral'


def test_every_requested_no_word_is_accepted():
    """না · ঠিক নাই · ঠিক না · ভুল · আবার বলি · no — again the human's list.
    `নাই`/`নেই` are what "ঠিক নাই" is built from; `আবার`+`বলি` are how a patient
    rejects without ever using the word "না"."""
    no = shipped_set("CONFIRM_NO")
    for word in ("না", "নাই", "ভুল", "আবার", "বলি", "no"):
        assert word in no, f"{word!r} must be understood as NO"


def test_the_two_vocabularies_do_not_overlap():
    """A word in both sets would make its verdict depend on the order of the checks."""
    assert not (shipped_set("CONFIRM_YES") & shipped_set("CONFIRM_NO"))
    assert not (shipped_set("CONFIRM_YES") & shipped_set("CONFIRM_FILLER"))
    assert not (shipped_set("CONFIRM_NO") & shipped_set("CONFIRM_FILLER"))


def test_no_ordinary_bangla_word_is_a_verdict():
    """The dangerous direction. These are words a patient uses while ANSWERING, and any
    of them mapped to a verdict would turn a real answer into an approval."""
    vocabulary = (shipped_set("CONFIRM_YES") | shipped_set("CONFIRM_NO")
                  | shipped_set("CONFIRM_FILLER"))
    for ordinary in ("ব্যথা", "আমার", "পেটে", "মাথা", "জ্বর", "ওষুধ", "ডাক্তার",
                     "দিন", "তিন", "বছর", "pain", "fever", "head", "doctor"):
        assert ordinary not in vocabulary, f"{ordinary!r} would turn an answer into a verdict"


def test_the_filler_list_is_deliberately_short():
    """Every filler entry widens what counts as a confirmation, and the whole safety of
    this scheme is that an unknown word makes the utterance ambiguous."""
    assert len(shipped_set("CONFIRM_FILLER")) <= 24


# --- the two rules that make it safe ---


def test_an_unknown_word_makes_the_whole_utterance_ambiguous():
    """This is the direct answer to "do not assume that every sentence containing না
    means NO": a patient who is TALKING rather than confirming gets asked again, and
    nothing is decided for them."""
    body = fn_body("parseConfirmation")
    assert "if (CONFIRM_FILLER.has(token)) continue;" in body
    assert "return null;   // an ordinary word" in body
    assert body.index("CONFIRM_FILLER.has(token)") < body.index("return null;   // an ordinary word")


def test_where_both_appear_no_wins():
    """`ঠিক নাই` and `ঠিক না` are a YES word plus a negation. Reading them as agreement
    would store an answer the patient had just rejected."""
    body = fn_body("parseConfirmation")
    assert "if (no) return 'no';" in body
    assert "return yes ? 'yes' : null;" in body
    assert body.index("if (no) return 'no';") < body.index("return yes ?")


def test_an_empty_utterance_is_never_a_verdict():
    """Silence must not be agreement — the same rule S34 established for answers."""
    assert "if (!tokens.length) return null;" in fn_body("parseConfirmation")


def test_the_parser_reuses_the_one_speech_tokenizer():
    """`তিনি` contains `তিন`; the same whole-word, NFC-folded tokenizer that stops a
    pronoun becoming a digit stops one becoming a verdict. There is ONE tokenizer."""
    assert "function speechTokens(text) {" in kiosk_js()
    assert "const tokens = speechTokens(text);" in fn_body("parseConfirmation")
    assert "for (const token of speechTokens(text))" in fn_body("digitsFromSpeech")


# --- routing: a verdict is never stored as an answer ---


def test_speech_during_a_read_back_is_routed_as_a_verdict():
    """If it were not, the word "হ্যাঁ" would be POSTed as the patient's symptom — and
    the answer they were confirming would still be sitting unsent."""
    stop = fn_body("stopListening")
    assert "else if (state.pendingAnswer) applySpokenConfirmation(text);" in stop
    # …checked BEFORE the clinical branches, and AFTER identification (which owns its own
    # confirmation and runs before a visit even exists).
    assert stop.index("applySpokenOtp") < stop.index("applySpokenConfirmation")
    assert stop.index("applySpokenConfirmation") < stop.index("holdForConfirmation")
    assert stop.index("applySpokenConfirmation") < stop.index("submitPatientTurn")


def test_yes_and_no_reuse_the_existing_button_handlers():
    """One confirmation mechanism, two ways to reach it. A separate voice path would be
    a second pipeline that could drift out of step with the buttons."""
    body = fn_body("applySpokenConfirmation")
    assert "if (verdict === 'yes') { acceptAnswer(); return; }" in body
    assert "if (verdict === 'no') { rejectAnswer(); return; }" in body
    assert "api(" not in body, "the verdict handler must not talk to the server itself"


def test_an_ambiguous_verdict_asks_the_confirmation_again_and_stores_nothing():
    """Not the answer again — the patient has already heard their own words. The pending
    answer stays on screen and stays unsent."""
    body = fn_body("applySpokenConfirmation")
    assert "showError(" in body
    assert "askConfirmationAloud();" in body
    assert "acceptAnswer" not in body.split("verdict === 'no'")[1], \
        "the ambiguous path must not fall through to accepting"
    assert "hideAnswerConfirm" not in body, "an ambiguous reply must not drop the answer"


def test_a_typing_patient_is_not_spoken_at():
    """Same rule as every other re-ask in this kiosk (F5b, S34): someone who chose the
    keyboard has the buttons in front of them and is left alone."""
    body = fn_body("applySpokenConfirmation")
    assert "if (state.inputMode === 'voice') askConfirmationAloud();" in body


def test_opening_the_mic_no_longer_clears_the_pending_answer():
    """THE defect this wiring would otherwise have. S34 cleared the read-back whenever
    listening started ("speaking again means say-it-again"). With voice confirmation the
    mic opens precisely IN ORDER to hear the verdict, so that line would have dropped
    `state.pendingAnswer` a moment before the word "হ্যাঁ" arrived — and the verdict
    would have been stored as the patient's symptom."""
    body = fn_body("toggleListening")
    # comments stripped: the block left in place deliberately NAMES the call it removed
    code = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    assert "hideAnswerConfirm()" not in code
    assert "S35 (ADR-0056) REMOVED" in body   # …and says so, so it is not quietly re-added


# --- what the patient is told ---


def test_the_prompt_names_the_two_words_out_loud():
    """A question the patient MAY answer aloud, but does not know they may, is a
    question they will hunt for a button for."""
    js = kiosk_js()
    assert "'এটা কি ঠিক আছে? হ্যাঁ বলুন অথবা না বলুন।'" in js
    assert "'Is this correct? Say yes, or say no.'" in js


def test_the_panel_presents_speaking_as_the_primary_action():
    html = kiosk_html()
    assert 'data-bn="🎤 শুধু বলুন “হ্যাঁ” অথবা “না”"' in html
    # One per clinical dock, PLUS the phone read-back, which reuses the same class for
    # its own "it will send by itself" line — three in total, one per confirmation the
    # patient can be asked for.
    assert html.count('class="confirm-say"') == 3
    assert 'id="phone-confirm-hint"' in html
    # …and the buttons are still there as the fallback (accessibility, not instruction)
    assert html.count('onclick="acceptAnswer()"') == 2
    assert html.count('onclick="rejectAnswer()"') == 2


def test_the_not_understood_message_is_bilingual_and_says_what_to_do():
    js = kiosk_js()
    assert "Sorry — please say yes, or say no." in js
    assert "অনুগ্রহ করে \"হ্যাঁ\" বলুন অথবা \"না\" বলুন।" in js
