"""The DocumentWriter interface.

A writer turns a completed session (an ``Utterance``) into the bytes of an export
file in one format. Today there is one implementation (.docx via python-docx); a
``PdfWriter`` can be added later behind the same interface without touching callers.

CONSTITUTION RULE #1: a writer renders the STORED strings as-is. It must reproduce
``raw_text`` verbatim and never edit, paraphrase, or re-correct it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.db.models import Utterance


class DocumentWriter(ABC):
    #: File extension / format key this writer produces (e.g. "docx").
    format: str = ""

    @abstractmethod
    def render(self, utterance: Utterance) -> bytes:
        """Return the file bytes for ``utterance`` (raw + corrected + metadata)."""
        raise NotImplementedError
