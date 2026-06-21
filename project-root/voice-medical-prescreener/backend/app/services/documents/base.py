"""The DocumentWriter interface.

A writer turns one *side* of a session (an ``Utterance``) into the bytes of an
export file. Raw and corrected transcripts are exported as SEPARATE, independently
downloadable files, so ``render`` takes a ``kind`` ("raw" | "corrected"). Today there
is one implementation (.docx via python-docx); a ``PdfWriter`` can be added later
behind the same interface without touching callers.

CONSTITUTION RULE #1: a writer renders the STORED strings as-is. It must reproduce
``raw_text`` verbatim and never edit, paraphrase, or re-correct it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from backend.app.db.models import Utterance

#: Which transcript a document holds. "combined" exists only for legacy rows and is
#: not produced by writers any more.
DocumentKind = Literal["raw", "corrected"]


class DocumentWriter(ABC):
    #: File extension / format key this writer produces (e.g. "docx").
    format: str = ""

    @abstractmethod
    def render(self, utterance: Utterance, *, kind: DocumentKind) -> bytes:
        """Return the file bytes for ``utterance``'s ``kind`` transcript + metadata."""
        raise NotImplementedError
