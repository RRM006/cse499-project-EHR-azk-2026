"""S1 of ADR-0048 — the follow-up answer contract, for BOTH input modes.

Two guarantees are locked here:

1. **Never silently submit an empty answer** — enforced on the SERVER, not only in
   the browser. Once the kiosk auto-endpoints on silence (step S4) a blank turn
   becomes reachable by accident; it must be rejected before it ever reaches the DB.
2. **Rule #1 — the patient's words are stored EXACTLY as captured.** The blank check
   uses `.strip()` to test emptiness ONLY; it must never rewrite the value.

Schema-level (no DB, no HTTP): FastAPI's ValidationError -> 422 mapping is framework
behaviour and is not re-tested here.
"""

import pytest
from pydantic import ValidationError

from backend.app.schemas.followup import AnswerRequest


@pytest.mark.parametrize("blank", ["", " ", "   ", "\t", "\n", " \t\n "])
def test_blank_answers_are_rejected(blank):
    with pytest.raises(ValidationError):
        AnswerRequest(question_id=1, raw_text=blank)


def test_raw_text_is_kept_byte_for_byte_including_padding():
    """Rule #1: padding is part of the verbatim record — the validator must not trim."""
    raw = "  আমার মাথা ব্যথা করছে  "
    req = AnswerRequest(question_id=1, raw_text=raw)
    assert req.raw_text == raw


def test_a_single_character_answer_is_accepted():
    """Real patients answer 'না'/'হ্যাঁ'. The guard rejects EMPTY, not SHORT."""
    assert AnswerRequest(question_id=1, raw_text="না").raw_text == "না"


def test_voice_and_typing_use_the_same_contract():
    """ADR-0048: one pipeline. Only `source`/`stt_provider` differ — nothing else."""
    spoken = AnswerRequest(
        question_id=1, raw_text="জ্বর তিন দিন", source="mic", stt_provider="browser_webspeech"
    )
    typed = AnswerRequest(
        question_id=1, raw_text="জ্বর তিন দিন", source="manual", stt_provider=None
    )
    assert spoken.raw_text == typed.raw_text
    assert spoken.question_id == typed.question_id
    assert {spoken.source, typed.source} == {"mic", "manual"}


def test_source_must_be_one_of_the_two_known_modes():
    with pytest.raises(ValidationError):
        AnswerRequest(question_id=1, raw_text="ok", source="keyboard")


def test_voice_is_the_default_source():
    """Voice-first: an omitted `source` means the patient spoke."""
    assert AnswerRequest(question_id=1, raw_text="ok").source == "mic"
