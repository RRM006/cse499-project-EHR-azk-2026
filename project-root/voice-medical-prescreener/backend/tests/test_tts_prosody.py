"""S35 / Finding 6 — pacing the text before a synthesizer reads it.

⚠ READ THIS BEFORE BELIEVING ANY OF IT. **Acoustic quality cannot be tested here and is
not claimed here.** Nothing in this file listens to anything. What it proves is that the
text handed to the engine is punctuated for speech, that this happens once for every
provider, and — the part that actually matters for safety — that it can never change a
WORD, because the kiosk's read-back sends the patient's own captured words down this
same path (ADR-0055). Whether the result *sounds* more natural is a human listening
judgement and belongs in the live run, not in a green tick.

Two things are also NOT claimed: that edge-tts's neural voice is a human (it is not),
and that the pitch/volume knobs improve naturalness (they are neutral by default and
exist for a noisy room or a hard-of-hearing patient).
"""

import pytest

from backend.app.core.config import get_settings
from backend.app.services.tts import service as tts_service
from backend.app.services.tts.base import TtsProvider, TtsUnavailable
from backend.app.services.tts.prosody import speech_text

BN_QUESTION = "আপনার ব্যথা কতদিন ধরে হচ্ছে"
EN_QUESTION = "How long have you had this pain"


# --- the two prosodic cues ---


@pytest.mark.parametrize(
    ("text", "lang", "expected"),
    [
        (BN_QUESTION, "bn", BN_QUESTION + "।"),        # Bangla gets a danda
        (EN_QUESTION, "en", EN_QUESTION + "."),        # English gets a full stop
        ("আপনার কি জ্বর আছে?", "bn", "আপনার কি জ্বর আছে?"),   # already terminated: untouched
        ("Do you have a fever?", "en", "Do you have a fever?"),
        ("ব্যথা আছে।", "bn", "ব্যথা আছে।"),
    ],
)
def test_a_bare_clause_gains_a_sentence_ending(text, lang, expected):
    """`spokenHalf()` strips the English half off an M7 question and routinely leaves no
    terminator at all. Every engine then reads the line flat and stops mid-breath."""
    assert speech_text(text, lang) == expected


def test_an_implied_pause_becomes_a_real_one():
    """This project's own strings use em dashes and ellipses as pauses — "Listening —
    just stop speaking", "Say the digits one at a time...". No engine pauses on either."""
    assert speech_text("শুনছি — বলা শেষ হলে থেমে যান", "bn") == "শুনছি, বলা শেষ হলে থেমে যান।"
    assert speech_text("Listening... please speak now", "en") == "Listening, please speak now."
    assert speech_text("এক — দুই -- তিন", "bn") == "এক, দুই, তিন।"


def test_a_newline_does_not_restart_the_intonation():
    """A run of spaces is silent, but a newline mid-question makes some engines begin a
    fresh sentence contour as though a new sentence had started."""
    assert speech_text("আপনার নাম\n   কী?", "bn") == "আপনার নাম কী?"


def test_a_dangling_or_doubled_comma_is_never_produced():
    """", ।" is heard as a stumble, which is the opposite of the point."""
    assert speech_text("ঠিক আছে —", "bn") == "ঠিক আছে।"
    assert speech_text("ব্যথা — ।", "bn") == "ব্যথা।"
    assert speech_text("okay...", "en") == "okay."


@pytest.mark.parametrize("empty", ["", "   ", None, "—", "..."])
def test_nothing_is_invented_out_of_nothing(empty):
    """An empty or punctuation-only line must stay empty, so the provider's own
    "refusing to synthesize empty text" guard still fires instead of being handed a
    lone full stop to read aloud."""
    assert speech_text(empty, "bn") == ""


# --- the safety property: words are never touched ---


@pytest.mark.parametrize("lang", ["bn", "en"])
@pytest.mark.parametrize(
    "spoken",
    [
        "আমার তিন দিন ধরে পেটে ব্যথা হচ্ছে",
        "মাথা ঘোরে আর বমি বমি ভাব লাগে",
        "I have had a headache for three days",
        "০১৭১৫ ৯৮৪৬৩২",
        "না নেই",
    ],
)
def test_no_word_is_changed_added_removed_or_reordered(spoken, lang):
    """THE rule. The kiosk read-back speaks the PATIENT's own captured words through this
    path (ADR-0055); a "helpful" rewrite there would read back something they never said.
    Compared on WORDS, so the added terminator is allowed and nothing else is."""
    result = speech_text(spoken, lang)
    stripped = result.rstrip("।.")
    assert stripped.split() == spoken.split()


def test_the_patient_read_back_path_survives_a_transcript_with_no_punctuation():
    """A recogniser returns no punctuation at all, which is exactly the flat-reading
    case this exists for — and exactly where a rewrite would be most tempting."""
    raw = "আমার পেটে ব্যথা আর বমি বমি ভাব তিন দিন ধরে"
    assert speech_text(raw, "bn") == raw + "।"


# --- it happens ONCE, for every provider ---


class _Recorder(TtsProvider):
    name = "recorder"
    media_type = "audio/wav"

    def __init__(self, fail: bool = False) -> None:
        self.seen: list[tuple[str, str]] = []
        self._fail = fail

    def synthesize(self, text: str, lang: str) -> bytes:
        self.seen.append((text, lang))
        if self._fail:
            raise TtsUnavailable("primary down")
        return b"x" * 2048


def test_every_provider_receives_the_same_paced_line(monkeypatch):
    """Paced in the SERVICE, not in a provider: the fallback must not read a different
    line from the primary, and a future provider must not have to remember to do this."""
    primary, fallback = _Recorder(fail=True), _Recorder()
    monkeypatch.setattr(tts_service, "get_provider", lambda: primary)
    monkeypatch.setattr(tts_service, "get_fallback_provider", lambda _p: fallback)

    tts_service.synthesize(BN_QUESTION, "bn")

    assert primary.seen == [(BN_QUESTION + "।", "bn")]
    assert fallback.seen == primary.seen


def test_pacing_does_not_bypass_the_language_guard(monkeypatch):
    """The unsupported-language check must still fire BEFORE any text handling."""
    monkeypatch.setattr(tts_service, "get_provider", lambda: _Recorder())
    with pytest.raises(TtsUnavailable):
        tts_service.synthesize(BN_QUESTION, "fr")


# --- the conservative voice knobs ---


def test_pitch_and_volume_default_to_neutral():
    """Deliberately neutral. The naturalness claim rests on ADR-0050's neural voice, not
    on prosody tuning — and a mis-tuned pitch is how an assistant starts sounding like a
    cartoon. These exist for a noisy room or a hard-of-hearing patient."""
    settings = get_settings()
    assert settings.tts_edge_pitch == "+0Hz"
    assert settings.tts_edge_volume == "+0%"


def test_the_knobs_actually_reach_the_engine(monkeypatch):
    """A setting that is read but never passed through is worse than no setting."""
    from backend.app.services.tts.edge import EdgeTtsProvider

    provider = EdgeTtsProvider(rate="-10%", pitch="-2Hz", volume="+6%")
    captured = {}

    class FakeCommunicate:
        def __init__(self, text, voice, **kwargs):
            captured.update(text=text, voice=voice, **kwargs)

        async def stream(self):
            yield {"type": "audio", "data": b"y" * 2048}

    import sys
    import types

    fake = types.ModuleType("edge_tts")
    fake.Communicate = FakeCommunicate
    monkeypatch.setitem(sys.modules, "edge_tts", fake)

    provider.synthesize(BN_QUESTION, "bn")
    assert captured["rate"] == "-10%"
    assert captured["pitch"] == "-2Hz"
    assert captured["volume"] == "+6%"
    assert captured["voice"] == "bn-BD-NabanitaNeural"


def test_the_bangla_voice_is_still_a_bangladeshi_neural_voice():
    """bn-IN-* exists and is Indian Bengali — a different accent for a Dhaka clinic."""
    settings = get_settings()
    assert settings.tts_edge_voice_bn.startswith("bn-BD-")
    assert settings.tts_edge_voice_bn.endswith("Neural")
