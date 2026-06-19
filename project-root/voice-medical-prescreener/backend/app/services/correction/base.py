"""The Corrector interface.

Module 2 (text correction) is intentionally pluggable: today it is one free LLM
behind an OpenAI-compatible API, tomorrow it could be a different provider or a
local model. Everything else in the app depends only on this small interface, so
swapping the implementation never ripples outward.

CONSTITUTION RULE #1: a Corrector receives the raw text and returns a SEPARATE
corrected string. It must never be wired to overwrite the stored raw transcript.
"""

from abc import ABC, abstractmethod


class Corrector(ABC):
    """Turns a raw Bangla / Banglish / Roman-Bangla utterance into a corrected one."""

    @abstractmethod
    def correct(self, raw_text: str) -> str:
        """Return a corrected version of ``raw_text``.

        Implementations must NOT add, remove, translate away, or infer meaning —
        spelling/grammar only. The returned value is a new string; the caller is
        responsible for storing it in a separate field from the raw text.
        """
        raise NotImplementedError
